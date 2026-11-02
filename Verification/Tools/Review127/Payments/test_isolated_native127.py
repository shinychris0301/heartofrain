"""Pure isolation guards only: no host sockets/prefs/processes/native/ADB calls."""
from __future__ import annotations
import ast
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('isolated_native_guard_tests127',HERE/'run_isolated_native127.py');wrapper=importlib.util.module_from_spec(spec);spec.loader.exec_module(wrapper)
SOURCE=(HERE/'run_isolated_native127.py').read_text('utf-8')

class Peer:
    def __init__(self,payload):self.payload=payload;self.requests=[];self.timeouts=[]
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def settimeout(self,value):self.timeouts.append(value)
    def sendall(self,value):self.requests.append(value)
    def recv(self,count):value=self.payload[:count];self.payload=self.payload[count:];return value

class Process:
    def __init__(self,pid):self.pid=pid;self.code=None;self.killed=False
    def poll(self):return self.code
    def kill(self):self.killed=True;self.code=-9

class Job:
    def __init__(self):self.pids=[];self.closed=False
    def assign(self,pid):self.pids.append(pid)
    def close(self):self.closed=True

class IsolationWrapper127(unittest.TestCase):
    def test_source_syntax_and_immutable_runner_delegation(self):
        ast.parse(SOURCE)
        self.assertIn("RUNNER=HERE/'run_payment_diagnostics127_02.py'",SOURCE)
        self.assertIn("sha(RUNNER)==RUNNER_SHA256",SOURCE)
        self.assertIn('runner.run(receipt_path,tag,build,layout,timeout,layout_report,layout_sha)',SOURCE)
        self.assertNotIn('local_password(',SOURCE);self.assertNotIn('keytool',SOURCE)

    def test_shared_endpoint_allows_only_host_version_never_lifecycle_or_device(self):
        peer=Peer(b'OKAY00040029');seen=[]
        def connector(address,timeout):seen.append((address,timeout));return peer
        self.assertEqual(wrapper.adb_query(5037,'host:version',connector),b'0029')
        self.assertEqual(seen[0][0],('127.0.0.1',5037));self.assertEqual(peer.requests,[b'000chost:version'])
        for service in ('host:devices-l','host:kill','kill-server','start-server','shell:echo test','host:connect:example'):
            with self.assertRaises(RuntimeError):wrapper.adb_query(5037,service,connector)
        self.assertEqual(len(seen),1)

    def test_private_endpoint_empty_devices_and_bounded_malformed_protocol(self):
        self.assertEqual(wrapper.adb_query(5039,'host:devices-l',lambda *a,**k:Peer(b'OKAY0000')),b'')
        for body in (b'FAIL0000',b'OKAYZZZZ',b'OKAYffff',b'OKAY0004002',b'OKAY0004zzzz'):
            with self.assertRaises(RuntimeError):wrapper.adb_query(5039,'host:version',lambda *a,**k:Peer(body))
        with self.assertRaises(RuntimeError):wrapper.adb_query(5038,'host:version',lambda *a,**k:Peer(b''))

    def test_read_protocol_has_total_deadline(self):
        peer=Peer(b'OKAY00040029')
        with patch.object(wrapper.time,'monotonic',side_effect=[0,2]):
            with self.assertRaisesRegex(RuntimeError,'AdbHostProtocolDeadline127'):wrapper.adb_query(5039,'host:version',lambda *a,**k:peer)

    def test_child_environment_disables_all_transport_initializers_and_clears_extra_keys(self):
        env=wrapper.private_environment('a'*32)
        for name in ('ADB_USB','ADB_EMU','ADB_MDNS','ADB_MDNS_AUTO_CONNECT'):self.assertEqual(env[name],'0')
        self.assertEqual(env['ADB_LOCAL_TRANSPORT_MAX_PORT'],'5554');self.assertEqual(env['ADB_SERVER_SOCKET'],'tcp:127.0.0.1:5039');self.assertEqual(env['ANDROID_ADB_SERVER_PORT'],'5039')
        self.assertIsNone(env['ADB_VENDOR_KEYS']);self.assertNotIn('HOME',env);self.assertNotIn('ANDROID_USER_HOME',env);self.assertNotIn('USERPROFILE',env)
        self.assertTrue(env['ANDROID_SERIAL'].startswith('HOTR_DIAGNOSTIC_NO_DEVICE_'))

    def test_child_environment_restores_original_presence_and_does_not_export_values(self):
        with patch.dict(os.environ,{'ADB_VENDOR_KEYS':'SYNTHETIC_EXISTING_PATH','ADB_USB':'SYNTHETIC_ORIGINAL'},clear=False):
            with wrapper.ChildEnvironment({'ADB_VENDOR_KEYS':None,'ADB_USB':'0'}):self.assertNotIn('ADB_VENDOR_KEYS',os.environ);self.assertEqual(os.environ['ADB_USB'],'0')
            self.assertEqual(os.environ['ADB_VENDOR_KEYS'],'SYNTHETIC_EXISTING_PATH');self.assertEqual(os.environ['ADB_USB'],'SYNTHETIC_ORIGINAL')

    def test_only_processes_explicitly_owned_are_assigned_or_stopped(self):
        job=Job();owned=wrapper.Ownership(job);server=Process(11);editor=Process(12);foreign=Process(13)
        owned.add(server,'daemon');owned.add(editor,'editor');self.assertEqual(job.pids,[11,12]);self.assertFalse(foreign.killed)
        owned.close();self.assertTrue(job.closed);extra=Process(14)
        with self.assertRaises(RuntimeError):owned.add(extra,'editor')
        self.assertTrue(extra.killed);self.assertFalse(foreign.killed)

    def test_failed_job_assignment_and_failed_kill_retain_process_for_cleanup_gate(self):
        class FailingJob(Job):
            def assign(self,pid):raise RuntimeError('SYNTHETIC_ASSIGNMENT_FAILURE')
        class FailingKill(Process):
            def kill(self):self.killed=True;raise OSError('SYNTHETIC_TERMINATION_FAILURE')
        owned=wrapper.Ownership(FailingJob());editor=FailingKill(27)
        with self.assertRaises(OSError):owned.add(editor,'editor')
        self.assertIs(owned.editor,editor);self.assertIn(('editor',editor),owned.processes)
        self.assertFalse(owned.editor_closed());self.assertFalse(owned.all_stopped())

    def test_unentered_lease_cannot_be_restored_without_mutex_ownership(self):
        final=SOURCE.split('finally:',1)[1]
        self.assertIn('if lease_entered:',final);self.assertIn("elif lease is not None:record['preferenceLease']=lease.report",final)
        self.assertIn('lease.__enter__();lease_entered=True',SOURCE)

    def test_lifecycle_argv_targets_only_owned_loopback_server(self):
        self.assertIn("[str(ADB),'-L','tcp:127.0.0.1:5039','--one-device',values['ANDROID_SERIAL'],'server','nodaemon']",SOURCE)
        self.assertNotIn("[str(ADB),'kill-server'",SOURCE);self.assertNotIn("'-P','5037'",SOURCE)
        self.assertIn('guards.require_same_listener(shared_before,shared_after)',SOURCE)
        self.assertIn('privateDaemonLogPubliclyCopied',SOURCE)
        self.assertNotIn('shutil.copyfile',SOURCE)

if __name__=='__main__':unittest.main()
