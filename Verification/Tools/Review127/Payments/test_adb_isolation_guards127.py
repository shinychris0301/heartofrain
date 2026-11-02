"""Synthetic helpers only: no Windows observation, registry, ADB or native invocation."""
import copy
import importlib.util
from pathlib import Path
import unittest

PATH=Path(__file__).with_name('adb_isolation_guards127.py')
SPEC=importlib.util.spec_from_file_location('adb_guards127_tested',PATH)
guard=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(guard)


class Stream:
    def __init__(self,data=b'OKAY00040029'):self.data=data;self.sent=[]
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def settimeout(self,value):self.timeout=value
    def sendall(self,data):self.sent.append(data)
    def recv(self,count):value=self.data[:min(count,2)];self.data=self.data[len(value):];return value


class Backend:
    def __init__(self):self.values={name:(guard.REG_DWORD,1) for name in guard.PREFERENCE_NAMES};self.writes=[];self.acquired=self.released=0;self.fail_write=None
    def acquire(self,name,timeout):self.acquired+=1;return 'owned-mutex'
    def release(self,token):self.released+=1
    def read(self,name):return self.values[name]
    def write(self,name,value):
        if self.fail_write==name:raise OSError('synthetic')
        self.writes.append((name,value));self.values[name]=(guard.REG_DWORD,value)


def snapshot():return {'port':5037,'listeners':[{'address':'127.0.0.1','pid':42}], 'process':{'pid':42,'imagePath':'C:/Fixture/adb.exe','creationTime':'2026-10-31T00:00:00Z','imageSHA256':'a'*64},'protocolVersion':None}


