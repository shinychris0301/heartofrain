"""Pure additive profile/friend DDL; root joins other schema5 social modules."""
SOCIAL_V5_DDL = '''
CREATE TABLE social_profiles (
 player_id TEXT PRIMARY KEY REFERENCES players(id), display_name TEXT NOT NULL,
 leaderboard_opt_in INTEGER NOT NULL DEFAULT 0 CHECK(leaderboard_opt_in IN (0,1)),
 created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
CREATE TABLE social_friend_requests (
 id TEXT PRIMARY KEY, low_id TEXT NOT NULL REFERENCES players(id),
 high_id TEXT NOT NULL REFERENCES players(id), requester_id TEXT NOT NULL REFERENCES players(id),
 state TEXT NOT NULL CHECK(state IN ('Pending','Accepted','Declined','Cancelled')),
 created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
 CHECK(low_id<high_id), CHECK(requester_id=low_id OR requester_id=high_id));
CREATE UNIQUE INDEX social_one_live_friend_pair ON social_friend_requests(low_id,high_id)
 WHERE state IN ('Pending','Accepted');
CREATE TABLE social_blocks (
 blocker_id TEXT NOT NULL REFERENCES players(id), blocked_id TEXT NOT NULL REFERENCES players(id),
 created_at INTEGER NOT NULL, PRIMARY KEY(blocker_id,blocked_id), CHECK(blocker_id!=blocked_id));
'''
