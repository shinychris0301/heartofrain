"""Friend/profile-only schemas; messaging/report schemas belong to their module."""
import unicodedata

from pydantic import Field, field_validator

from .schemas import Command, Id


def normalize_display_name(value):
    """NFC, trim and legacy Unity base+combining text-element budget.

    The existing ProfileRules exclude controls/formats/separators and malformed
    surrogates. A raw cap additionally bounds pathological combining-mark input.
    This is not a profanity filter or an impersonation/confusable detector.
    """
    if not isinstance(value, str) or not 1 <= len(value) <= 256:
        raise ValueError('Invalid display name')
    value = unicodedata.normalize('NFC', value.strip())
    if not value or any(unicodedata.category(c) in ('Cc', 'Cf', 'Cs', 'Zl', 'Zp') for c in value):
        raise ValueError('Invalid display name')
    count, in_element = 0, False
    for char in value:
        if not unicodedata.category(char).startswith('M') or not in_element:
            count += 1
            in_element = True
    if count > 20:
        raise ValueError('Display name too long')
    return value


class ProfileUpdate(Command):
    displayName: str = Field(min_length=1, max_length=256)
    leaderboardOptIn: bool = False

    @field_validator('displayName')
    @classmethod
    def valid_name(cls, value):
        return normalize_display_name(value)


class ProfileNameUpdate(Command):
    displayName: str = Field(min_length=1, max_length=256)

    @field_validator('displayName')
    @classmethod
    def valid_name(cls, value):
        return normalize_display_name(value)


class ProfileConsentUpdate(Command):
    # Required explicitly; a name edit or an omitted field is never consent.
    leaderboardOptIn: bool


class FriendTarget(Command):
    playerId: Id


class FriendResponse(Command):
    requestId: Id
    action: str = Field(pattern=r'^(accept|decline|cancel)$')
