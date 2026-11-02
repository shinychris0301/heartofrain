"""Private records and opt-in standings derived solely from trusted progression."""
from .guards import require_actor
from .service import ServiceError
from .regions import owner_region


class Records:
    def __init__(self, authority, enabled=False):
        if type(enabled) is not bool:
            raise ValueError('Explicit social activation required')
        self.authority, self.database, self.enabled = authority, authority.database, enabled

    def _guard(self, db, actor):
        require_actor(db, actor)
        if not self.enabled:
            raise ServiceError(503, 'social_not_configured')

    def mine(self, actor, after=0, limit=50):
        if type(after) is not int or not 0 <= after <= 9_223_372_036_854_775_807 or type(limit) is not int or not 1 <= limit <= 100:
            raise ServiceError(422, 'invalid_request')
        with self.database.read() as db:
            self._guard(db, actor)
            player = self.authority._player(db, actor)
            totals = {r['state']: r['amount'] for r in db.execute(
                'SELECT state,COUNT(*) AS amount FROM gameplay_attempts WHERE player_id=? GROUP BY state', (actor.player,))}
            rows = db.execute('SELECT level,created_at FROM verified_clears WHERE player_id=? AND level>? ORDER BY level LIMIT ?',
                              (actor.player, after, limit + 1)).fetchall()
            page = rows[:limit]
            return {'completedLevels': player['completed'], 'attempts': totals,
                    'firstClears': [{'level': r['level'], 'verifiedAt': r['created_at']} for r in page],
                    'nextCursor': page[-1]['level'] if page else after, 'hasMore': len(rows) > limit,
                    'scoreSource': 'server_verified_completed_levels', 'clientScoresAccepted': False}

    def leaderboard(self, actor, scope='global', offset=0, limit=50, *, include_self=False):
        if scope not in ('global', 'regional', 'friends', 'team') or type(offset) is not int or not 0 <= offset <= 10_000 or type(limit) is not int or not 1 <= limit <= 100:
            raise ServiceError(422, 'invalid_request')
        with self.database.read() as db:
            self._guard(db, actor)
            conditions = ["s.leaderboard_opt_in=1", "COALESCE(a.state,'Active')='Active'",
                          'NOT EXISTS(SELECT 1 FROM social_blocks b WHERE (b.blocker_id=? AND b.blocked_id=p.id) OR (b.blocker_id=p.id AND b.blocked_id=?))']
            parameters = [actor.player, actor.player]
            region = owner_region(db, actor.player) if scope == 'regional' else ''
            if scope == 'regional':
                if not region:
                    raise ServiceError(409, 'region_required')
                conditions.append('EXISTS(SELECT 1 FROM player_regions r WHERE r.player_id=p.id AND r.country_code=?)')
                parameters.append(region)
            elif scope == 'friends':
                conditions.append("(p.id=? OR EXISTS(SELECT 1 FROM social_friend_requests f WHERE f.state='Accepted' AND ((f.low_id=? AND f.high_id=p.id) OR (f.high_id=? AND f.low_id=p.id))))")
                parameters.extend([actor.player] * 3)
            elif scope == 'team':
                team = db.execute('SELECT team_id FROM social_team_members WHERE player_id=?', (actor.player,)).fetchone()
                if not team:
                    raise ServiceError(409, 'team_required')
                if not db.execute("SELECT 1 FROM social_teams t LEFT JOIN account_states a ON a.player_id=t.owner_id WHERE t.id=? AND t.active=1 AND COALESCE(a.state,'Active')='Active'", (team['team_id'],)).fetchone():
                    raise ServiceError(404, 'team_not_found')
                conditions.append('EXISTS(SELECT 1 FROM social_team_members m WHERE m.player_id=p.id AND m.team_id=?)')
                parameters.append(team['team_id'])
            base = (' FROM players p JOIN social_profiles s ON s.player_id=p.id '
                    'LEFT JOIN account_states a ON a.player_id=p.id WHERE ' + ' AND '.join(conditions))
            rows = db.execute('SELECT p.id,p.completed,s.display_name' + base + ' ORDER BY p.completed DESC,p.id LIMIT ? OFFSET ?',
                              (*parameters, limit + 1, offset)).fetchall()
            page = rows[:limit]
            # Scores are 0..50, so one grouped count gives every rank on the page at once.
            ahead, total = {}, 0
            for score, amount in db.execute('SELECT p.completed,COUNT(*)' + base + ' GROUP BY p.completed ORDER BY p.completed DESC', parameters).fetchall():
                ahead[score], total = total, total + amount
            def view(row):
                return {'playerId': row['id'], 'displayName': row['display_name'], 'score': row['completed'], 'rank': ahead[row['completed']] + 1}
            result = {'scope': scope, 'scoreSource': 'server_verified_completed_levels', 'tiesShareRank': True,
                      'entries': [view(row) for row in page], 'nextOffset': offset + len(page),
                      'hasMore': len(rows) > limit, 'rewardGranted': False, 'regionCode': region}
            if include_self:
                # Evaluate the actor through exactly the same opt-in, scope,
                # block and account predicates as the visible window.  Do not
                # infer a rank from the current page or expose an opted-out row.
                own = db.execute('SELECT p.id,p.completed,s.display_name' + base + ' AND p.id=?',
                                 (*parameters, actor.player)).fetchone()
                result['selfEntry'] = view(own) if own else None
                result['hasSelfEntry'] = own is not None
            return result

    def team_leaderboard(self, actor, scope='global', offset=0, limit=50, *, include_self=False):
        """Visible teams ranked by opted-in, active members' trusted clears.

        Team country follows its current leader's optional country preference.
        The leader must opt into standings. Blocked/inactive members contribute
        no score or visible count; a blocked/inactive leader hides the team.
        Existing /leaderboards/team remains the player's own member standings.
        """
        if scope not in ('global', 'regional') or type(offset) is not int or not 0 <= offset <= 10_000 or type(limit) is not int or not 1 <= limit <= 100:
            raise ServiceError(422, 'invalid_request')
        with self.database.read() as db:
            self._guard(db, actor)
            region = owner_region(db, actor.player) if scope == 'regional' else ''
            if scope == 'regional' and not region:
                raise ServiceError(409, 'region_required')
            # Rank the complete visible aggregate once, before pagination. A
            # shared-score tie keeps the same rank across page boundaries.
            conditions = ["t.active=1", "os.leaderboard_opt_in=1", "COALESCE(oa.state,'Active')='Active'",
                          'NOT EXISTS(SELECT 1 FROM social_blocks b WHERE (b.blocker_id=? AND b.blocked_id=t.owner_id) OR (b.blocker_id=t.owner_id AND b.blocked_id=?))']
            parameters = [actor.player, actor.player]
            if scope == 'regional':
                conditions.append('EXISTS(SELECT 1 FROM player_regions r WHERE r.player_id=t.owner_id AND r.country_code=?)')
                parameters.append(region)
            base = '''WITH visible_members AS (
                SELECT m.team_id,p.completed FROM social_team_members m
                JOIN players p ON p.id=m.player_id JOIN social_profiles s ON s.player_id=p.id
                LEFT JOIN account_states a ON a.player_id=p.id
                WHERE s.leaderboard_opt_in=1 AND COALESCE(a.state,'Active')='Active'
                AND NOT EXISTS(SELECT 1 FROM social_blocks b WHERE (b.blocker_id=? AND b.blocked_id=p.id)
                    OR (b.blocker_id=p.id AND b.blocked_id=?))), standings AS (
                SELECT t.id,t.name,t.badge_id,COALESCE(SUM(vm.completed),0) AS score,COUNT(vm.team_id) AS member_count
                FROM social_teams t JOIN social_profiles os ON os.player_id=t.owner_id
                LEFT JOIN account_states oa ON oa.player_id=t.owner_id
                LEFT JOIN visible_members vm ON vm.team_id=t.id WHERE ''' + ' AND '.join(conditions) + ' GROUP BY t.id,t.name) '
            bindings = [actor.player, actor.player, *parameters]
            rows = db.execute(base + '''SELECT * FROM (
                SELECT *,RANK() OVER (ORDER BY score DESC) AS position FROM standings)
                ORDER BY score DESC,id LIMIT ? OFFSET ?''',
                              (*bindings, limit + 1, offset)).fetchall()
            page = rows[:limit]
            def view(row):
                entry = {'teamId': row['id'], 'name': row['name'], 'score': row['score'],
                         'memberCount': row['member_count'], 'rank': row['position']}
                if include_self:
                    entry['badgeId'] = row['badge_id']
                return entry
            result = {'scope': scope, 'regionCode': region, 'scoreSource': 'server_verified_opted_in_team_completed_levels',
                      'tiesShareRank': True, 'entries': [view(row) for row in page], 'nextOffset': offset + len(page),
                      'hasMore': len(rows) > limit, 'rewardGranted': False,
                      'teamRegionSource': 'current_leader_selected_country'}
            if include_self:
                member = db.execute('''SELECT m.team_id FROM social_team_members m
                    JOIN social_teams t ON t.id=m.team_id
                    LEFT JOIN account_states a ON a.player_id=t.owner_id
                    WHERE m.player_id=? AND t.active=1 AND COALESCE(a.state,'Active')='Active' ''',
                                    (actor.player,)).fetchone()
                own = None
                if member:
                    # Rank the entire filtered population BEFORE selecting the
                    # actor's current team. Filtering first would always rank 1.
                    own = db.execute(base + '''SELECT * FROM (
                        SELECT *,RANK() OVER (ORDER BY score DESC) AS position FROM standings)
                        WHERE id=?''', (*bindings, member['team_id'])).fetchone()
                result['selfEntry'] = view(own) if own else None
                result['hasSelfEntry'] = own is not None
                # Membership is actor-owned information, distinct from whether
                # the team is visible/opted into this leaderboard scope.
                result['hasTeam'] = member is not None
            return result
