"""Host-only rejection controls; never instantiate a device transport."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:sys.path.insert(0,str(HERE))
import recover_regression95 as M


class Target:
    def __init__(self):self.commands=[]
    def identity(self):return {'bound':'target'}
    def packages(self):return {'package':'unchanged'}
    def adb(self,*args,**kw):self.commands.append(args);return ''


def context():
    return {'original':{'identity':{'bound':'target'},'fixturePID':123},
            'before':{'installedSHA256':M.A.APK_SHA,'activeAttempts':0,'preferences':{'p':'hash'}},
            'update':{'proof':{'source':'bound'},'packagesAfter':{'package':'unchanged'}},
            'originalInvocation':{'path':'old.json','sha256':'a'*64,'bytes':1}}


class RecoveryControls(unittest.TestCase):
    def test_read_only_inspection_checks_owner_data_no_mutation(self):
        target=Target();ctx=context();steps=[]
        with patch.object(M.R,'markers',return_value=[]),patch.object(M.R,'ordinary',return_value=ctx['before']),patch.object(M.R,'pid',return_value='456'):
            result=M.live_idle(target,ctx,steps.append)
        self.assertEqual(result,(ctx['original']['identity'],ctx['before'],'456'))
        self.assertEqual(target.commands,[])
        self.assertIn('ordinaryProfileAndPreferences',steps)

    def test_foreign_identity_fences_all_further_reads_and_stop(self):
        target=Target();ctx=context();ctx['original']['identity']={'foreign':True}
        with patch.object(M.R,'markers',side_effect=AssertionError('must not call')):
            with self.assertRaisesRegex(ValueError,'LDTargetChanged'):M.live_idle(target,ctx,lambda x:None)
        self.assertEqual(target.commands,[])

    def test_pending_marker_fences_profile_read_and_stop(self):
        target=Target()
        with patch.object(M.R,'markers',return_value=['HOTR_Foreign']),patch.object(M.R,'ordinary',side_effect=AssertionError('must not call')):
            with self.assertRaisesRegex(ValueError,'MarkersPreserved'):M.finalize(target,context(),lambda x:None)
        self.assertEqual(target.commands,[])

    def test_changed_save_fences_stop(self):
        target=Target()
        with patch.object(M.R,'markers',return_value=[]),patch.object(M.R,'ordinary',return_value={'drift':True}):
            with self.assertRaisesRegex(ValueError,'DataChanged'):M.finalize(target,context(),lambda x:None)
        self.assertEqual(target.commands,[])

    def test_package_drift_fences_stop(self):
        target=Target();ctx=context()
        with patch.object(target,'packages',return_value={'other':'new'}),patch.object(M.R,'markers',return_value=[]),patch.object(M.R,'ordinary',return_value=ctx['before']):
            with self.assertRaisesRegex(ValueError,'PackagesChanged'):M.finalize(target,ctx,lambda x:None)
        self.assertEqual(target.commands,[])

    def test_marker_appearing_after_idle_fences_stop(self):
        target=Target();ctx=context()
        with patch.object(M.R,'markers',side_effect=[[],['HOTR_Foreign']]),patch.object(M.R,'ordinary',return_value=ctx['before']),patch.object(M.R,'pid',return_value='456'):
            with self.assertRaisesRegex(ValueError,'MarkersPreserved'):M.finalize(target,ctx,lambda x:None)
        self.assertEqual(target.commands,[])

    def test_stop_timeout_has_no_launch_or_retry(self):
        target=Target();ctx=context();steps=[]
        with patch.object(M.R,'markers',return_value=[]),patch.object(M.R,'ordinary',return_value=ctx['before']),patch.object(M.R,'pid',return_value='456'),patch.object(target,'adb',side_effect=TimeoutError('unknown outcome')) as call,patch.object(M.R,'launch',side_effect=AssertionError('must not launch')):
            with self.assertRaises(TimeoutError):M.finalize(target,ctx,steps.append)
        self.assertEqual(call.call_count,1)
        self.assertEqual(call.call_args.args,('shell','am','force-stop',M.A.PACKAGE))
        self.assertEqual(steps[-1],'exactOwnerForceStop')

    def test_final_save_drift_never_reports_preserved(self):
        target=Target();ctx=context()
        with patch.object(M.R,'markers',return_value=[]),patch.object(M.R,'ordinary',side_effect=[ctx['before'],ctx['before'],{'changed':True}]),patch.object(M.R,'pid',side_effect=['456','']),patch.object(M.R,'launch',return_value='789'),patch.object(M.time,'sleep'):
            with self.assertRaisesRegex(ValueError,'DataChanged'):M.finalize(target,ctx,lambda x:None)

    def test_success_only_exact_app_stop_then_launch(self):
        target=Target();ctx=context();steps=[]
        with patch.object(M.R,'markers',return_value=[]),patch.object(M.R,'ordinary',return_value=ctx['before']),patch.object(M.R,'pid',side_effect=['456','']),patch.object(M.R,'launch',return_value='789'),patch.object(M.time,'sleep'):
            result=M.finalize(target,ctx,steps.append)
        self.assertTrue(result['ordinaryDataUnchanged'])
        self.assertEqual(result['normalRelaunch']['pid'],789)
        self.assertEqual(target.commands,[('shell','am','force-stop',M.A.PACKAGE)])
        self.assertEqual(steps[-1],'finalPackageInventory')

    def test_inspection_requires_current_exact_runner_source_and_target(self):
        ctx=context()
        good={'status':'PASS_READ_ONLY_ACCEPTED93_LD_REGRESSION95_RECOVERY_INSPECTION','action':'inspect','runner':{'r':'bound'},'originalInvocation':ctx['originalInvocation'],'proof':ctx['update']['proof'],'identity':ctx['original']['identity'],'ordinary':ctx['before'],'markers':[],'readOnlyDeviceCommands':True}
        with patch.object(M.A,'bound',return_value={'r':'bound'}):
            M.compare_inspection(good,ctx)
            for key,value in [('status','BLOCKED'),('action','finish'),('runner',{}),('identity',{}),('ordinary',{}),('markers',['HOTR_Foreign']),('readOnlyDeviceCommands',False),('proof',{}),('originalInvocation',{})]:
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,'PassedInspection'):
                    M.compare_inspection({**good,key:value},ctx)

    def test_output_requires_fresh_uuid_under_exact_parent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'Recovery';good=root/('a'*32)
            with patch.object(M,'OUT',root):
                self.assertEqual(M.output_path(good),good.resolve())
                for invalid in [good,root/'Set01',Path(temporary)/('b'*32)]:
                    with self.subTest(invalid=invalid),self.assertRaisesRegex(ValueError,'FreshUUID'):
                        M.output_path(invalid)


if __name__=='__main__':unittest.main()
