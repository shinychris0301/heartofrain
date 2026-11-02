import argparse
import json
import os
from pathlib import Path

from .api import create_app
from .operations import OperationError, backup_database, reconcile_bounded, require_mode, restore_database
from .invoice_discovery import DiscoveryScanner, RuStoreInvoiceLister, STATUSES
from .rustore_provider import RuStoreInvoiceProvider
from .service import ServiceError


def main(argv=None):
    parser = argparse.ArgumentParser(description='Local operator tools; credentials are never printed.')
    sub = parser.add_subparsers(dest='command', required=True)
    provision = sub.add_parser('provision')
    provision.add_argument('--out', required=True, type=Path, help='New ignored credential file outside source-controlled content')
    provision.add_argument('--player')
    provision.add_argument('--role', choices=('player', 'verifier'), default='player')
    provision.add_argument('--lifetime', type=int, default=86400)
    sub.add_parser('schema')
    for name in ('backup', 'restore'):
        operation = sub.add_parser(name, help='Validated SQLite copy to a new file; never replaces an existing database')
        operation.add_argument('--source', required=True, type=Path)
        operation.add_argument('--out', required=True, type=Path)
        operation.add_argument('--timeout-seconds', type=int, default=60)
    worker = sub.add_parser('reconcile-worker', help='Explicit bounded sandbox reconciliation batch; no daemon or secret output')
    worker.add_argument('--mode', required=True, choices=('local', 'staging'))
    worker.add_argument('--worker-id', default='operator')
    worker.add_argument('--max-jobs', type=int, default=50)
    worker.add_argument('--seed-limit', type=int, default=50)
    worker.add_argument('--poll-seconds', type=int, default=300)
    discovery = sub.add_parser('discover-invoices', help='Explicit bounded production listing hints; never credits a listing or enables live purchases')
    discovery.add_argument('--mode', required=True, choices=('local', 'staging'))
    discovery.add_argument('--environment', required=True, choices=('production', 'sandbox'))
    discovery.add_argument('--app-id', required=True, type=int)
    discovery.add_argument('--date', required=True, help='Explicit ISO date; provider timezone boundary requires operator overlap/rescan')
    discovery.add_argument('--days', type=int, default=3)
    discovery.add_argument('--max-pages', type=int, default=5, help='Maximum pages per explicit date in this batch')
    discovery.add_argument('--page-size', type=int, default=100)
    discovery.add_argument('--status', choices=STATUSES, default='CONFIRMED')
    discovery.add_argument('--rescan', action='store_true', help='Restart each date/status cursor to discover late additions')
    discovery.add_argument('--worker-id', default='operator')
    args = parser.parse_args(argv)
    try:
        require_mode(os.getenv('HOTR_BACKEND_MODE', 'local'))
        if args.command in ('backup', 'restore'):
            function = backup_database if args.command == 'backup' else restore_database
            print(json.dumps(function(args.source, args.out, timeout_seconds=args.timeout_seconds)))
            return
        if args.command in ('reconcile-worker', 'discover-invoices'):
            existing = os.getenv('HOTR_BACKEND_MODE')
            if existing is not None and existing != args.mode:
                raise OperationError('explicit_mode_conflicts_with_environment')
            os.environ['HOTR_BACKEND_MODE'] = args.mode
            try:
                app = create_app()
                if args.command == 'reconcile-worker':
                    value = reconcile_bounded(app, args.mode, worker_id=args.worker_id,
                        max_jobs=args.max_jobs, seed_limit=args.seed_limit, poll_seconds=args.poll_seconds)
                else:
                    provider = app.state.commerce.provider
                    if not isinstance(provider, RuStoreInvoiceProvider):
                        raise OperationError('invoice_discovery_not_configured')
                    scanner = DiscoveryScanner(app.state.authority, app.state.commerce,
                        RuStoreInvoiceLister(provider.token_supplier, provider.transport), enabled=True)
                    value = {'status': 'completed', 'mode': args.mode, 'productionEnabled': False,
                        'grantsFromListing': False, 'dates': scanner.scan_overlap(args.app_id, args.date,
                            args.environment == 'sandbox', args.worker_id, days=args.days, max_pages=args.max_pages,
                            page_size=args.page_size, status=args.status, rescan=args.rescan)}
            finally:
                if existing is None:
                    os.environ.pop('HOTR_BACKEND_MODE', None)
                else:
                    os.environ['HOTR_BACKEND_MODE'] = existing
            print(json.dumps(value))
            return
    except OperationError as error:
        raise SystemExit(str(error)) from None
    except ServiceError as error:
        raise SystemExit(error.code) from None
    except (OSError, RuntimeError, ValueError):
        raise SystemExit('operator_configuration_unavailable') from None
    app = create_app()
    if args.command == 'schema':
        print(json.dumps(app.openapi(), indent=2))
        return
    target = args.out.resolve()
    repo = Path(__file__).resolve().parents[2]
    allowed = (repo / '.verification-cache', repo / 'Backend/.local')
    if not any(target.is_relative_to(path) for path in allowed):
        raise SystemExit('Credential output must be inside ignored .verification-cache or Backend/.local')
    target.parent.mkdir(parents=True, exist_ok=True)
    # Create the destination BEFORE committing a credential; never overwrite one.
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as file:
            credential = app.state.authority.provision(args.player, args.role, args.lifetime)
            json.dump(credential, file)
            file.flush()
            os.fsync(file.fileno())
    except BaseException:
        # A failed credential export may leave an empty/partial file. Preserve it
        # for the operator; the endpoint has no way to reveal a lost token.
        raise
    print('Provisioned credential saved to the requested ignored local file; token not printed.')


if __name__ == '__main__':
    main()
