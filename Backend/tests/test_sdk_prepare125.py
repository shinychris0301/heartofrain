"""Stopped owned snapshot preparation; original authority never changes."""
from contextlib import closing
import copy
import hashlib
import json
import sqlite3
import unittest
import uuid
from unittest.mock import patch

from hotr_backend import production_runtime122 as runtime
from hotr_backend import sdk_prepare125 as prepare
from hotr_backend.operations import _validate
from hotr_backend.sdk_schema125 import validate_sdk_database
from production_fixture122 import ProductionFixture122

class SdkPreparation125Tests(unittest.TestCase):
    def setUp(self):
        self.fixture = ProductionFixture122()
        self.addCleanup(self.fixture.close)
        with self.fixture.context() as app, self.fixture.client(app) as client:
            self.identity, headers = self.fixture.provision(app)
            self.order = client.post('/v1/commerce/orders', json={
                'commandId': uuid.uuid4().hex, 'productId': 'wellkeeper'}, headers=headers).json()
            self.wallet = client.get('/v1/wallet', headers=headers).json()
        document = copy.deepcopy(self.fixture.document)
        catalog = copy.deepcopy(self.fixture.catalog)
        catalog['verificationMode'] = 'sdk_client_reported'
        path = self.fixture.root / 'sdk-catalog.json'
        path.write_text(json.dumps(catalog))
        document.update(verificationMode='sdk_client_reported', provider=None,
                        commerceConfig=str(path), commerceSHA256=hashlib.sha256(path.read_bytes()).hexdigest())
        self.sdk_path = self.fixture.root / 'sdk-manifest.json'
        self.sdk_path.write_text(json.dumps(document))
        self.sdk = runtime.read_manifest(self.sdk_path)
        self.database = self.fixture.manifest.data_directory / runtime.DATABASE

    def prepare(self, tag='owned'):
        return prepare.prepare_upgrade(self.fixture.manifest, self.sdk, tag=tag)

    def test_01_backup_backed_candidate_preserves_all_rows_ids_and_modes(self):
        source_before = self.database.read_bytes()
        marker_before = (self.fixture.manifest.data_directory / runtime.MARKER).read_bytes()
        result = self.prepare()
        self.assertEqual(result['status'], 'prepared_quarantined_sdk125')
        self.assertTrue(result['allOriginalTablesUnchanged'])
        candidate = self.fixture.manifest.data_directory / 'restores/sdk125-owned'
        with closing(sqlite3.connect(candidate / runtime.DATABASE)) as db:
            self.assertEqual(validate_sdk_database(db), 125)
            row = db.execute('SELECT id,player_id,verification_mode FROM commerce_orders').fetchone()
            self.assertEqual(row, (self.order['orderId'], self.identity['playerId'], 'provider_api'))
        with closing(sqlite3.connect(self.database)) as db:
            self.assertEqual(_validate(db), 15)
        self.assertEqual(self.database.read_bytes(), source_before)
        self.assertEqual((self.fixture.manifest.data_directory / runtime.MARKER).read_bytes(), marker_before)
        self.assertFalse((candidate / runtime.MARKER).exists())
        self.assertFalse(result['productionActivated'])
        with self.fixture.context() as app, self.fixture.client(app) as client:
            headers = {'Authorization': 'Bearer ' + self.identity['token']}
            self.assertEqual(client.get('/v1/wallet', headers=headers).json(), self.wallet)
        with self.assertRaises(runtime.ProductionError):
            with runtime.application_context(self.sdk):
                pass

    def test_02_running_api_lease_blocks_before_backup_or_candidate_creation(self):
        with self.fixture.context():
            with self.assertRaises(runtime.ProductionError):
                self.prepare()
        self.assertFalse((self.fixture.manifest.data_directory / 'restores/sdk125-owned').exists())

    def test_03_running_operations_lease_blocks_preparation(self):
        with self.fixture.context(purpose='operations'):
            with self.assertRaises(runtime.ProductionError):
                self.prepare()

    def test_04_failed_upgrade_rolls_back_candidate_and_keeps_source_exact15(self):
        def fault(stage):
            if stage == 'BeforeUpgradeCommit':
                raise RuntimeError('explicit_transaction_rollback')
        before = self.database.read_bytes()
        with patch.object(prepare, '_checkpoint', side_effect=fault):
            with self.assertRaises(RuntimeError):
                self.prepare()
        candidate = self.fixture.manifest.data_directory / 'restores/sdk125-owned'
        with closing(sqlite3.connect(candidate / runtime.DATABASE)) as db:
            self.assertEqual(_validate(db), 15)
        self.assertEqual(self.database.read_bytes(), before)
        self.assertEqual(json.loads((candidate / prepare.MARKER).read_text())['state'], 'Pending')
        with self.assertRaises(Exception):
            self.prepare()

    def test_05_interrupted_after_commit_candidate_stays_quarantined_and_source_restarts(self):
        def fault(stage):
            if stage == 'AfterUpgradeCommit':
                raise RuntimeError('explicit_post_commit_interruption')
        with patch.object(prepare, '_checkpoint', side_effect=fault):
            with self.assertRaises(RuntimeError):
                self.prepare()
        candidate = self.fixture.manifest.data_directory / 'restores/sdk125-owned'
        with closing(sqlite3.connect(candidate / runtime.DATABASE)) as db:
            self.assertEqual(validate_sdk_database(db), 125)
        self.assertEqual(json.loads((candidate / prepare.MARKER).read_text())['state'], 'Pending')
        self.assertFalse((candidate / runtime.MARKER).exists())
        with self.fixture.context() as app:
            self.assertFalse(app.state.commerce.database.sdk_commerce125)

    def test_06_identity_change_mode_ambiguity_or_path_traversal_rejected(self):
        self.assertRaises(runtime.ProductionError, self.prepare, '../escape')
        changed = copy.deepcopy(self.sdk.raw)
        changed['identityScope'] = 'prod-other'
        self.sdk_path.write_text(json.dumps(changed))
        other = runtime.read_manifest(self.sdk_path)
        with self.assertRaises(runtime.ProductionError):
            prepare.prepare_upgrade(self.fixture.manifest, other, tag='owned')
        with self.assertRaises(runtime.ProductionError):
            prepare.prepare_upgrade(self.fixture.manifest, self.fixture.manifest, tag='owned')

    def test_07_historical_api_order_cannot_be_reported_as_sdk_after_explicit_upgrade(self):
        self.prepare()
        candidate = self.fixture.manifest.data_directory / 'restores/sdk125-owned' / runtime.DATABASE
        from hotr_backend.api import create_app
        from hotr_backend.sdk_commerce_schemas125 import SdkPurchaseReport125
        from hotr_backend.service import Actor, ServiceError
        app = create_app(candidate, self.fixture.manifest.config_directory,
                         commerce_config_path=self.sdk.commerce_config)
        observation = {'invoiceId': '9999', 'purchaseId': str(uuid.uuid4()),
            'orderId': self.order['orderId'], 'productId': self.order['sdk']['productId'],
            'developerPayload': self.order['sdk']['developerPayload'], 'quantity': 1,
            'sandbox': False, 'status': 'CONFIRMED', 'purchaseType': 'ONE_STEP',
            'acknowledgementState': 'PENDING', 'productType': 'CONSUMABLE_PRODUCT',
            'amountMinor': self.order['amountMinor'], 'currency': 'RUB'}
        report = SdkPurchaseReport125.model_validate(observation)
        # Exercise the common commit guard directly: schema upgrade must never
        # reinterpret a historic API order even if given an SDK observation.
        with self.assertRaises(ServiceError) as caught:
            app.state.commerce._commit_observation(Actor(self.identity['playerId'], 1000),
                self.order['orderId'], report.invoiceId, report.purchaseId, report.status,
                report.acknowledgementState, verification_mode='sdk_client_reported', sdk_report=report)
        self.assertEqual(caught.exception.code, 'purchase_verification_mode_mismatch')

if __name__ == '__main__':
    unittest.main()

