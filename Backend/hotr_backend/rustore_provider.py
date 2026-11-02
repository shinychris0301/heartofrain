"""Bounded server-only RuStore Pay invoice lookup, with no embedded credentials.

The default is unavailable. A configured deployment may supply the server-only
RSA/JWE supplier. Only normalized necessary fields survive; card data is discarded.
"""
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable

import httpx


class ProviderUnavailable(Exception):
    pass


class InvalidProviderResponse(Exception):
    pass


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidProviderResponse()
        result[key] = value
    return result


def _invalid_constant(value):
    raise InvalidProviderResponse()


@dataclass(frozen=True)
class VerifiedInvoice:
    invoice_id: str
    purchase_id: str
    app_id: int
    sandbox: bool
    order_id: str
    product_id: str
    app_user_id: str
    developer_payload: str
    amount_minor: int
    currency: str
    status: str
    acknowledgement: str


class UnavailablePurchaseProvider:
    configured = False

    def lookup(self, invoice_id, sandbox):
        raise ProviderUnavailable()


class RuStoreInvoiceProvider:
    """Official v2 invoice API only; a caller cannot choose an arbitrary origin.

    PENDING/ACKNOWLEDGED is a delivery marker, not payment authorization. This
    adapter does not confirm PAID holds, issue refunds, or acknowledge delivery.
    The SDK can acknowledge after durable server credit; a later lookup verifies
    that marker. Production/gameplay-wallet activation remains separate.
    """
    configured = True
    origin = 'https://public-api-m.rustore.ru'

    def __init__(self, token_supplier: Callable[[], str], transport=None):
        if not callable(token_supplier):
            raise ValueError('A server-side token supplier is required')
        self.token_supplier = token_supplier
        self.transport = transport

    def lookup(self, invoice_id, sandbox):
        from .commerce_schemas import ReconcileCommerceOrder
        invoice_id = ReconcileCommerceOrder(invoiceId=invoice_id).invoiceId
        if type(sandbox) is not bool:
            raise ValueError('Explicit environment required')
        try:
            token = self.token_supplier()
            if not isinstance(token, str) or not token or len(token) > 16_384 or any(c.isspace() for c in token):
                raise ProviderUnavailable()
            # The documentation's historical page slug still says "purchase",
            # but its current normative GET path is /v2/invoices/{invoiceId}.
            path = '/public/' + ('sandbox/' if sandbox else '') + 'v2/invoices/' + invoice_id
            with httpx.Client(transport=self.transport, timeout=10, follow_redirects=False, trust_env=False) as client:
                with client.stream('GET', self.origin + path, headers={'Public-Token': token, 'Accept': 'application/json', 'Accept-Encoding': 'identity'}) as response:
                    if response.status_code != 200:
                        if response.status_code in (401, 403):
                            invalidate = getattr(self.token_supplier, 'invalidate', None)
                            if callable(invalidate):
                                invalidate()
                        raise ProviderUnavailable()
                    if response.headers.get('content-encoding', '').lower() not in ('', 'identity'):
                        raise InvalidProviderResponse()
                    chunks = bytearray()
                    for chunk in response.iter_bytes(chunk_size=16_384):
                        chunks.extend(chunk)
                        if len(chunks) > 65_536:
                            raise InvalidProviderResponse()
            value = json.loads(chunks, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
            if not isinstance(value, dict) or value.get('code') != 'OK' or not isinstance(value.get('body'), dict):
                raise InvalidProviderResponse()
            body = value['body']
            order = body['order']
            if not isinstance(order, dict):
                raise InvalidProviderResponse()
            amount = Decimal(str(order['amountCurrent']))
            if type(order['amountCurrent']) not in (int, float) or not amount.is_finite() or amount != amount.to_integral_value():
                raise InvalidProviderResponse()
            raw_invoice = body['invoiceId']
            if type(raw_invoice) is not int or raw_invoice < 1 or str(raw_invoice) != invoice_id or type(body['appId']) is not int:
                raise InvalidProviderResponse()
            strings = [body['purchaseId'], order['orderId'], order['itemCode'], body['appUserId'],
                       body['developerPayload'], order['currency'], body['invoiceStatus'], body['acknowledgementState']]
            if any(not isinstance(v, str) or not v or len(v) > 512 for v in strings):
                raise InvalidProviderResponse()
            return VerifiedInvoice(invoice_id, body['purchaseId'], body['appId'], sandbox,
                                   order['orderId'], order['itemCode'], body['appUserId'], body['developerPayload'],
                                   int(amount), order['currency'], body['invoiceStatus'].upper(), body['acknowledgementState'].upper())
        except (ProviderUnavailable, InvalidProviderResponse):
            raise
        except httpx.HTTPError:
            raise ProviderUnavailable() from None
        except (ValueError, TypeError, KeyError, InvalidOperation, UnicodeError):
            raise InvalidProviderResponse() from None
