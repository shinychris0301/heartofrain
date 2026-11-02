"""Synthetic host counterexamples only; no network, signature process or installer."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent))
SPEC = importlib.util.spec_from_file_location('component95_host', Path(__file__).with_name('download_component95.py'))
api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api)


class Response:
    def __init__(self, start, end, total, data, interrupt=False, status=206, headers=None, url=None):
        self.status = status
        self.headers = headers or {'Content-Range': f'bytes {start}-{end}/{total}', 'Content-Length': str(end-start+1)}
        self.data, self.interrupt = data, interrupt
        self.url = url or 'https://download.unity3d.com/fixture.exe'
        self.position = 0
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def geturl(self): return self.url
    def read1(self, amount):
        if self.interrupt and self.position >= 2:
            self.interrupt = False
            raise OSError('fixture interrupted transport')
        count = min(amount, 2 if self.interrupt else amount)
        result = self.data[self.position:self.position+count]
        self.position += len(result)
        return result


class ComponentHostGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.info = {'url': 'https://download.unity3d.com/fixture.exe', 'bytes': 64,
                     'filename': 'fixture.exe', 'md5': hashlib.md5(b'MZ' + b'x'*62).hexdigest()}
        self.deadline = time.monotonic()+10
        self.cancelled = threading.Event()

    def test_android_only_and_frozen_official_reader_metadata_are_required(self):
        with self.assertRaisesRegex(ValueError, 'FreshAndroidOnly'):
            api.component_info('editor')
        with patch.object(api.dl, 'digest', return_value='0'*64), patch.object(api.dl, 'component_info') as reader:
            with self.assertRaisesRegex(ValueError, 'FrozenOfficialReader'):
                api.component_info('android')
        reader.assert_not_called()

    def test_fresh_output_requires_matching_uuid_private_scope_and_no_overwrite(self):
        public, private = self.base/'public', self.base/'private'
        with patch.object(api, 'PUBLIC', public), patch.object(api, 'PRIVATE', private):
            output, destination = api.fresh_paths(public/('a'*32))
            self.assertEqual(destination, private/('a'*32))
            for wrong in (self.base/'elsewhere'/('a'*32), public/'Set01', public/'../outside'):
                with self.assertRaises(ValueError): api.fresh_paths(wrong)
            destination.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, 'FreshPrivateUUIDRequired'):
                api.fresh_paths(output)

    def test_sixteen_sections_cover_every_byte_once_with_explicit_boundaries(self):
        for total in (64, 1549360256, 16003):
            sections=api.section_ranges(total)
            self.assertEqual(len(sections), 16)
            self.assertEqual((sections[0][1],sections[-1][2]),(0,total-1))
            self.assertTrue(all(sections[i][2]+1==sections[i+1][1] for i in range(15)))
        for total in (0, -1, True, 15):
            with self.assertRaises(ValueError): api.section_ranges(total)

    def test_https_and_exact_range_headers_reject_redirect_query_encoding_and_status(self):
        for url in ('http://download.unity3d.com/fixture.exe', 'https://other.example/fixture.exe',
                    'https://download.unity3d.com/fixture.exe?token=fixture', 'https://user@download.unity3d.com/f.exe'):
            with self.assertRaises(ValueError): api.dl.safe_url(url)
        valid={'Content-Range':'bytes 0-3/64','Content-Length':'4'}
        for status, headers in [(200,valid),(206,{**valid,'Content-Range':'bytes 1-4/64'}),
                                (206,{**valid,'Content-Length':'5'}),(206,{**valid,'Content-Encoding':'gzip'})]:
            with self.assertRaises(ValueError): api.dl.validate_range(status,headers,0,3,64)

    def test_interrupted_section_retains_bytes_and_resumes_at_exact_offset(self):
        opener=Mock()
        opener.open.side_effect=[Response(0,5,64,b'MZabcd',interrupt=True),Response(2,5,64,b'abcd')]
        with patch.object(api.urllib.request,'build_opener',return_value=opener):
            part=api.download_section(self.info,(0,0,5),self.base,self.deadline,self.cancelled)
        self.assertEqual((part['bytes'],part['attempts']),(6,2))
        self.assertEqual((self.base/'Part00.bin').read_bytes(),b'MZabcd')
        self.assertEqual([c.args[0].get_header('Range') for c in opener.open.call_args_list],['bytes=0-5','bytes=2-5'])

    def test_malformed_range_never_appends_even_a_single_byte(self):
        opener=Mock(open=Mock(return_value=Response(1,4,64,b'xxxx')))
        with patch.object(api.urllib.request,'build_opener',return_value=opener),self.assertRaisesRegex(ValueError,'ContentRangeMismatch'):
            api.download_section(self.info,(0,0,3),self.base,self.deadline,self.cancelled)
        self.assertEqual((self.base/'Part00.bin').stat().st_size,0)

    def test_wrong_pe_prefix_and_excess_response_cannot_complete_section(self):
        for payload, category in [(b'NOxx','InvalidPEPrefix'),(b'MZxxx','ExcessResponseBytes')]:
            folder=self.base/category;folder.mkdir()
            opener=Mock(open=Mock(return_value=Response(0,3,64,payload)))
            with patch.object(api.urllib.request,'build_opener',return_value=opener),self.assertRaisesRegex(ValueError,category):
                api.download_section(self.info,(0,0,3),folder,self.deadline,self.cancelled)

    def test_retry_budget_and_expired_deadline_are_strict_without_deleting_partial(self):
        opener=Mock(open=Mock(side_effect=OSError('fixture interruption')))
        event=Mock(is_set=Mock(return_value=False))
        with patch.object(api.urllib.request,'build_opener',return_value=opener),self.assertRaisesRegex(RuntimeError,'RetriesExhausted'):
            api.download_section(self.info,(0,0,3),self.base,self.deadline,event)
        self.assertEqual(opener.open.call_count,16)
        self.assertTrue((self.base/'Part00.bin').exists())
        with self.assertRaisesRegex(ValueError,'OverallDeadline'):
            api.check_deadline(time.monotonic()-1,self.cancelled)
        self.cancelled.set()
        with self.assertRaisesRegex(ValueError,'OtherSectionFailed'):
            api.check_deadline(self.deadline,self.cancelled)

    def create_parts(self):
        payload=b'MZ'+b'x'*62
        specs=api.section_ranges(len(payload))
        parts=[]
        for index,first,last in specs:
            raw=payload[first:last+1]
            (self.base/('Part'+str(index).zfill(2)+'.bin')).write_bytes(raw)
            parts.append({'index':index,'first':first,'last':last,'bytes':len(raw),
                          'sha256':hashlib.sha256(raw).hexdigest(),'attempts':1})
        return payload,specs,parts

    def test_assembly_orders_all_sections_and_rechecks_hashes(self):
        payload,specs,parts=self.create_parts()
        target=api.assemble(self.info,specs,list(reversed(parts)),self.base,self.deadline)
        self.assertEqual(target.read_bytes(),payload)
        self.assertEqual(api.dl.digest(target,'md5'),self.info['md5'])

    def test_part_tamper_or_noncontiguous_boundaries_fail_assembly(self):
        _,specs,parts=self.create_parts()
        (self.base/'Part05.bin').write_bytes(b'evil')
        with self.assertRaisesRegex(ValueError,'PartChangedBeforeAssembly'):
            api.assemble(self.info,specs,parts,self.base,self.deadline)

    def test_publisher_md5_and_valid_signature_both_required(self):
        target=self.base/'fixture.exe';target.write_bytes(b'MZ'+b'x'*62)
        with patch.object(api.dl,'authenticode',side_effect=ValueError('FixtureInvalidUnitySignature')) as signature:
            with self.assertRaisesRegex(ValueError,'InvalidUnitySignature'):
                api.dl.verified_file(target,self.info,deadline=self.deadline)
        signature.assert_called_once()
        target.write_bytes(b'MZ'+b'y'*62)
        with patch.object(api.dl,'authenticode') as signature:
            with self.assertRaisesRegex(ValueError,'FullPublisherMD5Mismatch'):
                api.dl.verified_file(target,self.info,deadline=self.deadline)
        signature.assert_not_called()

    def test_source_guard_and_component_guard_precede_any_http(self):
        with patch.object(api,'component_info',return_value=self.info),patch.object(api,'fresh_paths',return_value=(self.base/'public',self.base/'private')), \
             patch.object(api,'protected_sources',side_effect=ValueError('FixtureSourceDrift')),patch.object(api,'download_section') as fetch:
            with self.assertRaisesRegex(ValueError,'FixtureSourceDrift'):
                api.download('android',self.base/'public')
        fetch.assert_not_called()
        for seconds in (0,59,5401,True):
            with self.assertRaisesRegex(ValueError,'BoundedSecondsRequired'):
                api.download('android',self.base/'public',seconds)

    def fake_pipeline(self, sources):
        payload=b'MZ'+b'x'*62
        def section(info,spec,private,deadline,cancelled):
            index,first,last=spec
            raw=payload[first:last+1]
            (private/('Part'+str(index).zfill(2)+'.bin')).write_bytes(raw)
            return {'index':index,'first':first,'last':last,'bytes':len(raw),
                    'sha256':hashlib.sha256(raw).hexdigest(),'attempts':1}
        public,private=self.base/'public',self.base/'private'
        with patch.object(api,'component_info',return_value=self.info),patch.object(api,'fresh_paths',return_value=(public,private)), \
             patch.object(api,'protected_sources',side_effect=sources),patch.object(api,'download_section',side_effect=section), \
             patch.object(api.dl,'authenticode',return_value={'Status':'Valid','SignerSubject':'Unity Technologies'}),patch('builtins.print'):
            return api.download('android',public),public,private

    def test_complete_mock_transport_still_requires_whole_file_proof_and_exact_install_plan(self):
        result,public,private=self.fake_pipeline([{'source':'same'},{'source':'same'}])
        self.assertEqual(result['status'],'PASS_COMPLETE_OFFICIAL_INSTALLER95')
        self.assertTrue(result['trustedInstaller'])
        self.assertFalse(result['installerExecuted'])
        self.assertEqual(result['installer']['md5'],self.info['md5'])
        self.assertEqual(result['normalInstallPlan']['arguments'],['/S','/D='+str(api.dl.TARGET)])
        self.assertEqual(len(result['retainedSections']),16)
        self.assertEqual(json.loads((public/'Report.json').read_text())['status'],result['status'])

    def test_final_source_drift_removes_trust_and_install_plan_even_after_complete_download(self):
        result,public,private=self.fake_pipeline([{'source':'before'},{'source':'changed'}])
        self.assertEqual(result['status'],'FAIL_FRESH_OFFICIAL_ANDROID_SECTIONS95_INVARIANT')
        self.assertFalse(result['trustedInstaller'])
        self.assertNotIn('normalInstallPlan',result)
        self.assertTrue((private/'fixture.exe').is_file())
        self.assertTrue((public/'Sources_after.json').is_file())


if __name__=='__main__': unittest.main()
