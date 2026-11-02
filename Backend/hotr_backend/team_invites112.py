"""Direct, recipient-owned team invitations. No external sending or deep links."""
import re
import unicodedata
import uuid
from pydantic import Field
from .friends import eligible_friend
from .guards import require_actor
from .messaging import identity, team_query
from .schemas import Model
from .service import ServiceError

class TeamInvitePolicy112(Model):
    version: str = Field(min_length=1, max_length=64)
    enabled: bool
    lifetimeSeconds: int = Field(ge=3600, le=2_592_000)
    limitPerHour: int = Field(ge=1, le=100)
    permission: str

    def model_post_init(self, __context):
        if self.permission != 'member':
            raise ValueError('unsupported invite permission')

class TeamInvites112:
    def __init__(self, authority, messaging, policy, *, enabled=False):
        if type(enabled) is not bool or not isinstance(policy, TeamInvitePolicy112):
            raise ValueError('Explicit invitation configuration required')
        self.authority, self.database, self.messaging = authority, authority.database, messaging
        self.policy, self.enabled = policy, enabled

    def _guard(self, db, actor):
        require_actor(db, actor)
        if not self.enabled:
            raise ServiceError(503, 'social_not_configured')
        digest = getattr(actor, 'credential_digest', None)
        row = db.execute('SELECT role FROM credentials WHERE digest=?', (digest,)).fetchone() if digest else None
        if row is None or row['role'] != 'player':
            raise ServiceError(403, 'social_owner_required')

    @staticmethod
    def _code(db, team):
        row = db.execute('SELECT code FROM team_public_codes WHERE team_id=?', (team,)).fetchone()
        if row:
            return row['code']
        for _ in range(16):
            code = uuid.uuid4().hex[:12].upper()
            if not db.execute('SELECT 1 FROM team_public_codes WHERE code=?', (code,)).fetchone():
                db.execute('INSERT INTO team_public_codes(team_id,code) VALUES(?,?)', (team, code))
                return code
        raise ServiceError(503, 'team_code_unavailable')

    @staticmethod
    def _active_invitation(db, team, recipient, now):
        rows=db.execute('SELECT * FROM team_invitations WHERE team_id=? AND recipient_id=? AND expires_at>? ORDER BY sequence DESC',(team,recipient,now))
        for row in rows:
            if eligible_friend(db,recipient,row['sender_id']) and db.execute('SELECT 1 FROM social_team_members WHERE team_id=? AND player_id=?',(team,row['sender_id'])).fetchone():
                return row
        return None

    def friends(self, actor, team, after='', query='', limit=8):
        identity(team)
        if after:
            identity(after)
        query = team_query(query)
        if type(limit) is not int or not 1 <= limit <= 8:
            raise ServiceError(422, 'invalid_social_page')
        with self.database.transaction() as db:
            actor = self.authority._transaction_actor(db, actor)
            self._guard(db, actor)
            row = self.messaging._member(db, actor, team)
            details = self.messaging._view_team(db, row)
            code = self._code(db, team)
            rows = db.execute('''SELECT CASE WHEN f.low_id=? THEN f.high_id ELSE f.low_id END AS peer
                FROM social_friend_requests f WHERE f.state='Accepted' AND (f.low_id=? OR f.high_id=?)
                AND (CASE WHEN f.low_id=? THEN f.high_id ELSE f.low_id END)>? ORDER BY peer''',
                (actor.player, actor.player, actor.player, actor.player, after)).fetchall()
            visible=[]
            for item in rows:
                peer=item['peer']
                if not eligible_friend(db,actor.player,peer):
                    continue
                profile=db.execute('SELECT p.completed,s.display_name FROM players p LEFT JOIN social_profiles s ON s.player_id=p.id WHERE p.id=?',(peer,)).fetchone()
                name=profile['display_name'] or 'Rainkeeper'
                if query and query not in unicodedata.normalize('NFC', name.casefold()):
                    continue
                membership=db.execute('SELECT team_id FROM social_team_members WHERE player_id=?',(peer,)).fetchone()
                invite=self._active_invitation(db,team,peer,actor.now)
                state='Member' if membership and membership['team_id']==team else 'Invited' if invite else 'Ready'
                visible.append(dict(friendId=peer,displayName=name,completedLevels=profile['completed'],inviteState=state,
                                    inviteId=invite['id'] if state=='Invited' else '',expiresAtUtc=invite['expires_at'] if state=='Invited' else 0))
                if len(visible)>limit:
                    break
            page=visible[:limit]
            return dict(teamId=team,serverUtc=actor.now,teamName=details['name'],badgeId=details['badgeId'],
                        memberCount=details['memberCount'],capacity=details['capacity'],publicTeamCode=code,
                        canInvite=self.policy.enabled and details['memberCount'] < details['capacity'],
                        friends=page,nextCursor=page[-1]['friendId'] if page else after,hasMore=len(visible)>limit)

    def send(self, actor, team, friend, request):
        identity(team); identity(friend)
        def run(db,current):
            self._guard(db,current)
            def execute():
                self.messaging._member(db,current,team)
                if not self.policy.enabled:
                    raise ServiceError(503,'team_invites_not_configured')
                if not eligible_friend(db,current.player,friend):
                    raise ServiceError(404,'social_player_not_found')
                if db.execute('SELECT 1 FROM social_team_bans WHERE team_id=? AND player_id=?',(team,friend)).fetchone():
                    raise ServiceError(403,'team_permission_denied')
                membership=db.execute('SELECT team_id FROM social_team_members WHERE player_id=?',(friend,)).fetchone()
                if membership and membership['team_id']==team:
                    raise ServiceError(409,'already_team_member')
                existing=self._active_invitation(db,team,friend,current.now)
                if existing:
                    return dict(receiptId=existing['id'],operation='invite.send',teamId=team,friendId=friend,inviteId=existing['id'],state='Invited',createdAtUtc=existing['created_at'],expiresAtUtc=existing['expires_at'],serverUtc=current.now)
                count=db.execute('SELECT COUNT(*) FROM social_team_members WHERE team_id=?',(team,)).fetchone()[0]
                if count>=self.messaging.capacity:
                    raise ServiceError(409,'team_full')
                sent=db.execute('SELECT COUNT(*) FROM team_invitations WHERE sender_id=? AND created_at>?',(current.player,current.now-3600)).fetchone()[0]
                if sent>=self.policy.limitPerHour:
                    raise ServiceError(429,'team_invite_rate_limited')
                invite=uuid.uuid4().hex; expires=current.now+self.policy.lifetimeSeconds
                db.execute('INSERT INTO team_invitations(id,team_id,sender_id,recipient_id,created_at,expires_at) VALUES(?,?,?,?,?,?)',(invite,team,current.player,friend,current.now,expires))
                return dict(receiptId=invite,operation='invite.send',teamId=team,friendId=friend,inviteId=invite,state='Invited',createdAtUtc=current.now,expiresAtUtc=expires,serverUtc=current.now)
            return self.authority._command(db,current,'social.invite.send/'+team+'/'+friend,request.commandId,request.model_dump(),execute)
        return self.authority._transaction(run,actor)

    def _recipient(self, db, actor, row):
        available=eligible_friend(db,actor.player,row['sender_id'])
        team=db.execute("SELECT t.* FROM social_teams t LEFT JOIN account_states a ON a.player_id=t.owner_id WHERE t.id=? AND t.active=1 AND COALESCE(a.state,'Active')='Active'",(row['team_id'],)).fetchone()
        active_sender=db.execute('SELECT 1 FROM social_team_members WHERE team_id=? AND player_id=?',(row['team_id'],row['sender_id'])).fetchone()
        banned=db.execute('SELECT 1 FROM social_team_bans WHERE team_id=? AND player_id=?',(row['team_id'],actor.player)).fetchone()
        if not available or not team or not active_sender or banned:
            return dict(inviteId=row['id'],sequence=row['sequence'],teamId='',teamName='',badgeId='',memberCount=0,capacity=0,senderName='',expiresAtUtc=row['expires_at'],state='Unavailable')
        detail=self.messaging._view_team(db,team)
        profile=db.execute('SELECT display_name FROM social_profiles WHERE player_id=?',(row['sender_id'],)).fetchone()
        me=db.execute('SELECT team_id FROM social_team_members WHERE player_id=?',(actor.player,)).fetchone()
        state=('Expired' if actor.now>=row['expires_at'] else 'AlreadyMember' if me and me['team_id']==row['team_id'] else 'TeamFull' if detail['memberCount']>=detail['capacity'] else 'Ready')
        return dict(inviteId=row['id'],sequence=row['sequence'],teamId=row['team_id'],teamName=detail['name'],badgeId=detail['badgeId'],memberCount=detail['memberCount'],capacity=detail['capacity'],senderName=(profile['display_name'] if profile and profile['display_name'] else 'Rainkeeper'),expiresAtUtc=row['expires_at'],state=state)

    def received(self, actor, before=0, limit=8):
        if type(before) is not int or not 0<=before<=9_223_372_036_854_775_807 or type(limit) is not int or not 1<=limit<=8:
            raise ServiceError(422,'invalid_social_page')
        with self.database.transaction() as db:
            actor=self.authority._transaction_actor(db,actor); self._guard(db,actor)
            where=' AND sequence<?' if before else ''
            params=(actor.player,before,limit+1) if before else (actor.player,limit+1)
            rows=db.execute('SELECT * FROM team_invitations WHERE recipient_id=?'+where+' ORDER BY sequence DESC LIMIT ?',params).fetchall()
            page=rows[:limit]
            return dict(serverUtc=actor.now,invitations=[self._recipient(db,actor,row) for row in page],nextCursor=page[-1]['sequence'] if page else 0,hasMore=len(rows)>limit)

    def detail(self, actor, invite):
        identity(invite)
        with self.database.transaction() as db:
            actor=self.authority._transaction_actor(db,actor); self._guard(db,actor)
            row=db.execute('SELECT * FROM team_invitations WHERE id=? AND recipient_id=?',(invite,actor.player)).fetchone()
            if not row:
                raise ServiceError(404,'team_invite_not_found')
            return dict(serverUtc=actor.now,invitation=self._recipient(db,actor,row))
