import os
from uuid import uuid4
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app, limits
from app.llm import OllamaLLM
from app.storage import LocalStorage

client = TestClient(app)
accounts = {}
real_client = httpx.Client

@pytest.fixture(autouse=True)
def account_services(monkeypatch, tmp_path):
    limits.clear()
    accounts.clear()
    monkeypatch.setenv('SUPABASE_URL', 'https://accounts.example')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY', 'test-public-key')
    def auth_server(request):
        token = request.headers.get('authorization', '').removeprefix('Bearer ')
        if token not in accounts:
            return httpx.Response(401, json={'message':'expired or invalid'})
        return httpx.Response(200, json={'id':accounts[token], 'email_confirmed_at':'2026-09-22T00:00:00Z'})
    monkeypatch.setattr(httpx, 'Client', lambda **kw: real_client(transport=httpx.MockTransport(auth_server), **kw))
    monkeypatch.setattr('app.main.AccountStorage', lambda account: LocalStorage(str(tmp_path/'data.db'), account.id))

def session(user_id=None):
    token = str(uuid4())
    accounts[token] = user_id or str(uuid4())
    return {'Authorization':'Bearer '+token}
def ask(headers,text): return client.post('/api/chat',headers=headers,json={'text':text}).json()

def test_auth_and_limits():
    assert client.post('/api/chat',json={'text':'hello'}).status_code in (401,403)
    assert client.post('/api/session',json={'access_code':'old-code'}).status_code==404
    assert client.post('/api/chat',headers={'Authorization':'Bearer forged'},json={'text':'hi'}).status_code==401
    h=session()
    for _ in range(15): assert client.post('/api/chat',headers=h,json={'text':'hi'}).status_code==200
    assert client.post('/api/chat',headers=h,json={'text':'hi'}).status_code==429

def test_math_and_actions():
    h=session()
    assert ask(h,'calculate 12 times 7')['text']=='The answer is 84.'
    assert 'zero' in ask(h,'calculate 1 / 0')['text']
    result=ask(h,'search google for cats & dogs')
    assert result['action']['url']=='https://www.google.com/search?q=cats+%26+dogs'
    assert ask(h,'open terminal')['action'] is None
    assert ask(h,'open javascript:alert(1)')['action'] is None

def test_storage_isolation_and_deletion():
    a,b=session(),session()
    ask(a,'remember that my favorite color is green')
    ask(a,'take a note buy a notebook')
    assert 'green' in ask(a,'show memory')['text']
    assert 'green' not in ask(b,'show memory')['text']
    assert 'notebook' in ask(a,'show notes')['text']
    assert client.delete('/api/data',headers=a).status_code==200
    assert 'green' not in ask(a,'show memory')['text']

def test_codegen_and_chat(monkeypatch):
    monkeypatch.setattr(OllamaLLM,'_chat',lambda self,messages,reasoning=False: 'print("hello")' if reasoning else 'Hello from a test model')
    h=session()
    assert ask(h,'Tell me a story')['text']=='Hello from a test model'
    result=ask(h,'create a python file that says hello')
    assert result['action']=={'type':'download','filename':'nova_generated.py','content':'print("hello")\n'}

def test_cors_and_validation():
    r=client.options('/api/chat',headers={'Origin':'https://evil.example','Access-Control-Request-Method':'POST'})
    assert 'access-control-allow-origin' not in r.headers
    r=client.options('/api/chat',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'POST'})
    assert r.headers['access-control-allow-origin']=='http://localhost:5173'
    h=session()
    assert client.post('/api/chat',headers=h,json={'text':'x'*4001}).status_code==422
    assert client.post('/api/chat',headers=h,json={'text':'x'*25000}).status_code==413
    assert client.post('/api/chat',headers=h,json={'text':'time','timezone':'bad/zone'}).status_code==422

def test_calculator_rejects_code():
    from app.calculator import safe_calculate
    from app.models import UnsafeExpressionError
    for expression in ['__import__("os")','2**100000','1e999','999999999999999999999999']:
        with pytest.raises(UnsafeExpressionError): safe_calculate(expression)


def test_expired_token():
    h=session()
    accounts.clear()
    assert client.post('/api/chat',headers=h,json={'text':'hello'}).status_code==401


