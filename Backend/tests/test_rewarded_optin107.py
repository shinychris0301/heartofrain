"""Owned rollout and actual ASGI/SQLite reward recovery; no SDK or real provider."""
from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from hotr_backend import staging105 as staging
from hotr_backend.staging_ops105 import backup_staging, restore_staging
from hotr_backend.storage import Database


def ident():
    return uuid.uuid4().hex


class RewardedOptIn107Tests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {k: v for k, v in os.environ.items() if not k.startswith('HOTR_')}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-rewarded-optin107-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'manifest.json'
        self.value = dict(version=1, mode='staging', publicOrigin='https://staging.hotr-native-fixture.net', identityScope='review-rewarded107', deploymentId='rewarded-fixture107', dataDirectory=str(self.root / 'authority'), port=0,
                          vk=dict(enabled=False, clientId='', redirectUri=''), replay=dict(enabled=False, bundle='', approvalFile='', approvalSHA256=''))
        self.path.write_text(json.dumps(self.value), encoding='utf-8')
        self.disabled = staging.read_manifest(self.path)
        self.enabled = replace(self.disabled, rewarded_ads_enabled=True)
        staging.initialize_owned_data(self.disabled, restore_pending=True)
        Database(self.disabled.data_directory / staging.DATABASE)
        staging.complete_restore(self.disabled)
        self.now = 2_000_000_000
        self.clients = []
        self.addCleanup(self.close_clients)

    def close_clients(self):
        for client in self.clients:
            client.close()

    def client(self, manifest):
        with patch.dict(os.environ, {'HOTR_BACKEND_MODE': 'staging'}):
            app = staging._construct(manifest, None)
        app.state.authority.clock = lambda: self.now
        client = TestClient(app, raise_server_exceptions=False)
        self.clients.append(client)
        return client

    def snapshot(self):
        root = self.disabled.data_directory
        return {name: (root / name).read_bytes() for name in (staging.DATABASE, staging.MARKER, staging.COMMERCE)}

    @staticmethod
    def headers(owner):
        return {'Authorization': 'Bearer ' + owner['token']}

    def reserve_report(self, client, owner):
        headers = self.headers(owner)
        response = client.post('/v1/ads/rewarded/reserve', headers=headers, json={'commandId': ident(), 'placement': 'shop_rewarded'})
        self.assertEqual(response.status_code, 200)
        value = response.json()
        response = client.post('/v1/ads/rewarded/opportunities/' + value['opportunityId'] + '/client-completion', headers=headers, json={'commandId': ident()})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['state'], 'CompletedReported')
        self.assertFalse(response.json()['completionAuthoritative'])
        return value

    def coins(self, client, owner):
        return client.get('/v1/wallet', headers=self.headers(owner)).json()['coins']

    def test_omitted_flag_is_disabled_and_environment_cannot_enable_it(self):
        self.assertFalse(self.disabled.rewarded_ads_enabled)
        with patch.dict(os.environ, {'HOTR_REWARDED_ADS_ENABLED': '1', 'HOTR_ADS_ENABLED': '1'}):
            client = self.client(self.disabled)
            owner = client.app.state.authority.provision()
            self.assertFalse(client.get('/v1/ads/rewarded/status', headers=self.headers(owner)).json()['enabled'])
            self.assertFalse(staging.preflight(self.disabled)['adsEnabled'])

    def test_flag_is_strict_and_unknown_policy_fields_are_rejected(self):
        for value in (None, 0, 1, 'true', [], {}):
            self.path.write_text(json.dumps(dict(self.value, rewardedAdsEnabled=value)), encoding='utf-8')
            with self.subTest(value=type(value).__name__), self.assertRaises(staging.StagingError):
                staging.read_manifest(self.path)
        self.path.write_text(json.dumps(dict(self.value, rewardCoins=999)), encoding='utf-8')
        with self.assertRaises(staging.StagingError):
            staging.read_manifest(self.path)
        with self.assertRaises(staging.StagingError):
            staging.read_manifest(replace(self.disabled, rewarded_ads_enabled=1))

    def test_existing_root_requires_explicit_transition_without_db_or_owner_changes(self):
        before = self.snapshot()
        with self.assertRaises(staging.StagingError) as error:
            staging.preflight(self.enabled)
        self.assertEqual(error.exception.code, 'staging_rewarded_ads_transition_required')
        result = staging.configure_rewarded_ads(self.enabled)
        self.assertTrue(result['enabled'] and result['changed'])
        self.assertFalse(result['completionAuthoritative'] or result['productionEnabled'] or result['databaseChanged'])
        self.assertEqual(before, self.snapshot())
        self.assertTrue(staging.preflight(self.enabled)['adsEnabled'])
        self.assertFalse(staging.preflight(self.enabled)['adDeliveryVerified'])
        self.assertFalse(staging.configure_rewarded_ads(self.enabled)['changed'])
        with self.assertRaises(staging.StagingError):
            staging.preflight(self.disabled)

    def test_runtime_lock_refuses_policy_change_without_touching_files(self):
        original = (self.disabled.data_directory / staging.ADS).read_bytes()
        before = self.snapshot()
        with staging._lock(self.disabled, staging.RUNTIME_LOCK):
            with self.assertRaises(staging.StagingError) as error:
                staging.configure_rewarded_ads(self.enabled)
        self.assertEqual(error.exception.code, 'staging_owned_lock_busy')
        self.assertEqual(original, (self.disabled.data_directory / staging.ADS).read_bytes())
        self.assertEqual(before, self.snapshot())

    def test_noncanonical_or_changed_reward_policy_is_preserved_and_rejected(self):
        path = self.disabled.data_directory / staging.ADS
        value = json.loads(path.read_bytes())
        value['rewardCoins'] = 401
        raw = json.dumps(value).encode()
        path.write_bytes(raw)
        with self.assertRaises(staging.StagingError):
            staging.configure_rewarded_ads(self.enabled)
        self.assertEqual(path.read_bytes(), raw)

    def test_interrupted_transition_before_replace_is_retryable_without_data_loss(self):
        before = self.snapshot()
        original = (self.disabled.data_directory / staging.ADS).read_bytes()
        with patch.object(staging.os, 'replace', side_effect=OSError('synthetic-before-replace')):
            with self.assertRaises(staging.StagingError):
                staging.configure_rewarded_ads(self.enabled)
        self.assertEqual((self.disabled.data_directory / staging.ADS).read_bytes(), original)
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(list(self.disabled.data_directory.glob('.rewarded107-*.tmp')))
        self.assertTrue(staging.configure_rewarded_ads(self.enabled)['changed'])
        self.assertEqual(self.snapshot(), before)

    def test_transition_committed_before_lost_reply_is_recovered_once(self):
        before = self.snapshot()
        original_replace = staging.os.replace
        def committed(source, target):
            original_replace(source, target)
            raise OSError('synthetic-lost-acknowledgement')
        with patch.object(staging.os, 'replace', side_effect=committed):
            with self.assertRaises(staging.StagingError):
                staging.configure_rewarded_ads(self.enabled)
        self.assertTrue(staging.preflight(self.enabled)['adsEnabled'])
        self.assertFalse(staging.configure_rewarded_ads(self.enabled)['changed'])
        self.assertEqual(self.snapshot(), before)

    def test_restoring_root_cannot_be_reconfigured_before_completion(self):
        target = staging.manifest_for_data_directory(self.disabled, self.root / 'pending')
        staging.initialize_owned_data(target, restore_pending=True)
        before = (target.data_directory / staging.ADS).read_bytes()
        with self.assertRaises(staging.StagingError):
            staging.configure_rewarded_ads(replace(target, rewarded_ads_enabled=True))
        self.assertEqual((target.data_directory / staging.ADS).read_bytes(), before)

    def test_real_service_report_and_duplicate_claim_commit_one_fixed_reward(self):
        staging.configure_rewarded_ads(self.enabled)
        client = self.client(self.enabled)
        owner = client.app.state.authority.provision()
        value = self.reserve_report(client, owner)
        self.assertEqual(self.coins(client, owner), 1250)
        path = '/v1/ads/rewarded/opportunities/' + value['opportunityId']
        report_id = ident()
        for _ in range(2):
            self.assertEqual(client.post(path + '/client-completion', headers=self.headers(owner), json={'commandId': report_id}).status_code, 200)
        claim_id = ident()
        first = client.post(path + '/claim', headers=self.headers(owner), json={'commandId': claim_id}).json()
        self.assertEqual(first['receipt']['coins'], 400)
        self.assertFalse(first['completionAuthoritative'])
        self.assertEqual(first['receipt']['completionSource'], 'sdk_client_reported_capped')
        self.assertEqual(client.post(path + '/claim', headers=self.headers(owner), json={'commandId': claim_id}).json(), first)
        self.assertEqual(client.post(path + '/claim', headers=self.headers(owner), json={'commandId': ident()}).json()['receipt'], first['receipt'])
        self.assertEqual(self.coins(client, owner), 1650)
        with client.app.state.authority.database.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM rewards WHERE source='client_reported_ad'").fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM rewarded_ad_completions').fetchone()[0], 0)

    def test_restart_and_disable_preserve_pending_claim_quota_and_cooldown(self):
        staging.configure_rewarded_ads(self.enabled)
        client = self.client(self.enabled)
        owner = client.app.state.authority.provision()
        value = self.reserve_report(client, owner)
        client.close()
        staging.configure_rewarded_ads(self.disabled)
        restarted = self.client(self.disabled)
        path = '/v1/ads/rewarded/opportunities/' + value['opportunityId']
        self.assertEqual(restarted.get(path, headers=self.headers(owner)).json()['state'], 'CompletedReported')
        claim = ident()
        result = restarted.post(path + '/claim', headers=self.headers(owner), json={'commandId': claim}).json()
        self.assertEqual(result['state'], 'Claimed')
        self.assertEqual(self.coins(restarted, owner), 1650)
        self.assertEqual(restarted.post('/v1/ads/rewarded/reserve', headers=self.headers(owner), json={'commandId': ident(), 'placement': 'shop_rewarded'}).status_code, 503)
        restarted.close()
        staging.configure_rewarded_ads(self.enabled)
        again = self.client(self.enabled)
        status = again.get('/v1/ads/rewarded/status', headers=self.headers(owner)).json()
        self.assertEqual((status['claimedToday'], status['remainingToday'], status['cooldownRemainingSeconds']), (1, 2, 600))
        self.assertEqual(again.post(path + '/claim', headers=self.headers(owner), json={'commandId': claim}).json()['receipt'], result['receipt'])
        self.assertEqual(self.coins(again, owner), 1650)

    def test_fixed_cap_cooldown_and_player_local_zone_through_opted_in_service(self):
        staging.configure_rewarded_ads(self.enabled)
        client = self.client(self.enabled)
        owner = client.app.state.authority.provision()
        headers = self.headers(owner)
        status = client.get('/v1/ads/rewarded/status', headers=headers, params={'timeZoneId': 'Asia/Kolkata', 'utcOffsetSeconds': 19800}).json()
        self.assertEqual((status['timeZoneId'], status['utcOffsetSeconds'], status['dailyLimit'], status['cooldownSeconds']), ('Asia/Kolkata', 19800, 3, 600))
        for index in range(3):
            value = self.reserve_report(client, owner)
            path = '/v1/ads/rewarded/opportunities/' + value['opportunityId'] + '/claim'
            self.assertEqual(client.post(path, headers=headers, json={'commandId': ident()}).json()['receipt']['coins'], 400)
            if index < 2:
                self.assertEqual(client.post('/v1/ads/rewarded/reserve', headers=headers, json={'commandId': ident(), 'placement': 'shop_rewarded'}).status_code, 409)
                self.now += 600
        self.assertEqual(self.coins(client, owner), 2450)
        self.assertEqual(client.get('/v1/ads/rewarded/status', headers=headers).json()['remainingToday'], 0)

    def test_backup_restore_keeps_optin_and_pending_receipt_without_source_wallet_merge(self):
        staging.configure_rewarded_ads(self.enabled)
        client = self.client(self.enabled)
        owner = client.app.state.authority.provision()
        value = self.reserve_report(client, owner)
        source_nonce = staging.ownership_metadata(self.enabled)['nonce']
        backup_staging(self.enabled, 'pending-ad')
        restore_staging(self.enabled, 'pending-ad', 'restored')
        restored_manifest = staging.manifest_for_data_directory(self.enabled, self.enabled.data_directory / 'restores/restored')
        self.assertTrue(restored_manifest.rewarded_ads_enabled)
        self.assertTrue(staging.preflight(restored_manifest)['adsEnabled'])
        self.assertNotEqual(staging.ownership_metadata(restored_manifest)['nonce'], source_nonce)
        restored = self.client(restored_manifest)
        path = '/v1/ads/rewarded/opportunities/' + value['opportunityId']
        self.assertEqual(restored.get(path, headers=self.headers(owner)).json()['state'], 'CompletedReported')
        request = {'commandId': ident()}
        first = restored.post(path + '/claim', headers=self.headers(owner), json=request).json()
        self.assertEqual(restored.post(path + '/claim', headers=self.headers(owner), json=request).json(), first)
        self.assertEqual(self.coins(restored, owner), 1650)
        self.assertEqual(self.coins(client, owner), 1250)

    def test_public_app_export_remains_exact_six_fields(self):
        config = staging.app_configuration(self.enabled)
        self.assertEqual(set(config), {'version', 'mode', 'origin', 'identityScope', 'allowDevelopmentLoopback', 'socialEnabled'})
        self.assertNotIn('rewardedAdsEnabled', config)
        self.assertTrue(staging.manifest_mapping(self.enabled)['rewardedAdsEnabled'])


if __name__ == '__main__':
    unittest.main()
