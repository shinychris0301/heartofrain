"""Stopped owned upgrades on temporary exact10 fixtures; no server or device."""
from contextlib import closing, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend import staging105 as staging
from hotr_backend import staging_ops105 as snapshots
from hotr_backend import staging_upgrade109 as upgrade
from hotr_backend.operations import _validate, backup_database
from tests.legacy_schema_fixture import copy_legacy

CONFIG = Path(__file__).resolve().parents[1] / 'config'


def ident():
    return uuid.uuid4().hex


class StagingUpgrade109Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-upgrade109-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = 2_000_000_000
        self.manifest_path = self.root / 'manifest.json'
        value = dict(version=1, mode='staging', publicOrigin='https://staging.hotr-native-fixture.net',
                     identityScope='review-upgrade109', deploymentId='upgrade109-fixture',
                     dataDirectory=str(self.root / 'owned'), port=0, rewardedAdsEnabled=True,
                     vk=dict(enabled=False, clientId='', redirectUri=''),
                     replay=dict(enabled=False, bundle='', approvalFile='', approvalSHA256=''))
        self.manifest_path.write_text(json.dumps(value), encoding='utf-8')
        self.manifest = staging.read_manifest(self.manifest_path)
        staging.initialize_owned_data(self.manifest, restore_pending=True)
        self.db_path = self.manifest.data_directory / staging.DATABASE
        self.marker_path = self.manifest.data_directory / staging.MARKER
        seed = create_app(self.root / 'seed.sqlite3', CONFIG, lambda: self.now,
                          social_enabled=True, identity_enabled=True,
                          ads_config_path=self.manifest.data_directory / staging.ADS)
        self.owner = seed.state.authority.provision(lifetime=2_592_000)
        self.other = seed.state.authority.provision(lifetime=2_592_000)
        self.headers = {'Authorization': 'Bearer ' + self.owner['token']}
        with TestClient(seed) as client:
            self.command = dict(commandId=ident(), name='Historic Team', description='Stable records')
            r = client.post('/v1/teams', headers=self.headers, json=self.command)
            self.assertEqual(r.status_code, 200)
            self.team = r.json()['teamId']
            r = client.post('/v1/ads/rewarded/reserve', headers=self.headers,
                            json={'commandId': ident(), 'placement': 'shop_rewarded'})
            self.opportunity = r.json()['opportunityId']
            r = client.post('/v1/ads/rewarded/opportunities/' + self.opportunity + '/client-completion',
                            headers=self.headers, json={'commandId': ident()})
            self.assertEqual(r.json()['state'], 'CompletedReported')
        with seed.state.authority.database.connect() as source, closing(sqlite3.connect(self.db_path)) as target:
            copy_legacy(source, target, 10)
        # Reconstruct the historical exact10 Ready state through the real owned
        # restore transition. Only its imported current-version constant is
        # scoped to10; no marker bytes or ownership credentials are fabricated.
        with patch('hotr_backend.storage.SCHEMA_VERSION', 10):
            staging.complete_restore(self.manifest)
        self.original_marker = self.marker_path.read_bytes()
        self.original_logical = self.logical()

    def logical(self):
        with closing(sqlite3.connect(self.db_path)) as db:
            return upgrade._logical(db)

    def version(self):
        with closing(sqlite3.connect(self.db_path)) as db:
            return _validate(db)

    def proof(self, name='before-badges'):
        path = self.manifest.data_directory / 'backups' / (name + '.upgrade109.json')
        return json.loads(path.read_text())

    def run_upgrade(self, name='before-badges'):
        return upgrade.migrate_team_badges(self.manifest, name)

    def interrupt(self, stage, exception=OSError):
        def fault(point):
            if point == stage:
                raise exception('controlled-upgrade109-fault')
        with patch.object(upgrade, '_checkpoint', side_effect=fault):
            with self.assertRaises((upgrade.UpgradeError, exception)):
                self.run_upgrade()

    def assert_pending_closed(self, expected_version):
        self.assertEqual(self.version(), expected_version)
        self.assertEqual(json.loads(self.marker_path.read_text())['state'], upgrade.PENDING)
        with self.assertRaises(staging.StagingError):
            staging.preflight(self.manifest)
        with patch('hotr_backend.api.create_app') as factory:
            with self.assertRaises(staging.StagingError):
                staging._construct(self.manifest, None)
            factory.assert_not_called()
        with patch.object(staging.socket, 'socket') as socket:
            with self.assertRaises(staging.StagingError):
                staging.start(self.manifest)
            socket.assert_not_called()

    def test_01_exact_upgrade_preserves_owner_finance_pending_rewards_and_old_create_receipt(self):
        result = self.run_upgrade()
        self.assertEqual((result['fromSchema'], result['toSchema'], result['alreadyCompleted']), (10, 11, False))
        self.assertEqual(self.marker_path.read_bytes(), self.original_marker)
        self.assertEqual(self.logical(), self.original_logical)
        self.assertEqual(self.version(), 11)
        self.assertEqual(self.proof()['state'], 'Complete')
        snapshot = self.manifest.data_directory / 'backups/before-badges.schema10.sqlite3'
        with closing(sqlite3.connect(snapshot)) as db:
            self.assertEqual(_validate(db), 10)
        with patch.dict(os.environ, {'HOTR_BACKEND_MODE': 'staging'}):
            app = staging._construct(self.manifest, None)
        app.state.authority.clock = lambda: self.now
        with TestClient(app) as client:
            detail = client.get('/v1/teams/' + self.team, headers=self.headers).json()
            self.assertEqual(detail['badgeId'], 'drop')
            replay = client.post('/v1/teams', headers=self.headers, json=self.command).json()
            self.assertEqual(replay, {'teamId': self.team, 'state': 'Joined'})
            path = '/v1/ads/rewarded/opportunities/' + self.opportunity + '/claim'
            command = {'commandId': ident()}
            first = client.post(path, headers=self.headers, json=command).json()
            self.assertEqual(first['receipt']['coins'], 400)
            self.assertEqual(client.post(path, headers=self.headers, json=command).json(), first)
            self.assertEqual(client.get('/v1/wallet', headers=self.headers).json()['coins'], 1650)

    def test_02_exact_completed_retry_preserves_backup_database_and_marker(self):
        self.run_upgrade()
        before = (self.logical(), self.marker_path.read_bytes(), self.proof())
        self.assertTrue(self.run_upgrade()['alreadyCompleted'])
        self.assertEqual((self.logical(), self.marker_path.read_bytes(), self.proof()), before)

    def test_03_running_service_lock_blocks_before_any_backup_or_database_mutation(self):
        with staging._lock(self.manifest, staging.RUNTIME_LOCK):
            with self.assertRaises(staging.StagingError) as error:
                self.run_upgrade()
        self.assertEqual(error.exception.code, 'staging_owned_lock_busy')
        self.assertEqual(list((self.manifest.data_directory / 'backups').iterdir()), [])
        self.assertEqual((self.version(), self.logical(), self.marker_path.read_bytes()),
                         (10, self.original_logical, self.original_marker))

    def test_04_failure_after_backup_before_pending_is_retryable_without_migration(self):
        self.interrupt('AfterBackupReady')
        self.assertEqual((self.version(), self.marker_path.read_bytes()), (10, self.original_marker))
        self.assertEqual(self.proof()['state'], 'ReadyBackup')
        self.run_upgrade()
        self.assertEqual(self.version(), 11)

    def test_05_failure_before_commit_rolls_back_but_keeps_startup_closed_until_retry(self):
        self.interrupt('BeforeCommit')
        self.assert_pending_closed(10)
        self.assertEqual(self.logical(), self.original_logical)
        self.run_upgrade()
        self.assertEqual((self.version(), self.marker_path.read_bytes()), (11, self.original_marker))

    def test_06_postcommit_lost_reply_cannot_start_before_receipt_and_ready_recovery(self):
        self.interrupt('AfterCommit')
        self.assert_pending_closed(11)
        self.assertEqual(self.proof()['state'], 'ReadyBackup')
        self.assertEqual(self.logical(), self.original_logical)
        self.run_upgrade()
        self.assertEqual((self.proof()['state'], self.marker_path.read_bytes()), ('Complete', self.original_marker))

    def test_07_complete_receipt_before_ready_marker_failure_is_recoverable_and_closed(self):
        self.interrupt('AfterCompleteReceipt')
        self.assert_pending_closed(11)
        self.assertEqual(self.proof()['state'], 'Complete')
        self.run_upgrade()
        self.assertEqual(self.marker_path.read_bytes(), self.original_marker)

    def test_08_lost_ack_after_ready_marker_reconciles_without_another_migration(self):
        self.interrupt('AfterReadyMarker')
        self.assertEqual((self.version(), self.marker_path.read_bytes()), (11, self.original_marker))
        self.assertTrue(self.run_upgrade()['alreadyCompleted'])
        self.assertEqual(self.logical(), self.original_logical)

    def test_09_changed_snapshot_is_preserved_and_cannot_authorize_pending_migration(self):
        self.interrupt('BeforeCommit')
        path = self.manifest.data_directory / 'backups/before-badges.schema10.sqlite3'
        raw = path.read_bytes() + b'foreign'
        path.write_bytes(raw)
        with self.assertRaises(upgrade.UpgradeError):
            self.run_upgrade()
        self.assertEqual(path.read_bytes(), raw)
        self.assert_pending_closed(10)

    def test_10_foreign_receipt_owner_is_rejected_without_rewriting_it(self):
        self.interrupt('BeforeCommit')
        path = self.manifest.data_directory / 'backups/before-badges.upgrade109.json'
        value = self.proof()
        value['nonce'] = ident()
        raw = snapshots._bytes(value)
        path.write_bytes(raw)
        with self.assertRaises(upgrade.UpgradeError):
            self.run_upgrade()
        self.assertEqual(path.read_bytes(), raw)
        self.assert_pending_closed(10)

    def test_11_replaced_authority_file_is_not_silently_adopted_on_resume(self):
        self.interrupt('BeforeCommit')
        replacement = self.root / 'replacement.sqlite3'
        backup_database(self.db_path, replacement)
        self.assertTrue(self.db_path.resolve().is_relative_to(self.root.resolve()))
        self.db_path.unlink()
        os.replace(replacement, self.db_path)
        with self.assertRaises(upgrade.UpgradeError) as error:
            self.run_upgrade()
        self.assertEqual(error.exception.code, 'staging_upgrade_database_replaced')
        self.assert_pending_closed(10)

    def test_12_incomplete_backup_is_preserved_without_mutation_and_requires_fresh_name(self):
        def partial(source, destination, **kwargs):
            destination.write_bytes(b'partial controlled snapshot')
            raise OSError('controlled-backup-interruption')
        with patch.object(upgrade, 'backup_database', side_effect=partial):
            with self.assertRaises(upgrade.UpgradeError):
                self.run_upgrade()
        self.assertEqual((self.version(), self.logical(), self.marker_path.read_bytes()),
                         (10, self.original_logical, self.original_marker))
        with self.assertRaises(snapshots.StagingOpsError):
            self.run_upgrade()
        self.run_upgrade('new-reviewed-name')
        self.assertEqual((self.manifest.data_directory / 'backups/before-badges.schema10.sqlite3').read_bytes(),
                         b'partial controlled snapshot')

    def test_13_current_database_without_this_operation_proof_does_not_forge_an_upgrade(self):
        self.run_upgrade()
        with self.assertRaises(upgrade.UpgradeError) as error:
            self.run_upgrade('unrelated-new-name')
        self.assertEqual(error.exception.code, 'staging_upgrade_schema10_required')
        self.assertFalse((self.manifest.data_directory / 'backups/unrelated-new-name.schema10.sqlite3').exists())

    def test_14_cli_prints_only_fixed_safe_metadata_and_never_activation_or_credentials(self):
        output = StringIO()
        with redirect_stdout(output):
            code = upgrade.main(['--manifest', str(self.manifest_path), '--name', 'before-badges'])
        text = output.getvalue()
        self.assertEqual(code, 0)
        value = json.loads(text)
        self.assertEqual(value['status'], 'completed')
        self.assertFalse(value['productionEnabled'] or value['processStarted'] or value['ownershipNonceChanged'])
        self.assertNotIn(self.owner['token'], text)
        self.assertNotIn(str(self.manifest.data_directory), text)

    def test_15_invalid_operator_arguments_are_not_echoed_and_do_not_write_artifacts(self):
        output = StringIO()
        with redirect_stdout(output):
            code = upgrade.main(['--manifest', str(self.manifest_path), '--name', 'before-badges',
                                 '--unknown', 'synthetic-do-not-echo'])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())['code'], 'staging_upgrade_arguments_invalid')
        self.assertNotIn('synthetic-do-not-echo', output.getvalue())
        self.assertEqual(list((self.manifest.data_directory / 'backups').iterdir()), [])


if __name__ == '__main__':
    unittest.main()
