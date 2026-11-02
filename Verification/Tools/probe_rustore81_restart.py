"""Bounded authenticated HTTP readback across a real disposable server restart."""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    started = datetime.now(timezone.utc).isoformat()
    parser = argparse.ArgumentParser()
    parser.add_argument('--connection', required=True)
    parser.add_argument('--phase', choices=('before', 'after'), required=True)
    args = parser.parse_args()
    private_path = Path(args.connection).resolve()
    if not private_path.is_relative_to((ROOT / '.verification-cache/RuStore81').resolve()):
        raise SystemExit('Only isolated fixture connections are accepted')
    private = json.loads(private_path.read_text('utf-8'))
    output = ROOT / 'Verification/Evidence/RuStore81'
    native = json.loads((output / 'Native/HTTP.json').read_text('utf-8-sig'))
    if native['status'] != 'PASS_NATIVE_RUSTORE81_HTTP_STAGING_CLIENT':
        raise SystemExit('Native HTTP proof required')
    source = json.loads((output / 'Backend/Service_Tests.json').read_text('utf-8-sig'))['sourceSHA256After']
    if any(sha(ROOT / name) != digest for name, digest in source.items()):
        raise SystemExit('Backend changed after service proof')
    with httpx.Client(base_url=private['origin'], headers={'Authorization': 'Bearer ' + private['token']},
                      timeout=10, follow_redirects=False, trust_env=False) as client:
        def get(path):
            result = client.get(path)
            if result.status_code != 200 or len(result.content) > 65_536:
                raise SystemExit('HTTP restart readback failed')
            return result.json()
        wallet = get('v1/wallet')
        order = get('v1/commerce/orders/' + native['orderId'])
        ledger = get('v1/wallet/ledger')
    if wallet['playerId'] != private['playerId'] or wallet['balanceScope'] != 'server_wallet' or not wallet['initialized']:
        raise SystemExit('Wallet identity/scope mismatch')
    if wallet['normalUnityProfileIntegrated'] or wallet['localProfileMutated'] or wallet['refundReviewRequired']:
        raise SystemExit('Unexpected wallet integration/review state')
    if not order['availableToSpend'] or order['state'] != 'Confirmed' or order['credit']['coins'] != 1000:
        raise SystemExit('Purchase state not durably confirmed')
    if order['purchaseId'] != private['expectedPurchaseId'] or order['invoiceId'] != private['invoiceId']:
        raise SystemExit('Purchase identity mismatch')
    if ledger['hasMore'] or sum(e['origin'].startswith('commerce/') for e in ledger['entries']) != 1:
        raise SystemExit('Duplicate or missing commerce wallet origin')
    # UTC observation advances; balances, timer, revisions and receipts do not.
    wallet.pop('serverUtc')
    state = {'wallet': wallet, 'ledger': ledger,
             'order': {key: order[key] for key in ('orderId', 'state', 'coins', 'credit', 'deliveryAcknowledgement',
                          'availableToSpend', 'availableInServerWallet', 'balanceScope', 'localProfileMutated')}}
    path = output / 'Backend/HTTP_Restart.json'
    report = {'status': 'WAITING_FOR_ACTUAL_PROCESS_RESTART', 'startedUtc': started,
              'utc': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(), 'runId': private['runId'],
              'nativeReportSHA256': sha(output / 'Native/HTTP.json'), 'sourceSHA256': source, 'before': state,
              'scope': 'Actual loopback HTTP and SQLite process-restart readback. Synthetic store provider only; no SDK call, real RuStore payment or production wallet migration.'}
    if args.phase == 'after':
        report = json.loads(path.read_text('utf-8'))
        if report['runId'] != private['runId'] or report['sourceSHA256'] != source or report['before'] != state:
            raise SystemExit('Durable state changed across actual process restart')
        report.update(status='PASS_RUSTORE81_ACTUAL_HTTP_PROCESS_RESTART', after=state,
                      afterStartedUtc=started, utc=datetime.now(timezone.utc).isoformat(), afterPid=os.getpid(),
                      nativeReportSHA256=sha(output / 'Native/HTTP.json'))
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(report['status'])


if __name__ == '__main__':
    main()
