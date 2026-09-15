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
from app.llm import OllamaLLM
assert TZPATH == (), TZPATH
OllamaLLM.generate_python = lambda self, request: 'print("hello")\\n'
client = TestClient(app)
token = client.post('/api/session', json={'access_code':os.environ['ACCESS_CODE']}).json()['token']
headers = {'Authorization':'Bearer '+token}
for name, hours in [('UTC',0), ('Asia/Kolkata',5.5), ('Asia/Calcutta',5.5)]:
    assert datetime(2026,9,15,tzinfo=ZoneInfo(name)).utcoffset() == timedelta(hours=hours)
    response = client.post('/api/chat', headers=headers, json={'text':'Create a Python file for a command-line to-do list.', 'timezone':name})
    assert response.status_code == 200, response.text
    assert response.json()['action']['type'] == 'download', response.text
"""
    result = subprocess.run([sys.executable, '-c', script], cwd=Path(__file__).resolve().parents[1],
                            env={**os.environ, 'PYTHONTZPATH':''}, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
