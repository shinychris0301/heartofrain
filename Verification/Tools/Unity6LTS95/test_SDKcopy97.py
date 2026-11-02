"""Host-only exact-copy rejection controls over disposable tiny directories."""
import copy
import hashlib
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import SDKcopy97 as M

LINKS=M.smoke.module('sdkcopy97_host_link_guard',M.ROOT/'Verification/Tools/Unity6Migration94/prepare_editor.py')
GUARDS=types.SimpleNamespace(reject_links=LINKS.reject_links_to_root)


def fixture(root):
    source=root/'Source';destination=root/'Destination';source.mkdir();destination.mkdir()
    for name,data in [('SDK/a.bin',b'sdka'),('NDK/sub/data.bin',b'ndka'),('OpenJDK/release',b'jdka')]:
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    (source/'SDK/empty').mkdir()
    return source,destination,M.external_manifest(source,GUARDS)


def minimal_inventory(path='SDK/a.bin'):
    return {'components':list(M.COMPONENTS),'files':[{'path':path,'bytes':1,'sha256':'a'*64}],'directories':[]}


def good_module():
    return {'runnerSHA256':M.MODULE_HELPER_SHA,'moduleLayoutRevision':97,'status':'PASS_NORMAL_STOCK_ANDROID_MODULE_INSTALL95',
            'target':str(M.module_install.TARGET),'installerExecuted':True,'normalUacRequired':False,'unityPidsAfter':[],
            **{name:True for name in ('mainInputsUnchanged','candidate66InputsUnchanged','stockCoreUnchanged',
                                     'exactEditorVersionUnchanged','moduleInstallerUnchanged')}}


