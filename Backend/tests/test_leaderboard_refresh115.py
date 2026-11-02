"""R3 standings: true ranks, scope privacy and legacy response compatibility.

Progression is explicitly synthetic upstream verification, not gameplay or a
production competition.  No provider, device or externally hosted service.
"""
import concurrent.futures
import unittest

from . import test_regions89 as fixtures


class LeaderboardRefresh115Tests(unittest.TestCase):
    setUp = fixtures.RegionRankings89Tests.setUp
    tearDown = fixtures.RegionRankings89Tests.tearDown
    open = fixtures.RegionRankings89Tests.open
    headers = fixtures.RegionRankings89Tests.headers
    get = fixtures.RegionRankings89Tests.get
    post = fixtures.RegionRankings89Tests.post
    ok = fixtures.RegionRankings89Tests.ok
    country = fixtures.RegionRankings89Tests.country
    profile = fixtures.RegionRankings89Tests.profile
    progress = fixtures.RegionRankings89Tests.progress
    fixture = fixtures.RegionRankings89Tests.fixture
    team = fixtures.RegionRankings89Tests.team

    def test_player_self_rank_is_full_scope_not_page_position(self):
        self.fixture()
        page = self.ok(self.get('/v1/leaderboards-refresh/global?limit=1', 3))
        self.assertEqual(len(page['entries']), 1)
        self.assertNotEqual(page['entries'][0]['playerId'], self.players[3]['playerId'])
        self.assertEqual(page['selfEntry']['playerId'], self.players[3]['playerId'])
        self.assertEqual(page['selfEntry']['rank'], 6)
        self.assertEqual(page['selfEntry']['score'], 0)
        self.assertTrue(page['hasSelfEntry'])
        later = self.ok(self.get('/v1/leaderboards-refresh/global?limit=1&offset=5', 3))
        self.assertEqual(page['selfEntry'], later['selfEntry'])
        self.assertEqual(later['selfEntry'], later['entries'][0])
        self.assertTrue(page['tiesShareRank'])

    def test_player_ties_are_not_relabelled_and_can_cross_page(self):
        for i in range(5):
            self.profile(i)
            self.progress(i, 1)
        self.profile(5)
        rows, offset = [], 0
        while True:
            page = self.ok(self.get('/v1/leaderboards-refresh/global?limit=2&offset=' + str(offset), 4))
            rows.extend(page['entries'])
            if not page['hasMore']:
                break
            offset = page['nextOffset']
        self.assertEqual([r['rank'] for r in rows], [1, 1, 1, 1, 1, 6])
        self.assertEqual(len({r['playerId'] for r in rows}), 6)
        self.assertEqual(page['selfEntry']['rank'], 1)

    def test_player_self_respects_opt_out_region_and_block_filters(self):
        self.fixture()
        self.profile(5, False)
        not_ranked = self.ok(self.get('/v1/leaderboards-refresh/global', 5))
        self.assertIsNone(not_ranked['selfEntry'])
        self.assertFalse(not_ranked['hasSelfEntry'])
        self.profile(5, True)
        self.ok(self.post('/v1/blocks/add', {'commandId': fixtures.ident(), 'playerId': self.players[0]['playerId']}, 5))
        global_page = self.ok(self.get('/v1/leaderboards-refresh/global', 5))
        self.assertEqual(global_page['selfEntry']['rank'], 3)
        self.assertNotIn(self.players[0]['playerId'], [v['playerId'] for v in global_page['entries']])
        regional = self.ok(self.get('/v1/leaderboards-refresh/regional', 5))
        self.assertEqual(regional['regionCode'], 'RU')
        self.assertEqual(regional['selfEntry']['rank'], 2)
        self.assertEqual(self.get('/v1/leaderboards-refresh/regional?regionCode=RU', 5).status_code, 200)
        # A query parameter never creates or overrides a missing chosen region.
        self.assertEqual(self.get('/v1/leaderboards-refresh/regional?regionCode=RU', 5).json()['regionCode'], 'RU')
        blank = self.authority.provision(lifetime=2592000)
        response = self.client.get('/v1/leaderboards-refresh/regional?regionCode=RU', headers={'Authorization': 'Bearer ' + blank['token']})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['error'], 'region_required')

    def test_team_self_badge_and_rank_are_authoritative_outside_page(self):
        self.fixture()
        first = self.team(0, (1, 2))
        second = self.team(4, (3, 5))
        # Identity badge is an existing authoritative server column, not a
        # fixture portrait or a game-economy reward.
        with self.authority.database.transaction() as db:
            db.execute('UPDATE social_teams SET badge_id=? WHERE id=?', ('oak', second))
        page = self.ok(self.get('/v1/team-leaderboards-refresh/global?limit=1', 5))
        self.assertTrue(page['hasTeam'])
        self.assertEqual([r['teamId'] for r in page['entries']], [first])
        self.assertEqual(page['selfEntry']['teamId'], second)
        self.assertEqual(page['selfEntry']['rank'], 2)
        self.assertEqual(page['selfEntry']['score'], 2)
        self.assertEqual(page['selfEntry']['badgeId'], 'oak')
        self.assertEqual(page['selfEntry']['memberCount'], 3)
        self.assertEqual(self.ok(self.get('/v1/team-leaderboards-refresh/global?limit=1&offset=1', 5))['entries'][0], page['selfEntry'])
        old = self.ok(self.get('/v1/team-leaderboards/global', 5))
        self.assertNotIn('selfEntry', old)
        self.assertNotIn('badgeId', old['entries'][0])

    def test_team_unranked_if_no_membership_hidden_owner_or_region_mismatch(self):
        self.fixture()
        not_ranked = self.ok(self.get('/v1/team-leaderboards-refresh/global', 5))
        self.assertIsNone(not_ranked['selfEntry'])
        self.assertFalse(not_ranked['hasSelfEntry'])
        self.assertFalse(not_ranked['hasTeam'])
        team = self.team(0, (5,))
        self.assertEqual(self.ok(self.get('/v1/team-leaderboards-refresh/regional', 5))['selfEntry']['teamId'], team)
        self.country(5, 'US')
        regional = self.ok(self.get('/v1/team-leaderboards-refresh/regional', 5))
        self.assertIsNone(regional['selfEntry'])
        self.assertTrue(regional['hasTeam'])
        self.assertIsNotNone(self.ok(self.get('/v1/team-leaderboards-refresh/global', 5))['selfEntry'])
        self.profile(0, False)
        hidden = self.ok(self.get('/v1/team-leaderboards-refresh/global', 5))
        self.assertIsNone(hidden['selfEntry'])
        self.assertTrue(hidden['hasTeam'])
        self.profile(0, True)
        self.ok(self.post('/v1/blocks/add', {'commandId': fixtures.ident(), 'playerId': self.players[0]['playerId']}, 5))
        page = self.ok(self.get('/v1/team-leaderboards-refresh/global', 5))
        self.assertIsNone(page['selfEntry'])
        self.assertTrue(page['hasTeam'])
        self.assertNotIn(team, [r['teamId'] for r in page['entries']])

    def test_team_ties_and_visible_count_preserve_existing_privacy(self):
        self.fixture()
        first = self.team(0, (3,))
        second = self.team(1, (5,))
        third = self.team(2, (4,))
        pages = [self.ok(self.get('/v1/team-leaderboards-refresh/global?limit=2&offset=' + str(offset), 5)) for offset in (0, 2)]
        rows = pages[0]['entries'] + pages[1]['entries']
        self.assertEqual({r['teamId'] for r in rows}, {first, second, third})
        self.assertEqual([r['rank'] for r in rows], [1, 1, 1])
        self.assertEqual(pages[1]['selfEntry']['rank'], 1)
        self.profile(1, False)
        self.assertIsNone(self.ok(self.get('/v1/team-leaderboards-refresh/global', 5))['selfEntry'])

    def test_reads_are_concurrent_consistent_and_do_not_mutate_wallet(self):
        self.fixture()
        def read(_):
            return self.ok(self.get('/v1/leaderboards-refresh/global?limit=2', 5))
        with self.authority.database.connect() as db:
            before = [tuple(r) for r in db.execute('SELECT player_id,revision,balances FROM wallets ORDER BY player_id')]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            pages = list(pool.map(read, range(12)))
        self.assertTrue(all(p['selfEntry'] == pages[0]['selfEntry'] for p in pages))
        self.assertTrue(all(p['entries'] == pages[0]['entries'] for p in pages))
        with self.authority.database.connect() as db:
            after = [tuple(r) for r in db.execute('SELECT player_id,revision,balances FROM wallets ORDER BY player_id')]
        self.assertEqual(before, after)

    def test_old_wire_unchanged_and_auth_gates_apply_to_new_routes(self):
        self.fixture()
        for path in ('/v1/leaderboards-refresh/global', '/v1/team-leaderboards-refresh/global'):
            self.assertEqual(self.client.get(path).status_code, 401)
            self.assertEqual(self.client.get(path, headers=self.headers(0, True)).status_code, 403)
        old = self.ok(self.get('/v1/leaderboards/global', 0))
        self.assertNotIn('selfEntry', old)
        self.assertEqual(set(old['entries'][0]), {'playerId', 'displayName', 'score', 'rank'})
        refreshed = self.ok(self.get('/v1/leaderboards-refresh/global', 0))
        self.assertEqual(old['entries'], refreshed['entries'])
        self.assertEqual({k: v for k, v in refreshed.items() if k not in ('selfEntry', 'hasSelfEntry')}, old)
        for path in ('/v1/leaderboards-refresh/global?limit=0', '/v1/team-leaderboards-refresh/global?offset=10001', '/v1/team-leaderboards-refresh/unknown'):
            self.assertEqual(self.get(path).status_code, 422)

