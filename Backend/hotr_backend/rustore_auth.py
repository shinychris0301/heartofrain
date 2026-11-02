"""Server-only RuStore Public API authentication; no key/token enters Unity.

Implements the official keyId+timestamp / SHA512withRSA contract. Network and
secret sources are explicit; the regular unconfigured service stays unavailable.
"""
import base64
import datetime as dt
import json
import re
import threading
import time
from pathlib import Path

import httpx
from Crypto.Hash import SHA512
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15

from .rustore_provider import ProviderUnavailable


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate field')
        value[key] = item
    return value


def _invalid_constant(_):
    raise ValueError('invalid constant')


class RuStoreTokenSupplier:
    origin = 'https://public-api-m.rustore.ru/public/auth/'

    def __init__(self, key_id, private_key_source, *, transport=None, utc_clock=None, monotonic=None):
        if not isinstance(key_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', key_id):
            raise ValueError('Invalid RuStore key identifier')
        if not callable(private_key_source):
            raise ValueError('A server-only private key source is required')
        self._key_id, self._source, self._transport = key_id, private_key_source, transport
        self._utc = utc_clock or (lambda: dt.datetime.now(dt.timezone.utc))
        self._monotonic = monotonic or time.monotonic
        self._lock = threading.Lock()
        self._token, self._expires = None, 0.0

    @classmethod
    def from_file(cls, key_id, path, **kwargs):
        """Read a deployment secret file on refresh, never a command-line key.

        The caller owns file permissions, encryption and rotation. This method
        never prints paths/content or copies the secret into project assets.
        """
        file = Path(path)

        def read():
            with file.open('rb') as stream:
                value = stream.read(16_385)
            if not value or len(value) > 16_384:
                raise ValueError('Invalid secret file')
            return value

        return cls(key_id, read, **kwargs)

    def invalidate(self):
        with self._lock:
            self._token, self._expires = None, 0.0

    def __repr__(self):
        return '<RuStoreTokenSupplier server-only>'

    def __call__(self):
        with self._lock:
            now = self._monotonic()
            if self._token is not None and now < self._expires:
                return self._token
            # Do not fall back to a stale token after a failed refresh.
            self._token, self._expires = None, 0.0
            try:
                raw = self._source()
                if not isinstance(raw, bytes) or not raw or len(raw) > 16_384:
                    raise ValueError('Invalid key source')
                key = RSA.import_key(raw if raw.startswith(b'-----BEGIN ') else base64.b64decode(b''.join(raw.split()), validate=True))
                if not key.has_private() or key.size_in_bits() < 2048:
                    raise ValueError('Private RSA key required')
                instant = self._utc()
                if not isinstance(instant, dt.datetime) or instant.tzinfo is None or instant.utcoffset() is None:
                    raise ValueError('UTC clock required')
                timestamp = instant.astimezone(dt.timezone.utc).isoformat(timespec='milliseconds')
                digest = SHA512.new((self._key_id + timestamp).encode('utf-8'))
                signature = base64.b64encode(pkcs1_15.new(key).sign(digest)).decode('ascii')
                payload = {'keyId': self._key_id, 'timestamp': timestamp, 'signature': signature}
                with httpx.Client(transport=self._transport, timeout=10, follow_redirects=False, trust_env=False) as client:
                    with client.stream('POST', self.origin, json=payload,
                                       headers={'Accept': 'application/json', 'Accept-Encoding': 'identity'}) as response:
                        if response.status_code != 200:
                            raise ValueError('Authentication unavailable')
                        data = bytearray()
                        for chunk in response.iter_bytes(chunk_size=16_384):
                            data.extend(chunk)
                            if len(data) > 65_536:
                                raise ValueError('Response too large')
                result = json.loads(data, object_pairs_hook=_object, parse_constant=_invalid_constant)
                if not isinstance(result, dict) or result.get('code') != 'OK' or not isinstance(result.get('body'), dict):
                    raise ValueError('Invalid authentication response')
                token, ttl = result['body'].get('jwe'), result['body'].get('ttl')
                if (not isinstance(token, str) or not 1 <= len(token) <= 16_384
                        or not re.fullmatch(r'[A-Za-z0-9_.-]+', token)
                        or type(ttl) is not int or not 31 <= ttl <= 900):
                    raise ValueError('Invalid authentication token')
                # Expiry starts before the request; clock changes do not extend it.
                expires = now + ttl - 30
                if self._monotonic() >= expires:
                    raise ValueError('Expired authentication response')
                self._token, self._expires = token, expires
                return token
            except Exception:
                # Secret providers, crypto and HTTP errors may contain private
                # data in their original messages; expose only this fixed code.
                raise ProviderUnavailable('rustore_auth_unavailable') from None
