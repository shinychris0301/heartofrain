"""Bounded human UGC-review requests, independent of financial authority."""
import unicodedata
from typing import Literal

from pydantic import Field, field_validator

from .schemas import Command, Id


def _clean(value, multiline):
    value = unicodedata.normalize('NFC', value).strip()
    if any(unicodedata.category(c) in ('Cc', 'Cf', 'Cs', 'Zl', 'Zp') and not (multiline and c == '\n') for c in value):
        raise ValueError('Invalid review text')
    return value


class UgcReport(Command):
    kind: Literal['Profile', 'Team']
    targetId: Id
    reason: Literal['Spam', 'Abuse', 'Threat', 'Impersonation', 'Other']
    details: str = Field(default='', max_length=500)

    @field_validator('details')
    @classmethod
    def clean_details(cls, value):
        return _clean(value, True)


class UgcModerate(Command):
    kind: Literal['Profile', 'Team']
    targetId: Id
    action: Literal['ResetProfileName', 'ResetTeamText', 'DismissReports']
    reason: str = Field(min_length=1, max_length=160)

    @field_validator('reason')
    @classmethod
    def clean_reason(cls, value):
        value = _clean(value, False)
        if not value:
            raise ValueError('Review reason required')
        return value
