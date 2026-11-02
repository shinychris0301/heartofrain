"""Host-only overlay guards using temporary text fixtures; no project export/execution."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

import export_overlay94 as export


def bound(raw):
    return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}


class OverlayHostTests(unittest.TestCase):
    def test_only_changed_and_new_project_inputs_enter_overlay(self):
        old={'Assets/keep.cs':bound(b'keep'),'Assets/change.cs':bound(b'old')}
        new={**old,'Assets/change.cs':bound(b'new'),'ProjectSettings/New.asset':bound(b'value: 1\n')}
        rows=export.overlay_rows(old,new)
        self.assertEqual([row['path'] for row in rows],['Assets/change.cs','ProjectSettings/New.asset'])
        self.assertEqual([row['kind'] for row in rows],['changed','added'])
        self.assertEqual(rows[0]['before'],old['Assets/change.cs'])

    def test_deletion_is_rejected_instead_of_silently_making_incomplete_overlay(self):
        with self.assertRaisesRegex(ValueError,'DeletionsCannotBeRepresented'):
            export.overlay_rows({'Assets/deleted.cs':bound(b'old')},{})

    def test_traversal_windows_drive_alt_separators_and_non_input_paths_are_rejected(self):
        for path in ('../Assets/a.cs','Assets/../a.cs','/Assets/a.cs','C:/Assets/a.cs','Assets\\a.cs',
                     'Library/a.cs','Assets//a.cs','Assets/./a.cs','Assets/a.cs/'):
            with self.subTest(path=path),self.assertRaises(ValueError):export.safe_relative(path)

    def test_sdk_binary_profile_log_and_credential_paths_are_refused(self):
        for path in ('Assets/native.dll','Assets/native.dll.meta','Assets/SDK/a.cs','Assets/Profiles/a.meta',
                     'Assets/Credentials/a.cs','Packages/archive.zip','ProjectSettings/secret.jks','ProjectSettings/raw.log'):
            with self.subTest(path=path),self.assertRaises(ValueError):export.safe_relative(path)

    def test_binary_and_non_utf8_payloads_are_refused(self):
        for raw in (b'\x00abc',b'\xff\xfe'):
            with self.assertRaises(ValueError):export.safe_text('Assets/Test.cs',raw)

    def test_populated_secret_fields_and_literal_credentials_are_refused_without_echoing_value(self):
        secret='sensitive-value-should-not-be-echoed'
        for raw in (('AndroidKeystorePass: '+secret).encode(),('clientSecret: "'+secret+'"').encode(),
                    ('string password = "'+secret+'";').encode(),b'-----BEGIN RSA PRIVATE KEY-----'):
            with self.assertRaises(ValueError) as caught:export.safe_text('ProjectSettings/ProjectSettings.asset',raw)
            self.assertNotIn(secret,str(caught.exception))

    def test_empty_credentials_and_code_reading_external_secrets_remain_text(self):
        raw=b'AndroidKeystorePass: \nclientSecret: ""\nstring password = Environment.GetEnvironmentVariable("PASSWORD");\n'
        self.assertEqual(export.safe_text('ProjectSettings/ProjectSettings.asset',raw),raw)

    def test_real_temporary_zip_has_exact_crc_sha_and_no_unchanged_project_payload(self):
        with tempfile.TemporaryDirectory(prefix='hotr94_overlay_host_') as folder:
            root=Path(folder);project=root/'Project';(project/'Assets').mkdir(parents=True)
            (project/'Assets/change.cs').write_bytes(b'new source\r\n')
            rows=[{'path':'Assets/change.cs','kind':'changed','before':bound(b'old'),'after':bound(b'new source\r\n')}]
            payloads=export.archive_payloads(project,rows,b'{"full":"before"}',b'{"full":"after"}',{'sourceAuditSHA256':'a'*64},lambda _:None)
            destination=root/'private.zip';members=export.write_zip(destination,payloads)
            self.assertEqual(len(members),5)
            self.assertEqual({row['path'] for row in members},{'README.txt','Manifests/BaseUnity5407.json','Manifests/CandidateUnity6.json','Manifests/MigrationOverlay94.json','Overlay/Assets/change.cs'})
            with zipfile.ZipFile(destination) as archive:self.assertEqual(archive.read('Overlay/Assets/change.cs'),b'new source\r\n')

    def test_candidate_byte_drift_is_rejected_before_archive_creation(self):
        with tempfile.TemporaryDirectory(prefix='hotr94_overlay_drift_host_') as folder:
            project=Path(folder);(project/'Assets').mkdir();(project/'Assets/Test.cs').write_bytes(b'unexpected')
            changes=[{'path':'Assets/Test.cs','kind':'added','before':None,'after':bound(b'approved')}]
            with self.assertRaisesRegex(ValueError,'CandidateFileChangedWhileReading'):
                export.archive_payloads(project,changes,b'{}',b'{}',{},lambda _:None)

    def test_crc_or_raw_member_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='hotr94_overlay_crc_host_') as folder:
            path=Path(folder)/'raw.zip';raw=b'unique-uncompressed-host-payload'
            with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_STORED) as archive:archive.writestr('README.txt',raw)
            data=path.read_bytes();location=data.index(raw);path.write_bytes(data[:location]+b'X'+data[location+1:])
            with self.assertRaises((ValueError,zipfile.BadZipFile)):export.verify_zip(path,{'README.txt':raw})

    def test_unexpected_or_case_duplicate_archive_members_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='hotr94_overlay_members_host_') as folder:
            path=Path(folder)/'extra.zip'
            with zipfile.ZipFile(path,'x') as archive:
                archive.writestr('README.txt',b'a');archive.writestr('readme.TXT',b'a')
            with self.assertRaisesRegex(ValueError,'ExactUniqueArchiveMembersRequired'):export.verify_zip(path,{'README.txt':b'a'})

    def test_existing_archive_is_preserved(self):
        with tempfile.TemporaryDirectory(prefix='hotr94_overlay_fresh_host_') as folder:
            path=Path(folder)/'existing.zip';path.write_bytes(b'preserve')
            with self.assertRaisesRegex(ValueError,'FreshArchiveRequired'):export.write_zip(path,{'README.txt':b'new'})
            self.assertEqual(path.read_bytes(),b'preserve')

    def test_readme_states_exact_base_version_missing_workspace_and_open_build_gates(self):
        text=export.readme(821).decode('utf-8')
        for phrase in ('NOT a complete project','NOT an APK','196f606d','5,407','6000.6.6f1',
                       'original workspace','unsigned Bee','9d7158','strict raw-turn JSON hash FAIL','not migrate'):
            self.assertIn(phrase,text)

    def test_failed_unstable_or_non_authorized_audit_is_rejected(self):
        files={'Assets/F'+str(i)+'.cs':bound(b'old') for i in range(5407)}
        after={**files,'Assets/New.cs':bound(b'new')}
        baseline={'inputCount':5407,'files':files};candidate={'inputCount':5408,'files':after}
        changes=export.overlay_rows(files,after)
        preparation={'status':'PASS_EXACT_MAIN_COPY94','authorization':'USER_APPROVED_ISOLATED_UNITY6_MIGRATION',
                     'baselineCommit':'196f606d','mainInputCount':5407,'project':export.CANDIDATE.relative_to(export.ROOT).as_posix()}
        report={'status':export.STATUS,'violations':[],'mainInputCount':5407,'mainInputsUnchanged':True,
                'candidateInputsStable':True,'allOriginalGuidsPreserved':True,'backendHeadSourceUnchanged':True,
                'inputsModifiedByAudit':False,'sdkOrUnityOrDeviceCommandsExecuted':False,'candidateInputCount':5408,
                'changeCounts':{'added':1,'changed':0,'deleted':0}}
        export.validate_report(report,baseline,candidate,preparation,changes)
        for key,value in (('status','FAIL_ISOLATED_CANDIDATE_SOURCE_AUDIT94'),('mainInputsUnchanged',False),
                          ('allOriginalGuidsPreserved',False),('sdkOrUnityOrDeviceCommandsExecuted',True)):
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'PassedExactSourceAuditRequired'):
                export.validate_report({**report,key:value},baseline,candidate,preparation,changes)
        with self.assertRaisesRegex(ValueError,'AuthorizedExactMigrationBaseRequired'):
            export.validate_report(report,baseline,candidate,{**preparation,'baselineCommit':'other'},changes)

    def test_existing_hardlinked_input_is_rejected_by_actual_inventory_guard(self):
        with tempfile.TemporaryDirectory(prefix='hotr94_overlay_link_host_') as folder:
            source=Path(folder)/'source.cs';linked=Path(folder)/'linked.cs';source.write_bytes(b'text')
            os.link(source,linked)
            with self.assertRaisesRegex(ValueError,'Hard-linked input refused'):
                export.audit_module().reject_links(linked)


if __name__=='__main__':unittest.main(verbosity=2)
