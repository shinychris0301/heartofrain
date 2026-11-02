"""Reader02: bounded fixed public diagnostic read as shell; no run-as or action."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HELPER = ROOT / 'Verification/Tools/Review127/device_ui127.py'
HELPER_SHA256 = 'c781bd471a89e9975cb7c6927802eccc7b8466456c70dac0be471dc510db329e'
PACKAGE = 'com.heartoftherain.ads127demo'
DEVICE_PATH = '/storage/emulated/0/Android/data/' + PACKAGE + '/files/Diagnostics/AdsDemo127.json'
PUBLIC = ROOT / 'Verification/Evidence/Review127/Ads/DeviceTelemetry'
MAX_BYTES = 32768
PHASES = {'Disconnected', 'BlockedFixtureProfile', 'Connecting', 'Blocked',
          'ConnectedProtectedTestGuest', 'Connected', 'ShowingDemo', 'RealFlowBusy',
          'DurableRewardObserved', 'PendingRecovery'}
JOURNAL_PHASES = {'None', 'BeforeCommit', 'AfterCommit', 'BeforeClear', 'AfterClear', 'DiagnosticUnavailable'}
KNOWN_ERRORS = {'', 'DiagnosticUnavailable', 'DiagnosticPersistenceUnavailable',
    'ExplicitConnectRequired', 'ProtectedSessionUnavailable', 'IdentityUnavailable',
    'FixtureOwnerChanged', 'WalletUnavailable', 'ProtectedIdentityUnavailable',
    'AdsOwnerThreadRequired', 'AdsSdkUnavailable', 'AdsPrivacyRequired', 'AdsBlockNotConfigured',
    'AdsProviderBusy', 'AdsLoadTimeout', 'AdsLoadFailed', 'AdsRecoveryRequired',
    'AdsSessionUnavailable', 'AdsOwnerChanged', 'AdsStatusUnavailable', 'AdsUnavailable',
    'AdsReserveUnavailable', 'AdsNotCompleted', 'AdsJournalUnavailable',
    'AdsCompletionPending', 'AdsRecoveryUnavailable', 'AdsCancellationPending',
    'AdsReceiptInvalid', 'AdsWalletPending', 'AdsSessionChanged',
    'ad_cooldown', 'ad_daily_limit', 'ad_placement_unavailable', 'ad_opportunity_pending'}
COUNTERS = {'connectActions', 'consentedWatchActions', 'loadRequests', 'loaded', 'loadFailed',
    'shown', 'rewardedSignals', 'closed', 'showFailed', 'reportResponses', 'claimResponses',
    'distinctReceipts'}
BALANCES = {'coins', 'coinsBeforeWatch', 'coinsAfterRefresh'}
FLAGS = {'connected', 'consent', 'pending', 'busy', 'presenting'}
KEYS = COUNTERS | BALANCES | FLAGS | {'version', 'package', 'unit', 'engine', 'phase', 'error',
    'actorDigest', 'utc', 'walletRevision', 'claimedToday', 'remainingToday', 'cooldownSeconds',
    'journalPhase', 'receiptDigests', 'scope'}
SCOPE = ('Actual Yandex demo SDK callbacks + owned staging API. Completion remains '
         'sdk_client_reported_capped; no provider SSV, payment, shipping-app or production acceptance.')

class Invalid(ValueError):
    pass

def need(ok, code):
    if not ok:
        raise Invalid(code)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'DuplicateTelemetryKey')
        result[key] = value
    return result

def integer(row, key, maximum):
    value = row[key]
    need(type(value) is int and 0 <= value <= maximum, 'InvalidTelemetryInteger')

def sanitize(raw):
    need(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, 'BoundedTelemetryRequired')
    try:
        row = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique,
                         parse_constant=lambda _: (_ for _ in ()).throw(Invalid('InvalidJsonConstant')))
    except Invalid:
        raise
    except Exception:
        raise Invalid('InvalidTelemetryJson') from None
    need(type(row) is dict and set(row) == KEYS, 'ExactTelemetryWhitelistRequired')
    need(type(row['version']) is int and row['version'] == 1 and row['package'] == PACKAGE
         and row['unit'] == 'demo-rewarded-yandex' and row['engine'] == '6000.3.27f1'
         and row['scope'] == SCOPE, 'ExactCompiledFixtureProfileRequired')
    need(type(row['phase']) is str and row['phase'] in PHASES
         and type(row['journalPhase']) is str and row['journalPhase'] in JOURNAL_PHASES,
         'KnownTelemetryStateRequired')
    need(type(row['error']) is str and len(row['error']) <= 80, 'BoundedErrorCodeRequired')
    redacted = row['error'] not in KNOWN_ERRORS
    if redacted:
        row['error'] = 'UnrecognizedCodeRedacted'
    for key in COUNTERS:
        integer(row, key, 1_000_000)
    for key in BALANCES:
        integer(row, key, 2_147_483_647)
    integer(row, 'walletRevision', 9_223_372_036_854_775_807)
    for key in ('claimedToday', 'remainingToday'):
        integer(row, key, 3)
    integer(row, 'cooldownSeconds', 600)
    for key in FLAGS:
        need(type(row[key]) is bool, 'BooleanTelemetryRequired')
    need(type(row['actorDigest']) is str and (row['actorDigest'] == '' or
         re.fullmatch('[a-f0-9]{64}', row['actorDigest']) is not None), 'ShaOnlyActorRequired')
    receipts = row['receiptDigests']
    need(type(receipts) is list and len(receipts) <= 1000 and all(type(v) is str and
         re.fullmatch('[a-f0-9]{64}', v) is not None for v in receipts)
         and len(set(receipts)) == len(receipts) and row['distinctReceipts'] == len(receipts),
         'ShaOnlyConsistentReceiptsRequired')
    need(type(row['utc']) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{7}Z', row['utc']) is not None,
         'ExactTelemetryUtcRequired')
    try:
        datetime.fromisoformat(row['utc'].replace('Z', '+00:00'))
    except ValueError:
        raise Invalid('ValidTelemetryUtcRequired') from None
    return row, redacted

def comparison(prior, current):
    return {'sameActorDigest': prior['actorDigest'] == current['actorDigest'],
        'loadRequestsDelta': current['loadRequests'] - prior['loadRequests'],
        'rewardedSignalsDelta': current['rewardedSignals'] - prior['rewardedSignals'],
        'receiptCountDelta': current['distinctReceipts'] - prior['distinctReceipts'],
        'sameReceiptDigests': prior['receiptDigests'] == current['receiptDigests'],
        'coinsDelta': current['coins'] - prior['coins'],
        'pendingBefore': prior['pending'], 'pendingAfter': current['pending'],
        'scope': 'Observed comparison only; no inferred provider completion or grant.'}

def collect(device):
    serial = device.phone()  # Existing exact physical-phone SHA guard.
    before = device.foreground(serial)
    allowed = {PACKAGE + '/com.unity3d.player.UnityPlayerActivity',
               PACKAGE + '/com.yandex.mobile.ads.common.AdActivity'}
    need(before in allowed, 'ExactDemoForegroundRequired')
    # No path, package or shell-action argument can be supplied by the caller.
    result = device.adb('-s', serial, 'exec-out', 'head', '-c',
                        str(MAX_BYTES + 1), DEVICE_PATH, timeout=15)
    need(result.returncode == 0, 'OwnPublicTelemetryReadFailed')
    raw = result.stdout
    need(type(raw) is bytes, 'PublicTelemetryBytesRequired')
    # exec-out may report a command/access error on stdout with exit zero.
    prefix = raw.lstrip(b'\xef\xbb\xbf \t\r\n')
    need(not prefix.startswith((b'head:', b'/system/bin/head:', b'sh:',
         b'/system/bin/sh:', b'run-as:')), 'PublicTelemetryReadCommandReportedError')
    need(prefix.startswith(b'{'), 'PublicTelemetryJsonObjectRequired')
    row, redacted = sanitize(raw)
    need(device.foreground(serial) == before, 'DemoForegroundChangedDuringRead')
    return row, redacted, hashlib.sha256(raw).hexdigest(), before

def load_helper():
    need(sha(HELPER) == HELPER_SHA256, 'ReviewedDeviceGuardChanged')
    spec = importlib.util.spec_from_file_location('review127_telemetry_device_guard', HELPER)
    device = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(device)
    return device

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tag', required=True)
    p.add_argument('--prior', type=Path)
    args = p.parse_args()
    need(re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,60}', args.tag) is not None, 'FreshSafeTagRequired')
    PUBLIC.mkdir(parents=True, exist_ok=True)
    output = PUBLIC / (args.tag + '.json')
    # Reserve a fresh destination before any device call, never replace evidence.
    with output.open('x', encoding='utf-8', newline='\n') as handle:
        record = {'version': 1, 'readerVersion': 2,
            'readCommand': 'FixedBoundedPublicHeadAsShell',
            'status': 'FAIL_READONLY_AD_TELEMETRY127',
            'collectedUtc': datetime.now(timezone.utc).isoformat(), 'readerSHA256': sha(__file__),
            'guardSHA256': HELPER_SHA256, 'expectedBuiltApkSHA256':
            'eb80e9c5748a3cf7b1e8d6836641c9ab72eafee04111e7e83014498abbf3b019',
            'scope': 'Read-only sanitized own diagnostic JSON; no independent installed-APK, SDK callback, playback or financial acceptance.',
            'deviceActionPerformed': False, 'backendRequested': False, 'dataCleared': False}
        try:
            prior = None
            if args.prior is not None:
                resolved = args.prior.resolve()
                need(resolved.is_relative_to(PUBLIC.resolve()) and resolved != output.resolve()
                     and resolved.is_file() and resolved.stat().st_size <= MAX_BYTES * 2,
                     'OwnedPriorTelemetryEvidenceRequired')
                old = json.loads(resolved.read_bytes())
                need(old['status'] == 'PASS_READONLY_AD_TELEMETRY127', 'PassingPriorSnapshotRequired')
                prior, _ = sanitize(json.dumps(old['telemetry']).encode())
                record['priorEvidenceSHA256'] = sha(resolved)
            device = load_helper()
            row, redacted, raw_hash, foreground = collect(device)
            record.update(status='PASS_READONLY_AD_TELEMETRY127', telemetry=row,
                unknownErrorRedacted=redacted, rawPublicFileSHA256=raw_hash,
                deviceSHA256=device.DEVICE, foreground=foreground,
                telemetryAgeSeconds=math.floor((datetime.now(timezone.utc) -
                    datetime.fromisoformat(row['utc'].replace('Z', '+00:00'))).total_seconds()),
                staleTelemetryDoesNotProveNoNativeSdkCallback=True)
            if prior is not None:
                record['comparison'] = comparison(prior, row)
        except Exception as error:
            record['code'] = str(error) if isinstance(error, Invalid) else 'ScopedReadOrValidationFailed'
        handle.write(json.dumps(record, indent=2) + '\n')
        handle.flush()
    print(json.dumps({'status': record['status'], 'evidence': str(output.relative_to(ROOT)),
                      'evidenceSHA256': sha(output)}))
    return 0 if record['status'].startswith('PASS_') else 1

if __name__ == '__main__':
    raise SystemExit(main())
