"""Artifact/qualifier guard tests only: this suite never starts the Unity worker."""
import copy
from contextlib import redirect_stderr,redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parent))
import package_worker126 as p
import qualify_worker126 as q

ROOT=Path(__file__).resolve().parents[3]
BUNDLE=ROOT/'.verification-cache/PinnedReplay83/Worker'
APPROVAL=ROOT/'Verification/Evidence/ServerReplay83/Standalone/27891d602a644d7b9afb15cf6af28074/Local_Approval.json'
JOB=ROOT/'Verification/Evidence/ServerReplay83/Native/Fixtures/L01_0.job.json'
EXPECTED=ROOT/'Verification/Evidence/ServerReplay83/Native/Fixtures/L01_0.expected.json'
ARCHIVE=ROOT/'.verification-cache/Review126/Deployment/Worker01/hotr-approved-worker83-v1.zip'
RECEIPT=ROOT/'Verification/Evidence/Review126/Deployment/Worker01/WorkerArchive126.json'

class WorkerArtifactGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract=q.load_contract(ROOT/'Backend')
        cls.job,cls.expected=q.check_fixtures(JOB,EXPECTED,cls.contract)
        cls.entries=json.loads(RECEIPT.read_text())['files']

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='hotr-worker-tools126-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def proof(self):
        result=copy.deepcopy(self.expected)
        canonical=p.sha(self.contract.encode_job(self.job))
        result['jobSHA256']=canonical
        return {'result':result,'approvalSHA256':p.APPROVAL_SHA256,'jobSHA256':canonical,
                'process':dict(jobObjectEnforced=True,namedMutexEnforced=True,exitCode=0,
                    wallLimitSeconds=60,memoryLimitBytes=268435456,processLimit=2)}

    def test_01_real_archive_matches_all_177_exact_approved_entries(self):
        self.assertEqual(p.verify_archive(ARCHIVE,self.entries),
                         '8b398dd58d472d23999dc0697bdc9f93d884706a1230b78346d27daf56f91b01')
        self.assertEqual(sum(item['bytes'] for name,item in self.entries.items() if name.startswith('Worker/')),71463004)

    def test_02_real_source_matches_original_receipt_no_new_approval_created(self):
        _,raw,entries,size=p.collect(BUNDLE,APPROVAL)
        self.assertEqual(p.sha(raw),p.APPROVAL_SHA256)
        self.assertEqual(entries,self.entries)
        self.assertEqual(size,71463004)

    def test_03_archive_missing_file_rejected_before_reading_payload(self):
        path=self.root/'invalid.zip'
        with zipfile.ZipFile(path,'x') as archive:
            for name in list(self.entries)[:-1]:
                archive.writestr(name,b'')
        with self.assertRaisesRegex(p.PackageError,'archive_inventory_mismatch'):
            p.verify_archive(path,self.entries)

    def test_04_archive_case_collision_rejected(self):
        path=self.root/'invalid.zip'
        names=list(self.entries)
        with zipfile.ZipFile(path,'x') as archive:
            for name in names[:-1]:
                archive.writestr(name,b'')
            archive.writestr(names[0].upper(),b'')
        with self.assertRaisesRegex(p.PackageError,'archive_inventory_mismatch'):
            p.verify_archive(path,self.entries)

    def test_05_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(p.PackageError,'duplicate_json_key'):
            p.parse(b'{"files":{},"files":{}}')

    def test_06_existing_output_preserved(self):
        existing=self.root/'existing';existing.mkdir()
        with self.assertRaisesRegex(p.PackageError,'fresh_qualification_directory_required'):
            q.isolated(existing,fresh=True)
        self.assertEqual(list(existing.iterdir()),[])

    def test_07_any_authority_marker_ancestor_rejected(self):
        (self.root/'.hotr-staging105-owner.json').write_text('{}')
        with self.assertRaisesRegex(p.PackageError,'qualification_authority_directory_rejected'):
            q.isolated(self.root/'fresh',fresh=True)
        self.assertFalse((self.root/'fresh').exists())

    def test_08_unpinned_backend_source_never_imported(self):
        fake=self.root/'hotr_backend';fake.mkdir()
        (fake/'replay_contract.py').write_text("raise AssertionError('must never import')")
        with self.assertRaisesRegex(p.PackageError,'tested_replay_contract_hash_mismatch'):
            q.load_contract(self.root)

    def test_09_guard_accepts_exact_native_observation_ignoring_only_canonical_json_hash(self):
        q.check_result(self.proof(),self.expected,self.job,self.contract)

    def test_10_guard_rejects_changed_checkpoint(self):
        proof=self.proof();proof['result']['checkpointSHA256']='0'*64
        with self.assertRaisesRegex(p.PackageError,'native_checkpoint_or_outcome_mismatch'):
            q.check_result(proof,self.expected,self.job,self.contract)

    def test_11_guard_rejects_wrong_canonical_job_hash(self):
        proof=self.proof();proof['jobSHA256']='0'*64
        with self.assertRaisesRegex(p.PackageError,'replay_proof_binding_mismatch'):
            q.check_result(proof,self.expected,self.job,self.contract)

    def test_12_guard_rejects_wrong_memory_cap_or_unenforced_job(self):
        for key,value in (('memoryLimitBytes',1073741824),('jobObjectEnforced',False)):
            proof=self.proof();proof['process'][key]=value
            with self.assertRaisesRegex(p.PackageError,'replay_os_limits_unproven'):
                q.check_result(proof,self.expected,self.job,self.contract)

    def test_13_memory_threshold_boundary(self):
        self.assertTrue(q.enough_memory(dict(availablePhysicalBytes=134217728,availableCommitBytes=536870912)))
        self.assertFalse(q.enough_memory(dict(availablePhysicalBytes=134217727,availableCommitBytes=536870912)))
        self.assertFalse(q.enough_memory(dict(availablePhysicalBytes=134217728,availableCommitBytes=536870911)))

    def test_14_nonlocalservice_rejected_before_output_or_worker(self):
        out=self.root/'fresh'
        with patch.object(q,'local_service',return_value=False),patch.object(q,'collect') as collect:
            with self.assertRaisesRegex(p.PackageError,'localservice_execution_required'):
                q.qualify(ROOT/'Backend',BUNDLE,APPROVAL,JOB,EXPECTED,out,True)
        collect.assert_not_called()
        self.assertFalse(out.exists())

    def test_15_low_headroom_actual_approved_bundle_preflight_starts_no_process(self):
        low=dict(totalPhysicalBytes=2147483648,availablePhysicalBytes=134217727,
                 availableCommitBytes=1073741824,memoryLoadPercent=94)
        out=self.root/'blocked'
        with patch.object(q,'local_service',return_value=True),patch.object(q,'memory_status',return_value=low), \
             patch.object(q,'load_contract',return_value=self.contract), \
             patch.object(self.contract,'_run_windows_bounded',side_effect=AssertionError('no process permitted')) as bounded:
            report=q.qualify(ROOT/'Backend',BUNDLE,APPROVAL,JOB,EXPECTED,out,True)
        bounded.assert_not_called()
        self.assertEqual(report['status'],'BLOCKED_LOW_HEADROOM_WORKER_SMOKE126')
        self.assertEqual(report['actualUnityReplays'],0)
        self.assertEqual(list((out/'Jobs').iterdir()),[])
        self.assertEqual(json.loads((out/'.hotr-isolated-worker-smoke126.json').read_text())['state'],'BlockedLowHeadroom')

    def test_16_timeout_control_requires_actual_timeout_rejection_not_success_return(self):
        # The local Python installation has a junction ancestor; production's
        # fixed Program Files interpreter must pass the real plain-path guard.
        with patch.object(q.sys,'_base_executable',str(ROOT/'Backend/.venv/Scripts/python.exe')):
            with patch.object(self.contract,'_run_windows_bounded',return_value={}):
                with self.assertRaisesRegex(p.PackageError,'timeout_control_failed_to_terminate'):
                    q.timeout_control(self.contract,self.root)
            with patch.object(self.contract,'_run_windows_bounded',side_effect=self.contract.ReplayError('replay_process_timeout')):
                result=q.timeout_control(self.contract,self.root)
                self.assertEqual(result['status'],'PASS_WINDOWS_JOB_TIMEOUT_CONTROL')
            with patch.object(self.contract,'_run_windows_bounded',side_effect=self.contract.ReplayError('worker_start_failed')):
                with self.assertRaisesRegex(p.PackageError,'timeout_control_unexpected_error'):
                    q.timeout_control(self.contract,self.root)

    def test_17_actual_windows_token_and_memory_telemetry_are_typed(self):
        self.assertIs(type(q.local_service()),bool)
        memory=q.memory_status()
        self.assertTrue(all(type(value) is int and value>=0 for value in memory.values()))
        self.assertGreater(memory['totalPhysicalBytes'],0)

    def test_18_cli_has_no_implicit_administrator_qualification_mode(self):
        arguments=[value for name in ('backend','bundle','approval','job','expected','out')
                   for value in ('--'+name,str(self.root/name))]
        with redirect_stderr(io.StringIO()),patch.object(q,'qualify') as qualify:
            with self.assertRaises(SystemExit) as result:
                q.main(arguments)
        self.assertEqual(result.exception.code,2)
        qualify.assert_not_called()

    def test_19_cli_explicit_developer_probe_keeps_distinct_status(self):
        arguments=[value for name in ('backend','bundle','approval','job','expected','out')
                   for value in ('--'+name,str(self.root/name))]
        observed=io.StringIO()
        diagnostic=dict(status='PASS_DEVELOPER_WORKER_PROBE126',actualUnityReplays=1,
                        executionAccountIsLocalService=False)
        with redirect_stdout(observed),patch.object(q,'qualify',return_value=diagnostic) as qualify:
            self.assertEqual(q.main(arguments+['--allow-developer-probe']),0)
        self.assertIs(qualify.call_args.args[-1],False)
        self.assertEqual(json.loads(observed.getvalue())['status'],'PASS_DEVELOPER_WORKER_PROBE126')

if __name__=='__main__':
    # No raw assertions/tracebacks or fixture/player identifiers enter receipts.
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(WorkerArtifactGuardTests)
    result=unittest.TextTestRunner(stream=io.StringIO(),verbosity=0).run(suite)
    report={'status':'PASS_WORKER_ARTIFACT_GUARDS126' if result.wasSuccessful() else 'FAIL_WORKER_ARTIFACT_GUARDS126',
            'tests':result.testsRun,'failures':[test.id() for test,_ in result.failures],
            'errors':[test.id() for test,_ in result.errors],'skipped':len(result.skipped),
            'actualUnityReplays':0,'scope':'Archive and qualifier guard unit tests only; no worker process executed.'}
    print(json.dumps(report))
    raise SystemExit(0 if result.wasSuccessful() else 1)

