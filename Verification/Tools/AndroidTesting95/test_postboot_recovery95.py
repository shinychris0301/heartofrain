"""Host-only post-boot safety controls; all transport calls are fakes."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
import postboot_recovery95 as M

OLD={'index':0,'serial':'emulator-5554','package':M.A.PACKAGE,'adb':'unchanged','console':'unchanged',
     'bootID':'11111111-1111-1111-1111-111111111111'}
NEW='22222222-2222-2222-2222-222222222222'


def context():
    return {'oldSelector':OLD,'before':{'installedSHA256':M.A.APK_SHA,'activeAttempts':0,'preferences':{'p':'hash'}},
            'update':{'packagesAfter':{'app':'unchanged'},'proof':{'source':'bound'}},
            'originalInvocation':{'path':'old.json','sha256':'a'*64,'bytes':1}}


class Fake:
    def __init__(self):self.commands=[]
    def identity(self):return {'postboot':'bound'}
    def packages(self):return {'app':'unchanged'}
    def adb(self,*args,**kwargs):self.commands.append(args);return ''


class PostBootControls(unittest.TestCase):
    def test_agreed_new_boot_is_explicitly_separate(self):
        current=M.agree_boot(NEW,NEW,OLD)
        self.assertEqual(current,{**OLD,'bootID':NEW})
        self.assertEqual(OLD['bootID'],'11111111-1111-1111-1111-111111111111')

    def test_unrelated_console_and_selected_adb_boot_refused(self):
        with self.assertRaisesRegex(ValueError,'MustMatch'):M.agree_boot(NEW,OLD['bootID'],OLD)

    def test_old_boot_is_not_mislabeled_as_postboot(self):
        with self.assertRaisesRegex(ValueError,'DistinctValid'):M.agree_boot(OLD['bootID'],OLD['bootID'],OLD)

    def test_malformed_matching_boot_refused(self):
        with self.assertRaisesRegex(ValueError,'MustMatch'):M.agree_boot('not-guid','not-guid',OLD)

    def test_changed_serial_index_package_or_transport_refused(self):
        current={**OLD,'bootID':NEW}
        for key,value in [('serial','emulator-5558'),('index',1),('package','foreign.app'),('adb','different'),('console','different')]:
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'OriginalLD'):
                M.validate_selector({**current,key:value},OLD)

    def test_extra_selector_fields_refused(self):
        with self.assertRaisesRegex(ValueError,'OriginalLD'):
            M.validate_selector({**OLD,'bootID':NEW,'unbound':True},OLD)

    def test_foreign_marker_fences_stop(self):
        target=Fake()
        with patch.object(M.R,'markers',return_value=['HOTR_Foreign']),patch.object(M.R,'ordinary',side_effect=AssertionError('must not read')):
            with self.assertRaisesRegex(ValueError,'MarkersPreserved'):
                M.finish(target,context(),{'postboot':'bound'},lambda x:None)
        self.assertEqual(target.commands,[])

    def test_changed_profiles_or_preferences_fence_stop(self):
        target=Fake()
        with patch.object(M.R,'markers',return_value=[]),patch.object(M.R,'ordinary',return_value={'changed':True}):
            with self.assertRaisesRegex(ValueError,'DataChanged'):
                M.finish(target,context(),{'postboot':'bound'},lambda x:None)
        self.assertEqual(target.commands,[])

    def test_boot_drift_since_inspection_fences_stop(self):
        target=Fake()
        with patch.object(M.R,'markers',side_effect=AssertionError('must not read')):
            with self.assertRaisesRegex(ValueError,'InspectedIdentityChanged'):
                M.finish(target,context(),{'postboot':'other'},lambda x:None)
        self.assertEqual(target.commands,[])

    def test_current_active_attempt_refused_by_original_canonical_parser(self):
        import json
        value=json.dumps({'payload':json.dumps({'attempts':[{'state':'Started'}]})})
        with self.assertRaisesRegex(ValueError,'ActiveAttempt'):
            M.A.canonical_attempts('Profiles/Development-v1/profile.json',value)

    def test_stop_timeout_is_not_retried_or_followed_by_launch(self):
        target=Fake();ctx=context();steps=[]
        with patch.object(M.R,'markers',return_value=[]),patch.object(M.R,'ordinary',return_value=ctx['before']),patch.object(M.R,'pid',return_value='123'),patch.object(target,'adb',side_effect=TimeoutError) as call,patch.object(M.R,'launch',side_effect=AssertionError('must not launch')):
            with self.assertRaises(TimeoutError):M.finish(target,ctx,{'postboot':'bound'},steps.append)
        self.assertEqual(call.call_count,1)
        self.assertEqual(call.call_args.args,('shell','am','force-stop',M.A.PACKAGE))
        self.assertEqual(steps[-1],'exactOwnerForceStop')

    def test_successful_finish_preserves_only_original_durable_data(self):
        target=Fake();ctx=context()
        with patch.object(M.R,'markers',return_value=[]),patch.object(M.R,'ordinary',return_value=ctx['before']),patch.object(M.R,'pid',side_effect=['123','']),patch.object(M.R,'launch',return_value='456'),patch.object(M.time,'sleep'):
            result=M.finish(target,ctx,{'postboot':'bound'},lambda x:None)
        self.assertEqual(result['ordinaryAfterRelaunch'],ctx['before'])
        self.assertTrue(result['ordinaryDataUnchanged'])
        self.assertEqual(target.commands,[('shell','am','force-stop',M.A.PACKAGE)])

    def test_final_durable_data_change_refused(self):
        target=Fake();ctx=context()
        with patch.object(M.R,'markers',return_value=[]),patch.object(M.R,'ordinary',side_effect=[ctx['before'],ctx['before'],{'changed':True}]),patch.object(M.R,'pid',side_effect=['123','']),patch.object(M.R,'launch',return_value='456'),patch.object(M.time,'sleep'):
            with self.assertRaisesRegex(ValueError,'DataChanged'):M.finish(target,ctx,{'postboot':'bound'},lambda x:None)

    def test_fresh_output_never_overwrites_previous_public_or_private(self):
        with tempfile.TemporaryDirectory() as temporary:
            public=Path(temporary)/'Public';private=Path(temporary)/'Private'
            with patch.object(M,'OUT',public),patch.object(M,'PRIVATE',private):
                output,secret=M.fresh_outputs(public/('a'*32))
                self.assertTrue(output.is_dir() and secret.is_dir())
                for invalid in [output,public/'Set01',Path(temporary)/('b'*32)]:
                    with self.subTest(path=invalid),self.assertRaisesRegex(ValueError,'FreshScoped'):
                        M.fresh_outputs(invalid)


if __name__=='__main__':unittest.main()
