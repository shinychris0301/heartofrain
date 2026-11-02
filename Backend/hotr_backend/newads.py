"""Durable rewarded-ad opportunities with explicit, unequal completion trust.

Approved policy: 400 coins, three credited grants per player-local day, and a
600-second cooldown beginning at the authoritative claim commit. Reservations,
cancel/no-fill and unverified SDK callbacks spend no quota and start no cooldown.
One unresolved opportunity serializes all of a player's devices. Verified
opportunities survive midnight/restart; their eventual claim uses the *current*
server day/cap. Unverified opportunities expire after the bounded technical TTL.

The SDK-reported mode deliberately accepts a forgeable client completion report
for capped soft currency. It is not impression proof or provider verification.
Only the authenticated server claim can credit the fixed policy reward; the
client cannot choose its amount, day or cooldown. Rollout defaults to disabled.
"""
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .guards import require_actor
from .production_runtime122 import production_enabled
from .newads_schemas import RewardedAdsConfig
from .newads_verifier import InvalidAdCompletion, UnavailableAdCompletionVerifier, valid_completion
from .schemas import Grant
from .service import Actor, ServiceError
from .storage import canonical

LATE_COMPLETION_SECONDS = 86400


class RewardedAds:
    def __init__(self, authority, config_path: Path, verifier=None):
        self.authority = authority
        self.database = authority.database
        self.config = RewardedAdsConfig.model_validate_json(Path(config_path).read_text('utf-8-sig'))
        self.verifier = verifier if verifier is not None else UnavailableAdCompletionVerifier()
        self.checkpoint = None  # In-process transaction fault controls only.

    def _transaction(self, run):
        with self.database.transaction() as db:
            value = run(db)
            if self.checkpoint:
                self.checkpoint('BeforeCommit')
        if self.checkpoint:
            self.checkpoint('AfterCommit')
        return value

    def _now(self, db, sampled):
        # A sampled request can wait for SQLite's writer across local midnight,
        # a cooldown boundary, or opportunity expiry. Claim time is the clock
        # inside this transaction, never the earlier authentication/read clock.
        return self.authority._transaction_clock(db, sampled)

    @staticmethod
    def _day(now, offset=36000):
        return (now + offset) // 86400

    @staticmethod
    def _zone(zone):
        if zone is None or zone == '':
            return None
        if not isinstance(zone, str) or len(zone) > 64 or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_+-]*(?:/[A-Za-z0-9_+-]+){0,3}', zone):
            raise ServiceError(422, 'ad_time_zone_invalid')
        try:
            return ZoneInfo(zone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ServiceError(422, 'ad_time_zone_invalid') from None

    @classmethod
    def _bounds(cls, now, offset, zone_name):
        zone = cls._zone(zone_name)
        if zone is None:
            start = cls._day(now, offset) * 86400 - offset
            return start, start + 86400, offset, offset
        try:
            local = datetime.fromtimestamp(now, timezone.utc).astimezone(zone)
            start = datetime.combine(local.date(), datetime.min.time(), zone)
            end = datetime.combine(local.date() + timedelta(days=1), datetime.min.time(), zone)
            return int(start.timestamp()), int(end.timestamp()), int(local.utcoffset().total_seconds()), int(end.utcoffset().total_seconds())
        except (ValueError, OverflowError):
            raise ServiceError(503, 'ad_calendar_unavailable') from None

    def _calendar(self, db, player, now, requested=None, requested_zone=None):
        """Use server time; a device may select a calendar, never its clock.

        Travel/offset changes wait until the current quota window ends. The
        transition window then ends at the next new local midnight; there is
        no extra 24-hour lockout. Changing an offset cannot reset the current
        quota. An unchanged IANA zone uses actual local midnights, including
        23/25-hour DST days. Offset fallback is for older/unsupported clients.
        The zone is separate
        from country/region and contains no precise location information.
        """
        if requested is not None and (type(requested) is not int or
                not -43200 <= requested <= 50400 or requested % 900):
            raise ServiceError(422, 'ad_local_offset_invalid')
        self._zone(requested_zone)
        row = db.execute('SELECT * FROM rewarded_ad_calendars WHERE player_id=?', (player,)).fetchone()
        if row is None:
            offset = self.config.utcOffsetSeconds if requested is None else requested
            zone_name = requested_zone or ''
            pending_zone = zone_name
            pending_offset = offset
            legacy_start = self._day(now, self.config.utcOffsetSeconds) * 86400 - self.config.utcOffsetSeconds
            # Installing the update must not erase credits already taken in
            # the former UTC+10 day. Retain that window through its midnight.
            if db.execute("SELECT 1 FROM rewarded_ad_opportunities WHERE player_id=? AND state='Claimed' AND claimed_at>=?", (player, legacy_start)).fetchone():
                offset = self.config.utcOffsetSeconds
                zone_name = ''
            start, end, offset, _ = self._bounds(now, offset, zone_name)
            db.execute('INSERT INTO rewarded_ad_calendars VALUES(?,?,?,?,?,?,?)',
                       (player, offset, pending_offset, zone_name, pending_zone, start, end))
            row = db.execute('SELECT * FROM rewarded_ad_calendars WHERE player_id=?', (player,)).fetchone()
        target = row['pending_offset'] if requested is None else requested
        target_zone = row['pending_zone'] if requested_zone is None else requested_zone
        zone_name = row['time_zone']
        offset, start, end = row['utc_offset'], row['starts_at'], row['ends_at']
        if now >= end:
            _, next_end, target, _ = self._bounds(now, target, target_zone)
            if (target_zone != zone_name or not zone_name and target != offset) and now < end + 86400:
                start = end
                end = next_end
            else:
                start, end, target, _ = self._bounds(now, target, target_zone)
            offset = target
            zone_name = target_zone
        # The returned current offset may change inside a DST day. The stored
        # quota boundaries remain the actual two local midnights for that day.
        _, _, offset, _ = self._bounds(now, offset, zone_name)
        _, _, _, next_offset = self._bounds(max(0, end - 1), offset, zone_name)
        db.execute('UPDATE rewarded_ad_calendars SET utc_offset=?,pending_offset=?,time_zone=?,pending_zone=?,starts_at=?,ends_at=? WHERE player_id=?',
                   (offset, target, zone_name, target_zone, start, end, player))
        return {'offset': offset, 'start': start, 'end': end, 'zone': zone_name, 'next_offset': next_offset}

    @staticmethod
    def _wallet_guard(db, actor):
        require_actor(db, actor)
        wallet = db.execute('SELECT initialized FROM wallets WHERE player_id=?', (actor.player,)).fetchone()
        if wallet is None or not wallet['initialized']:
            raise ServiceError(409, 'wallet_migration_required')
        if db.execute("SELECT 1 FROM commerce_orders WHERE player_id=? AND state='RefundReview'", (actor.player,)).fetchone():
            raise ServiceError(409, 'wallet_refund_review_required')

    @staticmethod
    def _expire(db, player, now):
        # A completion the player already reported never expires: the daily limit and cooldown
        # are enforced at the claim, so waiting costs nothing and a late claim keeps its coins.
        db.execute("UPDATE rewarded_ad_opportunities SET state='Expired' WHERE player_id=? AND state IN ('Reserved','AwaitingVerification') AND expires_at<=?", (player, now))

    @staticmethod
    def _row(db, actor, opportunity_id):
        require_actor(db, actor)
        if not isinstance(opportunity_id, str) or not re.fullmatch('[0-9a-f]{32}', opportunity_id):
            raise ServiceError(404, 'ad_opportunity_not_found')
        row = db.execute('SELECT * FROM rewarded_ad_opportunities WHERE id=? AND player_id=?', (opportunity_id, actor.player)).fetchone()
        if row is None:
            raise ServiceError(404, 'ad_opportunity_not_found')
        return row

    @staticmethod
    def _counts(db, player, calendar):
        count = db.execute("SELECT COUNT(*) FROM rewarded_ad_opportunities WHERE player_id=? AND state='Claimed' AND claimed_at>=? AND claimed_at<?", (player, calendar['start'], calendar['end'])).fetchone()[0]
        latest = db.execute("SELECT MAX(claimed_at) FROM rewarded_ad_opportunities WHERE player_id=? AND state='Claimed'", (player,)).fetchone()[0]
        return count, latest

    @staticmethod
    def _view(db, row, now):
        receipt = None
        if row['reward_id']:
            ledger = db.execute('SELECT id,revision,created_at FROM wallet_ledger WHERE player_id=? AND origin=?', (row['player_id'], 'reward/' + row['reward_id'])).fetchone()
            if ledger is None:
                raise ServiceError(503, 'ad_receipt_unavailable')
            receipt = {'id': row['reward_id'], 'walletReceiptId': ledger['id'], 'coins': row['coins'],
                       'serverUtc': ledger['created_at'], 'walletRevision': ledger['revision'],
                       'completionSource': row['completion_source']}
        return {'opportunityId': row['id'], 'playerId': row['player_id'], 'placement': row['placement'],
                'configVersion': row['config_version'], 'rewardCoins': row['coins'],
                'completionMode': row['completion_mode'], 'verificationMode': row['verification_mode'],
                'completionSource': row['completion_source'],
                'dailyLimit': row['daily_limit'], 'utcOffsetSeconds': row['local_utc_offset'],
                'claimedUtcOffsetSeconds': row['claim_utc_offset'],
                'cooldownSeconds': row['cooldown'], 'reservedDay': row['reserved_day'],
                'createdAt': row['created_at'], 'expiresAt': row['expires_at'], 'state': row['state'],
                'clientReportedAt': row['client_reported_at'], 'verifiedAt': row['verified_at'],
                'claimedAt': row['claimed_at'], 'claimedDay': row['claimed_day'], 'receipt': receipt,
                'serverUtc': now, 'completionAuthoritative': row['completion_source'] == 'provider_verified' and row['state'] in ('Verified', 'Claimed')}

    def status(self, actor, utc_offset_seconds=None, time_zone_id=None):
        sampled = self.authority._now()
        def run(db):
            require_actor(db, actor)
            now = self._now(db, sampled)
            self._expire(db, actor.player, now)
            calendar = self._calendar(db, actor.player, now, utc_offset_seconds, time_zone_id)
            count, latest = self._counts(db, actor.player, calendar)
            active = db.execute("SELECT * FROM rewarded_ad_opportunities WHERE player_id=? AND state IN ('Reserved','AwaitingVerification','CompletedReported','Verified')", (actor.player,)).fetchone()
            reported = self.config.completionMode == 'sdk_client_reported_capped'
            ready = self.config.enabled and (reported or bool(self.verifier.configured))
            cooldown = max(0, (latest + self.config.cooldownSeconds) - now) if latest is not None else 0
            reason = ('ads_disabled' if not self.config.enabled else 'trusted_completion_unavailable' if not reported and not self.verifier.configured
                      else 'pending_opportunity' if active is not None else 'daily_limit' if count >= self.config.dailyLimit
                      else 'cooldown' if cooldown else 'ready_client_reported_capped' if reported else 'ready')
            try:
                self._wallet_guard(db, actor)
            except ServiceError as error:
                if error.status != 409:
                    raise
                reason = error.code
            return {'enabled': self.config.enabled, 'available': ready and reason in ('ready', 'ready_client_reported_capped'),
                    'reason': reason, 'completionMode': self.config.completionMode,
                    'verificationMode': 'sdk_client_reported_capped' if reported else self.verifier.mode, 'productionEnabled': production_enabled(self.authority),
                    'placement': self.config.placement, 'configVersion': self.config.version,
                    'rewardCoins': self.config.rewardCoins, 'dailyLimit': self.config.dailyLimit,
                    'utcOffsetSeconds': calendar['offset'], 'cooldownSeconds': self.config.cooldownSeconds,
                    'timeZoneId': calendar['zone'], 'nextDayUtcOffsetSeconds': calendar['next_offset'],
                    'day': self._day(now, calendar['offset']), 'dayStartedAt': calendar['start'],
                    'claimedToday': count, 'remainingToday': max(0, self.config.dailyLimit - count),
                    'cooldownRemainingSeconds': cooldown, 'nextEligibleAt': max(now, latest + self.config.cooldownSeconds) if latest is not None else now,
                    'nextDayAt': calendar['end'],
                    'activeOpportunity': None if active is None else self._view(db, active, now), 'serverUtc': now}
        return self._transaction(run)

    def reserve(self, actor, request):
        sampled = self.authority._now()
        def run(db):
            require_actor(db, actor)
            now = self._now(db, sampled)
            self._wallet_guard(db, actor)
            self._expire(db, actor.player, now)
            def execute():
                if not self.config.enabled:
                    raise ServiceError(503, 'ads_disabled')
                if self.config.completionMode == 'trusted_completion' and not self.verifier.configured:
                    raise ServiceError(503, 'trusted_completion_unavailable')
                if request.placement != self.config.placement:
                    raise ServiceError(409, 'ad_placement_unavailable')
                if db.execute("SELECT 1 FROM rewarded_ad_opportunities WHERE player_id=? AND state IN ('Reserved','AwaitingVerification','CompletedReported','Verified')", (actor.player,)).fetchone():
                    raise ServiceError(409, 'ad_opportunity_pending')
                calendar = self._calendar(db, actor.player, now)
                count, latest = self._counts(db, actor.player, calendar)
                if count >= self.config.dailyLimit:
                    raise ServiceError(409, 'ad_daily_limit')
                if latest is not None and now < latest + self.config.cooldownSeconds:
                    raise ServiceError(409, 'ad_cooldown')
                opportunity = uuid.uuid4().hex
                db.execute('''INSERT INTO rewarded_ad_opportunities
                    (id,player_id,placement,config_version,completion_mode,verification_mode,coins,daily_limit,utc_offset,cooldown,reserved_day,created_at,expires_at,local_utc_offset,state)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,'Reserved')''',
                    (opportunity, actor.player, self.config.placement, self.config.version, self.config.completionMode,
                     'sdk_client_reported_capped' if self.config.completionMode == 'sdk_client_reported_capped' else self.verifier.mode, self.config.rewardCoins,
                     self.config.dailyLimit, self.config.utcOffsetSeconds, self.config.cooldownSeconds, self._day(now, calendar['offset']),
                     now, now + self.config.opportunityTtlSeconds, calendar['offset']))
                return self._view(db, self._row(db, actor, opportunity), now)
            return self.authority._command(db, actor, 'ads.reserve', request.commandId, request.model_dump(exclude={'commandId'}), execute)
        return self._transaction(run)

    def opportunity(self, actor, opportunity_id):
        sampled = self.authority._now()
        def run(db):
            require_actor(db, actor)
            now = self._now(db, sampled)
            self._expire(db, actor.player, now)
            return self._view(db, self._row(db, actor, opportunity_id), now)
        return self._transaction(run)

    def client_completion(self, actor, opportunity_id, request):
        sampled = self.authority._now()
        def run(db):
            now = self._now(db, sampled)
            self._expire(db, actor.player, now)
            row = self._row(db, actor, opportunity_id)
            def execute():
                # This mode already rests on the client's report, and the claim still enforces both
                # limits, so a report delayed by a lost network gains nothing beyond its own reward.
                late = (row['state'] == 'Expired' and row['completion_mode'] == 'sdk_client_reported_capped'
                        and not row['client_reported_at'] and now < row['created_at'] + LATE_COMPLETION_SECONDS
                        and not db.execute("SELECT 1 FROM rewarded_ad_opportunities WHERE player_id=? AND id<>? AND state IN ('Reserved','AwaitingVerification','CompletedReported','Verified')", (actor.player, opportunity_id)).fetchone())
                if row['state'] in ('Cancelled', 'Expired') and not late:
                    raise ServiceError(409, 'ad_opportunity_closed')
                if row['state'] == 'Reserved' or late:
                    if row['completion_mode'] == 'sdk_client_reported_capped':
                        db.execute("UPDATE rewarded_ad_opportunities SET state='CompletedReported',client_reported_at=?,completed_at=?,completion_source='sdk_client_reported_capped' WHERE id=?", (now, now, opportunity_id))
                    else:
                        db.execute("UPDATE rewarded_ad_opportunities SET state='AwaitingVerification',client_reported_at=? WHERE id=?", (now, opportunity_id))
                return self._view(db, self._row(db, actor, opportunity_id), now)
            return self.authority._command(db, actor, 'ads.client_completion', request.commandId, {'opportunityId': opportunity_id}, execute)
        return self._transaction(run)

    def cancel(self, actor, opportunity_id, request):
        sampled = self.authority._now()
        def run(db):
            now = self._now(db, sampled)
            self._expire(db, actor.player, now)
            row = self._row(db, actor, opportunity_id)
            def execute():
                if row['state'] in ('Verified', 'Claimed'):
                    raise ServiceError(409, 'ad_completion_already_verified')
                if row['state'] in ('Reserved', 'AwaitingVerification', 'CompletedReported'):
                    db.execute("UPDATE rewarded_ad_opportunities SET state='Cancelled' WHERE id=?", (opportunity_id,))
                return self._view(db, self._row(db, actor, opportunity_id), now)
            return self.authority._command(db, actor, 'ads.cancel', request.commandId, {'opportunityId': opportunity_id}, execute)
        return self._transaction(run)

    def claim(self, actor, opportunity_id, request):
        sampled = self.authority._now()
        def run(db):
            now = self._now(db, sampled)
            self._wallet_guard(db, actor)
            self._expire(db, actor.player, now)
            row = self._row(db, actor, opportunity_id)
            if row['state'] in ('Cancelled', 'Expired'):
                raise ServiceError(409, 'ad_opportunity_closed')
            if row['state'] not in ('Verified', 'Claimed', 'CompletedReported'):
                # A pending read is not a committed command receipt: retrying the
                # same ID after trusted verification must still be able to grant.
                return self._view(db, row, now)
            def execute():
                if row['state'] == 'Claimed':
                    return self._view(db, row, now)
                calendar = self._calendar(db, actor.player, now)
                count, latest = self._counts(db, actor.player, calendar)
                if count >= row['daily_limit']:
                    raise ServiceError(409, 'ad_daily_limit')
                if latest is not None and now < latest + row['cooldown']:
                    raise ServiceError(409, 'ad_cooldown')
                receipt_id = 'rewarded-ad/' + opportunity_id
                # Use the current commit clock, never the earlier authenticated
                # Actor's timestamp, for the authoritative grant/cooldown/day.
                grant_actor = Actor(actor.player, now, actor.credential_digest, actor._clock)
                source = 'client_reported_ad' if row['completion_source'] == 'sdk_client_reported_capped' else 'rewarded_ad'
                self.authority._grant(db, grant_actor, source, opportunity_id, Grant(coins=row['coins']), receipt_id)
                db.execute("UPDATE rewarded_ad_opportunities SET state='Claimed',claimed_at=?,claimed_day=?,claim_utc_offset=?,reward_id=? WHERE id=?",
                           (now, self._day(now, calendar['offset']), calendar['offset'], receipt_id, opportunity_id))
                return self._view(db, self._row(db, actor, opportunity_id), now)
            return self.authority._command(db, actor, 'ads.claim', request.commandId, {'opportunityId': opportunity_id}, execute)
        return self._transaction(run)

    def accept_trusted_completion(self, payload):
        """Server-only adapter entry, intentionally not mounted as an HTTP route."""
        if not self.verifier.configured:
            raise ServiceError(503, 'trusted_completion_unavailable')
        try:
            evidence = self.verifier.verify(payload)
        except InvalidAdCompletion as error:
            raise ServiceError(403, 'ad_completion_rejected') from error
        except Exception as error:
            raise ServiceError(503, 'ad_verifier_unavailable') from error
        if not valid_completion(evidence):
            raise ServiceError(403, 'ad_completion_rejected')
        sampled = self.authority._now()
        def run(db):
            now = self._now(db, sampled)
            actor = Actor(evidence.player_id, now)
            self._wallet_guard(db, actor)
            self._expire(db, actor.player, now)
            row = self._row(db, actor, evidence.opportunity_id)
            if row['completion_mode'] != 'trusted_completion':
                raise ServiceError(409, 'ad_completion_mode_mismatch')
            if (evidence.placement != row['placement'] or evidence.config_version != row['config_version']
                    or evidence.completed_at < row['created_at'] or evidence.completed_at >= row['expires_at']
                    or evidence.completed_at > now):
                raise ServiceError(409, 'ad_completion_binding_mismatch')
            digest = hashlib.sha256(canonical(evidence.__dict__).encode('ascii')).hexdigest()
            old = db.execute('SELECT * FROM rewarded_ad_completions WHERE provider=? AND event_id=?', (evidence.provider, evidence.event_id)).fetchone()
            if old is not None:
                if old['opportunity_id'] != row['id'] or old['payload_digest'] != digest:
                    raise ServiceError(409, 'ad_completion_conflict')
                return self._view(db, row, now)
            if db.execute('SELECT 1 FROM rewarded_ad_completions WHERE opportunity_id=?', (row['id'],)).fetchone():
                raise ServiceError(409, 'ad_completion_conflict')
            if row['state'] not in ('Reserved', 'AwaitingVerification'):
                raise ServiceError(409, 'ad_opportunity_closed')
            db.execute('INSERT INTO rewarded_ad_completions VALUES(?,?,?,?,?,?)',
                       (evidence.provider, evidence.event_id, row['id'], digest, now, evidence.completed_at))
            db.execute("UPDATE rewarded_ad_opportunities SET state='Verified',verified_at=?,completed_at=?,completion_source='provider_verified' WHERE id=?",
                       (now, evidence.completed_at, row['id']))
            return self._view(db, self._row(db, actor, row['id']), now)
        return self._transaction(run)
