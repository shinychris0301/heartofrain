from typing import Annotated, Literal

from pydantic import Field

from .schemas import Command, Model


class ReplayMove(Model):
    index: int = Field(ge=0, le=999)
    kind: Literal['Swap', 'Tap']
    x: int = Field(ge=0, le=14)
    y: int = Field(ge=0, le=14)
    toX: int = Field(ge=-1, le=14)
    toY: int = Field(ge=-1, le=14)


class VerifyReplay(Command):
    expectedPrefixRevision: int = Field(ge=0, le=9_223_372_036_854_775_807)
    actions: list[ReplayMove] = Field(max_length=128)


class ReplayTool(VerifyReplay):
    expectedWalletRevision: int = Field(ge=0, le=9_223_372_036_854_775_807)
    tool: int = Field(ge=0, le=3)
    x: int = Field(ge=-1, le=14)
    y: int = Field(ge=-1, le=14)


class ReplayContinue(VerifyReplay):
    expectedWalletRevision: int = Field(ge=0, le=9_223_372_036_854_775_807)


class ResumeReplay(Model):
    pass
