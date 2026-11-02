"""Strict SDK observations, explicitly client-reported and never provider proof."""
from typing import Literal
import uuid

from pydantic import Field, field_validator, model_validator

from .commerce_schemas import InvoiceId, ProductCode
from .schemas import INT_MAX, Model

class SdkPurchaseReport125(Model):
    invoiceId: InvoiceId
    purchaseId: str = Field(min_length=36, max_length=36)
    orderId: str = Field(pattern=r'^[0-9a-f]{32}$')
    productId: ProductCode
    developerPayload: str = Field(min_length=1, max_length=512)
    quantity: int = Field(ge=1, le=1)
    sandbox: bool
    status: Literal['INVOICE_CREATED', 'PROCESSING', 'EXECUTING', 'CONFIRMED', 'CANCELLED',
                    'REJECTED', 'EXPIRED', 'PAID', 'REVERSED', 'REFUNDING', 'REFUNDED']
    purchaseType: Literal['ONE_STEP', 'TWO_STEP', 'UNDEFINED']
    acknowledgementState: Literal['PENDING', 'ACKNOWLEDGED', 'UNKNOWN']
    productType: Literal['CONSUMABLE_PRODUCT']
    amountMinor: int = Field(gt=0, le=INT_MAX)
    currency: str = Field(pattern=r'^[A-Z]{3}$')

    @field_validator('purchaseId')
    @classmethod
    def canonical_purchase(cls, value):
        if str(uuid.UUID(value)) != value:
            raise ValueError('Canonical purchase identifier required')
        return value

    @model_validator(mode='after')
    def valid_phase(self):
        if self.status == 'PAID' and self.purchaseType != 'TWO_STEP':
            raise ValueError('Held funds require an explicit two-step purchase')
        if self.purchaseType == 'UNDEFINED' and self.status not in (
                'INVOICE_CREATED', 'PROCESSING', 'EXECUTING', 'CANCELLED', 'REJECTED', 'EXPIRED'):
            raise ValueError('Undefined purchase method cannot establish payment')
        return self