def test_account_history_survives_new_token_and_is_private():
    user_id = str(uuid4())
    first = session(user_id)
    ask(first, 'remember that my favorite color is green')
    second = session(user_id)
    stranger = session()
    history = client.get('/api/history', headers=second).json()['messages']
    assert history[0]['text'] == 'remember that my favorite color is green'
    assert len(history) == 2
    assert client.get('/api/history', headers=stranger).json() == {'messages':[]}
    assert 'green' in ask(second,'show memory')['text']
    client.delete('/api/data', headers=stranger)
    assert client.get('/api/history', headers=second).json()['messages']
    client.delete('/api/data', headers=second)
    assert client.get('/api/history', headers=first).json() == {'messages':[]}


def test_every_private_endpoint_requires_identity():
    for path in ['/api/history', '/api/model-status']:
        assert client.get(path).status_code == 401
        assert client.get(path, headers={'Authorization':'Bearer forged'}).status_code == 401
    assert client.delete('/api/data').status_code == 401


def test_model_status_reports_configuration_not_connectivity(monkeypatch):
    for name in ['LLM_PROVIDER', 'LLM_API_KEY', 'LLM_BASE_URL', 'CHAT_MODEL']:
        monkeypatch.delenv(name, raising=False)
    result=client.get('/api/model-status', headers=session()).json()
    assert result['status']=='unconfigured'
    monkeypatch.setenv('LLM_API_KEY','secret-do-not-expose')
    monkeypatch.setenv('LLM_BASE_URL','https://model.example/v1')
    monkeypatch.setenv('CHAT_MODEL','test-model')
    result=client.get('/api/model-status', headers=session()).json()
    assert result['status']=='configured'
    assert 'secret-do-not-expose' not in str(result)
    assert 'check the connection' in result['message']


def test_invalid_generated_python(monkeypatch):
    monkeypatch.setattr(OllamaLLM,'generate_python',lambda self,request: 'def broken(')
    result=ask(session(),'create a python file')
    assert result['action'] is None
    assert 'invalid Python' in result['text']


def test_original_website_shortcuts():
    h=session()
    for name, url in [('gmail','https://mail.google.com'),('chatgpt','https://chatgpt.com'),('linkedin','https://www.linkedin.com')]:
        assert ask(h,'open '+name)['action']['url']==url


def test_malformed_content_length():
    assert client.post('/api/session',headers={'Content-Length':'bad'},content='{}').status_code==400


@pytest.mark.parametrize('timezone', ['', '/etc/passwd', '../UTC', 'bad/zone'])
def test_invalid_timezone_returns_validation_error(timezone):
    response = client.post('/api/chat', headers=session(), json={'text':'hello', 'timezone':timezone})
    assert response.status_code == 422
    assert response.json()['detail'] == 'Unknown timezone.'


def test_timezone_data_without_system_database():
    """A fresh process prevents host timezone files or cached ZoneInfo hiding missing tzdata."""
    import subprocess
    import sys
    from pathlib import Path
    script = """
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, TZPATH
from fastapi.testclient import TestClient
from app.main import app
from app.auth import Account, identity
from app.storage import LocalStorage
import app.main as main
import tempfile
main.AccountStorage = lambda account: LocalStorage(db, account.id)
db = tempfile.mktemp(suffix='.db')
app.dependency_overrides[identity] = lambda: Account('test-user', 'test-token')
from app.llm import OllamaLLM
assert TZPATH == (), TZPATH
OllamaLLM.generate_python = lambda self, request: 'print("hello")\\n'
client = TestClient(app)
headers = {'Authorization':'Bearer test-token'}
for name, hours in [('UTC',0), ('Asia/Kolkata',5.5), ('Asia/Calcutta',5.5)]:
    assert datetime(2026,9,15,tzinfo=ZoneInfo(name)).utcoffset() == timedelta(hours=hours)
    response = client.post('/api/chat', headers=headers, json={'text':'Create a Python file for a command-line to-do list.', 'timezone':name})
    assert response.status_code == 200, response.text
    assert response.json()['action']['type'] == 'download', response.text
"""
    result = subprocess.run([sys.executable, '-c', script], cwd=Path(__file__).resolve().parents[1],
                            env={**os.environ, 'PYTHONTZPATH':''}, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
