"""Host-only retained-failure and data-preservation gates; no native calls."""
import unittest
import cold_launch97 as subject


class ColdLaunchTests(unittest.TestCase):
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