class SDKCopyControls(unittest.TestCase):
    def test_only_three_component_paths_and_no_traversal_or_absolute_paths(self):
        self.assertEqual(M.safe_relative('SDK/platforms/android-36/android.jar'),'SDK/platforms/android-36/android.jar')
        for path in ['Tools/gradle/file','UnityEditor.Android.Extensions.dll','SDK/../Unity.dll','/SDK/a','SDK//a','SDK/./a','C:/SDK/a','SDK\\a','NDK','OpenJDK/a\x00b']:
            with self.subTest(path=path),self.assertRaises(ValueError):M.safe_relative(path)

    def test_case_insensitive_file_collision_is_refused(self):
        value=minimal_inventory();value['files'].append({**value['files'][0],'path':'SDK/A.bin'})
        with self.assertRaisesRegex(ValueError,'Duplicate'):M.inventory_maps(value)

    def test_missing_parent_directory_is_refused(self):
        with self.assertRaisesRegex(ValueError,'ParentDirectory'):M.inventory_maps(minimal_inventory('SDK/sub/a.bin'))

    def test_directory_file_collision_is_refused(self):
        value=minimal_inventory();value['directories']=['SDK/a.bin']
        with self.assertRaisesRegex(ValueError,'Conflicting'):M.inventory_maps(value)

    def test_valid_copy_matches_every_byte_hash_and_empty_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            source,destination,authority=fixture(Path(temporary))
            copied=M.copy_components(source,destination,authority,GUARDS)
            self.assertEqual(copied,authority)
            self.assertTrue((destination/'SDK/empty').is_dir())
            self.assertEqual(M.external_manifest(source,GUARDS),authority)

    def test_changed_source_bytes_rejected_before_any_destination_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            source,destination,authority=fixture(Path(temporary));(source/'SDK/a.bin').write_bytes(b'evil')
            with self.assertRaisesRegex(ValueError,'InventoryMismatch'):M.copy_components(source,destination,authority,GUARDS)
            self.assertEqual(list(destination.iterdir()),[])

    def test_extra_source_file_rejected_before_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            source,destination,authority=fixture(Path(temporary));(source/'SDK/extra').write_bytes(b'foreign')
            with self.assertRaisesRegex(ValueError,'InventoryMismatch'):M.copy_components(source,destination,authority,GUARDS)
            self.assertEqual(list(destination.iterdir()),[])

    def test_missing_source_file_rejected_before_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            source,destination,authority=fixture(Path(temporary));(source/'SDK/a.bin').unlink()
            with self.assertRaisesRegex(ValueError,'InventoryMismatch'):M.copy_components(source,destination,authority,GUARDS)
            self.assertEqual(list(destination.iterdir()),[])

    def test_existing_component_preserved_without_any_source_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            source,destination,authority=fixture(Path(temporary));path=destination/'SDK';path.mkdir();(path/'keep').write_bytes(b'keep')
            with patch.object(M,'external_manifest',side_effect=AssertionError('must not hash')):
                with self.assertRaisesRegex(ValueError,'ExistingOrPartial'):M.copy_components(source,destination,authority,GUARDS)
            self.assertEqual((path/'keep').read_bytes(),b'keep')

    def test_source_change_after_first_file_is_detected_and_partial_copy_retained(self):
        with tempfile.TemporaryDirectory() as temporary:
            source,destination,authority=fixture(Path(temporary));normal=M.shutil.copystat;changed=[]
            def mutate(origin,target,**kwargs):
                normal(origin,target,**kwargs)
                if not changed:(source/'NDK/sub/data.bin').write_bytes(b'evil');changed.append(True)
            with patch.object(M.shutil,'copystat',side_effect=mutate):
                with self.assertRaisesRegex(ValueError,'CopiedBytesOrSourceChanged'):
                    M.copy_components(source,destination,authority,GUARDS)
            self.assertTrue((destination/'SDK/a.bin').exists());self.assertTrue((destination/'NDK/sub/data.bin').exists())

    def test_destination_corruption_after_copy_is_detected(self):
        with tempfile.TemporaryDirectory() as temporary:
            source,destination,authority=fixture(Path(temporary));normal=M.shutil.copystat
            def corrupt(origin,target,**kwargs):
                normal(origin,target,**kwargs)
                if Path(target)==destination/'SDK/a.bin':Path(target).write_bytes(b'evil')
            with patch.object(M.shutil,'copystat',side_effect=corrupt):
                with self.assertRaisesRegex(ValueError,'InventoryMismatch'):
                    M.copy_components(source,destination,authority,GUARDS)
            self.assertEqual((destination/'SDK/a.bin').read_bytes(),b'evil')

    def test_platform_and_gradle_are_preserved_outside_copy_components(self):
        with tempfile.TemporaryDirectory() as temporary:
            source,destination,authority=fixture(Path(temporary))
            platform=destination/'UnityEditor.Android.Extensions.dll';platform.write_bytes(b'own LTS platform')
            gradle=destination/'Tools/gradle/own.jar';gradle.parent.mkdir(parents=True);gradle.write_bytes(b'own LTS gradle')
            before=M.tree_manifest(destination,GUARDS,excluded=M.COMPONENTS)
            M.copy_components(source,destination,authority,GUARDS)
            self.assertEqual(before,M.tree_manifest(destination,GUARDS,excluded=M.COMPONENTS))
            self.assertEqual(platform.read_bytes(),b'own LTS platform');self.assertEqual(gradle.read_bytes(),b'own LTS gradle')

    def test_expired_deadline_prevents_component_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            source,destination,authority=fixture(Path(temporary))
            with self.assertRaisesRegex(ValueError,'Deadline'):M.copy_components(source,destination,authority,GUARDS,deadline=0)
            self.assertEqual(list(destination.iterdir()),[])

    def test_actual_matching_module_pass_and_all_invariants_are_required(self):
        value=good_module();M.validate_module_record(value)
        for key,change in [('status','RUNNING'),('moduleLayoutRevision',95),('runnerSHA256','wrong'),('target','E:/wrong'),('installerExecuted',False),('normalUacRequired',True),('unityPidsAfter',[1]),('mainInputsUnchanged',False),('candidate66InputsUnchanged',False),('stockCoreUnchanged',False),('exactEditorVersionUnchanged',False),('moduleInstallerUnchanged',False)]:
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'ActualMatching'):
                M.validate_module_record({**value,key:change})

    def test_source_reparse_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            source,destination,authority=fixture(Path(temporary))
            guarded=types.SimpleNamespace(reject_links=lambda p:(_ for _ in ()).throw(ValueError('ReparseRefused')) if Path(p)==source/'NDK/sub' else GUARDS.reject_links(p))
            with self.assertRaisesRegex(ValueError,'ReparseRefused'):
                M.copy_components(source,destination,authority,guarded)
            self.assertEqual(list(destination.iterdir()),[])

    def test_changed_source_module_provenance_is_rejected(self):
        original=M.hash_file
        def changed(path,deadline=None):
            return '0'*64 if Path(path)==M.SOURCE_MODULES else original(path,deadline)
        with patch.object(M,'hash_file',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'FrozenProvenanceChanged'):M.load_authority(GUARDS)


if __name__=='__main__':unittest.main(verbosity=2)
