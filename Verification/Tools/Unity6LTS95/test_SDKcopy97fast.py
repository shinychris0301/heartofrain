"""Host guard semantics and tiny-copy controls; never touch actual tool trees."""
from pathlib import Path
import os
import stat
import tempfile
import types
import unittest
from unittest.mock import patch

import SDKcopy97fast as M
import test_SDKcopy97 as original_tests


class FastGuardControls(unittest.TestCase):
    def test_regular_node_and_each_ancestor_use_exactly_one_lstat(self):
        path=Path('fixture/child/file');expected=[path,*path.parents];calls=[]
        def lstat(node):
            calls.append(node)
            return types.SimpleNamespace(st_mode=stat.S_IFREG if node==path else stat.S_IFDIR,
                                         st_nlink=1 if node==path else 2,st_file_attributes=0)
        with patch.object(Path,'lstat',lstat),patch.object(Path,'exists',side_effect=AssertionError('extra exists')),patch.object(Path,'is_symlink',side_effect=AssertionError('extra symlink')),patch.object(Path,'is_file',side_effect=AssertionError('extra file stat')):
            M.GuardProxy(None).reject_links(path)
        self.assertEqual(calls,expected)

    def test_missing_node_still_checks_every_ancestor_once(self):
        path=Path('fixture/missing/file');expected=[path,*path.parents];calls=[]
        def lstat(node):
            calls.append(node)
            if node in expected[:2]:raise FileNotFoundError()
            return types.SimpleNamespace(st_mode=stat.S_IFDIR,st_nlink=2,st_file_attributes=0)
        with patch.object(Path,'lstat',lstat):M.GuardProxy(None).reject_links(path)
        self.assertEqual(calls,expected)

    def test_symlink_node_is_rejected_from_lstat_without_following(self):
        result=types.SimpleNamespace(st_mode=stat.S_IFLNK,st_nlink=1,st_file_attributes=0)
        with patch.object(Path,'lstat',return_value=result) as observe:
            with self.assertRaisesRegex(ValueError,'Linked'):M.GuardProxy(None).reject_links(Path('fixture'))
        self.assertEqual(observe.call_count,1)

    def test_reparse_ancestor_is_rejected_even_with_regular_child(self):
        path=Path('fixture/child/file');ancestor=path.parent
        def lstat(node):return types.SimpleNamespace(st_mode=stat.S_IFREG if node==path else stat.S_IFDIR,
                    st_nlink=1 if node==path else 2,st_file_attributes=0x400 if node==ancestor else 0)
        with patch.object(Path,'lstat',lstat):
            with self.assertRaisesRegex(ValueError,'reparse'):M.GuardProxy(None).reject_links(path)

    def test_regular_hardlink_count_other_than_one_is_rejected(self):
        for links in (0,2,3):
            info=types.SimpleNamespace(st_mode=stat.S_IFREG,st_nlink=links,st_file_attributes=0)
            with self.subTest(links=links),patch.object(Path,'lstat',return_value=info):
                with self.assertRaisesRegex(ValueError,'Hard-linked'):M.GuardProxy(None).reject_links(Path('fixture'))

    def test_directory_link_count_is_not_confused_with_regular_hardlinks(self):
        info=types.SimpleNamespace(st_mode=stat.S_IFDIR,st_nlink=5,st_file_attributes=0)
        with patch.object(Path,'lstat',return_value=info):M.GuardProxy(None).reject_links(Path('fixture'))

    def test_permission_error_is_not_silently_treated_as_missing(self):
        with patch.object(Path,'lstat',side_effect=PermissionError('blocked')):
            with self.assertRaises(PermissionError):M.GuardProxy(None).reject_links(Path('fixture'))

    def test_no_ancestor_cache_across_guard_calls(self):
        path=Path('fixture/file');state={'reparse':False};calls=[]
        def lstat(node):
            calls.append(node)
            return types.SimpleNamespace(st_mode=stat.S_IFREG if node==path else stat.S_IFDIR,
                     st_nlink=1,st_file_attributes=0x400 if state['reparse'] and node==path.parent else 0)
        guard=M.GuardProxy(None)
        with patch.object(Path,'lstat',lstat):
            guard.reject_links(path);state['reparse']=True
            with self.assertRaisesRegex(ValueError,'reparse'):guard.reject_links(path)
        self.assertEqual(calls.count(path),2);self.assertEqual(calls.count(path.parent),2)

    def test_other_audit_and_inventory_readers_are_delegated_unchanged(self):
        audit=lambda value:('audit',value);inventory=lambda value:('inventory',value)
        proxy=M.GuardProxy(types.SimpleNamespace(audit_backend=audit,inventory=inventory))
        self.assertIs(proxy.audit_backend,audit);self.assertIs(proxy.inventory,inventory)
        self.assertEqual(proxy.audit_backend('baseline'),('audit','baseline'))

    def test_full_original_copy_with_fast_guard_has_identical_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            source,destination,authority=original_tests.fixture(Path(temporary));guard=M.GuardProxy(None)
            copied=M.reference.copy_components(source,destination,authority,guard)
            self.assertEqual(copied,authority)
            self.assertEqual(M.reference.external_manifest(source,guard),authority)

    def test_fast_guard_blocks_changed_source_before_destination_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            source,destination,authority=original_tests.fixture(Path(temporary));(source/'SDK/a.bin').write_bytes(b'evil')
            with self.assertRaisesRegex(ValueError,'InventoryMismatch'):
                M.reference.copy_components(source,destination,authority,M.GuardProxy(None))
            self.assertEqual(list(destination.iterdir()),[])

    def test_real_tiny_source_hardlink_is_refused_before_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source,destination,authority=original_tests.fixture(root)
            os.link(source/'SDK/a.bin',root/'external-host-fixture-link')
            with self.assertRaisesRegex(ValueError,'Hard-linked'):
                M.reference.copy_components(source,destination,authority,M.GuardProxy(None))
            self.assertEqual(list(destination.iterdir()),[])

    def test_running_prior_copy_pid_fences_all_readers_and_writes(self):
        with patch.object(M.process_reader,'stopped_pid',side_effect=ValueError('PriorCopyStillRunning')) as verify,patch.object(M.reference.smoke,'readers',side_effect=AssertionError('must not read or copy')):
            with self.assertRaisesRegex(ValueError,'StillRunning'):
                M.run(Path('module'),Path('out'),23752,60)
        verify.assert_called_once_with(23752)

    def test_no_running_helper_or_reference_global_guard_is_changed(self):
        M.verify_frozen_helpers()
        source=Path(M.__file__).read_text('utf-8')
        self.assertNotIn('setattr(',source);self.assertNotIn('unittest.mock',source)
        self.assertNotIn('reference.run(',source);self.assertNotIn('.kill(',source)
        self.assertNotIn('rmtree(',source);self.assertNotIn('Move-Item',source)
        self.assertIn('R.copy_components(R.SOURCE,R.DESTINATION,authority,guards,deadline)',source)


if __name__=='__main__':unittest.main(verbosity=2)
