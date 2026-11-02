"""Synthetic host controls in an explicit temporary LTS scope; no real log reads."""
import json
from pathlib import Path
import stat
import tempfile
import types
import unittest
from unittest.mock import patch

import sanitize_logs97 as M


class Privacy97Controls(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.anchor=Path(self.temp.name)
        self.evidence=self.anchor/'Verification/Evidence/Unity6LTS95';self.evidence.mkdir(parents=True)
        self.scope=M.LogScope(self.anchor,self.evidence,self.evidence/'Privacy97',
                              self.anchor/'.verification-cache/Unity6LTS95/PrivateEvidence97')
        self.output=self.scope.public/'Set01';self.addCleanup(self.cleanup)

    def cleanup(self):
        # Test-created read-only private fixtures only; never a project file.
        for path in self.anchor.rglob('*'):
            if path.is_file():path.chmod(stat.S_IREAD|stat.S_IWRITE)
        self.temp.cleanup()

    def source(self,name,raw=b'ordinary safe log\n'):
        path=self.evidence/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);return path

    def publish(self,**changes):
        options={'scope':self.scope,'writers_finished':True,'private_id':'a'*32};options.update(changes)
        return M.publish(self.output,**options)

    def test_exact_frozen94_values_only_redaction_preserves_bom_crlf_and_status(self):
        raw=b'\xef\xbb\xbfEngine header\r\n  Session Id: fixture-session\r\n[Licensing] Access token is unavailable\r\nnormal: ready\r\nMachine Id: fixture-machine\r\n'
        derivative,changes=M.load_redactor()(raw)
        self.assertEqual(derivative,b'\xef\xbb\xbfEngine header\r\n  Session Id: <redacted:session_id>\r\n[Licensing] Access token is unavailable\r\nnormal: ready\r\nMachine Id: <redacted:machine_id>\r\n')
        self.assertEqual(changes,[{'line':2,'category':'session_id'},{'line':5,'category':'machine_id'}])

    def test_publisher_preserves_raw_exact_private_readonly_and_bound_derivative(self):
        raw=self.source('Native/Case/Unity.log',b'Machine Id: fixture-machine\nPASS native check\n');before=raw.read_bytes()
        result=self.publish();entry=result['files'][0]
        self.assertEqual(raw.read_bytes(),before)
        private=self.anchor/entry['privateCopy'];public=self.anchor/entry['publicDerivative']
        self.assertEqual(private.read_bytes(),before);self.assertFalse(private.stat().st_mode&stat.S_IWRITE)
        self.assertEqual(entry['rawSHA256'],M.sha(before));self.assertEqual(entry['publicSHA256'],M.sha(public.read_bytes()))
        self.assertNotIn(b'fixture-machine',public.read_bytes());self.assertNotIn('fixture-machine',json.dumps(result))
        self.assertEqual(M.verify_receipt(self.output/'Receipt.json',scope=self.scope),result)

    def test_only_exact_raw_basename_casing_in_lts_scope_is_collected(self):
        first=self.source('One/UNITY.LOG');second=self.source('Two/cOnSoLe.LoG')
        self.source('One/Runtime.log');self.source('One/Unity.sanitized.log');self.source('One/SomeUnity.log')
        result=self.publish();self.assertEqual(result['rawLogCount'],2)
        self.assertEqual([self.anchor/entry['rawSource'] for entry in result['files']],[first,second])

    def test_old94_and_other95_receipts_are_never_read_or_modified(self):
        self.source('Current/Unity.log')
        old=self.anchor/'Verification/Evidence/Unity6Migration94/Native/Unity.log';old.parent.mkdir(parents=True);old.write_bytes(b'Bearer fixture-old-secret-material\n')
        old_receipt=self.evidence/'Older/Receipt.json';old_receipt.parent.mkdir(parents=True);old_receipt.write_bytes(b'old bound receipt')
        result=self.publish();self.assertEqual(result['rawLogCount'],1)
        self.assertEqual(old.read_bytes(),b'Bearer fixture-old-secret-material\n');self.assertEqual(old_receipt.read_bytes(),b'old bound receipt')

    def test_unsupported_secret_refuses_entire_set_before_any_outputs(self):
        self.source('A/Unity.log');self.source('B/Console.log',b'Bearer fixture-secret-material\n')
        with self.assertRaisesRegex(RuntimeError,'UnsupportedSensitiveValue'):self.publish()
        self.assertFalse(self.output.exists());self.assertFalse(self.scope.private.exists())

    def test_private_key_material_is_not_silently_published(self):
        self.source('Unity.log',b'-----BEGIN PRIVATE KEY-----\nfixture\n')
        with self.assertRaisesRegex(RuntimeError,'UnsupportedSensitiveValue'):self.publish()
        self.assertFalse(self.output.exists())

    def test_bad_encoding_is_not_lossily_decoded(self):
        self.source('Unity.log',b'\xff\x00fixture')
        with self.assertRaises(UnicodeDecodeError):self.publish()
        self.assertFalse(self.output.exists())

    def test_error_output_never_includes_decoder_bytes_or_unknown_messages(self):
        error=UnicodeDecodeError('utf-8',b'fixture-secret\xff',14,15,'invalid')
        self.assertEqual(M.public_error(error),{'errorType':'UnicodeDecodeError'})
        self.assertEqual(M.public_error(RuntimeError('unknown fixture-secret text')),{'errorType':'RuntimeError'})

    def test_root_writer_completion_acknowledgement_is_required(self):
        self.source('Unity.log')
        with self.assertRaisesRegex(RuntimeError,'WriterCompletion'):self.publish(writers_finished=False)
        self.assertFalse(self.output.exists());self.assertFalse(self.scope.private.exists())

    def test_fresh_public_output_is_never_overwritten(self):
        self.source('Unity.log');self.publish();before=(self.output/'Receipt.json').read_bytes()
        with self.assertRaisesRegex(RuntimeError,'FreshPublic'):self.publish()
        self.assertEqual((self.output/'Receipt.json').read_bytes(),before)

    def test_private_set_is_never_reused(self):
        self.source('Unity.log');self.publish();self.output=self.scope.public/'Set02'
        with self.assertRaisesRegex(RuntimeError,'FreshPrivate'):self.publish()
        self.assertFalse(self.output.exists())

    def test_outside_or_nested_public_outputs_and_private_traversal_refused(self):
        self.source('Unity.log')
        for output in [self.anchor/'Unity/Set01',self.scope.public/'nested/Set01',self.scope.public/'../Other/Set01']:
            with self.subTest(output=output),self.assertRaisesRegex(RuntimeError,'DirectPublic'):
                M.publish(output,scope=self.scope,writers_finished=True)
        with self.assertRaisesRegex(RuntimeError,'PrivateSetIdentifier'):self.publish(private_id='../escape')

    def test_existing_derivative_does_not_become_raw_input(self):
        self.source('Unity.log');self.publish()
        self.assertEqual(len(M.source_logs(self.scope)),1)
        self.output=self.scope.public/'Set02';result=self.publish(private_id='b'*32)
        self.assertEqual(result['rawLogCount'],1)

    def test_raw_mutation_during_copy_retains_failure_and_no_success_receipt(self):
        raw=self.source('Unity.log',b'Machine Id: fixture-machine\n');normal=M.write_new;changed=[]
        def mutate(path,body,readonly=False):
            normal(path,body,readonly)
            if readonly and not changed:raw.write_bytes(b'changed raw by external test writer\n');changed.append(True)
        with patch.object(M,'write_new',side_effect=mutate):
            with self.assertRaisesRegex(RuntimeError,'PreservationFailed'):self.publish()
        self.assertTrue((self.output/'Failure.json').is_file());self.assertFalse((self.output/'Receipt.json').exists())
        self.assertEqual(raw.read_bytes(),b'changed raw by external test writer\n')

    def test_raw_mutation_after_publication_invalidates_receipt(self):
        raw=self.source('Unity.log');self.publish();raw.write_bytes(b'changed ordinary log\n')
        with self.assertRaisesRegex(RuntimeError,'Changed'):M.verify_receipt(self.output/'Receipt.json',scope=self.scope)

    def test_derivative_mutation_invalidates_receipt(self):
        self.source('Unity.log');result=self.publish();(self.anchor/result['files'][0]['publicDerivative']).write_bytes(b'tampered')
        with self.assertRaisesRegex(RuntimeError,'Changed'):M.verify_receipt(self.output/'Receipt.json',scope=self.scope)

    def test_private_raw_mutation_invalidates_receipt(self):
        self.source('Unity.log');result=self.publish();private=self.anchor/result['files'][0]['privateCopy']
        private.chmod(stat.S_IREAD|stat.S_IWRITE);private.write_bytes(b'tampered')
        with self.assertRaisesRegex(RuntimeError,'Changed'):M.verify_receipt(self.output/'Receipt.json',scope=self.scope)

    def test_new_native_raw_log_after_publication_requires_fresh_set(self):
        self.source('Unity.log');self.publish();self.source('NewWriter/Console.log')
        with self.assertRaisesRegex(RuntimeError,'RawLogSetChanged'):M.verify_receipt(self.output/'Receipt.json',scope=self.scope)

    def test_derivative_is_idempotent_under_same_frozen_policy(self):
        redact=M.load_redactor();first,changes=redact(b'Correlation Id: fixture-value\n')
        second,repeated=redact(first)
        self.assertEqual(first,second);self.assertTrue(changes);self.assertEqual(repeated,[])

    def test_modified_redactor_source_is_rejected_without_global_scope_patch(self):
        copied=self.anchor/'modified_redactor.py';copied.write_bytes(M.REDACTOR_PATH.read_bytes()+b'\n# changed\n')
        with patch.object(M,'REDACTOR_PATH',copied):
            with self.assertRaisesRegex(RuntimeError,'Frozen94RedactorChanged'):M.load_redactor()

    def test_reparse_raw_log_is_rejected_before_output_creation(self):
        raw=self.source('Unity.log');original=Path.lstat
        def lstat(path,*args,**kwargs):
            if path==raw:return types.SimpleNamespace(st_mode=stat.S_IFREG,st_file_attributes=0x400)
            return original(path,*args,**kwargs)
        with patch.object(Path,'lstat',lstat):
            with self.assertRaisesRegex(RuntimeError,'LinkedPath'):self.publish()
        self.assertFalse(self.output.exists())

    def test_lts_scope_cannot_be_repointed_to_main_or_old94(self):
        scope=M.LogScope(self.anchor,self.anchor/'Unity',self.scope.public,self.scope.private)
        with self.assertRaisesRegex(RuntimeError,'ExactExplicit'):scope.validated()

    def test_recorded_failure_prevents_success_receipt_reuse(self):
        self.source('Unity.log');self.publish();(self.output/'Failure.json').write_text('{}')
        with self.assertRaisesRegex(RuntimeError,'FailedPublication'):M.verify_receipt(self.output/'Receipt.json',scope=self.scope)

    def test_oversize_log_is_refused_before_copy(self):
        self.source('Unity.log',b'12345')
        with patch.object(M,'MAX_LOG_BYTES',4):
            with self.assertRaisesRegex(RuntimeError,'SizeBound'):self.publish()
        self.assertFalse(self.output.exists());self.assertFalse(self.scope.private.exists())


if __name__=='__main__':unittest.main(verbosity=2)
