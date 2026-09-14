import hashlib
import os
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from pydantic import BaseModel, Field
from .storage import LocalStorage
from .llm import OllamaLLM
from .actions import DesktopActions
from .assistant import NovaAssistant

SECRET = os.getenv('SESSION_SECRET', '')
ACCESS = os.getenv('ACCESS_CODE', '')
if len(SECRET) < 32 or len(ACCESS) < 12:
    raise RuntimeError('Set SESSION_SECRET (32+ characters) and ACCESS_CODE (12+ characters).')
DB = os.getenv('DATABASE_PATH','./data/nova.db')
serializer = URLSafeTimedSerializer(SECRET, salt='nova-session-v1')
app = FastAPI(title='Nova Voice API', docs_url=None, redoc_url=None)
origins = [s.strip().rstrip('/') for s in os.getenv('ALLOWED_ORIGINS','http://localhost:5173').split(',') if s.strip()]
if '*' in origins: raise RuntimeError('Use exact ALLOWED_ORIGINS, never wildcard.')
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET','POST','DELETE'], allow_headers=['Authorization','Content-Type'])
bearer = HTTPBearer()
limits = defaultdict(deque)
lock = threading.Lock()
capacity = threading.BoundedSemaphore(4)

def throttle(key, maximum, window=60):
    now = time.monotonic()
    with lock:
        for old in list(limits):
            if not limits[old] or limits[old][-1] < now-3600: del limits[old]
        queue = limits[key]
        while queue and queue[0] < now-window: queue.popleft()
        if len(queue) >= maximum: raise HTTPException(429, 'Too many requests. Please wait a minute.')
        queue.append(now)

def identity(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    try: return serializer.loads(credentials.credentials, max_age=30*24*3600)
    except (BadSignature, SignatureExpired): raise HTTPException(401, 'Session expired. Please reconnect.')

class Login(BaseModel):
    access_code: str = Field(min_length=1,max_length=256)
class Message(BaseModel):
    text: str = Field(min_length=1,max_length=4000)
    timezone: str = Field(default='UTC',max_length=80)

@app.middleware('http')
async def safety(request: Request, call_next):
    from starlette.responses import JSONResponse
    try:
        declared_size = int(request.headers.get('content-length', '0') or 0)
        if declared_size < 0: raise ValueError
    except ValueError:
        return JSONResponse({'detail': 'Invalid Content-Length'}, status_code=400)
    if declared_size > 20000:
        from starlette.responses import JSONResponse
        return JSONResponse({'detail':'Request too large'},status_code=413)
    # Bound streamed/chunked bodies as well as declared Content-Length.
    if request.method in ('POST','PUT','PATCH'):
        size = 0
        chunks = []
        async for chunk in request.stream():
            size += len(chunk)
            if size > 20000:
                from starlette.responses import JSONResponse
                return JSONResponse({'detail':'Request too large'},status_code=413)
            chunks.append(chunk)
        request._body = b''.join(chunks)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@app.get('/healthz')
def health(): return {'status':'ok'}

@app.post('/api/session')
def login(body: Login, request: Request):
    throttle('login-global', 60)
    throttle('login:'+request.client.host, 10)
    if not secrets.compare_digest(hashlib.sha256(body.access_code.encode()).digest(), hashlib.sha256(ACCESS.encode()).digest()):
        raise HTTPException(403,'Incorrect access code.')
    return {'token':serializer.dumps(secrets.token_urlsafe(24))}

@app.post('/api/chat')
def chat(body: Message, session: str = Depends(identity)):
    throttle('global', int(os.getenv('GLOBAL_REQUESTS_PER_MINUTE','60')))
    throttle('chat:'+session, 15)
    if not capacity.acquire(blocking=False): raise HTTPException(503,'Nova is busy. Please try again shortly.')
    try:
        try: timezone = ZoneInfo(body.timezone)
        except ZoneInfoNotFoundError: raise HTTPException(422,'Unknown timezone.')
        storage = LocalStorage(DB, session)
        llm = OllamaLLM(storage)
        actions = DesktopActions(llm)
        assistant = NovaAssistant(storage,llm,actions,now=lambda: datetime.now(timezone))
        response = assistant.handle(body.text)
        return {'text':response.text,'should_exit':response.should_exit,'action':actions.result}
    finally: capacity.release()

@app.delete('/api/data')
def clear(session: str = Depends(identity)):
    LocalStorage(DB,session).clear()
    return {'deleted':True}
