"""Host-only guards; these do not install or launch Unity/Hub/Android tools."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location('prepare_editor94',
    Path(__file__).with_name('prepare_editor.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def release_fixture():
    children = [{'id': module_id, 'url': 'https://dl.google.com/android/repository/test.zip',
                 'downloadSize': {'value': 1, 'unit': 'BYTE'},
                 'installedSize': {'value': 2, 'unit': 'BYTE'}, 'subModules': []}
                for module_id in sorted(MODULE.EXPECTED_MODULES - {'android'})]
    android = {'id': 'android', 'url': 'https://download.unity3d.com/test.exe',
               'downloadSize': {'value': 1, 'unit': 'BYTE'},
               'installedSize': {'value': 2, 'unit': 'BYTE'}, 'subModules': children}
    return {'results': [{'version': MODULE.VERSION, 'shortRevision': MODULE.REVISION,
                         'downloads': [{'platform': 'WINDOWS', 'architecture': 'X86_64',
                                        'modules': [android]}]}]}


class PortableEditorGuards(unittest.TestCase):
    def test_boundary_rejects_parent_and_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for candidate in (root, root / '..' / 'escape'):
                with self.assertRaises(ValueError):
                    MODULE.bounded(candidate, root)
            self.assertEqual(MODULE.bounded(root / 'new' / 'child', root), root / 'new' / 'child')

    def test_existing_reparse_ancestor_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            linked = root / 'linked'
            linked.mkdir()
            original = MODULE.is_linklike
            with mock.patch.object(MODULE, 'is_linklike',
                    side_effect=lambda path: Path(path) == linked or original(path)):
                with self.assertRaisesRegex(ValueError, 'reparse'):
                    MODULE.bounded(linked / 'child', root)

    def test_regular_copy_preserves_metadata_files_and_all_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'installed'
            (source / 'Editor' / 'Data').mkdir(parents=True)
            (source / 'Editor' / 'Unity.exe').write_bytes(b'fixture-not-an-executable')
            (source / 'modules.json').write_text('{"id":"webgl"}', encoding='utf-8')
            (source / 'metadata.hub.json').write_text('{"architecture":"x86_64"}', encoding='utf-8')
            (source / 'Editor' / 'Data' / 'empty').mkdir()
            before = MODULE.walk_tree(source)
            destination = root / 'portable'
            records = MODULE.copy_fresh(source, destination, *before)
            self.assertEqual(before, MODULE.walk_tree(source))
            self.assertEqual(before, MODULE.walk_tree(destination))
            self.assertEqual({item['path'] for item in records},
                             {'Editor/Unity.exe', 'modules.json', 'metadata.hub.json'})
            for record in records:
                self.assertEqual(record['sha256'], MODULE.digest(source / record['path']))
                self.assertEqual(record['sha256'], MODULE.digest(destination / record['path']))
                self.assertNotEqual((source / record['path']).stat().st_ino,
                                    (destination / record['path']).stat().st_ino)

    def test_existing_destination_is_never_overlaid(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, target = root / 'source', root / 'target'
            source.mkdir()
            target.mkdir()
            (target / 'keep.txt').write_bytes(b'owner-content')
            with self.assertRaisesRegex(ValueError, 'fresh'):
                MODULE.copy_fresh(source, target, [], [])
            self.assertEqual((target / 'keep.txt').read_bytes(), b'owner-content')

    def test_source_inventory_rejects_linklike_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'linked.bin').write_bytes(b'x')
            original = MODULE.is_linklike
            with mock.patch.object(MODULE, 'is_linklike', side_effect=lambda path:
                    Path(path).name == 'linked.bin' or original(path)):
                with self.assertRaisesRegex(ValueError, 'linked file'):
                    MODULE.walk_tree(root)

    def test_exact_release_and_module_tree_are_accepted(self):
        _, android, modules = MODULE.select_release(release_fixture())
        self.assertEqual(android['id'], 'android')
        self.assertEqual({module['id'] for module in modules}, MODULE.EXPECTED_MODULES)

    def test_wrong_changeset_and_duplicate_release_fail(self):
        document = release_fixture()
        document['results'][0]['shortRevision'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'changeset'):
            MODULE.select_release(document)
        document = release_fixture()
        document['results'].append(copy.deepcopy(document['results'][0]))
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            MODULE.select_release(document)

    def test_module_addition_or_missing_child_requires_review(self):
        for missing in (True, False):
            document = release_fixture()
            children = document['results'][0]['downloads'][0]['modules'][0]['subModules']
            if missing:
                children.pop()
            else:
                extra = copy.deepcopy(children[0])
                extra['id'] = 'unexpected-sdk'
                children.append(extra)
            with self.assertRaisesRegex(ValueError, 'tree changed'):
                MODULE.select_release(document)

    def test_insecure_or_unrelated_module_url_is_rejected(self):
        for url in ('http://dl.google.com/sdk.zip', 'https://example.org/sdk.zip',
                    'https://user:password@download.unity3d.com/sdk.zip'):
            document = release_fixture()
            document['results'][0]['downloads'][0]['modules'][0]['url'] = url
            with self.assertRaisesRegex(ValueError, 'module URL'):
                MODULE.select_release(document)

    def test_nonbyte_size_is_rejected(self):
        document = release_fixture()
        document['results'][0]['downloads'][0]['modules'][0]['downloadSize']['unit'] = 'MEGABYTE'
        with self.assertRaisesRegex(ValueError, 'size metadata'):
            MODULE.select_release(document)


if __name__ == '__main__':
    unittest.main(verbosity=2)
