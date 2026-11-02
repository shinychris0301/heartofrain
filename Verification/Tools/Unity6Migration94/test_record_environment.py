"""Host-only parsing controls; no Unity/CLI/Java/installer process is launched."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
SPEC = importlib.util.spec_from_file_location('record_environment94',
    Path(__file__).with_name('record_environment.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def result_fixture():
    identifiers = sorted(MODULE.EXPECTED_MODULES)
    return {'success': True, 'command': 'install-modules',
        'data': {'completedUids': identifiers,
                 'items': [{'uid': identifier, 'kind': 'module', 'status': 'installed'}
                           for identifier in identifiers]},
        'errors': [], 'warnings': ['Module install failed; retrying (attempt 1 of 2) in 2s...']}


class EnvironmentReceiptGuards(unittest.TestCase):
    def test_utf16_wrapped_terminal_result_retains_recovered_warning(self):
        payload = result_fixture()
        text = ('Adding module android...\nPowerShell NativeCommandError wrapper text\n' +
                json.dumps(payload, indent=2) + '\n')
        self.assertEqual(MODULE.parse_install_log(text.encode('utf-16')), payload)

    def test_utf8_terminal_result_is_supported(self):
        payload = result_fixture()
        self.assertEqual(MODULE.parse_install_log(json.dumps(payload).encode('utf-8')), payload)

    def test_truncated_or_nonterminal_result_cannot_certify_installation(self):
        encoded = json.dumps(result_fixture())
        for text in (encoded[:-3], encoded + '\nIncomplete second invocation'):
            with self.assertRaisesRegex(ValueError, 'complete terminal'):
                MODULE.parse_install_log(text.encode('utf-8'))

    def test_failed_result_and_errors_are_not_accepted(self):
        for change in ({'success': False}, {'errors': [{'code': 'FAILED'}]}):
            payload = result_fixture()
            payload.update(change)
            with self.assertRaisesRegex(ValueError, 'success without errors'):
                MODULE.parse_install_log(json.dumps(payload).encode())

    def test_missing_or_duplicate_completion_id_is_not_accepted(self):
        for duplicate in (False, True):
            payload = result_fixture()
            ids = payload['data']['completedUids']
            if duplicate:
                ids[-1] = ids[0]
            else:
                ids.pop()
            with self.assertRaisesRegex(ValueError, 'all 11'):
                MODULE.parse_install_log(json.dumps(payload).encode())

    def test_failed_item_or_wrong_kind_is_not_accepted(self):
        for key, value in (('status', 'failed'), ('kind', 'editor')):
            payload = result_fixture()
            payload['data']['items'][0][key] = value
            with self.assertRaisesRegex(ValueError, 'all 11'):
                MODULE.parse_install_log(json.dumps(payload).encode())

    def test_arbitrary_private_warning_is_never_exported(self):
        payload = result_fixture()
        payload['warnings'] = ['Unexpected provider/account diagnostic']
        with self.assertRaisesRegex(ValueError, 'root review'):
            MODULE.parse_install_log(json.dumps(payload).encode())

    def test_nonzero_wrapper_exit_is_retained_separately(self):
        observed = MODULE.outcome(result_fixture(), 1)
        self.assertEqual(observed['wrapperExitCode'], 1)
        self.assertFalse(observed['wrapperPassed'])
        self.assertTrue(observed['cliReportedSuccess'])
        self.assertIsNone(observed['cliProcessExitCode'])

    def test_java_requires_exact_build_and_architecture(self):
        valid = ('openjdk version "17.0.18" 2026-01-20\n'
                 'OpenJDK Runtime Environment Temurin-17.0.18+8 (build 17.0.18+8)\n'
                 'OpenJDK 64-Bit Server VM Temurin-17.0.18+8 (build 17.0.18+8, mixed mode)\n')
        self.assertEqual(MODULE.parse_java_version(valid)['runtimeBuild'], '17.0.18+8')
        for invalid in (valid.replace('17.0.18', '11.0.28'),
                        valid.replace('Temurin-17.0.18+8', 'DifferentBuild'),
                        valid.replace('64-Bit Server VM', 'Client VM')):
            with self.assertRaises(ValueError):
                MODULE.parse_java_version(invalid)

    def test_properties_ignore_comments_but_reject_repeated_keys(self):
        self.assertEqual(MODULE.properties('# note\nPkg.Revision = 27.2.12479018\n'
                         'Pkg.ReleaseName=r27c\nJAVA_VERSION="17.0.18"\n'),
                         {'Pkg.Revision': '27.2.12479018', 'Pkg.ReleaseName': 'r27c',
                          'JAVA_VERSION': '17.0.18'})
        with self.assertRaisesRegex(ValueError, 'Repeated property'):
            MODULE.properties('Pkg.Revision=27.2.12479018\nPkg.Revision=wrong\n')


if __name__ == '__main__':
    unittest.main(verbosity=2)
