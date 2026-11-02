"""Disposable direct-invitation tests; no external network or real recipients."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
import uuid
from fastapi.testclient import TestClient
from hotr_backend.api import create_app
from hotr_backend.team_invites112 import TeamInvitePolicy112

CONFIG=Path(__file__).resolve().parents[1]/'config'
def ident(): return uuid.uuid4().hex

class TeamInvites112Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='hotr-invites112-'); self.addCleanup(self.temp.cleanup)
  self.now=2_000_000_000
  self.app=create_app(Path(self.temp.name)/'test.sqlite3',CONFIG,lambda:self.now,social_enabled=True)
  self.authority=self.app.state.authority; self.client=TestClient(self.app,raise_server_exceptions=False);self.addCleanup(self.client.close)
  self.users=[self.authority.provision(lifetime=2_592_000) for _ in range(5)]
  self.team=self.post('/v1/teams',name='Invite Fixture')['teamId']; self.base='/v1/teams/'+self.team+'/invitations'
 def head(self,user=0): return {'Authorization':'Bearer '+self.users[user]['token']}
 def get(self,path,user=0,status=200):
  r=self.client.get(path,headers=self.head(user));self.assertEqual(r.status_code,status,r.text);return r.json()
 def post(self,path,user=0,status=200,command=None,**body):
  r=self.client.post(path,headers=self.head(user),json={'commandId':command or ident(),**body});self.assertEqual(r.status_code,status,r.text);return r.json()
 def enabled(self,**kwargs):
  self.app.state.team_invites.policy=TeamInvitePolicy112(version='fixture',enabled=True,permission='member',lifetimeSeconds=kwargs.get('seconds',604800),limitPerHour=kwargs.get('limit',10))
 def befriend(self,a=0,b=1):
  req=self.post('/v1/friends/request',a,playerId=self.users[b]['playerId']);self.post('/v1/friends/respond',b,requestId=req['requestId'],action='accept')
 def test_default_policy_disabled_and_code_lookup(self):
  self.befriend(); obj=self.get(self.base);self.assertFalse(obj['canInvite']);code=obj['publicTeamCode'];self.assertEqual(len(code),12)
  self.assertEqual(self.get('/v1/teams?query=%23'+code)['teams'][0]['teamId'],self.team)
  self.assertEqual(self.get(self.base)['publicTeamCode'],code)
  self.post(self.base+'/'+self.users[1]['playerId'],status=503)
  self.assertEqual(self.get('/v1/invitations/received',1)['invitations'],[])
 def test_invite_exact_retry_global_discovery_and_no_automatic_join(self):
  self.enabled();self.befriend();command=ident();path=self.base+'/'+self.users[1]['playerId'];r=self.post(path,command=command);self.assertEqual(r,self.post(path,command=command))
  self.assertEqual(self.post(path)['inviteId'],r['inviteId'])
  page=self.get('/v1/invitations/received',1);self.assertEqual(page['invitations'][0]['state'],'Ready')
  self.assertEqual(self.get('/v1/invitations/'+r['inviteId'],1)['invitation']['teamId'],self.team)
  self.get('/v1/invitations/'+r['inviteId'],2,status=404)
  self.assertFalse(self.get('/v1/teams/'+self.team,1)['isMember'])
  self.assertEqual(self.get(self.base)['friends'][0]['inviteState'],'Invited')
  self.post('/v1/teams/'+self.team+'/join',1)
  self.assertEqual(self.get('/v1/invitations/'+r['inviteId'],1)['invitation']['state'],'AlreadyMember')
  self.assertEqual(self.get(self.base)['friends'][0]['inviteState'],'Member')
 def test_expiry_uses_server_clock_and_allows_new_invitation(self):
  self.enabled(seconds=3600);self.befriend();path=self.base+'/'+self.users[1]['playerId'];old=self.post(path);self.now+=3600
  self.assertEqual(self.get('/v1/invitations/'+old['inviteId'],1)['invitation']['state'],'Expired')
  self.assertNotEqual(self.post(path)['inviteId'],old['inviteId'])
 def test_friendship_block_and_membership_guards(self):
  self.enabled();path=self.base+'/'+self.users[1]['playerId'];self.post(path,status=404)
  self.befriend();r=self.post(path)
  self.post('/v1/blocks/add',1,playerId=self.users[0]['playerId'])
  details=self.get('/v1/invitations/'+r['inviteId'],1)['invitation'];self.assertEqual(details['state'],'Unavailable');self.assertEqual((details['teamId'],details['teamName'],details['senderName']),('','',''))
  self.assertEqual(self.get(self.base)['friends'],[]);self.post(path,status=404)
  self.get(self.base,2,status=403)
 def test_recipient_already_in_other_team_never_leaves(self):
  self.enabled();self.befriend();other=self.post('/v1/teams',1,name='Other')['teamId'];r=self.post(self.base+'/'+self.users[1]['playerId'])
  self.assertEqual(self.get('/v1/invitations/'+r['inviteId'],1)['invitation']['state'],'Ready')
  self.post('/v1/teams/'+self.team+'/join',1,status=409);self.assertTrue(self.get('/v1/teams/'+other,1)['isMember'])
 def test_full_team_checked_on_send_and_refreshed_on_receipt(self):
  self.enabled();self.befriend();r=self.post(self.base+'/'+self.users[1]['playerId'])
  self.app.state.messaging.capacity=2;self.post('/v1/teams/'+self.team+'/join',2)
  self.assertEqual(self.get('/v1/invitations/'+r['inviteId'],1)['invitation']['state'],'TeamFull');self.assertFalse(self.get(self.base)['canInvite'])
 def test_rate_limit_and_idempotent_receipt(self):
  self.enabled(limit=1);self.befriend(0,1);self.befriend(0,2);path=self.base+'/'+self.users[1]['playerId'];cmd=ident();r=self.post(path,command=cmd)
  self.assertEqual(self.post(path,command=cmd),r);self.post(self.base+'/'+self.users[2]['playerId'],status=429)
 def test_concurrent_duplicate_sends_record_once(self):
  self.enabled();self.befriend();path=self.base+'/'+self.users[1]['playerId'];ids=[ident(),ident()]
  def call(command):return self.client.post(path,headers=self.head(),json={'commandId':command})
  with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(call,ids))
  self.assertEqual([r.status_code for r in results],[200,200]);self.assertEqual(results[0].json()['inviteId'],results[1].json()['inviteId'])
  with self.authority.database.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM team_invitations').fetchone()[0],1)
 def test_search_and_pagination_only_matching_friends(self):
  self.enabled();[self.befriend(0,i) for i in range(1,5)]
  self.post('/v1/profile/name',1,displayName='Blue River');self.post('/v1/profile/name',2,displayName='Rain River')
  items=self.get(self.base+'?query=river&limit=1');self.assertEqual(len(items['friends']),1);self.assertTrue(items['hasMore'])
  next_page=self.get(self.base+'?query=river&limit=1&after='+items['nextCursor']);self.assertEqual(len(next_page['friends']),1);self.assertFalse(next_page['hasMore'])
 def test_owner_receipt_recovery_and_verifier_denied(self):
  self.enabled();self.befriend();cmd=ident();peer=self.users[1]['playerId'];self.post(self.base+'/'+peer,command=cmd)
  op='social.invite.send/'+self.team+'/'+peer;receipt=self.get('/v1/social/operations/'+cmd+'?operation='+op);self.assertEqual(receipt['status'],'Committed')
  token=self.authority.provision(player=self.users[0]['playerId'],role='verifier')['token'];r=self.client.get(self.base,headers={'Authorization':'Bearer '+token});self.assertEqual(r.status_code,403)
 def test_sender_removed_and_team_ban_hide_recipient_details(self):
  self.enabled();self.befriend();r=self.post(self.base+'/'+self.users[1]['playerId'])
  with self.authority.database.transaction() as db:
   db.execute('INSERT INTO social_team_bans VALUES(?,?,?)',(self.team,self.users[1]['playerId'],self.now))
  self.assertEqual(self.get('/v1/invitations/'+r['inviteId'],1)['invitation']['state'],'Unavailable')
  self.post(self.base+'/'+self.users[1]['playerId'],status=403)
 def test_account_deletion_clears_invitation_records(self):
  from hotr_backend.social_deletion import close_social_account
  self.enabled();self.befriend();r=self.post(self.base+'/'+self.users[1]['playerId'])
  with self.authority.database.transaction() as db:
   close_social_account(db,self.users[0]['playerId'],self.now)
   self.assertEqual(db.execute('SELECT COUNT(*) FROM team_invitations').fetchone()[0],0)
  self.get('/v1/invitations/'+r['inviteId'],1,status=404)
if __name__=='__main__':unittest.main()
