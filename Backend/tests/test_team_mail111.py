"""Disposable recipient-mail fixtures; no producer or live messages are enabled."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import secrets
import tempfile
import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from Crypto.PublicKey import ECC
from hotr_backend.api import create_app
from hotr_backend.service import ServiceError
from hotr_backend.wallet import ZERO, project
from tests import test_messaging as messaging_fixtures

CONFIG = Path(__file__).resolve().parents[1] / 'config'


def ident():
    return uuid.uuid4().hex


class TeamMail111Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-mail111-')
        self.addCleanup(self.temp.cleanup)
        self.now = 2_000_000_000
        self.path = Path(self.temp.name) / 'authority.sqlite3'
        self.app = create_app(self.path, CONFIG, lambda: self.now, social_enabled=True, identity_enabled=True)
        self.authority = self.app.state.authority
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.addCleanup(self.client.close)
        self.users = [self.authority.provision(lifetime=2_592_000) for _ in range(3)]
        self.team = self.post('/v1/teams', name='Fixture Team')['teamId']
        self.post('/v1/teams/'+self.team+'/join', user=1)
        self.base = '/v1/teams/'+self.team+'/mail'

    def headers(self, user=0):
        return {'Authorization':'Bearer '+self.users[user]['token']}

    def get(self, path, user=0, status=200):
        result = self.client.get(path, headers=self.headers(user))
        self.assertEqual(result.status_code,status,result.text)
        return result.json()

    def post(self, path, user=0, status=200, command=None, **body):
        result = self.client.post(path, headers=self.headers(user), json={'commandId':command or ident(),**body})
        self.assertEqual(result.status_code,status,result.text)
        return result.json()

    def issue(self, user=0, source=None, **overrides):
        params = dict(issuer='fixture', source_key=source or ident(), team_id=self.team,
                      player_id=self.users[user]['playerId'], sender_label='Village', title='A letter',
                      body='Fixture message', coins=300, lives=2, expires_at=self.now+3600)
        params.update(overrides)
        with self.authority.database.transaction() as db:
            return self.app.state.team_mail.issue_in_transaction(db,**params)

    def capacity(self, lives):
        actor=self.authority.authenticate(self.users[0]['token'])
        with self.authority.database.transaction() as db:
            actor=self.authority._transaction_actor(db,actor)
            self.app.state.wallet._regenerate(db,actor)
            current=json.loads(self.app.state.wallet._row(db,actor.player)['balances'])[10]
            delta=ZERO.copy();delta[10]=lives-current
            if delta[10]: project(db,actor.player,'fixture111/'+ident(),delta,actor.now)
            self.app.state.wallet._life_timer(db,actor,lives)

    def test_empty_and_no_player_issuance_route(self):
        inbox=self.get(self.base)
        self.assertEqual((inbox['messages'],inbox['unreadCount'],inbox['olderCursor'],inbox['hasOlder']),([],0,0,False))
        self.post(self.base,status=405,title='invented',coins=500)

    def test_internal_issuance_idempotent_and_immutable(self):
        first=self.issue(source='once')
        self.assertEqual(first,self.issue(source='once'))
        with self.assertRaises(ServiceError): self.issue(source='once',coins=301)
        self.assertEqual(len(self.get(self.base)['messages']),1)
        with self.assertRaises(ServiceError): self.issue(user=2)

    def test_invalid_text_and_amounts_fail_closed_without_a_message(self):
        for values in ({'coins':-1}, {'lives':6}, {'title':'bad\x00name'}, {'body':'bad\u2028separator'}, {'expires_at':self.now}):
            with self.subTest(values=values), self.assertRaises(ServiceError): self.issue(**values)
        self.assertEqual(self.get(self.base)['messages'],[])

    def test_verifier_credential_cannot_read_or_claim_mail(self):
        msg=self.issue()
        token=self.authority.provision(player=self.users[0]['playerId'],role='verifier')['token']
        headers={'Authorization':'Bearer '+token}
        self.assertEqual(self.client.get(self.base,headers=headers).status_code,403)
        self.assertEqual(self.client.get('/v1/mail/rewards/owned',headers=headers).status_code,403)
        self.assertEqual(self.client.post('/v1/mail/rewards/'+msg+'/claim',headers=headers,json={'commandId':ident()}).status_code,403)

    def test_uninitialized_wallet_blocks_bundle_without_a_ledger_entry(self):
        msg=self.issue()
        with self.authority.database.transaction() as db:
            db.execute('UPDATE wallets SET initialized=0 WHERE player_id=?',(self.users[0]['playerId'],))
        row=self.get(self.base+'/'+msg)['message']
        self.assertEqual((row['canClaim'],row['claimBlockedReason']),(False,'WalletMigrationRequired'))
        self.post(self.base+'/'+msg+'/claim',status=409)
        with self.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM wallet_ledger WHERE origin=?',('team_mail/'+msg,)).fetchone()[0],0)

    def test_wallet_quarantine_blocks_entire_bundle(self):
        msg=self.issue(); self.capacity(3)
        with patch.object(self.app.state.wallet,'_quarantined',return_value=True):
            row=self.get(self.base+'/'+msg)['message']
            self.assertEqual((row['canClaim'],row['claimBlockedReason']),(False,'WalletRefundReviewRequired'))
            self.post(self.base+'/'+msg+'/claim',status=409)
        with self.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM wallet_ledger WHERE origin=?',('team_mail/'+msg,)).fetchone()[0],0)

    def test_concurrent_internal_issuance_is_one_message(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            values=list(pool.map(lambda _: self.issue(source='racing-source'),range(2)))
        self.assertEqual(values[0],values[1])
        self.assertEqual(len(self.get(self.base)['messages']),1)

    def test_deletion_transaction_scrubs_text_and_blocks_future_access(self):
        from hotr_backend.social_deletion import close_social_account
        msg=self.issue();player=self.users[0]['playerId']
        with self.authority.database.transaction() as db:
            db.execute("INSERT INTO account_states VALUES(?,'DeletionRequested',?)",(player,self.now))
            close_social_account(db,player,self.now)
            row=db.execute('SELECT sender_label,title,body FROM team_mail WHERE id=?',(msg,)).fetchone()
            self.assertEqual(tuple(row),('','',''))
        self.get('/v1/mail/rewards/owned',status=410)
        self.post('/v1/mail/rewards/'+msg+'/claim',status=410)
        with self.assertRaises(ServiceError): self.issue(source='new-after-delete')

    def test_signed_guest_account_deletion_scrubs_mail_and_revokes_access(self):
        key,refresh=ECC.generate(curve='P-256'),secrets.token_urlsafe(32)
        signup=messaging_fixtures.MessagingTests.signed_identity(self,key,{'refreshToken':refresh,'recoverySecret':secrets.token_urlsafe(32)},'guest')
        response=self.client.post('/v1/identity/guest',json=signup)
        self.assertEqual(response.status_code,200,response.text)
        guest=response.json();user=len(self.users)
        self.users.append({'token':guest['accessToken'],'playerId':guest['playerId']})
        self.post('/v1/teams/'+self.team+'/join',user=user)
        msg=self.issue(user=user)
        delete=messaging_fixtures.MessagingTests.signed_identity(self,key,{'playerId':guest['playerId'],'refreshToken':refresh},'delete')
        response=self.client.post('/v1/account/deletion',json=delete)
        self.assertEqual(response.status_code,200,response.text)
        self.get('/v1/mail/rewards/owned',user=user,status=401)
        self.post('/v1/mail/rewards/'+msg+'/claim',user=user,status=401)
        with self.authority.database.connect() as db:
            self.assertEqual(tuple(db.execute('SELECT sender_label,title,body FROM team_mail WHERE id=?',(msg,)).fetchone()),('','',''))

    def test_recipient_privacy_and_membership(self):
        message=self.issue()
        self.assertEqual(self.get(self.base,user=1)['messages'],[])
        self.get(self.base+'/'+message,user=1,status=404)
        self.get(self.base,user=2,status=403)
        self.post(self.base+'/'+message+'/read',user=1,status=404)
        self.post(self.base+'/'+message+'/claim',user=1,status=404)

    def test_read_is_independent_of_claim_and_exact_retry(self):
        msg=self.issue(); cmd=ident()
        self.assertEqual(self.get(self.base)['unreadCount'],1)
        first=self.post(self.base+'/'+msg+'/read',command=cmd)
        self.assertEqual(first,self.post(self.base+'/'+msg+'/read',command=cmd))
        row=self.get(self.base+'/'+msg)['message']
        self.assertEqual((self.get(self.base)['unreadCount'],row['claimState'],row['readAtUtc']),(0,'CapacityBlocked',self.now))

    def test_whole_bundle_defers_then_claims_once(self):
        msg=self.issue(); self.capacity(4)
        cmd=ident(); blocked=self.post(self.base+'/'+msg+'/claim',command=cmd)
        self.assertEqual((blocked['state'],blocked['coins'],blocked['lives']),('CapacityBlocked',1250,4))
        self.capacity(3)
        self.assertEqual(self.post(self.base+'/'+msg+'/claim',command=cmd),blocked)
        claimed=self.post(self.base+'/'+msg+'/claim')
        self.assertEqual((claimed['state'],claimed['coins'],claimed['lives']),('Claimed',1550,5))
        self.assertEqual(self.post(self.base+'/'+msg+'/claim'),claimed)
        with self.authority.database.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM wallet_ledger WHERE origin=?",('team_mail/'+msg,)).fetchone()[0],1)

    def test_concurrent_claim_is_once_and_read_does_not_claim(self):
        msg=self.issue();self.capacity(3)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.client.post(self.base+'/'+msg+'/claim',headers=self.headers(),json={'commandId':ident()}),range(2)))
        self.assertEqual([r.status_code for r in results],[200,200])
        self.assertEqual(results[0].json(),results[1].json())
        self.assertEqual(self.get(self.base)['unreadCount'],1)

    def test_expiry_is_server_authoritative(self):
        msg=self.issue();self.capacity(3);self.now+=3601
        self.assertEqual(self.get(self.base+'/'+msg)['message']['claimState'],'Expired')
        self.post(self.base+'/'+msg+'/claim',status=409)
        self.post(self.base+'/'+msg+'/read')

    def test_pagination_cursor_and_unread_count(self):
        ids=[self.issue() for _ in range(11)]
        first=self.get(self.base+'?limit=8');self.assertEqual(len(first['messages']),8)
        self.assertEqual(first['messages'][0]['messageId'],ids[-1]);self.assertTrue(first['hasOlder'])
        second=self.get(self.base+'?before='+str(first['olderCursor'])+'&limit=8')
        self.assertEqual([r['messageId'] for r in second['messages']],list(reversed(ids[:3])))
        self.assertEqual(second['unreadCount'],11)

    def test_unknown_commit_replays_and_owner_receipt(self):
        msg=self.issue();self.capacity(3);cmd=ident()
        def checkpoint(stage):
            if stage=='AfterCommit': raise RuntimeError('fixture lost response')
        self.authority.checkpoint=checkpoint
        self.post(self.base+'/'+msg+'/claim',command=cmd,status=500)
        self.authority.checkpoint=None
        op='social.mail.claim/'+self.team+'/'+msg
        self.assertEqual(self.get('/v1/social/operations/'+cmd+'?operation='+op)['status'],'Committed')
        self.assertEqual(self.post(self.base+'/'+msg+'/claim',command=cmd)['coins'],1550)

    def test_leaving_preserves_only_minimal_reward_and_same_claim(self):
        msg=self.issue(user=1); self.post('/v1/teams/'+self.team+'/leave',user=1)
        self.get(self.base,user=1,status=403)
        self.get(self.base+'/'+msg,user=1,status=403)
        owned=self.get('/v1/mail/rewards/owned',user=1)
        self.assertEqual(len(owned['rewards']),1)
        row=owned['rewards'][0]
        self.assertEqual(set(row),{'messageId','sequence','sentAtUtc','expiresAtUtc','rewardCoins','rewardLives','claimState','canClaim','claimBlockedReason'})
        self.assertEqual(row['messageId'],msg)
        self.get('/v1/mail/rewards/owned',user=2)
        self.post('/v1/mail/rewards/'+msg+'/claim',user=2,status=404)
        self.post('/v1/mail/rewards/'+msg+'/claim',user=1,status=200)
        self.assertEqual(len(self.get('/v1/mail/rewards/owned',user=1)['rewards']),1) # Full wallet; bundle deferred.
        self.now += 3601
        self.assertEqual(self.get('/v1/mail/rewards/owned',user=1)['rewards'],[])
        self.post('/v1/mail/rewards/'+msg+'/claim',user=1,status=409)

    def test_recovered_owned_claim_after_leave_has_no_double_credit(self):
        msg=self.issue();self.capacity(3)
        self.post('/v1/teams/'+self.team+'/members/transfer',playerId=self.users[1]['playerId'])
        self.post('/v1/teams/'+self.team+'/leave')
        command=ident();result=self.post('/v1/mail/rewards/'+msg+'/claim',command=command)
        op='social.mail.claim-owned/'+msg
        self.assertEqual(self.get('/v1/social/operations/'+command+'?operation='+op)['response'],result)
        self.assertEqual(self.post('/v1/mail/rewards/'+msg+'/claim',command=command),result)
        self.assertEqual(self.get('/v1/mail/rewards/owned')['rewards'],[])
        with self.authority.database.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM wallet_ledger WHERE origin=?',('team_mail/'+msg,)).fetchone()[0],1)


if __name__ == '__main__':
    unittest.main()
