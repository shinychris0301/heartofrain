"""Owned production invoice discovery; listing results never authorize credits.

Use an explicit provider date and bounded overlap. The provider's date/timezone
boundary is not inferred from the host clock. Resume Pending cursors before
starting a rescan, which deliberately resets a date/status cursor to page zero.

The existing RuStoreInvoiceLister owns the fixed HTTP contract. No caller can
select a hostname, provide a token, choose another application, or emit invoice
identifiers through this operator entrypoint.
"""
import argparse
import datetime as dt
import json
import re

from . import production_runtime122 as runtime
from .invoice_discovery import DiscoveryScanner, RuStoreInvoiceLister, STATUSES
from .rustore_provider import RuStoreInvoiceProvider
from .service import ServiceError


class ProductionDiscoveryError(Exception):
    """Fixed public diagnostics without provider or configuration input values."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require(value, code):
    if not value:
        raise ProductionDiscoveryError(code)


def _scope(date, days, max_pages, page_size, status, rescan, worker_id):
    _require(type(date) is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', date),
             'production_discovery_explicit_iso_date_required')
    _require(type(days) is int and 1 <= days <= 7
             and type(max_pages) is int and 1 <= max_pages <= 20
             and type(page_size) is int and 1 <= page_size <= 500
             and type(status) is str and status in STATUSES
             and type(rescan) is bool
             and type(worker_id) is str and re.fullmatch(r'[A-Za-z0-9_.-]{1,64}', worker_id),
             'production_discovery_scope_invalid')
    try:
        anchor = dt.date.fromisoformat(date)
        # Validate the entire overlap before any cursor/clock/job mutation.
        anchor - dt.timedelta(days=days - 1)
    except (ValueError, OverflowError):
        raise ProductionDiscoveryError('production_discovery_date_range_invalid') from None


class _OwnedLister:
    """Keep each network page bound to the still-open operations owner."""
    configured = True
    supports_sandbox = False

    def __init__(self, app, manifest, inner):
        self.app, self.manifest, self.inner = app, manifest, inner

    def page(self, *args, **kwargs):
        runtime.require_owned_application(self.app, self.manifest, purpose='operations')
        return self.inner.page(*args, **kwargs)


def discover_bounded(app, manifest_or_path, *, date, days=3, max_pages=5,
                     page_size=100, status='CONFIRMED', rescan=False,
                     worker_id='production-discovery122'):
    """Queue hints under the real operations lease; never run reconciliation.

    An existing reconciliation supervisor owns the same operations lease.
    Pause that supervisor before invoking the separate CLI, or invoke this
    function inside an already owned operations process. The API can keep its
    independent runtime lease throughout discovery.
    """
    _scope(date, days, max_pages, page_size, status, rescan, worker_id)
    manifest = runtime.read_manifest(manifest_or_path)
    _require(manifest.verification_mode == 'provider_api', 'sdk_mode_has_no_provider_discovery')
    permit = runtime.require_owned_application(app, manifest, purpose='operations')
    _require(permit.enter(), 'production_discovery_runtime_closed')
    try:
        commerce = app.state.commerce
        provider = commerce.provider
        _require(commerce.config.enabled and commerce.config.sandbox is False
                 and type(commerce.config.appId) is int
                 and isinstance(provider, RuStoreInvoiceProvider) and provider.configured,
                 'production_discovery_provider_not_configured')
        lister = _OwnedLister(app, manifest,
            RuStoreInvoiceLister(provider.token_supplier, provider.transport))
        scanner = DiscoveryScanner(app.state.authority, commerce, lister, enabled=True)
        result = scanner.scan_overlap(commerce.config.appId, date, False, worker_id,
            days=days, max_pages=max_pages, page_size=page_size, status=status, rescan=rescan)
        runtime.require_owned_application(app, manifest, purpose='operations')
        allowed_states = ('Pending', 'Complete', 'Busy', 'StaleLease')
        counts = dict.fromkeys(('pages', 'queued', 'ignored', 'duplicates'), 0)
        states = dict.fromkeys(allowed_states, 0)
        for row in result:
            _require(row.get('state') in allowed_states, 'production_discovery_result_invalid')
            states[row['state']] += 1
            for field in counts:
                value = row.get(field)
                _require(type(value) is int and value >= 0, 'production_discovery_result_invalid')
                counts[field] += value
        remaining = states['Pending'] + states['Busy'] + states['StaleLease']
        return {'status': 'more_work_pending' if remaining else 'completed',
                'operation': 'production_invoice_discovery', 'mode': 'production',
                'datesRequested': days, 'dateStates': states, **counts,
                'maxPagesPerDate': max_pages, 'pageSize': page_size,
                'resumeRequired': bool(remaining), 'rescanRequested': rescan,
                'grantsFromListing': False, 'reconciliationPerformed': False,
                'sdkAcknowledgementWritten': False, 'activationPerformed': False,
                'providerAcceptanceVerified': False}
    except ProductionDiscoveryError:
        raise
    except ServiceError as error:
        # Scanner errors already omit values; export only a local fixed code.
        raise ProductionDiscoveryError('production_discovery_provider_or_storage_unavailable') from None
    finally:
        permit.leave()


def discover_production(manifest_or_path, **scope):
    # Validate before taking ownership or opening an authority, not only before
    # calling the scanner. Defaults exactly match discover_bounded.
    _scope(scope.get('date'), scope.get('days', 3), scope.get('max_pages', 5),
           scope.get('page_size', 100), scope.get('status', 'CONFIRMED'),
           scope.get('rescan', False), scope.get('worker_id', 'production-discovery122'))
    manifest = runtime.read_manifest(manifest_or_path)
    _require(manifest.verification_mode == 'provider_api', 'sdk_mode_has_no_provider_discovery')
    with runtime.application_context(manifest, purpose='operations') as app:
        return discover_bounded(app, manifest, **scope)


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ProductionDiscoveryError('production_discovery_arguments_invalid')


def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--date', required=True, help='Explicit provider ISO date, YYYY-MM-DD')
    parser.add_argument('--days', type=int, default=3)
    parser.add_argument('--max-pages', type=int, default=5)
    parser.add_argument('--page-size', type=int, default=100)
    parser.add_argument('--status', choices=STATUSES, default='CONFIRMED')
    parser.add_argument('--rescan', action='store_true')
    parser.add_argument('--worker-id', default='production-discovery122')
    try:
        args = vars(parser.parse_args(argv))
        manifest = args.pop('manifest')
        print(json.dumps(discover_production(manifest, **args), separators=(',', ':')))
        return 0
    except (ProductionDiscoveryError, runtime.ProductionError, OSError, ValueError, TypeError, RuntimeError):
        print(json.dumps({'status': 'blocked_production_discovery122',
                          'grantsFromListing': False, 'activationPerformed': False}, separators=(',', ':')))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
