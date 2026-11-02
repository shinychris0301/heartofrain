from typing import Literal

from pydantic import Field, model_validator

from .schemas import Command, Id
from .teams_schema109 import TeamBadge109


class CreateTeam(Command):
    name: str = Field(min_length=2, max_length=32)
    description: str = Field(default='', max_length=160)
    badgeId: TeamBadge109 = 'drop'


class TeamTarget(Command):
    playerId: Id


class TeamLeave(Command):
    # Legacy clients omit this entirely. An explicitly supplied value must be
    # a real server-issued incarnation, never an ambiguous null.
    expectedMembershipVersion: Id | None = None

    @model_validator(mode='after')
    def supplied_version_is_nonnull(self):
        if 'expectedMembershipVersion' in self.model_fields_set and self.expectedMembershipVersion is None:
            raise ValueError('membership version cannot be null')
        return self


class SendMessage(Command):
    text: str = Field(min_length=1, max_length=1000)


class ReadMessages(Command):
    through: int = Field(ge=0, le=9_223_372_036_854_775_807)


class ReportMessage(Command):
    messageId: Id
    reason: Literal['Spam', 'Abuse', 'Threat', 'Other']
    details: str = Field(default='', max_length=500)


class ModerateMessage(Command):
    messageId: Id
    action: Literal['Hide', 'Restore', 'Delete', 'DismissReports']
    reason: str = Field(min_length=1, max_length=160)