class IsolationGuards127(unittest.TestCase):
    def test_host_only_version_is_fragment_bounded_and_listener_double_checked(self):
        value=snapshot();stream=Stream();seen=[]
        def observe(port):seen.append(port);return copy.deepcopy(value)
        result=guard.capture_adb_listener(5037,_observer=observe,_connector=lambda *a,**k:stream)
        self.assertEqual(seen,[5037,5037]);self.assertEqual(stream.sent,[b'000chost:version']);self.assertEqual(result['protocolVersion'],'0029')

    def test_absent_never_connects_or_autostarts(self):
        value={'port':5039,'listeners':[],'process':None,'protocolVersion':None}
        def forbidden(*a,**k):raise AssertionError('network called')
        self.assertEqual(guard.capture_adb_listener(5039,True,_observer=lambda p:value,_connector=forbidden),value)
        with self.assertRaises(guard.IsolationError):guard.capture_adb_listener(5039,_observer=lambda p:value,_connector=forbidden)

    def test_protocol_failure_length_truncation_or_nonhex_rejects(self):
        for data in (b'FAIL',b'OKAYffff',b'OKAY0004',b'OKAY0004xxxx',b'OKAYzzzz'):
            with self.subTest(data=data),self.assertRaises(guard.IsolationError):guard.capture_adb_listener(5037,_observer=lambda p:snapshot(),_connector=lambda *a,**k:Stream(data))

    def test_listener_race_blocks_after_readonly_probe(self):
        first=snapshot();second=copy.deepcopy(first);second['process']['pid']=43;items=iter((first,second))
        with self.assertRaisesRegex(guard.IsolationError,'AdbListenerChangedDuringProbe'):guard.capture_adb_listener(5037,_observer=lambda p:next(items),_connector=lambda *a,**k:Stream())

    def test_all_protected_identity_and_protocol_fields_must_remain_exact(self):
        first=snapshot();first['protocolVersion']='0029';guard.require_same_listener(first,copy.deepcopy(first))
        for field,value in [('pid',43),('imagePath','C:/Other/adb.exe'),('creationTime','later'),('imageSHA256','b'*64)]:
            after=copy.deepcopy(first);after['process'][field]=value
            with self.assertRaises(guard.IsolationError):guard.assert_shared_unchanged(first,after)
        after=copy.deepcopy(first);after['protocolVersion']='0028'
        with self.assertRaises(guard.IsolationError):guard.require_same_listener(first,after)

    def test_port_rejects_bool_noninteger_and_out_of_range(self):
        for value in (True,0,65536,'5037'):
            with self.assertRaises(guard.IsolationError):guard.capture_adb_listener(value,_observer=lambda p:None)

    def test_exact_two_key_lease_and_typed_original_restore(self):
        backend=Backend();before=copy.deepcopy(backend.values)
        with guard.EditorPrefsLease(lambda:True,_backend=backend) as lease:
            self.assertEqual(lease.report['status'],'LEASE_ACTIVE');self.assertTrue(all(v==(4,0) for v in backend.values.values()))
        self.assertEqual(backend.values,before);self.assertTrue(lease.report['restored']);self.assertEqual(backend.released,1)
        self.assertEqual([name for name,value in backend.writes],list(guard.PREFERENCE_NAMES)*2)

    def test_editor_not_closed_preserves_both_zero_values_and_blocks(self):
        backend=Backend();lease=guard.EditorPrefsLease(lambda:False,_backend=backend)
        with self.assertRaises(guard.IsolationError):
            with lease:pass
        self.assertEqual(lease.report['status'],'BLOCKED_OWNED_EDITOR_NOT_CLOSED');self.assertTrue(all(v==(4,0) for v in backend.values.values()));self.assertEqual(len(backend.writes),2)

    def test_either_changed_value_preserves_both_without_partial_restore(self):
        backend=Backend();lease=guard.EditorPrefsLease(lambda:True,_backend=backend)
        with self.assertRaises(guard.IsolationError):
            with lease:backend.values[guard.PREFERENCE_NAMES[0]]=(4,1)
        self.assertEqual(lease.report['status'],'BLOCKED_PREFERENCE_OWNERSHIP_LOST');self.assertEqual(len(backend.writes),2);self.assertEqual(backend.values[guard.PREFERENCE_NAMES[1]],(4,0))

    def test_non_dword_missing_or_nonboolean_existing_value_blocks_before_write(self):
        for value in ((1,'private-not-exported'),(4,3),None):
            backend=Backend()
            if value is None:del backend.values[guard.PREFERENCE_NAMES[1]]
            else:backend.values[guard.PREFERENCE_NAMES[1]]=value
            lease=guard.EditorPrefsLease(lambda:True,_backend=backend)
            with self.assertRaises(guard.IsolationError):lease.__enter__()
            self.assertEqual(backend.writes,[]);self.assertEqual(backend.released,1);self.assertNotIn('private-not-exported',str(lease.report))

    def test_partial_setup_failure_is_visible_and_never_creates_missing_key(self):
        backend=Backend();backend.fail_write=guard.PREFERENCE_NAMES[1];lease=guard.EditorPrefsLease(lambda:True,_backend=backend)
        with self.assertRaises(guard.IsolationError):lease.__enter__()
        self.assertEqual(lease.report['status'],'BLOCKED_PREFERENCE_LEASE_SETUP');self.assertEqual(len(backend.writes),1);self.assertFalse(lease.report['restored'])

    def test_callback_exception_or_existing_body_failure_never_causes_unsafe_restore(self):
        backend=Backend()
        def failed():raise RuntimeError('synthetic')
        lease=guard.EditorPrefsLease(failed,_backend=backend)
        with self.assertRaisesRegex(ValueError,'body'):
            with lease:raise ValueError('body')
        self.assertEqual(lease.report['status'],'BLOCKED_OWNED_EDITOR_NOT_CLOSED');self.assertEqual(len(backend.writes),2)

    def test_original_zero_is_restored_as_zero(self):
        backend=Backend();backend.values[guard.PREFERENCE_NAMES[0]]=(4,0);original=copy.deepcopy(backend.values)
        with guard.EditorPrefsLease(lambda:True,_backend=backend):pass
        self.assertEqual(backend.values,original)

    def test_durable_checkpoint_precedes_any_write_and_failure_blocks_mutation(self):
        backend=Backend();seen=[]
        def save(value):self.assertEqual(backend.writes,[]);seen.append(value)
        with guard.EditorPrefsLease(lambda:True,checkpoint=save,_backend=backend):pass
        self.assertEqual(len(seen),1);self.assertEqual(seen[0]['status'],'CAPTURED_BEFORE_MUTATION');self.assertEqual(len(seen[0]['originalValues']),2)
        backend=Backend()
        def fail(value):raise OSError('synthetic checkpoint failure')
        with self.assertRaises(guard.IsolationError):guard.EditorPrefsLease(lambda:True,checkpoint=fail,_backend=backend).__enter__()
        self.assertEqual(backend.writes,[])

    def test_post_checkpoint_external_change_blocks_before_write(self):
        backend=Backend()
        def conflict(value):backend.values[guard.PREFERENCE_NAMES[0]]=(4,0)
        with self.assertRaises(guard.IsolationError):guard.EditorPrefsLease(lambda:True,checkpoint=conflict,_backend=backend).__enter__()
        self.assertEqual(backend.writes,[])

    def test_exact_known_registry_scope(self):
        self.assertEqual(guard.REGISTRY_KEY,r'Software\Unity Technologies\Unity Editor 5.x');self.assertEqual(len(guard.PREFERENCE_NAMES),2)


if __name__=='__main__':unittest.main()
