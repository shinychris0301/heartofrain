"""Explicit scripted provider/worker fixture; never real provider/model acceptance."""
from contextlib import ExitStack, contextmanager
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import socket
import tempfile
from unittest.mock import patch
import uuid

from fastapi.testclient import TestClient

from hotr_backend import production_runtime122 as runtime
from hotr_backend.rustore_provider import VerifiedInvoice
from tests.test_replay_service import ScriptedWorker

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'Backend/config'


class ScriptedPurchaseProvider122:
    configured = True
    def __init__(self):
        self.values, self.calls = {}, []
    def lookup(self, invoice_id, sandbox):
        self.calls.append((invoice_id, sandbox))
        return self.values[invoice_id]


class ProductionFixture122:
    def __init__(self, *, initialize=True, ads_enabled=False):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-production122-scripted-')
        self.root = Path(self.temp.name)
        self.now = 100 * 86400 + 1000
        self.provider = ScriptedPurchaseProvider122()
        self.worker = ScriptedWorker()
        self.catalog_path = self.root / 'commerce.json'
        self.catalog = json.loads((ROOT / 'Release/RuStore/commerce.example.json').read_text('utf-8-sig'))
        self.catalog.update(enabled=True, sandbox=False, appId=123)
        for p in self.catalog['products']:
            p['enabled'] = True
        self.catalog_path.write_text(json.dumps(self.catalog), encoding='utf-8')
        (self.root / 'test-private-key-ref').write_bytes(b'explicit-placeholder-not-a-provider-key')
        (self.root / 'test-notification-key-ref').write_bytes(b'explicit-placeholder-not-a-provider-key')
        (self.root / 'worker-bundle').mkdir()
        (self.root / 'worker-approval.json').write_text('{}', encoding='utf-8')
        with socket.socket() as reserve:
            reserve.bind(('127.0.0.1', 0))
            port = reserve.getsockname()[1]
        self.document = {
            'version': 1, 'mode': 'production',
            'publicOrigin': 'https://api.owned-production-fixture.ru',
            'identityScope': 'prod-explicit-scripted-fixture',
            'deploymentId': uuid.uuid4().hex,
            'dataDirectory': str(self.root / 'authority'), 'port': port,
            'configDirectory': str(CONFIG), 'commerceConfig': str(self.catalog_path),
            'commerceSHA256': hashlib.sha256(self.catalog_path.read_bytes()).hexdigest(),
            'provider': {'keyId': 'synthetic-key-id',
                         'privateKeyFile': str(self.root / 'test-private-key-ref'),
                         'notificationKeyFile': str(self.root / 'test-notification-key-ref'),
                         'allowedNetworks': sorted(runtime.PROVIDER_NETWORKS)},
            'replay': {'bundle': str(self.root / 'worker-bundle'),
                       'approvalFile': str(self.root / 'worker-approval.json'), 'approvalSHA256': 'a' * 64},
            'vk': {'enabled': False, 'clientId': '', 'redirectUri': ''},
            'ads': {'enabled': False, 'configFile': '', 'configSHA256': '',
                    'acceptClientReportedCompletion': False},
            'ingress': {'trustedProxyPeer': '127.0.0.1',
                        'clientAddressHeader': 'X-Hotr-Verified-Client-IP'},
        }
        if ads_enabled:
            self.ad_path = self.root / 'ads.json'
            self.ad_path.write_text(json.dumps({'version': 'explicit-scripted-122', 'enabled': True,
                'completionMode': 'sdk_client_reported_capped'}), encoding='utf-8')
            self.document['ads'] = {'enabled': True, 'configFile': str(self.ad_path),
                'configSHA256': hashlib.sha256(self.ad_path.read_bytes()).hexdigest(),
                'acceptClientReportedCompletion': True}
        self.manifest_path = self.root / 'production.json'
        self.write_manifest()
        if initialize:
            runtime.initialize_owned_data(self.manifest)

    def write_manifest(self):
        self.manifest_path.write_text(json.dumps(self.document), encoding='utf-8')
        self.manifest = runtime.read_manifest(self.manifest_path)

    @contextmanager
    def context(self, *, purpose='api'):
        with ExitStack() as stack:
            stack.enter_context(patch('hotr_backend.production_runtime122._create_worker', return_value=self.worker))
            stack.enter_context(patch('hotr_backend.rustore_provider.RuStoreInvoiceProvider', return_value=self.provider))
            app = stack.enter_context(runtime.application_context(self.manifest, purpose=purpose, clock=lambda: self.now))
            yield app

    @staticmethod
    def client(app, *, peer='127.0.0.1'):
        return TestClient(app, raise_server_exceptions=False, client=(peer, 12345),
                          headers={'X-Hotr-Verified-Client-IP': '198.51.100.20'})

    @staticmethod
    def provision(app):
        identity = app.state.authority.provision(lifetime=2_592_000)
        return identity, {'Authorization': 'Bearer ' + identity['token']}

    def invoice(self, order, *, status='CONFIRMED', **changes):
        number = str(1000 + len(self.provider.values))
        sku = order['sdk']
        value = VerifiedInvoice(number, str(uuid.uuid4()), 123, False, order['orderId'],
            sku['productId'], order['playerId'], sku['developerPayload'], order['amountMinor'],
            order['currency'], status, 'PENDING')
        self.provider.values[number] = replace(value, **changes)
        return number

    def close(self):
        self.temp.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
