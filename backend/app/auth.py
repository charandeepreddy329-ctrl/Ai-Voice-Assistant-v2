"""Validate bearer tokens with Supabase Auth; never trust client-provided identity."""
import os
from dataclasses import dataclass, field
from uuid import UUID
import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer = HTTPBearer(auto_error=False)

@dataclass(frozen=True)
class Account:
    id: str
    token: str = field(repr=False)

def settings():
    url = os.getenv('SUPABASE_URL', '').rstrip('/')
    key = os.getenv('SUPABASE_PUBLISHABLE_KEY', '')
    if not url.startswith('https://') or not key:
        raise HTTPException(503, 'Email sign-in is not configured yet. Please contact the owner.')
    return url, key

def identity(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials or credentials.scheme.lower() != 'bearer':
        raise HTTPException(401, 'Please sign in with your email.')
    url, key = settings()
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(url + '/auth/v1/user', headers={
                'apikey': key, 'Authorization': 'Bearer ' + credentials.credentials})
        if response.status_code in (401, 403):
            raise HTTPException(401, 'Your session expired. Please sign in again.')
        response.raise_for_status()
        user = response.json()
        if not user.get('email_confirmed_at') or user.get('is_anonymous'):
            raise HTTPException(401, 'Verify your email before continuing.')
        user_id = str(UUID(user['id']))
        return Account(user_id, credentials.credentials)
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise HTTPException(503, 'Sign-in verification is temporarily unavailable. Please try again.') from None
