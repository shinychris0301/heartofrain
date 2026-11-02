import hashlib
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

INT_MAX = 2_147_483_647
Id = Annotated[str, Field(pattern=r'^[0-9a-f]{32}$')]
Digest = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$')]
Quantity = Annotated[int, Field(ge=0, le=INT_MAX)]


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Grant(Model):
    coins: Quantity = 0
    stars: Quantity = 0
    starting: list[Quantity] = Field(default_factory=lambda: [0] * 4, min_length=4, max_length=4)
    tools: list[Quantity] = Field(default_factory=lambda: [0] * 4, min_length=4, max_length=4)

    def quantities(self):
        return [self.coins, self.stars, *self.starting, *self.tools]


class DailyRules(Model):
    version: str = Field(min_length=1, max_length=128)
    days: list[Grant] = Field(min_length=7, max_length=7)


class Milestone(Model):
    level: int = Field(ge=1, le=50)
    grant: Grant


class WellworksRules(Model):
    milestones: list[Milestone] = Field(min_length=1, max_length=50)

    @model_validator(mode='after')
    def ordered(self):
        if [m.level for m in self.milestones] != sorted({m.level for m in self.milestones}):
            raise ValueError('Milestones must be unique and ordered')
        if any(m.grant.stars for m in self.milestones):
            raise ValueError('Milestones cannot award story stars')
        return self


class CupRules(Model):
    version: str = Field(min_length=1, max_length=128)
    unlockClears: int = Field(ge=0, lt=50)
    durationSeconds: int = Field(ge=1, le=2_592_000)
    rivalFinalScores: list[Annotated[int, Field(ge=0, le=50)]] = Field(min_length=4, max_length=4)
    rankRewards: list[Grant] = Field(min_length=5, max_length=5)

    @model_validator(mode='after')
    def no_stars(self):
        if any(g.stars for g in self.rankRewards):
            raise ValueError('Cup cannot award story stars')
        return self


class GiftRequest(Model):
    requestId: Id
    offerId: str = Field(min_length=1, max_length=256)
    day: int = Field(ge=0)
    step: int = Field(ge=0, le=6)
    schedule: str = Field(min_length=1, max_length=128)
    expectedGrant: Grant


class Command(Model):
    commandId: Id


class MilestoneRequest(Command):
    level: int = Field(ge=1, le=50)


class CupClaimRequest(Command):
    runId: Id


class VerifiedClear(Model):
    # Only a separately provisioned verifier credential may call this contract.
    # A player's telemetry or self-reported win is never accepted as proof.
    attemptId: Id
    level: int = Field(ge=1, le=50)
    proofDigest: Digest


class AuditEvent(Model):
    model_config = ConfigDict(extra='forbid', strict=True, serialize_by_alias=True)
    schema_version: Literal[1] = Field(alias='schema')
    id: Digest
    stream: Digest
    kind: Literal['attempt_reserved', 'attempt_started', 'attempt_cancelled', 'attempt_won',
                  'attempt_lost', 'attempt_interrupted', 'tool_spent', 'level_completed',
                  'reward_granted', 'cup_joined', 'cup_point', 'cup_finished', 'cup_claimed',
                  'lives_regenerated', 'lives_refilled', 'attempt_released']
    receipt: Digest
    aggregate: Digest
    category: Literal['campaign', 'daily_gift', 'wellworks', 'rain_cup', 'other']
    level: int = Field(ge=0, le=50)
    rank: int = Field(ge=0, le=5)
    points: int = Field(ge=0, le=1)
    delta: list[int] = Field(min_length=12, max_length=12)

    @model_validator(mode='after')
    def valid_event(self):
        expected = hashlib.sha256(f'hotr-event-v1|{self.stream}|{self.kind}|{self.receipt}'.encode()).hexdigest()
        if self.id != expected:
            raise ValueError('Event ID does not match schema')
        for index, value in enumerate(self.delta):
            allowed = value == 0
            if self.kind == 'attempt_started' and 4 <= index < 8:
                allowed = value in (0, -1)
            if self.kind == 'attempt_released' and 4 <= index < 8:
                allowed = value in (0, 1)
            if self.kind == 'tool_spent' and index >= 8:
                allowed = value in (0, -1)
            if self.kind in ('attempt_lost', 'attempt_interrupted') and index == 2:
                allowed = value == -1
            if self.kind == 'level_completed' and index == 3:
                allowed = value == 1
            if self.kind == 'reward_granted' and (index < 2 or index >= 4):
                allowed = 0 <= value <= INT_MAX
            if self.kind == 'lives_regenerated' and index == 2:
                allowed = 1 <= value <= INT_MAX
            if self.kind == 'lives_refilled' and index == 0:
                allowed = -INT_MAX <= value < 0
            if self.kind == 'lives_refilled' and index == 2:
                allowed = 1 <= value <= INT_MAX
            if not allowed:
                raise ValueError('Invalid event delta')
        if self.kind == 'tool_spent' and sum(self.delta) != -1:
            raise ValueError('Invalid tool quantity')
        if self.points != (1 if self.kind == 'cup_point' else 0):
            raise ValueError('Invalid points')
        attempt = self.kind.startswith('attempt_') or self.kind in ('tool_spent', 'level_completed', 'cup_point')
        if attempt and self.level == 0 or not attempt and self.kind != 'reward_granted' and self.level != 0:
            raise ValueError('Invalid event level')
        if (self.kind in ('cup_finished', 'cup_claimed')) != (self.rank > 0):
            raise ValueError('Invalid event rank')
        if self.kind.startswith('cup_'):
            if self.category != 'rain_cup':
                raise ValueError('Invalid event category')
        elif self.kind != 'reward_granted' and self.category != 'campaign':
            raise ValueError('Invalid event category')
        if self.kind == 'reward_granted' and ((self.category == 'campaign') != (self.level > 0)):
            raise ValueError('Invalid reward origin')
        return self


class EventBatch(Model):
    events: list[AuditEvent] = Field(min_length=1, max_length=100)
