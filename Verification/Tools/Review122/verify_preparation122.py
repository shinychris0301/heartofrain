"""Run the focused preparation/monitor controls with sanitized, source-bound evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Backend'))
MODULES = ('tests.test_production_prepare122', 'tests.test_provider_readiness122',
           'tests.test_monitoring122')
FILES = [
    'Backend/hotr_backend/production_prepare122.py',
    'Backend/hotr_backend/payment_readiness122.py',
    'Backend/hotr_backend/provider_readiness122.py',
    'Backend/hotr_backend/monitoring122.py',
    'Backend/tests/test_production_prepare122.py',
    'Backend/tests/test_provider_readiness122.py',
    'Backend/tests/test_monitoring122.py',
    'Backend/hotr_backend/commerce_schemas.py',
    'Backend/hotr_backend/newads_schemas.py', 'Backend/hotr_backend/schemas.py',
    'Backend/hotr_backend/vk_provider.py',
    'Release/RuStore/commerce.example.json', 'Release/RuStore/checkout.example.json',
    'Release/RuStore/release.example.json', 'Release/RuStore/registered-products122.json',
    'Release/Advertising/advertising.example.json', 'Backend/config/ads.json',
    'Release/Production122/monitoring/Install-Monitor122.ps1',
    'Verification/Tools/Review122/verify_preparation122.py',
]


def pins():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in FILES}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    before = pins()
    started = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromNames(MODULES)
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    after = pins()
    success = result.wasSuccessful() and not result.skipped and before == after
    report = {
        'status': 'PASS_PREPARATION122_CONTROLS' if success else 'FAIL_PREPARATION122_CONTROLS',
        'checkedAtUtc': datetime.now(timezone.utc).isoformat(),
        'tests': result.testsRun, 'failures': [t.id() for t, _ in result.failures],
        'errors': [t.id() for t, _ in result.errors], 'skipped': [t.id() for t, _ in result.skipped],
        'modules': MODULES, 'seconds': round(time.monotonic() - started, 3),
        'sourceSHA256': before, 'sourceSHA256After': after,
        'inputsUnchanged': before == after,
        'scope': 'Host configuration and monitor controls, including disposable HTTP. No Unity, Android, live provider, deployed task or production acceptance claim.',
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('status', 'tests', 'failures', 'errors', 'skipped', 'inputsUnchanged')}))
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
