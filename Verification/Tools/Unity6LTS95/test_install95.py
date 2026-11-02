"""Host-only installer ownership/UAC guards; no installer is executed."""
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

import install95 as installer


class InstallerHostTests(unittest.TestCase):
    def test_stock_arguments_are_literal_silent_and_unquoted_destination_last(self):
        command=installer.installer_command(Path('C:/fixture path/UnitySetup.exe'))
        self.assertEqual(command[1:],['/S','/D='+str(installer.TARGET)])
        self.assertFalse(command[-1].startswith('"'));self.assertNotIn('cmd',command)

    def test_suspended_process_is_owned_before_resume_and_waited_bounded(self):
        calls=[]
        job=types.SimpleNamespace(assign=lambda pid:calls.append(('assign',pid)),close=lambda:calls.append(('close',)))
        process=types.SimpleNamespace(pid=123,returncode=0,wait=lambda timeout:calls.append(('wait',timeout)),poll=lambda:0)
        api=types.SimpleNamespace(OwnedJob=lambda:job);jobs=types.SimpleNamespace(resume_owned_primary=lambda p:calls.append(('resume',p.pid)))
        with tempfile.TemporaryDirectory(prefix='hotr95_install_owned_host_') as folder,patch.object(installer.subprocess,'Popen',return_value=process) as launch:
            result=installer.launch_owned(['fixture-installer','/S','/D=E:/fixture'],Path(folder),60,api,jobs)
        self.assertEqual(result['outcome'],'Completed');self.assertLess(calls.index(('assign',123)),calls.index(('resume',123)))
        self.assertIn(('wait',60),calls);self.assertEqual(launch.call_args.kwargs['creationflags'],subprocess.CREATE_NO_WINDOW|0x4)

    def test_error740_requires_normal_uac_without_fallback_process_or_target_mutation(self):
        error=OSError('normal elevation required');error.winerror=740;closed=[]
        job=types.SimpleNamespace(assign=lambda pid:self.fail('Nothing launched'),close=lambda:closed.append(True))
        api=types.SimpleNamespace(OwnedJob=lambda:job);jobs=types.SimpleNamespace(resume_owned_primary=lambda p:self.fail('Nothing launched'))
        with tempfile.TemporaryDirectory(prefix='hotr95_install_uac_host_') as folder,patch.object(installer.subprocess,'Popen',side_effect=error) as launch:
            result=installer.launch_owned(['fixture-installer'],Path(folder),60,api,jobs)
            self.assertEqual(len(list(Path(folder).iterdir())),2)
        self.assertEqual(result['outcome'],'RequiresNormalUAC');self.assertFalse(result['installerLaunched']);self.assertEqual(launch.call_count,1);self.assertTrue(closed)

    def test_timeout_closes_only_owned_job_and_never_reports_completion(self):
        calls=[];state={'wait':0}
        def wait(timeout):
            state['wait']+=1
            if state['wait']==1:raise subprocess.TimeoutExpired('fixture-installer',timeout)
        process=types.SimpleNamespace(pid=1,returncode=-1,wait=wait,poll=lambda:-1)
        api=types.SimpleNamespace(OwnedJob=lambda:types.SimpleNamespace(assign=lambda pid:None,close=lambda:calls.append('closed')))
        jobs=types.SimpleNamespace(resume_owned_primary=lambda p:None)
        with tempfile.TemporaryDirectory(prefix='hotr95_install_timeout_host_') as folder,patch.object(installer.subprocess,'Popen',return_value=process):
            result=installer.launch_owned(['fixture-installer'],Path(folder),60,api,jobs)
        self.assertEqual(result['outcome'],'TimedOut');self.assertTrue(result['timedOut']);self.assertTrue(calls)

    def test_out_of_range_deadline_is_rejected_before_popen(self):
        with patch.object(installer.subprocess,'Popen') as launch:
            for seconds in (0,59,3601):
                with self.assertRaises(ValueError):installer.launch_owned([],Path('.'),seconds,None,None)
        launch.assert_not_called()

    def test_no_elevation_compatibility_or_security_bypass_is_implemented(self):
        text=Path(installer.__file__).read_text('utf-8-sig')
        self.assertNotIn('ShellExecuteEx',text);self.assertNotIn('__COMPAT_LAYER',text);self.assertNotIn('Set-MpPreference',text)
        self.assertNotRegex(text,r'''lpVerb\s*=\s*['"]runas['"]''');self.assertNotIn('winreg.Set',text);self.assertNotIn('subprocess.CREATE_BREAKAWAY_FROM_JOB',text)
        self.assertIn('ExistingTargetPreserved',text);self.assertIn('verified_editor_installer',text)


if __name__=='__main__':unittest.main(verbosity=2)
