"""Indexes for server-verified records; no client-authored score table."""

RECORDS_V5_DDL = '''
CREATE INDEX social_leaderboard_progress ON players(completed DESC,id);
CREATE INDEX social_verified_records ON verified_clears(player_id,created_at,level);
'''
