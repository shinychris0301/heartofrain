"""Strict client requests and approved rewarded-ad configuration."""
from typing import Literal

from pydantic import Field

from .schemas import Command, Model


class RewardedAdsConfig(Model):
    version: str = Field(pattern=r'^[A-Za-z0-9_.-]{1,64}$')
    enabled: bool = False
    completionMode: Literal['trusted_completion', 'sdk_client_reported_capped'] = 'trusted_completion'
    placement: Literal['shop_rewarded'] = 'shop_rewarded'
    rewardCoins: Literal[400] = 400
    dailyLimit: Literal[3] = 3
    # Compatibility fallback for clients which have not yet sent their local
    # offset. Updated clients set the player's durable calendar via /status.
    utcOffsetSeconds: Literal[36000] = 36000
    dayMode: Literal['player_local'] = 'player_local'
    cooldownSeconds: Literal[600] = 600
    opportunityTtlSeconds: int = Field(default=900, ge=60, le=3600)


class ReserveRewardedAd(Command):
    placement: Literal['shop_rewarded']


class RewardedAdCommand(Command):
    pass
