import json
import httpx
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.auth import identity, Account
from app.cloud_storage import AccountStorage
from app.llm import OllamaLLM
from app.models import LLMUnavailableError

USER = '11111111-1111-4111-8111-111111111111'

@pytest.fixture
def remote(monkeypatch):
    real_client = httpx.Client
    monkeypatch.setenv('SUPABASE_URL','https://accounts.example')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY','public-test-key')
    def install(handler):
        monkeypatch.setattr(httpx, 'Client', lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    return install

@pytest.mark.parametrize('user', [
    {'id':USER},
    {'id':USER,'email_confirmed_at':'today','is_anonymous':True},
])
def test_auth_rejects_unverified_and_anonymous(remote, user):
    remote(lambda r: httpx.Response(200,json=user))
    with pytest.raises(HTTPException) as e:
        identity(HTTPAuthorizationCredentials(scheme='Bearer',credentials='token'))
    assert e.value.status_code==401

def test_auth_validates_with_server_and_uses_only_verified_id(remote):
    def handler(r):
        assert str(r.url)=='https://accounts.example/auth/v1/user'
        assert r.headers['Authorization']=='Bearer opaque-user-token'
        assert r.headers['apikey']=='public-test-key'
        return httpx.Response(200,json={'id':USER,'email_confirmed_at':'today'})
    remote(handler)
    account=identity(HTTPAuthorizationCredentials(scheme='Bearer',credentials='opaque-user-token'))
    assert account.id==USER
    assert 'opaque-user-token' not in repr(account)

@pytest.mark.parametrize('status', [401,403,500])
def test_auth_failures_are_safe(remote,status):
    remote(lambda r: httpx.Response(status,json={'message':'internal-secret'}))
    with pytest.raises(HTTPException) as e:
        identity(HTTPAuthorizationCredentials(scheme='Bearer',credentials='token'))
    assert e.value.status_code==(401 if status in (401,403) else 503)
    assert 'internal-secret' not in e.value.detail

def test_missing_auth_config_fails_closed(monkeypatch):
    monkeypatch.delenv('SUPABASE_URL',raising=False)
    with pytest.raises(HTTPException) as e:
        identity(HTTPAuthorizationCredentials(scheme='Bearer',credentials='token'))
    assert e.value.status_code==503

def test_storage_forwards_user_token_and_filters_every_read_delete(remote):
    methods=[]
    def handler(r):
        assert r.headers['authorization']=='Bearer user-jwt'
        assert r.headers['apikey']=='public-test-key'
        assert r.url.path=='/rest/v1/nova_records'
        methods.append(r.method)
        if r.method=='POST':
            assert json.loads(r.content)['user_id']==USER
            return httpx.Response(201)
        assert r.url.params['user_id']=='eq.'+USER
        if r.method=='GET':
            assert r.url.params['limit']=='100'
            return httpx.Response(200,json=[{'payload':{'content':'new'}},{'payload':{'content':'old'}}])
        return httpx.Response(204)
    remote(handler)
    storage=AccountStorage(Account(USER,'user-jwt'))
    storage.remember('hello')
    assert storage.read('memories',1000)==[{'content':'old'},{'content':'new'}]
    storage.clear()
    assert methods==['POST','GET','DELETE']

def test_storage_failure_does_not_look_like_empty_history(remote):
    remote(lambda r: httpx.Response(500,text='private detail'))
    with pytest.raises(HTTPException) as e:
        AccountStorage(Account(USER,'token')).read('messages',100)
    assert e.value.status_code==503
    assert 'private detail' not in e.value.detail

@pytest.fixture
def llm_config(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER','compatible')
    monkeypatch.setenv('LLM_BASE_URL','https://model.example/v1')
    monkeypatch.setenv('LLM_API_KEY','private-model-key')
    monkeypatch.setenv('CHAT_MODEL','test-chat')
    monkeypatch.delenv('REASONING_MODEL',raising=False)

def test_hosted_chat_and_codegen_use_configured_model(remote,llm_config):
    def handler(r):
        assert str(r.url)=='https://model.example/v1/chat/completions'
        assert r.headers['authorization']=='Bearer private-model-key'
        payload=json.loads(r.content)
        assert payload['model']=='test-chat'
        assert payload['max_tokens']==1200
        return httpx.Response(200,json={'choices':[{'message':{'content':'print("hello")'}}]})
    remote(handler)
    assert OllamaLLM(None).generate_python('hello')=='print("hello")\n'

@pytest.mark.parametrize('payload',[{'choices':[]},{'choices':[{'message':{'content':None}}]},{'choices':[{'message':{'content':''}}]}])
def test_invalid_provider_responses_are_handled(remote,llm_config,payload):
    remote(lambda r: httpx.Response(200,json=payload))
    with pytest.raises(LLMUnavailableError): OllamaLLM(None)._chat([])

@pytest.mark.parametrize('status',[401,429,500])
def test_provider_errors_do_not_expose_secrets(remote,llm_config,status):
    remote(lambda r: httpx.Response(status,text='private-model-key'))
    with pytest.raises(LLMUnavailableError) as e: OllamaLLM(None)._chat([])
    assert 'private-model-key' not in str(e.value)

def test_missing_model_config_does_not_call_localhost(remote,monkeypatch):
    for name in ['LLM_PROVIDER','LLM_API_KEY','CHAT_MODEL']:
        monkeypatch.delenv(name,raising=False)
    def handler(r): raise AssertionError('Must not make network request')
    remote(handler)
    with pytest.raises(LLMUnavailableError,match='setup is incomplete'): OllamaLLM(None)._chat([])
