"""Protocol/allowlist and real Windows process limits; not Unity replay proof."""
import copy
import concurrent.futures
import json
import os
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from hotr_backend.replay_contract import ApprovedWorker, ReplayError, TrustedModelFault, MAX_BYTES, _run_windows_bounded, encode_job, sha256, strict_json, validate_job, validate_output


def ident():
    return uuid.uuid4().hex


def receipt():
    return 'wallet/' + sha256(ident().encode())


class ReplayContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-replay-contract-')
        self.root = Path(self.temp.name)
        self.bundle, self.jobs = self.root / 'bundle', self.root / 'jobs'
        self.bundle.mkdir(); self.jobs.mkdir()
        self.job = {'version': 1, 'level': 1, 'initialMoves': 26, 'seed': 4_294_967_295,
            'jobId': ident(), 'playerId': ident(), 'attemptId': ident(), 'pinsSHA256': 'a' * 64,
            'levelSHA256': 'b' * 64, 'startReceiptId': receipt(), 'starting': [0, 1, 0, 1],
            'actions': [], 'receipts': []}

    def tearDown(self):
        self.temp.cleanup()

    def action(self, kind='Swap', index=0):
        return {'index': index, 'kind': kind, 'ax': 1, 'ay': 1, 'bx': 1 if kind == 'Swap' else -1,
                'by': 2 if kind == 'Swap' else -1, 'tool': -1, 'movesAfter': 0, 'receiptId': ''}

    def add_receipt(self, action):
        action['receiptId'] = receipt()
        self.job['receipts'].append({'receiptId': action['receiptId'], 'attemptId': self.job['attemptId'], 'kind': action['kind'],
            'actionIndex': action['index'], 'tool': action['tool'], 'coins': 900 if action['kind'] == 'Continue' else 0,
            'quantity': 1 if action['kind'] == 'Tool' else 0, 'movesAfter': action['movesAfter']})

    def output(self):
        moves, turn, actions = self.job['initialMoves'], 0, []
        for index, action in enumerate(self.job['actions']):
            if action['kind'] in ('Swap', 'Tap'): moves -= 1; turn += 1
            elif action['kind'] == 'Continue': moves = 5
            actions.append({'index': index, 'kind': action['kind'], 'moves': moves, 'turn': turn,
                            'status': 'Playing', 'checkpointSHA256': 'c' * 64})
        return {'version': 1, 'level': self.job['level'], 'actions': len(actions), 'moves': moves, 'turn': turn,
            'remainingGoals': 20, 'status': 'PASS_PINNED_MODEL_REPLAY', 'code': '', 'unity': '2022.3.62f3',
            'jobSHA256': sha256(encode_job(self.job)), 'pinsSHA256': self.job['pinsSHA256'],
            'levelSHA256': self.job['levelSHA256'], 'checkpointSHA256': 'c' * 64, 'outcome': 'Playing',
            'productionEnabled': False, 'financialMutation': False, 'actionResults': actions}

    def approval(self):
        # Deliberately fake binary fixture validates allowlisting only, never
        # passes for an actual Unity/Windows model execution.
        (self.bundle / 'PinnedReplayWorker.exe').write_bytes(b'not-an-executable-fixture')
        levels = []
        for number in range(1, 51):
            relative = f'Levels/C01_L{number:03}.json'
            path = self.bundle / 'ReplayPins' / relative
            path.parent.mkdir(parents=True, exist_ok=True); path.write_text('{"fixture":true}')
            levels.append({'level': number, 'id': f'C01_L{number:03}', 'path': relative, 'sha256': sha256(path.read_bytes()), 'moves': 26})
        pins_path = self.bundle / 'ReplayPins/manifest.json'
        pins_path.write_text(json.dumps({'version': 1, 'unity': '2022.3.62f3', 'levels': levels}))
        files = {path.relative_to(self.bundle).as_posix(): sha256(path.read_bytes()) for path in self.bundle.rglob('*') if path.is_file()}
        approval = {'version': 1, 'kind': 'PinnedUnityReplayWorker', 'unity': '2022.3.62f3',
                    'executable': 'PinnedReplayWorker.exe', 'pins': 'ReplayPins/manifest.json', 'files': files}
        path = self.root / 'approval.json'; path.write_text(json.dumps(approval))
        self.job['pinsSHA256'] = sha256(pins_path.read_bytes()); self.job['levelSHA256'] = levels[0]['sha256']
        return path, sha256(path.read_bytes()), approval

    def broker(self, enabled=True):
        path, digest, _ = self.approval()
        return ApprovedWorker(self.bundle, path, digest, self.jobs, enabled=enabled)

    def test_01_exact_job_roundtrip_rejects_client_won_checkpoint_and_duplicate_keys(self):
        self.job['actions'] = [self.action()]
        self.assertEqual(strict_json(encode_job(self.job)), self.job)
        for field, value in (('expectedWon', True), ('checkpoint', {}), ('rewardCoins', 999999)):
            with self.subTest(field=field), self.assertRaises(ReplayError):
                validate_job(dict(self.job, **{field: value}))
        with self.assertRaises(ReplayError): strict_json(b'{"seed":1,"seed":2}')
        for raw in (b'{"seed":NaN}', b' ' * (MAX_BYTES + 1), b'\xff\xff'):
            with self.assertRaises(ReplayError): strict_json(raw)

    def test_02_bounds_no_bool_scalar_coercion_malformed_ids_and_extra_fields(self):
        for field, value in (('version', True), ('seed', True), ('seed', 0), ('seed', 4_294_967_296),
            ('level', 51), ('initialMoves', 0), ('jobId', ident() + '\n'), ('playerId', 'x' * 32),
            ('pinsSHA256', 'a' * 64 + '\n'), ('startReceiptId', 'wallet/' + 'b' * 64 + '\n'), ('starting', [True, 0, 0, 0])):
            with self.subTest(field=field, value=type(value).__name__), self.assertRaises(ReplayError):
                validate_job(dict(self.job, **{field: value}))
        self.job['actions'] = [self.action(index=1)]
        with self.assertRaises(ReplayError): validate_job(self.job)

    def test_03_receipts_bind_attempt_action_kind_and_are_consumed_exactly_once(self):
        tool = self.action('Tool'); tool['tool'] = 2
        self.add_receipt(tool); self.job['actions'] = [tool]
        self.assertEqual(validate_job(self.job), self.job)
        for field, value in (('attemptId', ident()), ('actionIndex', 1), ('kind', 'Continue'), ('coins', 1), ('quantity', True)):
            changed = copy.deepcopy(self.job); changed['receipts'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ReplayError): validate_job(changed)
        changed = copy.deepcopy(self.job); changed['receipts'].append(changed['receipts'][0].copy())
        with self.assertRaises(ReplayError): validate_job(changed)
        changed = copy.deepcopy(self.job); changed['actions'].append(dict(tool, index=1))
        with self.assertRaises(ReplayError): validate_job(changed)
        changed = copy.deepcopy(self.job); changed['actions'] = []
        with self.assertRaises(ReplayError): validate_job(changed)

    def test_04_continue_requires_typed900_plus5_and_no_client_balance(self):
        action = {**self.action('Continue'), 'ax': -1, 'ay': -1, 'movesAfter': 5}
        self.add_receipt(action); self.job['actions'] = [action]
        validate_job(self.job)  # Model will separately enforce actual OutOfMoves.
        for field, value in (('coins', 899), ('movesAfter', 999), ('tool', 0)):
            changed = copy.deepcopy(self.job); changed['receipts'][0][field] = value
            with self.subTest(field=field), self.assertRaises(ReplayError): validate_job(changed)
        changed = copy.deepcopy(self.job); changed['actions'][0]['movesAfter'] = 999
        with self.assertRaises(ReplayError): validate_job(changed)

    def test_05_output_bound_to_exact_job_pins_level_checkpoint_and_counters(self):
        self.job['actions'] = [self.action()]
        output = self.output(); data = encode_job(self.job)
        self.assertEqual(validate_output(json.dumps(output).encode(), self.job, data), output)
        for key, value in (('jobSHA256', 'd' * 64), ('pinsSHA256', 'd' * 64), ('levelSHA256', 'd' * 64),
            ('productionEnabled', True), ('financialMutation', True), ('moves', 26), ('turn', 0), ('unity', '6000.1'),
            ('outcome', 'Won'), ('remainingGoals', 0), ('checkpointSHA256', 'e' * 64)):
            with self.subTest(key=key), self.assertRaises(ReplayError):
                validate_output(json.dumps(dict(output, **{key: value})).encode(), self.job, data)

    def test_06_output_rejects_oversize_duplicate_unknown_and_failure(self):
        output = self.output(); data = encode_job(self.job)
        for raw in (b' ' * (MAX_BYTES + 1), b'{"version":1,"version":1}',
            json.dumps(dict(output, clientApproved=True)).encode(), json.dumps(dict(output, status='FAIL')).encode()):
            with self.assertRaises(ReplayError): validate_output(raw, self.job, data)

    def test_07_complete_bundle_and_authored_levels_are_approved_before_process(self):
        broker = self.broker()
        approval, pins, digest = broker._verify_bundle()
        self.assertEqual((len(pins['levels']), digest), (50, self.job['pinsSHA256']))
        (self.bundle / 'unapproved.dll').write_bytes(b'fixture')
        with self.assertRaises(ReplayError) as error: broker._verify_bundle()
        self.assertEqual(str(error.exception), 'unapproved_worker_files')

    def test_08_tampered_binary_approval_and_level_are_rejected(self):
        broker = self.broker()
        (self.bundle / 'PinnedReplayWorker.exe').write_bytes(b'tampered')
        with self.assertRaises(ReplayError): broker._verify_bundle()
        path, digest, approval = self.approval()
        broker = ApprovedWorker(self.bundle, path, digest, self.jobs, enabled=True)
        path.write_text('{}')
        with self.assertRaises(ReplayError) as error: broker._verify_bundle()
        self.assertEqual(str(error.exception), 'approval_hash_mismatch')
        path, digest, _ = self.approval()
        broker = ApprovedWorker(self.bundle, path, digest, self.jobs, enabled=True)
        (self.bundle / 'ReplayPins/Levels/C01_L001.json').write_text('{"fixture":false}')
        with self.assertRaises(ReplayError): broker._verify_bundle()

    def test_09_bundle_paths_cannot_select_arbitrary_executable_or_escape(self):
        path, _, approval = self.approval()
        for value in ('../external.exe', 'C:/external.exe', '/external.exe', 'other.exe'):
            changed = copy.deepcopy(approval); changed['executable'] = value
            path.write_text(json.dumps(changed))
            broker = ApprovedWorker(self.bundle, path, sha256(path.read_bytes()), self.jobs, enabled=True)
            with self.subTest(value=value), self.assertRaises(ReplayError): broker._verify_bundle()
        changed = copy.deepcopy(approval); changed['files']['../external.dll'] = 'f' * 64
        path.write_text(json.dumps(changed))
        with self.assertRaises(ReplayError):
            ApprovedWorker(self.bundle, path, sha256(path.read_bytes()), self.jobs, enabled=True)._verify_bundle()

    def test_10_disabled_and_unsupported_platform_never_start_a_process(self):
        broker = self.broker(enabled=False)
        with patch('hotr_backend.replay_contract._run_windows_bounded') as process, self.assertRaises(ReplayError): broker.run(self.job)
        process.assert_not_called()
        broker.enabled = True
        with patch('hotr_backend.replay_contract.os.name', 'posix'), patch('hotr_backend.replay_contract._run_windows_bounded') as process, self.assertRaises(ReplayError): broker.run(self.job)
        process.assert_not_called()

    def test_11_invalid_limits_and_job_directory_in_bundle_are_rejected(self):
        path, digest, _ = self.approval()
        for changes in ({'timeout_seconds': 0}, {'timeout_seconds': 121}, {'memory_bytes': 1}, {'process_limit': 3}, {'enabled': 1}):
            with self.subTest(changes=changes), self.assertRaises(ReplayError):
                ApprovedWorker(self.bundle, path, digest, self.jobs, **changes)
        with self.assertRaises(ReplayError): ApprovedWorker(self.bundle, path, digest, self.bundle)

    @unittest.skipUnless(os.name == 'nt', 'Real Windows Job Object control')
    def test_12_real_windows_job_hard_deadline_kills_the_child(self):
        start = time.monotonic()
        with self.assertRaises(ReplayError) as error:
            _run_windows_bounded(Path(sys._base_executable), ['-c', 'import time;time.sleep(30)'], self.root, 1, 134_217_728, 1)
        self.assertEqual(str(error.exception), 'replay_process_timeout')
        self.assertLess(time.monotonic() - start, 5)

    @unittest.skipUnless(os.name == 'nt', 'Real Windows Job Object control')
    def test_13_real_windows_memory_cap_rejects_large_commit_and_scrubs_secret_environment(self):
        script = "import os,sys;assert 'HOTR_EPHEMERAL_TEST_SECRET' not in os.environ\ntry: x=bytearray(512*1024*1024)\nexcept MemoryError: sys.exit(7)\nsys.exit(99)"
        with patch.dict(os.environ, {'HOTR_EPHEMERAL_TEST_SECRET': 'fixture-never-forward'}):
            value = _run_windows_bounded(Path(sys._base_executable), ['-c', script], self.root, 10, 134_217_728, 1)
        self.assertEqual(value['exitCode'], 7)
        self.assertTrue(value['jobObjectEnforced']); self.assertFalse(value['logsCaptured'])
        self.assertLessEqual(value['peakProcessMemoryBytes'], value['memoryLimitBytes'])

    @unittest.skipUnless(os.name == 'nt', 'Real Windows Job Object control')
    def test_14_real_windows_process_count_cap_prevents_extra_child(self):
        script = "import subprocess,sys\ntry: subprocess.Popen([sys.executable,'-c','pass'])\nexcept OSError: sys.exit(0)\nsys.exit(99)"
        value = _run_windows_bounded(Path(sys._base_executable), ['-c', script], self.root, 10, 134_217_728, 1)
        self.assertEqual((value['exitCode'], value['processLimit']), (0, 1))

    @unittest.skipUnless(os.name == 'nt', 'Broker process seam only; not a Unity execution')
    def test_15_broker_writes_new_job_validates_output_clears_good_runs_and_keeps_failed_artifacts(self):
        broker = self.broker()
        output = self.output()
        def process(executable, arguments, directory, *limits):
            # Windows may pass an 8.3 path for the same temporary file.
            self.assertTrue(executable.samefile(self.bundle / 'PinnedReplayWorker.exe'))
            target = Path(arguments[arguments.index('--out') + 1])
            source = Path(arguments[arguments.index('--job') + 1])
            self.assertEqual(source.read_bytes(), encode_job(self.job))
            self.assertTrue(source.parent.parent.samefile(self.jobs))
            target.write_text(json.dumps(output))
            return {'exitCode': 0, 'jobObjectEnforced': False, 'scope': 'mocked broker seam only'}
        with patch('hotr_backend.replay_contract._run_windows_bounded', side_effect=process):
            value = broker.run(self.job)
        self.assertEqual(value['result']['checkpointSHA256'], 'c' * 64)
        self.assertEqual(value['approvalSHA256'], broker.approval_sha256)
        self.assertEqual(len(list(self.jobs.glob('*/job.json'))), 0)
        def oversize(executable, arguments, directory, *limits):
            Path(arguments[arguments.index('--out') + 1]).write_bytes(b' ' * (MAX_BYTES + 1))
            return {'exitCode': 0}
        with patch('hotr_backend.replay_contract._run_windows_bounded', side_effect=oversize), self.assertRaises(ReplayError): broker.run(self.job)
        self.assertEqual(len(list(self.jobs.glob('*/job.json'))), 1)

    @unittest.skipUnless(os.name == 'nt', 'Actual Windows global named-mutex control')
    def test_16_global_named_mutex_prevents_overlapping_model_processes_and_releases(self):
        started = self.root / 'child-started'
        script = "import pathlib,time;pathlib.Path(" + repr(str(started)) + ").write_text('started');time.sleep(2)"
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            active = pool.submit(_run_windows_bounded, Path(sys._base_executable), ['-c', script], self.root, 10, 134_217_728, 1)
            deadline = time.monotonic() + 5
            while not started.exists() and time.monotonic() < deadline: time.sleep(0.01)
            self.assertTrue(started.exists())
            with self.assertRaises(ReplayError) as error:
                _run_windows_bounded(Path(sys._base_executable), ['-c', 'pass'], self.root, 10, 134_217_728, 1)
            self.assertEqual(str(error.exception), 'replay_worker_busy')
            self.assertEqual(active.result(10)['exitCode'], 0)
        subsequent = _run_windows_bounded(Path(sys._base_executable), ['-c', 'pass'], self.root, 10, 134_217_728, 1)
        self.assertTrue(subsequent['namedMutexEnforced'])

    @unittest.skipUnless(os.name == 'nt', 'Approved-process output seam only, not a real model guard')
    def test_17_only_exact_bound_approved_binary_model_guard_gets_typed_fault(self):
        broker = self.broker()
        failure = {'version': 1, 'status': 'FAIL', 'code': 'model_fault', 'unity': '2022.3.62f3',
            'jobSHA256': sha256(encode_job(self.job)), 'productionEnabled': False, 'financialMutation': False}
        def process(executable, arguments, directory, *limits):
            Path(arguments[arguments.index('--out') + 1]).write_text(json.dumps(failure))
            return {'exitCode': 1, 'scope': 'explicit process seam'}
        with patch('hotr_backend.replay_contract._run_windows_bounded', side_effect=process), self.assertRaises(TrustedModelFault) as caught:
            broker.run(self.job)
        self.assertEqual(caught.exception.proof['jobSHA256'], sha256(encode_job(self.job)))
        for changes in ({'jobSHA256': 'e' * 64}, {'code': 'worker_unavailable'}, {'code': 'model_action_rejected'},
                        {'unity': 'other'}, {'financialMutation': True}, {'version': True}):
            original = failure.copy(); failure.update(changes)
            with self.subTest(changes=changes), patch('hotr_backend.replay_contract._run_windows_bounded', side_effect=process), self.assertRaises(ReplayError) as denied:
                broker.run(self.job)
            self.assertNotIsInstance(denied.exception, TrustedModelFault)
            failure.clear(); failure.update(original)


if __name__ == '__main__':
    unittest.main()
