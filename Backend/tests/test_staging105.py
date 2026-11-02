"""Controlled staging lifecycle/config tests; not hosting/provider acceptance."""
from dataclasses import replace
import json
import os
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from hotr_backend import staging105 as staging
from hotr_backend.storage import Database


class Staging105Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.path = self.base / 'manifest.json'
        self.value = dict(version=1, mode='staging', publicOrigin='https://staging.hotr-native-fixture.net', identityScope='review-vk-staging', deploymentId='controlled-staging', dataDirectory=str(self.base / 'authority'), port=0,
                          vk=dict(enabled=False, clientId='', redirectUri=''), replay=dict(enabled=False, bundle='', approvalFile='', approvalSHA256=''))
        self.write()

    def write(self):
        self.path.write_text(json.dumps(self.value), encoding='utf-8')
        return self.path

    def initialized(self, pending=False):
        manifest = staging.read_manifest(self.path)
        staging.initialize_owned_data(manifest, restore_pending=pending)
        return manifest

    def ready(self):
        manifest = self.initialized(True)
        Database(manifest.data_directory / staging.DATABASE)
        staging.complete_restore(manifest)
        return manifest

    def test_unconfigured_example_blocks_without_mutation(self):
        self.value['publicOrigin'] = ''
        self.write()
        before = set(self.base.rglob('*'))
        with self.assertRaises(staging.StagingError):
            staging.initialize_owned_data(self.path)
        self.assertEqual(set(self.base.rglob('*')), before)
        self.assertFalse(Path(self.value['dataDirectory']).exists())

    def test_unknown_duplicate_and_bad_scalar_types_rejected(self):
        for change in (dict(apiSecret='synthetic-never-print'), dict(version=True), dict(port=True), dict(mode='production'), dict(identityScope='production'), dict(deploymentId=''), dict(publicOrigin='https://example.com')):
            value = dict(self.value, **change)
            self.path.write_text(json.dumps(value), encoding='utf-8')
            with self.subTest(change=tuple(change)), self.assertRaises(staging.StagingError):
                staging.read_manifest(self.path)
        raw = json.dumps(self.value)
        self.path.write_text(raw[:-1] + ',"port":8751}', encoding='utf-8')
        with self.assertRaises(staging.StagingError):
            staging.read_manifest(self.path)

    def test_initialize_and_preflight_are_database_free(self):
        m = self.initialized()
        before = {p.relative_to(m.data_directory).as_posix(): p.read_bytes() for p in m.data_directory.rglob('*') if p.is_file()}
        result = staging.preflight(m)
        self.assertEqual(result['state'], 'Initialized')
        self.assertFalse(result['gameplayEnabled'])
        self.assertFalse(result['providerAcceptanceVerified'])
        self.assertFalse(result['commerceEnabled'])
        self.assertFalse(result['adsEnabled'])
        self.assertFalse(result['databaseStructureChecked'])
        self.assertEqual(before, {p.relative_to(m.data_directory).as_posix(): p.read_bytes() for p in m.data_directory.rglob('*') if p.is_file()})
        self.assertFalse((m.data_directory / staging.DATABASE).exists())

    def test_initializer_preserves_existing_data(self):
        root = Path(self.value['dataDirectory'])
        root.mkdir()
        (root / 'unknown.sqlite3').write_bytes(b'foreign')
        with self.assertRaises(staging.StagingError):
            staging.initialize_owned_data(self.path)
        self.assertEqual((root / 'unknown.sqlite3').read_bytes(), b'foreign')
        self.assertFalse((root / staging.MARKER).exists())

    def test_initial_database_ambiguity_blocks_before_factory(self):
        m = self.initialized()
        database = m.data_directory / staging.DATABASE
        database.write_bytes(b'interrupted-created-database')
        with patch.object(staging, '_construct') as construct, self.assertRaises(staging.StagingError) as error:
            staging.start(m)
        self.assertEqual(error.exception.code, 'staging_initialized_database_ambiguous')
        construct.assert_not_called()
        self.assertEqual(database.read_bytes(), b'interrupted-created-database')

    def test_ready_missing_database_never_reinitializes(self):
        m = self.ready()
        (m.data_directory / staging.DATABASE).unlink()
        with patch.object(staging, '_construct') as construct, self.assertRaises(staging.StagingError) as error:
            staging.start(m)
        self.assertEqual(error.exception.code, 'staging_ready_database_missing')
        construct.assert_not_called()
        self.assertFalse((m.data_directory / staging.DATABASE).exists())

    def test_pending_restore_requires_complete_valid_current_database(self):
        m = self.initialized(True)
        with self.assertRaises(staging.StagingError):
            staging.preflight(m)
        with self.assertRaises(staging.StagingError):
            staging.complete_restore(m)
        self.assertEqual(staging.ownership_metadata(m, allowed_states=('RestorePending',))['state'], 'RestorePending')
        Database(m.data_directory / staging.DATABASE)
        self.assertEqual(staging.complete_restore(m)['state'], 'Ready')
        self.assertEqual(staging.preflight(m)['state'], 'Ready')

    def test_failed_restore_validation_keeps_pending(self):
        m = self.initialized(True)
        (m.data_directory / staging.DATABASE).write_bytes(b'invalid restore')
        with self.assertRaises(staging.StagingError):
            staging.complete_restore(m)
        self.assertEqual(staging.ownership_metadata(m, allowed_states=('RestorePending',))['state'], 'RestorePending')

    def test_marker_binds_authority_but_not_optional_settings(self):
        m = self.initialized()
        metadata = staging.ownership_metadata(m, allowed_states=('Initialized',))
        self.assertEqual(staging.ownership_metadata(replace(m, port=8751), allowed_states=('Initialized',))['nonce'], metadata['nonce'])
        enabled = replace(m, vk=staging.VkSettings(True, '1234567', m.public_origin + '/v1/identity/vk/callback'))
        self.assertEqual(staging.ownership_metadata(enabled, allowed_states=('Initialized',))['nonce'], metadata['nonce'])
        for changed in (replace(m, deployment_id='other-deployment'), replace(m, identity_scope='review-other'), replace(m, public_origin='https://other.hotr-native-fixture.net')):
            with self.assertRaises(staging.StagingError):
                staging.ownership_metadata(changed, allowed_states=('Initialized',))

    def test_environment_drops_payment_provider_proxy_and_python_injection(self):
        m = staging.read_manifest(self.path)
        ambient = dict(PATH='system-path', SystemRoot='system-root', HOTR_RUSTORE_KEY_ID='synthetic', HOTR_RUSTORE_PRIVATE_KEY_FILE='synthetic', HOTR_VK_ID_ENABLED='1', HOTR_GAMEPLAY_REPLAY_ENABLED='1', HTTPS_PROXY='synthetic', PYTHONPATH='synthetic', UVICORN_HOST='0.0.0.0')
        safe = staging.child_environment(m, ambient)
        self.assertNotIn('HOTR_RUSTORE_KEY_ID', safe)
        self.assertNotIn('HOTR_RUSTORE_PRIVATE_KEY_FILE', safe)
        for key in ('HTTPS_PROXY', 'PYTHONPATH', 'UVICORN_HOST'):
            self.assertNotIn(key, safe)
        self.assertEqual(safe['HOTR_VK_ID_ENABLED'], '0')
        self.assertEqual(safe['HOTR_GAMEPLAY_REPLAY_ENABLED'], '0')
        self.assertEqual(safe['HOTR_BACKEND_MODE'], 'staging')

    def test_control_lock_is_exclusive_and_released(self):
        m = self.initialized()
        with staging.root_lock(m):
            with self.assertRaises(staging.StagingError):
                with staging.root_lock(m):
                    self.fail('second lock admitted')
        with staging.root_lock(m):
            pass

    def test_occupied_loopback_port_does_not_create_database(self):
        m = self.initialized()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied:
            occupied.bind(('127.0.0.1', 0))
            occupied.listen(1)
            m = replace(m, port=occupied.getsockname()[1])
            with patch.object(staging, '_construct') as construct, self.assertRaises(staging.StagingError) as error:
                staging.start(m)
            self.assertEqual(error.exception.code, 'staging_loopback_bind_unavailable')
            construct.assert_not_called()
        self.assertFalse((m.data_directory / staging.DATABASE).exists())

    def test_factory_failure_leaves_ambiguous_initial_data_blocked(self):
        m = self.initialized()
        def failed(manifest, worker):
            Database(manifest.data_directory / staging.DATABASE)
            raise staging.StagingError('synthetic_factory_failure')
        with patch.dict(os.environ, dict(os.environ), clear=True), patch.object(staging, '_construct', side_effect=failed):
            original = dict(os.environ)
            with self.assertRaises(staging.StagingError):
                staging.start(m)
            self.assertEqual(dict(os.environ), original)
        self.assertEqual(staging.ownership_metadata(m, allowed_states=('Initialized',))['state'], 'Initialized')
        with self.assertRaises(staging.StagingError) as error:
            staging.preflight(m)
        self.assertEqual(error.exception.code, 'staging_initialized_database_ambiguous')

    def test_app_export_only_six_fields_and_no_overwrite(self):
        m = staging.read_manifest(self.path)
        target = self.base / 'app.json'
        result = staging.export_app_configuration(m, target)
        self.assertEqual(result['status'], 'staging_app_configuration_exported')
        data = json.loads(target.read_bytes())
        self.assertEqual(set(data), {'version', 'mode', 'origin', 'identityScope', 'allowDevelopmentLoopback', 'socialEnabled'})
        self.assertEqual(data['origin'], m.public_origin)
        before = target.read_bytes()
        with self.assertRaises(staging.StagingError):
            staging.export_app_configuration(m, target)
        self.assertEqual(target.read_bytes(), before)

    def test_invalid_export_never_creates_output(self):
        self.value['publicOrigin'] = ''
        self.write()
        target = self.base / 'absent.json'
        with self.assertRaises(staging.StagingError):
            staging.export_app_configuration(self.path, target)
        self.assertFalse(target.exists())

    def test_source_tree_and_disabled_provider_garbage_rejected(self):
        for raw in (str(staging.REPO / 'Backend/.local'), str(staging.REPO / 'Unity/Assets/Resources')):
            self.value['dataDirectory'] = raw
            self.write()
            with self.assertRaises(staging.StagingError):
                staging.read_manifest(self.path)
        self.value['dataDirectory'] = str(self.base / 'authority')
        self.value['vk']['clientId'] = '1234567'
        self.write()
        with self.assertRaises(staging.StagingError):
            staging.read_manifest(self.path)

    def test_network_and_filesystem_root_rejected_before_stat(self):
        for raw in (r'\\uncontacted-server\share\authority', '//uncontacted-server/share/authority', self.base.anchor):
            with self.subTest(raw=raw), patch.object(staging, '_plain') as plain, self.assertRaises(staging.StagingError):
                staging._private_path(raw)
            plain.assert_not_called()


if __name__ == '__main__':
    unittest.main()
