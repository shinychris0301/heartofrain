"""Host counterexamples only; no HTTP, signature process, installer or Hub cache."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('official_download95', Path(__file__).with_name('official_download95.py'))
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class DownloadControls(unittest.TestCase):
    def assert_timing(self, report):
        self.assertTrue(report['startedUtc'].endswith('Z'))
        self.assertTrue(report['finishedUtc'].endswith('Z'))
        self.assertGreaterEqual(report['elapsedSeconds'], 0)

    def test_signature_powershell_is_hidden_without_real_process(self):
        value = SimpleNamespace(returncode=0, stdout=json.dumps({'Status': 'Valid', 'SignerSubject': 'Unity Technologies'}))
        with patch.object(M.subprocess, 'run', return_value=value) as run:
            self.assertEqual(M.authenticode(Path('not-executed.exe'))['Status'], 'Valid')
        self.assertEqual(run.call_args.kwargs['creationflags'], M.subprocess.CREATE_NO_WINDOW)

    def test_prepare_failure_keeps_timing_and_redacted_public_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            private, public = Path(temp)/'private', Path(temp)/'public'
            with patch.object(M, 'PRIVATE', private), patch.object(M, 'PUBLIC', public), \
                    patch.object(M, 'stopped_pid', side_effect=ValueError('Download95CLIStillRunning')):
                with self.assertRaisesRegex(ValueError, 'StillRunning'):
                    M.prepare(Path('cache-not-read.exe'), 10, private/'Set01', public/'PrepareSet01')
            record = M.read(public/'PrepareSet01/Report.json')
            self.assert_timing(record)
            self.assertEqual(record['status'], 'FAIL_PREPARATION95')
            self.assertNotIn('privateOriginalPath', record)
            self.assertFalse((private/'Set01/editor').exists())

    def test_download_preflight_failure_keeps_timing_without_http(self):
        with tempfile.TemporaryDirectory() as temp:
            private, public = Path(temp)/'private', Path(temp)/'public'
            prepared = private/'Set01/Preparation.json'; prepared.parent.mkdir(parents=True)
            prepared.write_text(json.dumps({'status': 'bad'}), encoding='utf-8')
            with patch.object(M, 'PRIVATE', private), patch.object(M, 'PUBLIC', public):
                with self.assertRaisesRegex(ValueError, 'Binding'):
                    M.download(prepared, 'editor', 60, public/'DownloadSet01')
            record = M.read(public/'DownloadSet01/Report.json')
            self.assert_timing(record)
            self.assertEqual(record['status'], 'FAIL_INDEPENDENT_DOWNLOAD95')
            self.assertFalse(record['trustedInstaller'])

    def test_parallel_completion_returns_exact_start_order(self):
        completed = []
        def fetch(info, start, end, deadline):
            if start == 0:
                time.sleep(0.04)
            completed.append(start)
            return bytearray([start]) * (end-start+1)
        with patch.object(M, 'CHUNK', 2):
            result = M.ordered_batch({'bytes': 8}, 0, 4, time.monotonic()+2, fetch)
        self.assertNotEqual(completed[0], 0)
        self.assertEqual([item[0] for item in result], [0,2,4,6])
        self.assertEqual(b''.join(item[1] for item in result), b'\0\0\2\2\4\4\6\6')

    def test_failed_batch_exposes_no_partial_batch_to_append(self):
        appended = []
        def fetch(info, start, end, deadline):
            if start == 2:
                raise ValueError('bad-range')
            return bytearray(end-start+1)
        with patch.object(M, 'CHUNK', 2):
            with self.assertRaisesRegex(ValueError, 'bad-range'):
                batch = M.ordered_batch({'bytes': 8}, 0, 4, time.monotonic()+2, fetch)
                appended.extend(batch)
        self.assertEqual(appended, [])

    def test_short_final_range_has_no_gap_or_padding(self):
        fetch = lambda info, start, end, deadline: bytearray(end-start+1)
        with patch.object(M, 'CHUNK', 2):
            result = M.ordered_batch({'bytes': 5}, 0, 4, time.monotonic()+2, fetch)
        self.assertEqual([(start,len(block)) for start,block in result], [(0,2),(2,2),(4,1)])

    def test_parallel_wrong_length_refused(self):
        with patch.object(M, 'CHUNK', 2):
            with self.assertRaisesRegex(ValueError, 'Length'):
                M.ordered_batch({'bytes': 8}, 0, 4, time.monotonic()+2, lambda *args: b'x')

    def test_truncated_http_body_refused(self):
        class Response:
            status = 206
            headers = {'Content-Range':'bytes 0-3/4','Content-Length':'4'}
            body = b'ab'
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def geturl(self): return M.component_info('editor')['url']
            def readinto(self, view):
                count = min(len(view),len(self.body));view[:count]=self.body[:count];self.body=self.body[count:];return count
            def read(self,count): return b''
        class Opener:
            def open(self,*args,**kwargs): return Response()
        with self.assertRaisesRegex(ValueError,'Truncated'):
            M.range_bytes(Opener(),M.component_info('editor')['url'],0,3,4,time.monotonic()+2)

    def test_exact_official_metadata(self):
        self.assertEqual(M.component_info('editor')['bytes'], 4235893440)
        self.assertEqual(M.component_info('android')['md5'], 'cfe45daf03586b1840752d62e0704b8b')

    def test_http_and_foreign_credentials_refused(self):
        for url in ['http://download.unity3d.com/a', 'https://example.com/a',
                    'https://user:secret@download.unity3d.com/a', 'https://download.unity3d.com/a?token=x']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                M.safe_url(url)

    def test_exact206(self):
        M.validate_range(206, {'Content-Range': 'bytes 4-7/20', 'Content-Length': '4'}, 4, 7, 20)

    def test_full200_refused(self):
        with self.assertRaisesRegex(ValueError, '206'):
            M.validate_range(200, {'Content-Range': 'bytes 4-7/20', 'Content-Length': '4'}, 4, 7, 20)

    def test_range_total_or_offset_refused(self):
        for value in ['bytes 0-3/20', 'bytes 4-7/21', 'bytes 4-7/*']:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'Range'):
                M.validate_range(206, {'Content-Range': value, 'Content-Length': '4'}, 4, 7, 20)

    def test_length_and_encoding_refused(self):
        for extra in [{'Content-Length': '5'}, {'Content-Encoding': 'gzip'}]:
            headers = {'Content-Range': 'bytes 4-7/20', 'Content-Length': '4', **extra}
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                M.validate_range(206, headers, 4, 7, 20)

    def test_stable_partial_copy_is_untrusted(self):
        with tempfile.TemporaryDirectory() as temp:
            source, target = Path(temp)/'source', Path(temp)/'target'
            source.write_bytes(b'MZ' + b'x' * M.PREFIX)
            value = M.stable_copy(source, target)
            self.assertEqual(source.read_bytes(), target.read_bytes())
            self.assertFalse(value['trustedInstaller'])
            self.assertEqual(value['partialMD5'], hashlib.md5(source.read_bytes()).hexdigest())

    def test_non_pe_prefix_retained_but_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            source, target = Path(temp)/'source', Path(temp)/'target'
            source.write_bytes(b'not-an-installer' + b'x' * M.PREFIX)
            with self.assertRaisesRegex(ValueError, 'Prefix'):
                M.stable_copy(source, target)
            self.assertEqual(source.read_bytes(), target.read_bytes())

    def test_expired_deadline_before_http(self):
        class NoHTTP:
            def open(self, *args, **kwargs):
                raise AssertionError('HTTP reached')
        with self.assertRaisesRegex(ValueError, 'Deadline'):
            M.range_bytes(NoHTTP(), M.component_info('editor')['url'], 0, 3, 20, time.monotonic()-1)

    def test_unfinished_or_wrong_hash_never_reaches_signature(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'setup.exe';path.write_bytes(b'bad')
            for size in [4, 3]:
                with self.subTest(size=size), self.assertRaises(ValueError):
                    M.verified_file(path, {'bytes': size, 'md5': '0'*32}, lambda _: self.fail('signature reached'))

    def test_complete_hash_signature_record(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'setup.exe';path.write_bytes(b'complete')
            info = {'bytes': 8, 'md5': hashlib.md5(b'complete').hexdigest()}
            result = M.verified_file(path, info, lambda _: {'Status': 'Valid', 'SignerSubject': 'Unity Technologies'})
            self.assertEqual(result['sha256'], hashlib.sha256(b'complete').hexdigest())


if __name__ == '__main__':
    unittest.main()
