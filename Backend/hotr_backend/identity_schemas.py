"""Bounded provider-independent guest lifecycle requests; never wallet imports."""
from typing import Literal

from pydantic import Field

from .schemas import Digest, Id, Model

PUBLIC_KEY_MAX = 256
SECRET_PATTERN = r'^[A-Za-z0-9_-]{43}$'


class ChallengeRequest(Model):
    purpose: Literal['guest', 'session', 'recover', 'logout', 'delete', 'vk']
    requestId: Id
    publicKey: str = Field(min_length=64, max_length=PUBLIC_KEY_MAX)
    payloadDigest: Digest


class SignedRequest(Model):
    requestId: Id
    challengeId: Id
    publicKey: str = Field(min_length=64, max_length=PUBLIC_KEY_MAX)
    signature: str = Field(min_length=80, max_length=112)


class GuestRequest(SignedRequest):
    refreshToken: str = Field(pattern=SECRET_PATTERN)
    recoverySecret: str = Field(pattern=SECRET_PATTERN)


class SessionRequest(SignedRequest):
    refreshToken: str = Field(pattern=SECRET_PATTERN)
    replacementToken: str = Field(pattern=SECRET_PATTERN)


class RecoverRequest(SignedRequest):
    playerId: Id
    recoverySecret: str = Field(pattern=SECRET_PATTERN)
    replacementRecoverySecret: str = Field(pattern=SECRET_PATTERN)
    refreshToken: str = Field(pattern=SECRET_PATTERN)


class LogoutRequest(SignedRequest):
    refreshToken: str = Field(pattern=SECRET_PATTERN)


class DeletionRequest(SignedRequest):
    playerId: Id
    refreshToken: str = Field(pattern=SECRET_PATTERN)
