"""Host-only retained-failure and data-preservation gates; no native calls."""
import unittest
import copy
import hashlib
import cold_launch97b as subject


class ColdLaunchTests(unittest.TestCase):
    def test_current_boot_selector_api_abi_and_tool_bytes_must_match_cross_proved_boot(self):
        boot='12345678-1234-1234-1234-123456789abc'
        abi={'advertisedAbis':['arm64-v8a'],'advertised64BitAbis':['arm64-v8a']}
        tools={'adbTool':{'sha256':'host-adb'},'console':{'sha256':'host-console'}}
        original={'consoleAndADBCurrentBootMatch':True,'index':0,'selectorSHA256':'host-selector',
                  'bootSHA256':hashlib.sha256(boot.encode()).hexdigest(),'api':34,**abi,**tools}
        subject.validate_continuity(original,boot,0,'host-selector',34,abi,tools)
        for key,value in (('consoleAndADBCurrentBootMatch',False),('index',1),('selectorSHA256','changed'),
                          ('bootSHA256','changed'),('api',35),('advertisedAbis',[]),('adbTool',{}),('console',{})):
            bad=copy.deepcopy(original);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                subject.validate_continuity(bad,boot,0,'host-selector',34,abi,tools)

    def good(self):
        owner = {'ownerStopped': True, 'activeAttempts': 0, 'preferences': {'host': 'fixture'}}
        return {'status': 'FAIL_FULL_GAME_LDPLAYER95_INSTALL', 'errorCategory': 'LD95CandidateUnexpectedlyStarted',
                'ownerPreservedAtExit': True, 'ownerBefore': owner, 'ownerAfter': dict(owner), 'ownerFinal': dict(owner)}

    def test_only_retained_unexpected_pid_failure_is_eligible(self):
        subject.validate_install_fields(self.good())
        for key, value in (('status', 'PASS'), ('errorCategory', 'OtherFailure'), ('ownerPreservedAtExit', False)):
            row = self.good(); row[key] = value
            with self.assertRaises(ValueError): subject.validate_install_fields(row)

    def test_owner_byte_drift_or_active_attempt_is_never_waived(self):
        for change in ('bytes', 'active', 'running'):
            row = self.good()
            if change == 'bytes': row['ownerFinal']['preferences'] = {'host': 'changed'}
            else:
                for key in ('ownerBefore', 'ownerAfter', 'ownerFinal'):
                    row[key]['activeAttempts' if change == 'active' else 'ownerStopped'] = 1 if change == 'active' else False
            with self.subTest(change=change), self.assertRaises(ValueError): subject.validate_install_fields(row)


if __name__ == '__main__': unittest.main(verbosity=2)
