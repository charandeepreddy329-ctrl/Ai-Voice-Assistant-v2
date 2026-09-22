import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .auth import Account, identity
from .cloud_storage import AccountStorage
from .llm import OllamaLLM
from .actions import DesktopActions
from .assistant import NovaAssistant

app = FastAPI(title='Nova Voice API', docs_url=None, redoc_url=None)
origins = [s.strip().rstrip('/') for s in os.getenv('ALLOWED_ORIGINS','http://localhost:5173').split(',') if s.strip()]
if '*' in origins: raise RuntimeError('Use exact ALLOWED_ORIGINS, never wildcard.')
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET','POST','DELETE'], allow_headers=['Authorization','Content-Type'])
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

@app.get('/api/history')
def history(account: Account = Depends(identity)):
    return {'messages': AccountStorage(account).read('messages', 100)}

@app.get('/api/model-status')
def model_status(account: Account = Depends(identity)):
    return OllamaLLM.configuration_status()

@app.post('/api/chat')
def chat(body: Message, account: Account = Depends(identity)):
    throttle('global', int(os.getenv('GLOBAL_REQUESTS_PER_MINUTE','60')))
    throttle('chat:'+account.id, 15)
    if not capacity.acquire(blocking=False): raise HTTPException(503,'Nova is busy. Please try again shortly.')
    try:
        try: timezone = ZoneInfo(body.timezone)
        except (ZoneInfoNotFoundError, ValueError): raise HTTPException(422,'Unknown timezone.')
        storage = AccountStorage(account)
        llm = OllamaLLM(storage)
        actions = DesktopActions(llm)
        assistant = NovaAssistant(storage,llm,actions,now=lambda: datetime.now(timezone))
        response = assistant.handle(body.text)
        result = {'text':response.text,'should_exit':response.should_exit,'action':actions.result}
        storage.append('messages', {'role':'user', 'text':body.text})
        storage.append('messages', {'role':'assistant', **result})
        return result
    finally: capacity.release()

@app.delete('/api/data')
def clear(account: Account = Depends(identity)):
    AccountStorage(account).clear()
    return {'deleted':True}
