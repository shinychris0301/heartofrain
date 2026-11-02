"""Server-side configuration and bounded player commands; no client quantities."""
import re
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .schemas import Command, Grant, INT_MAX, Model

ProductCode = Annotated[str, Field(pattern=r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')]
InvoiceId = Annotated[str, Field(pattern=r'^[1-9][0-9]{0,29}$')]


class CommerceProduct(Model):
    id: ProductCode
    storeProductId: ProductCode | None = None
    enabled: bool = False
    coins: int = Field(gt=0, le=INT_MAX)
    grant: Grant | None = None
    purchaseLimitPerPlayer: int | None = Field(default=None, ge=1, le=1)
    amountMinor: int | None = Field(default=None, gt=0, le=INT_MAX)
    currency: str = Field(default='RUB', pattern=r'^[A-Z]{3}$')

    @model_validator(mode='after')
    def complete_grant(self):
        # Legacy six-coin catalogs remain valid; item quantities are exclusively
        # server-configured. Story stars cannot be bought.
        if self.grant is None:
            self.grant = Grant(coins=self.coins)
        if self.grant.coins != self.coins or self.grant.stars:
            raise ValueError('Commerce grant must match coins and cannot award story stars')
        return self


class CommerceConfig(Model):
    verificationMode: Literal['provider_api', 'sdk_client_reported'] = 'provider_api'
    version: str = Field(min_length=1, max_length=128)
    enabled: bool = False
    appId: int | None = Field(default=None, gt=0, le=9_223_372_036_854_775_807)
    sandbox: bool = True
    products: list[CommerceProduct] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def valid_mapping(self):
        if len({p.id for p in self.products}) != len(self.products):
            raise ValueError('Duplicate internal product')
        active = [p for p in self.products if p.enabled]
        if len({p.storeProductId for p in active}) != len(active):
            raise ValueError('Duplicate enabled store product')
        if self.enabled and (self.appId is None or not active):
            raise ValueError('Enabled commerce requires an app and configured products')
        if any(p.storeProductId is None or p.amountMinor is None for p in active):
            raise ValueError('Enabled product requires an explicit store mapping and amount')
        return self


class CreateCommerceOrder(Command):
    productId: ProductCode


class ReconcileCommerceOrder(Model):
    invoiceId: InvoiceId


def valid_order_id(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{32}', value) is not None
