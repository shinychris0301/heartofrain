"""Recipient-owned team mail; issuing is an internal transaction, never an API.

No producer is enabled by this module. A trusted source must authorize its own
issuance and call issue_in_transaction while committing that source's event.
"""
import hashlib
import json
import re
import uuid

from .guards import require_actor, require_active_player
from .messaging import identity, text
from .service import ServiceError
from .storage import canonical
from .wallet import ZERO, project


class TeamMail111:
    def __init__(self, authority, wallet, messaging, *, enabled=False):
        if type(enabled) is not bool:
            raise ValueError('Explicit social configuration required')
        self.authority, self.database = authority, authority.database
        self.wallet, self.messaging, self.enabled = wallet, messaging, enabled

    def _guard(self, db, actor):
        require_actor(db, actor)
        if not self.enabled:
            raise ServiceError(503, 'social_not_configured')
        digest = getattr(actor, 'credential_digest', None)
        credential = db.execute('SELECT role FROM credentials WHERE digest=?', (digest,)).fetchone() if digest else None
        if credential is None or credential['role'] != 'player':
            raise ServiceError(403, 'social_owner_required')

    def issue_in_transaction(self, db, *, issuer, source_key, team_id, player_id,
                             sender_label, title, body, coins, lives, expires_at):
        """For an authorized server source only, in its existing transaction.

        The caller must prove source eligibility and own the writer transaction;
        this method provides no HTTP, admin or player-facing issuance authority.
        Identical source retries return the same message; a conflict fails closed.
        """
        if not isinstance(issuer, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,31}', issuer):
            raise ServiceError(422, 'mail_invalid_issuer')
        if not isinstance(source_key, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', source_key):
            raise ServiceError(422, 'mail_invalid_source')
        identity(team_id); identity(player_id)
        sender_label = text(sender_label, 64, empty=True)
        title = text(title, 120)
        body = text(body, 2000, multiline=True)
        if type(coins) is not int or not 0 <= coins <= 1_000_000 or type(lives) is not int or not 0 <= lives <= 5:
            raise ServiceError(422, 'mail_invalid_reward')
        if type(expires_at) is not int or not 0 <= expires_at <= 253_402_300_799:
            raise ServiceError(422, 'mail_invalid_expiry')
        payload = dict(teamId=team_id, playerId=player_id, senderLabel=sender_label, title=title, body=body,
                       rewardCoins=coins, rewardLives=lives, expiresAtUtc=expires_at)
        digest = hashlib.sha256(canonical(payload).encode('ascii')).hexdigest()
        require_active_player(db, player_id)
        prior = db.execute('SELECT id,payload_digest FROM team_mail WHERE issuer=? AND source_key=? AND player_id=?',
                           (issuer, source_key, player_id)).fetchone()
        if prior:
            if prior['payload_digest'] != digest:
                raise ServiceError(409, 'mail_source_conflict')
            return prior['id']
        if not db.execute('SELECT 1 FROM social_team_members m JOIN social_teams t ON t.id=m.team_id WHERE m.player_id=? AND m.team_id=? AND t.active=1', (player_id, team_id)).fetchone():
            raise ServiceError(409, 'mail_recipient_not_member')
        now = self.authority._transaction_clock(db)
        if expires_at and expires_at <= now:
            raise ServiceError(422, 'mail_invalid_expiry')
        message_id = uuid.uuid4().hex
        db.execute('''INSERT INTO team_mail(id,team_id,player_id,issuer,source_key,payload_digest,
                      sender_label,title,body,sent_at,expires_at,coins,lives)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                   (message_id,team_id,player_id,issuer,source_key,digest,sender_label,title,body,now,expires_at,coins,lives))
        return message_id

    def _row(self, db, actor, team, message):
        row = db.execute('SELECT * FROM team_mail WHERE id=? AND team_id=? AND player_id=?', (identity(message), identity(team), actor.player)).fetchone()
        if not row:
            raise ServiceError(404, 'mail_not_found')
        return row

    def _view(self, db, actor, row):
        reward = bool(row['coins'] or row['lives'])
        blocked = 'None'
        if not reward:
            state = 'None'
        elif row['claimed_at']:
            state = 'Claimed'
        elif row['expires_at'] and row['expires_at'] <= actor.now:
            state = 'Expired'
        else:
            self.wallet._regenerate(db, actor)
            wallet = self.wallet._row(db, actor.player)
            if not wallet['initialized']:
                blocked = 'WalletMigrationRequired'
            elif self.wallet._quarantined(db, actor.player):
                blocked = 'WalletRefundReviewRequired'
            elif json.loads(wallet['balances'])[10] + row['lives'] > 5:
                blocked = 'FullLives'
            state = 'CapacityBlocked' if blocked == 'FullLives' else 'Ready'
        return dict(messageId=row['id'],teamId=row['team_id'],sequence=row['sequence'],senderLabel=row['sender_label'],
                    title=row['title'],body=row['body'],sentAtUtc=row['sent_at'],readAtUtc=row['read_at'],
                    expiresAtUtc=row['expires_at'],rewardCoins=row['coins'],rewardLives=row['lives'],
                    claimState=state,canClaim=state == 'Ready' and blocked == 'None',claimBlockedReason=blocked)

    def list(self, actor, team, before=None, limit=8):
        identity(team)
        if type(limit) is not int or not 1 <= limit <= 8 or before is not None and (type(before) is not int or not 1 <= before <= 9_223_372_036_854_775_807):
            raise ServiceError(422, 'invalid_request')
        with self.database.read() as db:
            actor = self.authority._read_actor(db, actor)
            self._guard(db, actor); self.messaging._member(db, actor, team)
            query = 'SELECT * FROM team_mail WHERE player_id=? AND team_id=?'
            args = [actor.player,team]
            if before is not None:
                query += ' AND sequence<?'; args.append(before)
            rows = db.execute(query+' ORDER BY sequence DESC LIMIT ?', (*args,limit+1)).fetchall()
            page = rows[:limit]
            unread = db.execute('SELECT COUNT(*) FROM team_mail WHERE player_id=? AND team_id=? AND read_at=0', (actor.player,team)).fetchone()[0]
            return dict(teamId=team,serverUtc=actor.now,unreadCount=unread,messages=[self._view(db,actor,row) for row in page],
                        olderCursor=page[-1]['sequence'] if page else 0,hasOlder=len(rows)>limit)

    def detail(self, actor, team, message):
        identity(team); identity(message)
        with self.database.read() as db:
            actor = self.authority._read_actor(db, actor)
            self._guard(db, actor); self.messaging._member(db, actor, team)
            return dict(serverUtc=actor.now, message=self._view(db,actor,self._row(db,actor,team,message)))

    def owned(self, actor, after=0, limit=8):
        if type(after) is not int or not 0 <= after <= 9_223_372_036_854_775_807 or type(limit) is not int or not 1 <= limit <= 8:
            raise ServiceError(422, 'invalid_request')
        with self.database.read() as db:
            actor = self.authority._read_actor(db, actor)
            self._guard(db, actor)
            rows = db.execute('''SELECT * FROM team_mail WHERE player_id=? AND sequence>? AND claimed_at=0
                                 AND (coins>0 OR lives>0) AND (expires_at=0 OR expires_at>?)
                                 ORDER BY sequence LIMIT ?''', (actor.player,after,actor.now,limit+1)).fetchall()
            page=rows[:limit]
            # Do not reveal any old team or sender/message content.
            keys=('messageId','sequence','sentAtUtc','expiresAtUtc','rewardCoins','rewardLives','claimState','canClaim','claimBlockedReason')
            rewards=[{key:value[key] for key in keys} for value in (self._view(db,actor,row) for row in page)]
            return dict(serverUtc=actor.now,rewards=rewards,nextCursor=page[-1]['sequence'] if page else after,hasMore=len(rows)>limit)

    def _mutation(self, actor, team, message, request, kind, execute):
        identity(team); identity(message)
        def run(db, current):
            self._guard(db,current)
            return self.authority._command(db,current,'social.mail.'+kind+'/'+team+'/'+message,request.commandId,
                                           request.model_dump(),lambda: execute(db,current))
        return self.authority._transaction(run,actor)

    def read(self, actor, team, message, request):
        def execute(db, current):
            self.messaging._member(db,current,team)
            row = self._row(db,current,team,message)
            at = row['read_at'] or current.now
            if not row['read_at']:
                db.execute('UPDATE team_mail SET read_at=? WHERE id=?', (at,message))
            return dict(receiptId=uuid.uuid4().hex,operation='mail.read',teamId=team,messageId=message,readAtUtc=at,serverUtc=current.now)
        return self._mutation(actor,team,message,request,'read',execute)

    def claim(self, actor, team, message, request, *, owned=False):
        def execute(db, current):
            if owned:
                row = db.execute('SELECT * FROM team_mail WHERE id=? AND player_id=?', (identity(message),current.player)).fetchone()
                if not row:
                    raise ServiceError(404,'mail_not_found')
            else:
                self.messaging._member(db,current,team)
                row = self._row(db,current,team,message)
            if row['claimed_at']:
                return json.loads(row['claim_receipt'])
            if not (row['coins'] or row['lives']) or row['expires_at'] and row['expires_at'] <= current.now:
                raise ServiceError(409, 'mail_claim_unavailable')
            self.wallet._regenerate(db,current)
            wallet = self.wallet._guard(db,current,self.wallet._row(db,current.player)['revision'])
            blocked = json.loads(wallet['balances'])[10] + row['lives'] > 5
            if not blocked:
                delta = ZERO.copy(); delta[0] = row['coins']; delta[10] = row['lives']
                project(db,current.player,'team_mail/'+message,delta,current.now)
                self.wallet._life_timer(db,current,json.loads(self.wallet._row(db,current.player)['balances'])[10])
            view = self.wallet._view(db,current)
            result = dict(receiptId=uuid.uuid4().hex,operation='mail.claim',teamId=row['team_id'],messageId=message,
                          state='CapacityBlocked' if blocked else 'Claimed',serverUtc=current.now,
                          rewardCoins=row['coins'],rewardLives=row['lives'],walletRevision=view['revision'],
                          coins=view['coins'],lives=view['lives'],maxLives=view['maxLives'],nextLifeAt=view['nextLifeAt'])
            if not blocked:
                db.execute('UPDATE team_mail SET claimed_at=?,claim_receipt=? WHERE id=?', (current.now,canonical(result),message))
            return result
        if not owned:
            return self._mutation(actor,team,message,request,'claim',execute)
        identity(message)
        def run(db,current):
            self._guard(db,current)
            return self.authority._command(db,current,'social.mail.claim-owned/'+message,request.commandId,
                                           request.model_dump(),lambda: execute(db,current))
        return self.authority._transaction(run,actor)
