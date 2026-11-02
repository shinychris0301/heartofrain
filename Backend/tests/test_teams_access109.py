"""Actual ASGI/SQLite badge persistence, literal search and historic-schema recovery.

No hosted service, provider, device, team-fee, invite or public-roster claim.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
from typing import get_args
import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from hotr_backend.api import create_app
from hotr_backend.messaging import team_query
from hotr_backend.operations import _expected, _validate, backup_database, restore_database
from hotr_backend.service import ServiceError
from hotr_backend.storage import Database, SCHEMA_VERSION, canonical
from hotr_backend.teams_schema109 import TeamBadge109, TEAMS_V11_DDL
from tests.legacy_schema_fixture import copy_legacy

CONFIG = Path(__file__).resolve().parents[1] / 'config'
BADGES = ('drop', 'lantern', 'well', 'sun', 'wave', 'crystal', 'book', 'oak', 'moon', 'cottage', 'banners', 'raincloud')


def ident():
    return uuid.uuid4().hex


class TeamsAccess109Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-teams109-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'authority.sqlite3'
        self.now = 2_000_000_000
        self.clients = []
        self.addCleanup(lambda: [c.close() for c in self.clients])
        self.open()
        self.owners = [self.authority.provision(lifetime=2_592_000) for _ in range(4)]

    def open(self, path=None, enabled=True):
        app = create_app(path or self.path, CONFIG, lambda: self.now, social_enabled=enabled, identity_enabled=True)
        client = TestClient(app, raise_server_exceptions=False)
        self.clients.append(client)
        self.app, self.client, self.authority = app, client, app.state.authority

    def headers(self, index=0):
        return {'Authorization': 'Bearer ' + self.owners[index]['token']}

    def request(self, method, path, index=0, status=200, **kwargs):
        r = self.client.request(method, path, headers=self.headers(index), **kwargs)
        self.assertEqual(r.status_code, status, r.text)
        return r.json()

    def get(self, path='/v1/teams', index=0, **kwargs):
        return self.request('GET', path, index, **kwargs)

    def count(self, table):
        with self.authority.database.connect() as db:
            return db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]

    def finance(self):
        with self.authority.database.connect() as db:
            return {table: [tuple(r) for r in db.execute('SELECT * FROM ' + table + ' ORDER BY 1')]
                    for table in ('wallets', 'wallet_ledger', 'rewards', 'gameplay_attempts', 'commerce_orders', 'commerce_credits')}

    def create(self, index=0, *, name='Rainkeepers', description='', badge=None, command=None, team_id=None):
        body = dict(commandId=command or ident(), name=name, description=description)
        if badge is not None:
            body['badgeId'] = badge
        before = self.finance()
        if team_id:
            with patch('hotr_backend.messaging.uuid', SimpleNamespace(uuid4=lambda: SimpleNamespace(hex=team_id))):
                result = self.request('POST', '/v1/teams', index, json=body)
        else:
            result = self.request('POST', '/v1/teams', index, json=body)
        self.assertEqual(set(result), {'teamId', 'state'})
        self.assertEqual(result['state'], 'Joined')
        self.assertEqual(self.finance(), before, 'Cosmetic creation changed financial state')
        return result

    def guest(self):
        self.owners.append(self.authority.provision(lifetime=2_592_000))
        return len(self.owners) - 1

    def legacy10(self):
        path = self.root / 'historic10.sqlite3'
        with self.authority.database.connect() as source, closing(sqlite3.connect(path)) as target:
            copy_legacy(source, target, 10)
        return path

    @staticmethod
    def historic_rows(path):
        with closing(sqlite3.connect(path)) as db:
            tables = [name for kind, name, _, _ in _expected(10) if kind == 'table' and name != 'schema_info']
            data = {}
            for table in tables:
                columns = [r[1] for r in db.execute('PRAGMA table_info(' + table + ')') if r[1] != 'badge_id']
                data[table] = db.execute('SELECT ' + ','.join(columns) + ' FROM ' + table + ' ORDER BY 1').fetchall()
            return data

    def test_01_default_badge_adds_public_cosmetic_field_but_preserves_legacy_command_digest(self):
        command = ident()
        result = self.create(command=command)
        directory = self.get()
        self.assertEqual(directory['teams'][0]['badgeId'], 'drop')
        public = self.get('/v1/teams/' + result['teamId'], 1)
        self.assertEqual(public['badgeId'], 'drop')
        self.assertNotIn('members', public)
        self.assertFalse(public['isMember'])
        with self.authority.database.connect() as db:
            digest = db.execute("SELECT payload_digest FROM commands WHERE operation='social.team.create' AND command_id=?", (command,)).fetchone()[0]
        old = dict(commandId=command, name='Rainkeepers', description='')
        self.assertEqual(digest, self.authority._digest(canonical(old)))
        self.assertEqual(self.request('POST', '/v1/teams', json=old), result)

    def test_02_all_approved_badges_persist_and_no_fee_is_charged(self):
        self.assertEqual(set(get_args(TeamBadge109)), set(BADGES))
        for badge in BADGES:
            owner = self.guest()
            result = self.create(owner, badge=badge)
            self.assertEqual(self.get('/v1/teams/' + result['teamId'], owner)['badgeId'], badge)
        self.assertEqual({r['badgeId'] for r in self.get(params={'limit': 50})['teams']}, set(BADGES))

    def test_03_unknown_null_or_extra_badge_values_never_create_a_team(self):
        for value in (None, True, 1, '', 'Drop', 'unknown', '../drop', 'drop\n'):
            self.request('POST', '/v1/teams', status=422, json=dict(commandId=ident(), name='Rainkeepers', badgeId=value))
        self.request('POST', '/v1/teams', status=422, json=dict(commandId=ident(), name='Rainkeepers', badgeId='drop', createFeeCoins=100))
        self.assertEqual((self.count('social_teams'), self.count('social_team_members')), (0, 0))

    def test_04_badge_intent_is_bound_to_the_idempotency_key(self):
        command = ident()
        result = self.create(badge='oak', command=command)
        self.assertEqual(self.create(badge='oak', command=command), result)
        self.request('POST', '/v1/teams', status=409, json=dict(commandId=command, name='Rainkeepers', description='', badgeId='well'))
        self.request('POST', '/v1/teams', status=409, json=dict(commandId=command, name='Rainkeepers', description=''))
        self.assertEqual(self.count('social_teams'), 1)

    def test_05_lost_commit_reply_and_restart_replay_one_team_with_the_same_badge(self):
        command = ident()
        body = dict(commandId=command, name='Rainkeepers', description='', badgeId='crystal')
        before = self.finance()
        def lost(stage):
            if stage == 'AfterCommit':
                raise OSError('controlled-lost-reply')
        self.authority.checkpoint = lost
        self.request('POST', '/v1/teams', status=500, json=body)
        self.client.close()
        self.open()
        first = self.request('POST', '/v1/teams', json=body)
        self.assertEqual(self.request('POST', '/v1/teams', json=body), first)
        self.assertEqual(self.get('/v1/teams/' + first['teamId'])['badgeId'], 'crystal')
        self.assertEqual((self.count('social_teams'), self.count('social_team_members')), (1, 1))
        self.assertEqual(self.finance(), before)

    def test_06_concurrent_exact_create_retries_share_the_original_team(self):
        body = dict(commandId=ident(), name='Concurrent Team', badgeId='moon')
        before = self.finance()
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: self.client.post('/v1/teams', headers=self.headers(), json=body), range(2)))
        self.assertEqual([r.status_code for r in responses], [200, 200])
        self.assertEqual(responses[0].json(), responses[1].json())
        self.assertEqual((self.count('social_teams'), self.count('social_team_members')), (1, 1))
        self.assertEqual(self.finance(), before)

    def test_07_badge_survives_member_join_leave_and_ownership_transfer(self):
        team = self.create(badge='lantern')['teamId']
        self.request('POST', '/v1/teams/' + team + '/join', 1, json={'commandId': ident()})
        self.request('POST', '/v1/teams/' + team + '/members/transfer', json={'commandId': ident(), 'playerId': self.owners[1]['playerId']})
        self.request('POST', '/v1/teams/' + team + '/leave', json={'commandId': ident()})
        result = self.get('/v1/teams/' + team, 1)
        self.assertEqual((result['badgeId'], result['memberCount'], result['ownerId']), ('lantern', 1, self.owners[1]['playerId']))

    def test_08_filter_runs_before_limit_and_cursor_pagination(self):
        ids = [format(i, '032x') for i in range(1, 7)]
        for i, name in enumerate(('Other One', 'Other Two', 'Rain First', 'Other Four', 'Rain Last', 'Other Six')):
            self.create(self.guest(), name=name, team_id=ids[i])
        first = self.get(params={'query': '  rAiN  ', 'limit': 1})
        self.assertEqual([r['teamId'] for r in first['teams']], [ids[2]])
        self.assertTrue(first['hasMore'])
        self.assertEqual(first['nextCursor'], ids[2])
        second = self.get(params={'query': 'RAIN', 'limit': 1, 'after': first['nextCursor']})
        self.assertEqual([r['teamId'] for r in second['teams']], [ids[4]])
        self.assertFalse(second['hasMore'])
        self.assertEqual(self.get(params={'query': 'RAIN', 'after': ids[4]})['teams'], [])

    def test_09_unicode_nfc_and_casefold_search_use_the_same_literal_normalization(self):
        a = self.create(0, name='Stra\u00dfe Rain', badge='book')['teamId']
        b = self.create(1, name='Caf\u00e9 Oak', badge='oak')['teamId']
        c = self.create(2, name='\u0414\u043e\u0436\u0434\u044c', badge='raincloud')['teamId']
        for query, expected in (('STRASSE', a), ('Cafe\u0301', b), ('\u0414\u041e\u0416\u0414\u042c', c)):
            self.assertEqual([t['teamId'] for t in self.get(params={'query': query})['teams']], [expected])

    def test_10_full_team_id_search_is_case_insensitive_without_exposing_member_rosters(self):
        team = self.create(team_id='abcdef0123456789abcdef0123456789', badge='sun')['teamId']
        result = self.get( index=1, params={'query': team.upper()})
        self.assertEqual([r['teamId'] for r in result['teams']], [team])
        self.assertNotIn('members', result['teams'][0])
        detail = self.get('/v1/teams/' + team, 1)
        self.assertFalse(detail['isMember'])
        self.assertNotIn('members', detail)
        self.assertEqual(set(detail), {'teamId', 'name', 'description', 'memberCount', 'capacity', 'ownerId', 'badgeId', 'isMember'})

    def test_11_percent_underscore_and_sql_fragments_are_literal_not_wildcards(self):
        a = self.create(0, name='100% Rain')['teamId']
        b = self.create(1, name='Oak_Team')['teamId']
        for query, expected in (('%', [a]), ('_', [b]), ("' OR 1=1 --", [])):
            self.assertEqual([t['teamId'] for t in self.get(params={'query': query})['teams']], expected)
        self.assertEqual(self.count('social_teams'), 2)

    def test_12_empty_query_keeps_directory_and_membership_contract_unchanged(self):
        self.create(badge='cottage')
        original = self.get()
        self.assertEqual(self.get(params={'query': ''}), original)
        self.assertEqual(self.get(params={'query': '   '}), original)
        self.assertEqual(set(original), {'teams', 'myTeamId', 'nextCursor', 'hasMore'})

    def test_13_queries_reject_controls_formats_and_scalar_or_raw_utf16_overflow(self):
        invalid = ('x' * 65, 'x' * 129, 'rain\n', 'rain\t', 'rain\u200b', 'rain\u2028', '\U0001f600' * 32 + '\u1100\u1161\u11a8' * 32)
        for query in invalid:
            with self.subTest(kind=repr(query[:12])):
                self.get(status=422, params={'query': query})
        with self.assertRaises(ServiceError) as error:
            team_query('\ud800')
        self.assertEqual(error.exception.code, 'invalid_team_query')
        self.assertEqual(self.count('social_teams'), 0)
        self.assertEqual(self.get(params={'query': ('e\u0301') * 64})['teams'], [])

    def test_14_query_cannot_restore_inactive_teams_or_override_social_activation(self):
        team = self.create(name='Inactive Oak')['teamId']
        with self.authority.database.transaction() as db:
            db.execute('UPDATE social_teams SET active=0 WHERE id=?', (team,))
        self.assertEqual(self.get(params={'query': 'Oak'})['teams'], [])
        self.assertEqual(self.get(params={'query': team})['teams'], [])
        self.open(enabled=False)
        self.get(status=503, params={'query': 'Oak'})
        self.request('POST', '/v1/teams', status=503, json={'commandId': ident(), 'name': 'Disabled Team', 'badgeId': 'drop'})

    def test_15_legacy10_migration_preserves_all_old_records_and_exact_legacy_create_replay(self):
        command = ident()
        first = self.create(command=command)
        old = self.legacy10()
        before = self.historic_rows(old)
        snapshot = self.root / 'snapshot10.sqlite3'
        self.assertEqual(backup_database(old, snapshot)['schemaVersion'], 10)
        Database(old)
        self.assertEqual(self.historic_rows(old), before)
        with closing(sqlite3.connect(old)) as db:
            self.assertEqual(_validate(db), SCHEMA_VERSION)
            self.assertEqual(db.execute('SELECT badge_id FROM social_teams').fetchone()[0], 'drop')
        self.open(old)
        replay = self.request('POST', '/v1/teams', json=dict(commandId=command, name='Rainkeepers', description=''))
        self.assertEqual(replay, first)
        self.assertEqual(self.count('social_teams'), 1)
        self.assertEqual(self.get('/v1/teams/' + first['teamId'])['badgeId'], 'drop')

    def test_16_failed11_migration_rolls_back_version_column_and_every_old_record(self):
        self.create()
        old = self.legacy10()
        before = self.historic_rows(old)
        with patch('hotr_backend.teams_schema109.TEAMS_V11_DDL', TEAMS_V11_DDL + '\nINVALID MIGRATION;'):
            with self.assertRaises(sqlite3.OperationalError):
                Database(old)
        self.assertEqual(self.historic_rows(old), before)
        with closing(sqlite3.connect(old)) as db:
            self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], 10)
            self.assertNotIn('badge_id', [r[1] for r in db.execute('PRAGMA table_info(social_teams)')])
            self.assertEqual(_validate(db), 10)
        self.assertEqual(backup_database(old, self.root / 'failed11-safe10.sqlite3')['schemaVersion'], 10)

    def test_17_current_snapshot_restore_retains_badge_and_duplicate_receipt(self):
        command = ident()
        first = self.create(badge='banners', command=command)
        before = self.finance()
        snapshot, restored = self.root / 'snapshot11.sqlite3', self.root / 'restored11.sqlite3'
        self.assertEqual(backup_database(self.path, snapshot)['schemaVersion'], SCHEMA_VERSION)
        self.assertEqual(restore_database(snapshot, restored)['schemaVersion'], SCHEMA_VERSION)
        self.open(restored)
        self.assertEqual(self.create(badge='banners', command=command), first)
        self.assertEqual(self.get('/v1/teams/' + first['teamId'])['badgeId'], 'banners')
        self.assertEqual(self.finance(), before)

    def test_18_database_rejects_invalid_cosmetic_values_and_duplicate_column_does_not_adopt_unknown_schema(self):
        team = self.create()['teamId']
        with self.authority.database.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('UPDATE social_teams SET badge_id=? WHERE id=?', ('unapproved', team))
        old = self.legacy10()
        with closing(sqlite3.connect(old)) as db:
            db.execute("ALTER TABLE social_teams ADD COLUMN badge_id TEXT NOT NULL DEFAULT 'unapproved'")
        with self.assertRaises(sqlite3.OperationalError):
            Database(old)
        with closing(sqlite3.connect(old)) as db:
            self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], 10)
            self.assertEqual(db.execute('SELECT badge_id FROM social_teams').fetchone()[0], 'unapproved')


if __name__ == '__main__':
    unittest.main()
