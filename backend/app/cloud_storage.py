"""Persistent storage using the user's JWT and database row-level security.
No service-role key is required or accepted by this adapter.
"""
import httpx
from fastapi import HTTPException
from .auth import settings
from .storage import LocalStorage

class AccountStorage(LocalStorage):
    def __init__(self, account):
        self.account = account
        self.url, key = settings()
        self.headers = {'apikey': key, 'Authorization': 'Bearer ' + account.token}

    def _request(self, method, **kwargs):
        try:
            with httpx.Client(timeout=15) as client:
                response = client.request(method, self.url + '/rest/v1/nova_records', headers=self.headers, **kwargs)
            if response.status_code in (401, 403):
                raise HTTPException(401, 'Your session expired. Please sign in again.')
            response.raise_for_status()
            return response.json() if response.content else None
        except (httpx.HTTPError, ValueError):
            raise HTTPException(503, 'Your saved workspace is temporarily unavailable. Please try again.') from None

    def append(self, collection, record):
        self._request('POST', json={'user_id': self.account.id, 'collection': collection, 'payload': record})

    def read(self, collection, limit):
        rows = self._request('GET', params={'select': 'payload', 'user_id': 'eq.' + self.account.id,
            'collection': 'eq.' + collection, 'order': 'id.desc', 'limit': min(limit, 100)})
        return [row['payload'] for row in reversed(rows)]

    def clear(self):
        self._request('DELETE', params={'user_id': 'eq.' + self.account.id})
