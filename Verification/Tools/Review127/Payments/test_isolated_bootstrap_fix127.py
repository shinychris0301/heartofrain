"""One proven SDK37 listen-syntax regression. No native/ADB/prefs execution."""
import ast
import hashlib
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent

class IsolatedBootstrapListenFix127(unittest.TestCase):
    def test_only_server_listen_spec_changes_while_client_and_all_guards_stay_exact(self):
        old=HERE/'run_isolated_native127.py';new=HERE/'run_isolated_native127_02.py';before=old.read_bytes();after=new.read_bytes()
        self.assertEqual(hashlib.sha256(before).hexdigest(),'e976ba102d238a17ea26cba0832aab6fe4205dba27c6e0bea32615ff67693439')
        source=b"command=[str(ADB),'-L','tcp:127.0.0.1:5039','--one-device'";target=b"command=[str(ADB),'-L','tcp:5039','--one-device'"
        self.assertEqual(before.count(source),1);self.assertEqual(after,before.replace(source,target,1))
        ast.parse(after.decode('utf-8'))
        spec=importlib.util.spec_from_file_location('bootstrap_fixed_wrapper127',new);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        env=module.private_environment('a'*32)
        self.assertEqual(env['ADB_SERVER_SOCKET'],'tcp:127.0.0.1:5039');self.assertEqual(env['ANDROID_ADB_SERVER_PORT'],'5039')
        self.assertNotIn("'-a'",after.decode('utf-8'))

if __name__=='__main__':unittest.main()
