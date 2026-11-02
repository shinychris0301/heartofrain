import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from hotr_backend import staging105, windows_vps_setup


class WindowsVpsSetupTests(unittest.TestCase):
    def test_generates_private_staging_files_without_starting_or_overwriting(self):
        backend = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='hotr-vps-') as temporary:
            base = Path(temporary)
            python, caddy = base / 'python.exe', base / 'caddy.exe'
            python.write_bytes(b'test')
            caddy.write_bytes(b'test')
            output, data = base / 'services', base / 'data'
            parameters = dict(backend_root=str(backend), python_exe=str(python),
                              caddy_exe=str(caddy), output_root=str(output), data_root=str(data))
            result = windows_vps_setup.prepare(**parameters)
            self.assertEqual(result['status'], 'prepared_only')
            self.assertFalse(result['servicesInstalled'])
            self.assertFalse(data.exists())
            manifest = staging105.read_manifest(output / 'staging-manifest.json')
            self.assertEqual(manifest.public_origin, windows_vps_setup.ORIGIN)
            self.assertEqual(manifest.identity_scope, windows_vps_setup.SCOPE)
            self.assertFalse(manifest.replay.enabled)
            self.assertFalse(manifest.vk.enabled)
            self.assertFalse(manifest.rewarded_ads_enabled)
            staging105.initialize_owned_data(output / 'staging-manifest.json')
            self.assertEqual(staging105.preflight(output / 'staging-manifest.json')['status'],
                             'staging_preflight_passed')
            app = json.loads((output / 'staging-build.json').read_text('utf-8'))
            self.assertEqual(app['origin'], manifest.public_origin)
            self.assertEqual(app['identityScope'], manifest.identity_scope)
            checked_in = backend.parent / 'Release/RuStore/WindowsVps/staging-build.novamind.json'
            self.assertEqual(app, json.loads(checked_in.read_text('utf-8')))
            self.assertIn('reverse_proxy 127.0.0.1:8751', (output / 'Caddyfile').read_text('utf-8'))
            for service in ('HOTRStaging', 'HOTRCaddy'):
                xml = ET.parse(output / (service + '.xml')).getroot()
                self.assertEqual(xml.findtext('serviceaccount/domain'), 'NT AUTHORITY')
                self.assertEqual(xml.findtext('serviceaccount/user'), 'LocalService')
                self.assertEqual(xml.findtext('id'), service)
                self.assertEqual(xml.find('log').attrib['mode'], 'roll-by-size')
            with self.assertRaises(ValueError):
                windows_vps_setup.prepare(**parameters)
            self.assertTrue((output / 'staging-manifest.json').is_file())


if __name__ == '__main__':
    unittest.main()
