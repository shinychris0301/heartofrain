"""Trusted completion seam. There is deliberately no Yandex verification claim.

The synthetic HMAC adapter is an in-process local/staging test facility. No HTTP
route accepts its messages, and neither a client SDK callback nor a player token
can invoke this authority. A real provider adapter must verify the provider's
authenticated server evidence before returning VerifiedAdCompletion.
"""
from dataclasses import dataclass
import hashlib
import hmac
import re

from pydantic import Field

from .schemas import Id, Model
from .storage import canonical


class InvalidAdCompletion(Exception):
    pass


@dataclass(frozen=True)
class VerifiedAdCompletion:
    provider: str
    event_id: str
    opportunity_id: str
    player_id: str
    placement: str
    config_version: str
    completed_at: int


class UnavailableAdCompletionVerifier:
    configured = False
    mode = 'unavailable'

    def verify(self, payload):
        raise InvalidAdCompletion('trusted_completion_unavailable')


class SyntheticCompletion(Model):
    eventId: str = Field(pattern=r'^[A-Za-z0-9_.-]{1,128}$')
    opportunityId: Id
    playerId: Id
    placement: str = Field(pattern=r'^[A-Za-z0-9_.-]{1,64}$')
    configVersion: str = Field(pattern=r'^[A-Za-z0-9_.-]{1,64}$')
    completedAt: int = Field(ge=0, le=253_402_300_799)
    signature: str = Field(pattern=r'^[0-9a-f]{64}$')


class SyntheticHmacCompletionVerifier:
    configured = True
    mode = 'synthetic_local_staging_only'

    def __init__(self, key: bytes, *, mode: str):
        if mode not in ('local', 'staging') or type(key) is not bytes or len(key) < 32:
            raise ValueError('Synthetic completion is local/staging only and requires a private test key')
        self._key = key

    def verify(self, payload):
        try:
            value = SyntheticCompletion.model_validate(payload)
        except Exception as error:
            raise InvalidAdCompletion('invalid_completion') from error
        body = value.model_dump(exclude={'signature'})
        expected = hmac.new(self._key, canonical(body).encode('ascii'), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, value.signature):
            raise InvalidAdCompletion('invalid_completion')
        return VerifiedAdCompletion('synthetic_hmac', value.eventId, value.opportunityId,
                                    value.playerId, value.placement, value.configVersion, value.completedAt)


def valid_completion(value):
    return (type(value) is VerifiedAdCompletion
            and all(type(field) is str for field in (value.provider, value.event_id, value.opportunity_id,
                                                    value.player_id, value.placement, value.config_version))
            and re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', value.provider or '')
            and re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', value.event_id or '')
            and re.fullmatch(r'[0-9a-f]{32}', value.opportunity_id or '')
            and re.fullmatch(r'[0-9a-f]{32}', value.player_id or '')
            and re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', value.placement or '')
            and re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', value.config_version or '')
            and type(value.completed_at) is int and 0 <= value.completed_at <= 253_402_300_799)
