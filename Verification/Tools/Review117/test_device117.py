"""Mocked safety checks only; never contacts adb or an actual device."""
import importlib.util
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

path=Path(__file__).with_name('device117.py');spec=importlib.util.spec_from_file_location('device117',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class PhoneSafetyTests(unittest.TestCase):
    def test_phone_inspection_is_read_only_and_reports_existing_game_process(self):
        calls=[]
        def fake(*args,serial=None,**kw):
            calls.append(args)
            replies={('devices','-l'):'List of devices attached\nUSB_SERIAL device product:sample',
                ('shell','getprop','ro.kernel.qemu'):'0',('shell','getprop','ro.product.model'):'Fixture phone',
                ('shell','getprop','ro.build.version.sdk'):'36',('shell','am','get-current-user'):'0',
                ('shell','dumpsys','window','policy'):'KeyguardServiceDelegate\n showing=false',
                ('shell','dumpsys','power'):'mWakefulness=Awake',
                ('shell','pm','list','packages','--user','0'):'package:com.heartoftherain.review98',
                ('shell','pidof','com.heartoftherain.review98'):'111'}
            if args not in replies: raise AssertionError('Unexpected command: '+repr(args))
            return replies[args],0
        with patch.object(module,'adb',side_effect=fake),patch.object(module.ADB.__class__,'is_file',return_value=True):
            _,state=module.phone()
        self.assertTrue(state['existingGameProcessRunning']);self.assertFalse(state['testPackagePresent'])
        self.assertTrue(all(c[0] in ('devices','shell') for c in calls))
        self.assertFalse(any(c[0]=='shell' and c[1] in ('cat','run-as','input','am force-stop','pm clear') for c in calls))

    def test_running_original_app_blocks_before_install(self):
        state={'existingGameProcessRunning':True,'testPackagePresent':False}
        with patch.object(module,'phone',return_value=('private',state)),patch.object(module,'adb') as adb,patch.object(sys,'argv',['device117','install','--execute','--tag','NoMutation']):
            with self.assertRaisesRegex(ValueError,'ExistingGameMustBeClosedWithoutInterruptingAnAttempt'): module.main()
            adb.assert_not_called()

    def test_mutation_modes_require_explicit_execute(self):
        with patch.object(module,'phone') as phone,patch.object(sys,'argv',['device117','install','--tag','NoMutation']):
            with self.assertRaisesRegex(ValueError,'ExplicitFreshTagRequired'): module.main()
            phone.assert_not_called()

    def test_process_identity_changes_when_pid_is_reused(self):
        start=['10']
        def fake(*args,**kw):
            if args==('shell','pidof',module.PACKAGE): return '123',0
            if args==('shell','cat','/proc/123/stat'): return '123 (fixture) '+' '.join(['0']*19+[start[0]]+['0']*4),0
            if args==('shell','cat','/proc/sys/kernel/random/boot_id'): return '12345678-1234-1234-1234-123456789abc',0
            raise AssertionError(repr(args))
        with patch.object(module,'adb',side_effect=fake):
            first=module.process_identity('private');start[0]='11';second=module.process_identity('private')
        self.assertNotEqual(first,second)

    def test_old_fixture_receipt_cannot_stop_an_unbound_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);evidence=root/'Verification/Evidence/Review117/Device';private=root/'.verification-cache/Review117/Physical/Collected';private.mkdir(parents=True)
            install=evidence/'Install/Install.json';launch=evidence/'Launch/Launch.json';collect=evidence/'Collect/Collect.json'
            for path in (install,launch,collect):path.parent.mkdir(parents=True,exist_ok=True)
            apk='a'*64;nonce='b'*32
            install.write_text(json.dumps({'status':'PASS_ISOLATED_TEST_INSTALL','package':'com.heartoftherain.review117preview','apkSHA256':apk}))
            launch.write_text(json.dumps({'status':'PASS_ISOLATED_TEST_LAUNCH_REQUESTED','fixture':'all','fixtureLevel':1,'runNonce':nonce,'apkSHA256':apk}))
            raw=json.dumps({'status':'PASS_DEVICE_FIXTURE','runNonce':nonce,'level':1}).encode();(private/'Report.json').write_bytes(raw)
            collect.write_text(json.dumps({'status':'PASS_ISOLATED_DEVICE_FIXTURE_COLLECTED','fixture':'all','apkSHA256':apk,'fixtureReportSHA256':hashlib.sha256(raw).hexdigest(),'privateEvidenceDirectory':'.verification-cache/Review117/Physical/Collected'}))
            def adb(*args,**kw):
                if args[:3]==('shell','pm','path'):return 'package:/data/app/base.apk',0
                if args[:2]==('shell','sha256sum'):return apk+'  /data/app/base.apk',0
                raise AssertionError('Unexpected device command '+repr(args))
            state={'existingGameProcessRunning':False,'testPackagePresent':True}
            argv=['device117','reset','--execute','--preview','--tag','Attempt','--receipt',str(install),'--launch-receipt',str(launch),'--collect-receipt',str(collect)]
            with patch.object(module,'ROOT',root),patch.object(module,'EVIDENCE',evidence),patch.object(module,'phone',return_value=('private',state)),patch.object(module,'adb',side_effect=adb),patch.object(sys,'argv',argv):
                self.assertEqual(module.main(),1)
            result=json.loads((evidence/'Attempt/Reset.json').read_text());self.assertEqual(result['code'],'FixtureProcessIdentityRequired')

if __name__=='__main__':unittest.main()
