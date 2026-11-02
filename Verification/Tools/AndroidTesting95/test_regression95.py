"""Host counterexamples; fake transport only, never contact Android or Unity."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
import regression95 as M


class MarkerTransport:
    def __init__(self,files):self.files=dict(files);self.commands=[]
    def exists(self,path):return path==M.accepted.BASE or path in self.files
    def adb(self,*args,**kwargs):
        self.commands.append(args)
        if args[:2]==('shell','find'):return '\n'.join(self.files)
        if args[:2]==('exec-out','cat'):return self.files[args[2]]
        if args[:2]==('shell','rm'):
            del self.files[args[2]];return ''
        raise AssertionError('Unexpected fake command')


class RegressionControls(unittest.TestCase):
    def fresh(self,**changes):
        value={'unity':'2022.3.62f3','platform':'Android','width':540,'height':960,'utc':'2026-10-27T10:00:01Z'}
        value.update(changes);raw=json.dumps(value).encode();return value,raw

    def test_actual_emulator_geometry_not_phone_hardcode(self):
        report,raw=self.fresh()
        M.fresh_report(report,raw,None,1793095200,1793095201,540,960,M_datetime)

    def test_previous_report_hash_rejected_even_with_fresh_timestamp(self):
        report,raw=self.fresh()
        with self.assertRaisesRegex(ValueError,'Stale'):
            M.fresh_report(report,raw,hashlib.sha256(raw).hexdigest(),0,1793095201,540,960,M_datetime)

    def test_mtime_stale_rejected_despite_changed_json(self):
        report,raw=self.fresh()
        with self.assertRaisesRegex(ValueError,'Stale'):
            M.fresh_report(report,raw,None,1793095200,1793095199,540,960,M_datetime)

    def test_wrong_native_engine_or_platform_rejected(self):
        for change in [{'unity':'6000.3.27f1'},{'platform':'WindowsPlayer'},{'width':720}]:
            with self.subTest(change=change):
                report,raw=self.fresh(**change)
                with self.assertRaisesRegex(ValueError,'Scope'):
                    M.fresh_report(report,raw,None,0,1793095201,540,960,M_datetime)

    def test_ordinary_preference_change_rejected(self):
        before={'installedSHA256':M.accepted.APK_SHA,'activeAttempts':0,'preferences':{'a':'b'}}
        with self.assertRaisesRegex(ValueError,'DataChanged'):
            M.same_ordinary(before,{**before,'preferences':{'a':'changed'}})

    def test_active_attempt_parser_blocks_fixture(self):
        raw=json.dumps({'payload':json.dumps({'attempts':[{'state':'Started'}]})})
        with self.assertRaisesRegex(ValueError,'ActiveAttempt'):
            M.accepted.canonical_attempts('Profiles/Development-v1/profile.json',raw)

    def test_nested_authority_is_not_player_profile(self):
        self.assertIsNone(M.accepted.canonical_attempts('Profiles/Development-v1/DailyGiftDevelopmentAuthority/profile.json','not read'))

    def test_foreign_marker_prevents_stop(self):
        target=MarkerTransport({M.accepted.BASE+'/HOTR_RunOther':b'foreign'})
        with patch.object(M,'ordinary',side_effect=AssertionError('must not read/stop')):
            with self.assertRaisesRegex(ValueError,'Marker'):
                M.stop_idle(target,{})
        self.assertFalse(any('force-stop' in command for command in target.commands))

    def test_data_drift_prevents_stop(self):
        target=MarkerTransport({})
        with patch.object(M,'ordinary',return_value={'drift':True}):
            with self.assertRaisesRegex(ValueError,'DataChanged'):
                M.stop_idle(target,{'installedSHA256':M.accepted.APK_SHA,'activeAttempts':0})
        self.assertFalse(any('force-stop' in command for command in target.commands))

    def test_wrong_marker_content_preserved(self):
        target=MarkerTransport({M.accepted.BASE+'/'+M.MARKER:b'foreign'})
        payload=b'our-request';receipt={'sha256':hashlib.sha256(payload).hexdigest()}
        with self.assertRaisesRegex(ValueError,'ContentPreserved'):
            M.cleanup_marker(target,payload,receipt)
        self.assertTrue(target.exists(M.accepted.BASE+'/'+M.MARKER))
        self.assertFalse(any(command[:2]==('shell','rm') for command in target.commands))

    def test_exact_owned_marker_only_is_removed(self):
        payload=b'our-request';path=M.accepted.BASE+'/'+M.MARKER
        target=MarkerTransport({path:payload})
        M.cleanup_marker(target,payload,{'sha256':hashlib.sha256(payload).hexdigest()})
        self.assertFalse(target.exists(path))
        self.assertEqual([c for c in target.commands if c[:2]==('shell','rm')],[('shell','rm',path)])

    def test_foreign_marker_survives_own_cleanup_and_blocks_relaunch(self):
        payload=b'our-request';ours=M.accepted.BASE+'/'+M.MARKER;foreign=M.accepted.BASE+'/HOTR_RunForeign'
        target=MarkerTransport({ours:payload,foreign:b'other'})
        with self.assertRaisesRegex(ValueError,'ForeignMarkers'):
            M.cleanup_marker(target,payload,{'sha256':hashlib.sha256(payload).hexdigest()})
        self.assertTrue(target.exists(foreign));self.assertFalse(target.exists(ours))

    def test_cleanup_without_owned_receipt_is_refused(self):
        path=M.accepted.BASE+'/'+M.MARKER;target=MarkerTransport({path:b'ours'})
        with self.assertRaisesRegex(ValueError,'Receipt'):
            M.cleanup_marker(target,b'ours',{'sha256':'0'*64})
        self.assertTrue(target.exists(path))

    def test_remote_hash_inventory_requires_exact_unique_paths(self):
        path=M.REMOTE+'/A.png';digest='a'*64
        result=M.parse_metadata(digest+'  '+path,[path],r'([0-9a-fA-F]{64})\s+(.+)','bad')
        self.assertEqual(result,{path:digest})
        for raw in ['',digest+'  '+path+'\n'+digest+'  '+path,digest+'  '+M.REMOTE+'/B.png']:
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                M.parse_metadata(raw,[path],r'([0-9a-fA-F]{64})\s+(.+)','bad')

    def test_geometry_uses_actual_override_and_portrait(self):
        target=type('Display',(),{'adb':lambda *args:'Physical size: 720x1280\nOverride size: 960x540'})()
        self.assertEqual(M.geometry(target),(540,960))


def M_datetime(value):return datetime.fromisoformat(value.replace('Z','+00:00'))


if __name__=='__main__':unittest.main()
