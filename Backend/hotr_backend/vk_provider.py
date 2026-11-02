"""VK ID OAuth 2.1 PKCE transport. Provider credentials never enter the game.

The subject is obtained from VK's authenticated user_info endpoint, with the
token's state and user_id independently bound. An unverified JWT is never used.
"""
import hashlib
import json
import re
import asyncio
import math
import time
from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit

import httpx

from .service import ServiceError

# VK ID's current authorize and token endpoints use this canonical origin.
# The browser redirects the former .com origin; the token client intentionally
# does not follow redirects, so it must call the canonical host directly.
VK_ORIGIN = 'https://id.vk.ru'
EXCHANGE_SECONDS = 15


@dataclass(frozen=True)
class VkConfiguration:
    enabled: bool = False
    client_id: str = ''
    redirect_uri: str = ''

    def __post_init__(self):
        if type(self.enabled) is not bool:
            raise ValueError('Invalid VK configuration')
        if self.enabled:
            parsed = urlsplit(self.redirect_uri)
            if (not re.fullmatch(r'[1-9][0-9]{0,19}', self.client_id)
                    or parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                    or parsed.port not in (None, 443) or parsed.query or parsed.fragment
                    or parsed.path != '/v1/identity/vk/callback'
                    or parsed.hostname.lower() in ('localhost', '127.0.0.1', '::1')
                    or len(self.redirect_uri) > 512):
                raise ValueError('Explicit VK client ID and registered HTTPS callback required')

    @property
    def fingerprint(self):
        return hashlib.sha256((self.client_id + '\n' + self.redirect_uri).encode()).hexdigest()


class VkProvider:
    def __init__(self, configuration, transport=None, monotonic=None):
        self.configuration = configuration
        # Injection is process-local for HTTP contract tests; never client input.
        self.transport = transport
        self.monotonic = monotonic or time.monotonic

    def authorize_url(self, state, verifier):
        import base64
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode('ascii')).digest()).decode().rstrip('=')
        return VK_ORIGIN + '/authorize?' + urlencode({
            'response_type': 'code', 'client_id': self.configuration.client_id,
            'redirect_uri': self.configuration.redirect_uri, 'state': state,
            'code_challenge': challenge, 'code_challenge_method': 's256', 'scope': '',
            'prompt': 'login',
        })

    def _remaining(self, deadline):
        remaining = deadline - self.monotonic()
        if not math.isfinite(remaining) or remaining <= 0:
            raise ServiceError(502, 'vk_provider_unavailable')
        return remaining

    async def _post(self, client, path, data, deadline):
        # Fixed origin/path, no redirects, bounded total body, no credential logs.
        try:
            remaining = self._remaining(deadline)
            async with client.stream('POST', VK_ORIGIN + path, data=data, timeout=httpx.Timeout(remaining, connect=min(5, remaining)),
                                     headers={'Accept': 'application/json', 'Accept-Encoding': 'identity'}) as response:
                self._remaining(deadline)
                if response.status_code != 200 or response.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
                    raise ValueError('Invalid provider response')
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    self._remaining(deadline)
                    if len(raw) + len(chunk) > 32768:
                        raise ValueError('Provider response limit')
                    raw.extend(chunk)
                value = json.loads(raw.decode('utf-8'))
                if not isinstance(value, dict) or 'error' in value:
                    raise ValueError('Provider rejected request')
                return value
        except Exception:
            # Includes malformed/deep JSON and transport/protocol failures. The
            # caller records Failed rather than leaking payloads or stranding
            # an Exchanging flow. Cancellation propagates to the outer budget.
            raise ServiceError(502, 'vk_provider_unavailable') from None

    def verify(self, code, device_id, state, verifier):
        try:
            return asyncio.run(self._verify_async(code, device_id, state, verifier))
        except ServiceError:
            raise
        except Exception:
            raise ServiceError(502, 'vk_provider_unavailable') from None

    async def _verify_async(self, code, device_id, state, verifier):
        deadline = self.monotonic() + EXCHANGE_SECONDS
        # A single cancellation budget spans DNS/connect/headers/body across
        # BOTH calls. A peer sending one byte before every read timeout cannot
        # hold a backend worker indefinitely. The shared monotonic checks also
        # guard each delivered chunk and the transition to user_info.
        async with asyncio.timeout(EXCHANGE_SECONDS), httpx.AsyncClient(timeout=httpx.Timeout(10, connect=5), follow_redirects=False, transport=self.transport, trust_env=False) as client:
            token = await self._post(client, '/oauth2/auth', {
                'grant_type': 'authorization_code', 'client_id': self.configuration.client_id,
                'redirect_uri': self.configuration.redirect_uri, 'code_verifier': verifier,
                'device_id': device_id, 'state': state, 'code': code,
            }, deadline)
            import hmac
            access = token.get('access_token')
            subject = token.get('user_id')
            if (not isinstance(token.get('state'), str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token['state'])
                    or not hmac.compare_digest(token['state'], state)
                    or not isinstance(access, str) or not 1 <= len(access) <= 8192
                    or type(subject) not in (str, int) or not re.fullmatch(r'[1-9][0-9]{0,19}', str(subject))):
                raise ServiceError(502, 'vk_provider_identity_invalid')
            user = (await self._post(client, '/oauth2/user_info', {'client_id': self.configuration.client_id, 'access_token': access}, deadline)).get('user')
            if not isinstance(user, dict) or str(user.get('user_id')) != str(subject):
                raise ServiceError(502, 'vk_provider_identity_invalid')
            # Discard access/refresh/id tokens and all optional personal fields.
            return hashlib.sha256(('vk\n' + str(subject)).encode('ascii')).hexdigest()
