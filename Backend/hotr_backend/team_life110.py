"""Social-gated, authoritative requests/help/partial life claims.

No donor debit, coin reward, client balance import, mailbox or production gate.
"""
import json
from pathlib import Path
from typing import Literal
import uuid

from pydantic import Field

from .friends import blocked
from .guards import require_actor
from .messaging import identity
from .schemas import Model
from .service import ServiceError
from .storage import canonical
from .wallet import ZERO, project


class TeamLifeRules110(Model):
    version: str = Field(min_length=1, max_length=64)
    capacity: int = Field(ge=1, le=5)
    cooldownSeconds: int = Field(ge=60, le=86400)
    lifetimeSeconds: int = Field(ge=60, le=86400)
    helpSpendsDonorLives: Literal[False] = False


def close_member_requests(db, player, team, now, reason='MembershipEnded'):
    db.execute("UPDATE team_life_requests SET close_reason=?,closed_at=? WHERE player_id=? AND team_id=? AND close_reason='None'",
               (reason, now, player, team))


def close_team_requests(db, team, now):
    db.execute("UPDATE team_life_requests SET close_reason='TeamClosed',closed_at=? WHERE team_id=? AND close_reason='None'", (now, team))


class TeamLife110:
    def __init__(self, authority, wallet, messaging, rules, enabled=False):
        if type(enabled) is not bool or not isinstance(rules, TeamLifeRules110):
            raise ValueError('Explicit team-help configuration required')
        self.authority, self.database, self.wallet = authority, authority.database, wallet
        self.messaging, self.rules, self.enabled = messaging, rules, enabled

    def _guard(self, db, actor):
        require_actor(db, actor)
        if not self.enabled:
            raise ServiceError(503, 'social_not_configured')

    @staticmethod
    def _row(db, request_id):
        row = db.execute('SELECT * FROM team_life_requests WHERE id=?', (identity(request_id),)).fetchone()
        if not row:
            raise ServiceError(404, 'life_request_not_found')
        return row

    def _refresh(self, db, row, now):
        if row['close_reason'] != 'None':
            return row
        team = db.execute("SELECT t.active,COALESCE(a.state,'Active') AS owner_state FROM social_teams t LEFT JOIN account_states a ON a.player_id=t.owner_id WHERE t.id=?", (row['team_id'],)).fetchone()
        message = db.execute('SELECT visibility FROM social_messages WHERE id=?', (row['message_id'],)).fetchone()
        reason = ('Full' if row['received'] >= row['required'] else
                  'Expired' if now >= row['closes_at'] else
                  'TeamClosed' if not team or not team['active'] or team['owner_state'] != 'Active' else
                  'MembershipEnded' if not db.execute('SELECT 1 FROM social_team_members WHERE player_id=? AND team_id=?', (row['player_id'], row['team_id'])).fetchone() else
                  'Moderated' if not message or message['visibility'] != 'Visible' else 'None')
        if reason != 'None':
            db.execute("UPDATE team_life_requests SET close_reason=?,closed_at=? WHERE id=? AND close_reason='None'", (reason, now, row['id']))
            row = self._row(db, row['id'])
        return row

    @staticmethod
    def _visible(db, viewer, row):
        return not blocked(db, viewer, row['player_id']) and bool(db.execute(
            "SELECT 1 FROM social_messages m LEFT JOIN account_states a ON a.player_id=m.author_id WHERE m.id=? AND m.visibility='Visible' AND COALESCE(a.state,'Active')='Active'",
            (row['message_id'],)).fetchone())

    def _view(self, db, actor, row, *, own_only=False):
        row = self._refresh(db, row, actor.now)
        remaining = row['received'] - row['claimed']
        closed = row['close_reason'] != 'None'
        state = ('Open' if not closed else 'Claimable' if remaining else
                 'Claimed' if row['received'] else 'Expired' if row['close_reason'] == 'Expired' else 'Closed')
        own = row['player_id'] == actor.player
        helped = bool(db.execute('SELECT 1 FROM team_life_donations WHERE request_id=? AND player_id=?', (row['id'], actor.player)).fetchone())
        current = bool(db.execute('SELECT 1 FROM social_team_members WHERE player_id=? AND team_id=?', (actor.player, row['team_id'])).fetchone())
        can_help = not own_only and current and not own and not helped and not closed and self._visible(db, actor.player, row)
        collect_block = 'NotOwner' if not own else 'NotClosed' if not closed else 'NoEntitlement' if not remaining else 'None'
        if collect_block == 'None':
            self.wallet._regenerate(db, actor)
            wallet = self.wallet._row(db, actor.player)
            if not wallet['initialized']:
                collect_block = 'WalletMigrationRequired'
            elif self.wallet._quarantined(db, actor.player):
                collect_block = 'WalletRefundReviewRequired'
            elif json.loads(wallet['balances'])[10] >= 5:
                collect_block = 'FullLives'
        profile = db.execute('SELECT display_name FROM social_profiles WHERE player_id=?', (row['player_id'],)).fetchone()
        return dict(requestId=row['id'], messageId=row['message_id'], eventId=row['event_id'], sequence=row['sequence'],
                    teamId=row['team_id'], playerId=row['player_id'], displayName=profile[0] if profile else 'Player',
                    createdAt=row['created_at'], closesAt=row['closes_at'], nextRequestAt=row['next_request_at'],
                    received=row['received'], required=row['required'], claimed=row['claimed'], remaining=remaining,
                    state=state, closeReason=row['close_reason'], canHelp=bool(can_help), helped=helped,
                    canCollect=collect_block == 'None', collectBlockedReason=collect_block)

    def _latest(self, db, player, team=None):
        clause, parameters = (' AND team_id=?', (player, team)) if team else ('', (player,))
        return db.execute('SELECT * FROM team_life_requests WHERE player_id=?' + clause + ' ORDER BY sequence DESC LIMIT 1', parameters).fetchone()

    def team_requests(self, actor, team_id, *, before=None, limit=8, message_ids=None):
        identity(team_id)
        if type(limit) is not int or not 1 <= limit <= 8 or before is not None and (type(before) is not int or not 1 <= before <= 9_223_372_036_854_775_807):
            raise ServiceError(422, 'invalid_request')
        ids = None
        if message_ids is not None:
            if type(message_ids) is not str:
                raise ServiceError(422, 'invalid_request')
            ids = message_ids.split(',')
            if not 1 <= len(ids) <= 8 or len(set(ids)) != len(ids) or before is not None:
                raise ServiceError(422, 'invalid_request')
            for value in ids:
                identity(value)
        with self.database.transaction() as db:
            actor = self.authority._transaction_actor(db, actor)
            self._guard(db, actor)
            self.messaging._member(db, actor, team_id)
            query = 'SELECT * FROM team_life_requests WHERE team_id=?'
            params = [team_id]
            if ids is not None:
                query += ' AND message_id IN (' + ','.join('?' for _ in ids) + ')'
                params.extend(ids)
            elif before is not None:
                query += ' AND sequence<?'
                params.append(before)
            # Blocked/deleted/hidden rows are filtered before the bounded page.
            query += " AND EXISTS(SELECT 1 FROM social_messages m LEFT JOIN account_states a ON a.player_id=m.author_id WHERE m.id=message_id AND m.visibility='Visible' AND COALESCE(a.state,'Active')='Active') AND NOT EXISTS(SELECT 1 FROM social_blocks b WHERE (b.blocker_id=? AND b.blocked_id=player_id) OR (b.blocker_id=player_id AND b.blocked_id=?)) ORDER BY sequence DESC LIMIT ?"
            params.extend((actor.player, actor.player, limit + 1))
            rows = db.execute(query, params).fetchall()
            page = list(reversed(rows[:limit]))
            latest = self._latest(db, actor.player)
            own = self._latest(db, actor.player, team_id)
            return dict(teamId=team_id, serverUtc=actor.now, policy=self.rules.model_dump(),
                        nextRequestAt=latest['next_request_at'] if latest else 0,
                        ownRequest=self._view(db, actor, own) if own else None,
                        requests=[self._view(db, actor, row) for row in page],
                        olderCursor=page[0]['sequence'] if page else 0, hasOlder=ids is None and len(rows) > limit)

    def owned(self, actor, after=0, limit=8):
        if type(after) is not int or not 0 <= after <= 9_223_372_036_854_775_807 or type(limit) is not int or not 1 <= limit <= 8:
            raise ServiceError(422, 'invalid_request')
        with self.database.transaction() as db:
            actor = self.authority._transaction_actor(db, actor)
            self._guard(db, actor)
            rows = db.execute('SELECT * FROM team_life_requests WHERE player_id=? AND received>claimed AND sequence>? ORDER BY sequence LIMIT ?', (actor.player, after, limit + 1)).fetchall()
            page = rows[:limit]
            return dict(serverUtc=actor.now, policy=self.rules.model_dump(), requests=[self._view(db, actor, row, own_only=True) for row in page],
                        nextCursor=page[-1]['sequence'] if page else after, hasMore=len(rows) > limit)

    def _mutate(self, actor, operation, request, execute):
        def run(db, current):
            self._guard(db, current)
            # Cached minimal receipts recover after leave/removal. A new command
            # must pass execute's current permissions; no old roster is returned.
            return self.authority._command(db, current, operation, request.commandId, request.model_dump(), lambda: execute(db, current))
        return self.authority._transaction(run, actor)

    @staticmethod
    def _receipt(row, operation, state, now, *, event=None, credited=0):
        return dict(receiptId=uuid.uuid4().hex, operation=operation, teamId=row['team_id'], requestId=row['id'],
                    messageId=row['message_id'], eventId=event or row['event_id'], state=state, createdAt=now,
                    serverUtc=now, creditedLives=credited, received=row['received'], claimed=row['claimed'],
                    remaining=row['received'] - row['claimed'])

    def request(self, actor, team_id, request):
        identity(team_id)
        def execute(db, current):
            self.messaging._member(db, current, team_id)
            old = self._latest(db, current.player)
            if old:
                old = self._refresh(db, old, current.now)
                if old['team_id'] == team_id and old['close_reason'] == 'None':
                    return json.loads(old['receipt_json'])
                if current.now < old['next_request_at']:
                    raise ServiceError(409, 'life_request_cooldown')
            rid, mid, event = (uuid.uuid4().hex for _ in range(3))
            cursor = db.execute("INSERT INTO social_messages(id,kind,author_id,target_id,body,created_at) VALUES(?,'Team',?,?,?,?)", (mid, current.player, team_id, 'Life request', current.now))
            db.execute('INSERT INTO team_life_requests(sequence,id,team_id,player_id,message_id,event_id,created_at,closes_at,next_request_at,required,receipt_json) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                       (cursor.lastrowid, rid, team_id, current.player, mid, event, current.now,
                        current.now + self.rules.lifetimeSeconds, current.now + self.rules.cooldownSeconds, self.rules.capacity, '{}'))
            result = self._receipt(self._row(db, rid), 'life.request', 'Requested', current.now)
            db.execute('UPDATE team_life_requests SET receipt_json=? WHERE id=?', (canonical(result), rid))
            return result
        return self._mutate(actor, 'social.life.request/' + team_id, request, execute)

    def help(self, actor, team_id, request_id, request):
        identity(team_id)
        identity(request_id)
        def execute(db, current):
            self.messaging._member(db, current, team_id)
            row = self._refresh(db, self._row(db, request_id), current.now)
            if row['team_id'] != team_id:
                raise ServiceError(404, 'life_request_not_found')
            if row['player_id'] == current.player:
                raise ServiceError(409, 'life_self_help_forbidden')
            old = db.execute('SELECT receipt_json FROM team_life_donations WHERE request_id=? AND player_id=?', (request_id, current.player)).fetchone()
            if old:
                return json.loads(old[0])
            if row['close_reason'] != 'None' or not self._visible(db, current.player, row):
                raise ServiceError(409, 'life_help_unavailable')
            event = uuid.uuid4().hex
            db.execute('UPDATE team_life_requests SET received=received+1 WHERE id=?', (request_id,))
            row = self._refresh(db, self._row(db, request_id), current.now)
            result = self._receipt(row, 'life.help', 'Sent', current.now, event=event)
            db.execute('INSERT INTO team_life_donations VALUES(?,?,?,?,?)', (request_id, current.player, event, current.now, canonical(result)))
            return result
        return self._mutate(actor, 'social.life.help/' + team_id + '/' + request_id, request, execute)

    def claim(self, actor, request_id, request):
        identity(request_id)
        def execute(db, current):
            row = self._refresh(db, self._row(db, request_id), current.now)
            if row['player_id'] != current.player:
                raise ServiceError(403, 'life_owner_required')
            remaining = row['received'] - row['claimed']
            if row['close_reason'] == 'None' or remaining <= 0:
                raise ServiceError(409, 'life_claim_unavailable')
            self.wallet._regenerate(db, current)
            # The revision comes from this retained writer transaction, never
            # client data. Reuse the host migration/quarantine/revision guard.
            wallet = self.wallet._guard(db, current, self.wallet._row(db, current.player)['revision'])
            count = min(remaining, 5 - json.loads(wallet['balances'])[10])
            if count:
                delta = ZERO.copy()
                delta[10] = count
                project(db, current.player, 'team_life/' + request_id + '/' + request.commandId, delta, current.now)
                db.execute('UPDATE team_life_requests SET claimed=claimed+? WHERE id=?', (count, request_id))
                self.wallet._life_timer(db, current, json.loads(self.wallet._row(db, current.player)['balances'])[10])
            row = self._row(db, request_id)
            state = 'Deferred' if not count else 'Collected' if row['claimed'] == row['received'] else 'PartiallyCollected'
            result = self._receipt(row, 'life.claim', state, current.now, credited=count)
            wallet = self.wallet._view(db, current)
            result.update(walletRevision=wallet['revision'], lives=wallet['lives'], maxLives=wallet['maxLives'], nextLifeAt=wallet['nextLifeAt'])
            return result
        return self._mutate(actor, 'social.life.claim/' + request_id, request, execute)
