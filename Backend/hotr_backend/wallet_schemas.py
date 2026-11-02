from typing import Annotated, Literal

from pydantic import Field

from .schemas import Command, Digest, Id, Model


class WalletCommand(Command):
    expectedRevision: int = Field(ge=0, le=9_223_372_036_854_775_807)


class ReserveAttempt(WalletCommand):
    level: int = Field(ge=1, le=50)
    starting: list[Annotated[int, Field(ge=0, le=1)]] = Field(min_length=4, max_length=4)


class SpendTool(WalletCommand):
    tool: int = Field(ge=0, le=3)


class SettleAttempt(WalletCommand):
    playerId: Id
    attemptId: Id
    outcome: Literal['Won', 'OutOfMoves', 'Lost', 'Fault']
    proofDigest: Digest


class LevelReward(Model):
    coins: Literal[50]
    stars: Literal[1]


class LevelContract(Model):
    level: int = Field(ge=1, le=50)
    source: str
    sourceSHA256: Digest
    configHash: Digest
    moves: int = Field(ge=1, le=1000)
    tileSeed: int = Field(ge=1)
    goals: list[dict]
    reward: LevelReward


class LevelCatalog(Model):
    version: str
    scope: str
    rewardSource: str
    levels: list[LevelContract] = Field(min_length=50, max_length=50)
