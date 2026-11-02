"""Owned SDK125 fixture: synthetic SDK observations, actual SQLite; no payment proof."""
import hashlib
import json
import uuid
from production_fixture122 import ProductionFixture122
from hotr_backend import production_runtime122 as runtime

class SdkProductionFixture125(ProductionFixture122):
    def __init__(self, *, initialize=True):
        super().__init__(initialize=False)
        self.catalog['verificationMode'] = 'sdk_client_reported'
        self.catalog_path.write_text(json.dumps(self.catalog), encoding='utf-8')
        self.document['verificationMode'] = 'sdk_client_reported'
        self.document['provider'] = None
        self.document['commerceSHA256'] = hashlib.sha256(self.catalog_path.read_bytes()).hexdigest()
        for name in ('test-private-key-ref', 'test-notification-key-ref'):
            (self.root / name).unlink()
        self.write_manifest()
        self.sequence = 1000
        if initialize:
            runtime.initialize_owned_data(self.manifest)

    def observation(self, order, **changes):
        self.sequence += 1
        value = {'invoiceId': str(self.sequence), 'purchaseId': str(uuid.uuid4()),
                 'orderId': order['orderId'], 'productId': order['sdk']['productId'],
                 'developerPayload': order['sdk']['developerPayload'], 'quantity': 1,
                 'sandbox': order['sdk']['sandbox'], 'status': 'CONFIRMED',
                 'purchaseType': 'ONE_STEP', 'acknowledgementState': 'PENDING',
                 'productType': 'CONSUMABLE_PRODUCT', 'amountMinor': order['amountMinor'],
                 'currency': order['currency']}
        value.update(changes)
        return value

