import os
import tempfile
os.environ['SESSION_SECRET']='test-session-secret-with-more-than-32-characters'
os.environ['ACCESS_CODE']='test-access-code-only'
os.environ['DATABASE_PATH']=tempfile.mktemp(suffix='.db')
from fastapi.testclient import TestClient
from app.main import app, limits
from app.llm import OllamaLLM
import pytest

@pytest.fixture(autouse=True)
def reset_limits(): limits.clear()
client=TestClient(app)
def session():
    r=client.post('/api/session',json={'access_code':'test-access-code-only'})
    assert r.status_code==200
    return {'Authorization':'Bearer '+r.json()['token']}
def ask(headers,text): return client.post('/api/chat',headers=headers,json={'text':text}).json()

def test_auth_and_limits():
    assert client.post('/api/chat',json={'text':'hello'}).status_code in (401,403)
    assert client.post('/api/session',json={'access_code':'wrong'}).status_code==403
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


def test_expired_token(monkeypatch):
    import itsdangerous.timed
    h=session()
    monkeypatch.setattr(itsdangerous.timed.TimestampSigner, 'get_timestamp', lambda self: 9999999999)
    assert client.post('/api/chat',headers=h,json={'text':'hello'}).status_code==401


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
