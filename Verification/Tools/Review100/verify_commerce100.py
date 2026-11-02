"""Bounded Python-only financial regression set; no native gameplay worker."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import unittest
import warnings

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / 'Backend'
PATTERNS = ('test_commerce.py', 'test_commerce_grants100.py', 'test_wallet.py',
            'test_identity.py', 'test_notifications.py', 'test_invoice_discovery.py',
            'test_operations.py', 'test_actor_deadline93.py', 'test_release_pricing.py',
            'test_migration89.py', 'test_newads.py')
AFFECTED = ('tests.test_commerce_grants100',
            'tests.test_newads.RewardedAdTests.test_19_migration6_preserves_wallet_and_backup_restore_exact_new_receipts',
            'tests.test_newads.RewardedAdTests.test_32_real_schema6_backup_validates_and_failed_migration_rolls_back_all_ads_objects',
            'tests.test_newads.RewardedAdTests.test_40_schema7_upgrade_keeps_existing_reward_receipts_and_quota',
            'tests.test_operations.OperationsTests.test_schema4_purchase_wallet_snapshot_stays_known_after_schema5_added')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs():
    paths = [p for folder in ('hotr_backend', 'config', 'tests')
             for p in sorted((BACKEND / folder).rglob('*')) if p.is_file() and p.suffix in ('.py', '.json')]
    paths.extend(sorted((ROOT / 'Release/RuStore').glob('*.json')))
    paths.extend((Path(__file__),
                  ROOT / 'Unity/Assets/HeartOfTheRain/App/Shop/Data/ShopCatalog.json',
                  ROOT / 'Unity/Assets/HeartOfTheRain/App/NoMovesDesign/Data/Shop_Preview_Products.json'))
    return [{'path': p.relative_to(ROOT).as_posix(), 'sha256': digest(p)} for p in paths]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--affected-imports', action='store_true', help='Reproduce the full-run package imports and four historic-schema cases only.')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)  # Never rewrite old receipts.
    os.chdir(BACKEND)
    sys.path[:0] = [str(BACKEND)]
    before, started = inputs(), time.time()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('default')
        suite = unittest.TestSuite()
        if args.affected_imports:
            suite.addTests(unittest.defaultTestLoader.loadTestsFromNames(AFFECTED))
        else:
            for pattern in PATTERNS:
                suite.addTests(unittest.defaultTestLoader.discover(str(BACKEND / 'tests'), pattern=pattern, top_level_dir=str(BACKEND)))
        with (out / 'unittest.log').open('w', encoding='utf-8', newline='\n') as log:
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    after = inputs()
    stable = before == after
    report = {'status': 'PASS' if result.wasSuccessful() and stable else 'FAIL',
              'scope': 'Actual SQLite/ASGI transactions with scripted providers and Python subprocesses; no Unity/Mono/SDK/ADB or real payments',
              'selection': 'affected_package_imports' if args.affected_imports else 'focused_financial_suites',
              'patterns': list(AFFECTED if args.affected_imports else PATTERNS), 'testsRun': result.testsRun, 'failures': len(result.failures),
              'errors': len(result.errors), 'skipped': len(result.skipped), 'seconds': time.time() - started,
              'inputsUnchanged': stable, 'inputs': before,
              'changedInputs': [p for p in after if p not in before],
              'warnings': [{'category': w.category.__name__, 'message': str(w.message)} for w in caught],
              'runnerSha256': digest(Path(__file__)), 'logSha256': digest(out / 'unittest.log')}
    (out / 'Report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('inputs', 'changedInputs', 'patterns')}))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
