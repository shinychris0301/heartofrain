"""Additive social storage; no wallet, reward or credential-role changes."""

MESSAGING_V5_DDL = '''
CREATE TABLE social_teams (
 id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES players(id),
 name TEXT NOT NULL, description TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
CREATE TABLE social_team_members (
 player_id TEXT PRIMARY KEY REFERENCES players(id), team_id TEXT NOT NULL REFERENCES social_teams(id),
 joined_at INTEGER NOT NULL);
CREATE INDEX social_team_members_by_team ON social_team_members(team_id,joined_at,player_id);
CREATE TABLE social_team_bans (
 team_id TEXT NOT NULL REFERENCES social_teams(id), player_id TEXT NOT NULL REFERENCES players(id),
 created_at INTEGER NOT NULL, PRIMARY KEY(team_id,player_id));
CREATE TABLE social_messages (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
 kind TEXT NOT NULL CHECK(kind IN ('Direct','Team')), author_id TEXT NOT NULL REFERENCES players(id),
 target_id TEXT NOT NULL, body TEXT NOT NULL, created_at INTEGER NOT NULL,
 visibility TEXT NOT NULL DEFAULT 'Visible' CHECK(visibility IN ('Visible','Hidden','Deleted')));
CREATE INDEX social_messages_channel ON social_messages(kind,target_id,sequence);
CREATE INDEX social_messages_author ON social_messages(author_id,created_at);
CREATE TABLE social_message_reads (
 player_id TEXT NOT NULL REFERENCES players(id), kind TEXT NOT NULL CHECK(kind IN ('Direct','Team')),
 target_id TEXT NOT NULL, last_sequence INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(player_id,kind,target_id));
CREATE TABLE social_reports (
 id TEXT PRIMARY KEY, reporter_id TEXT NOT NULL REFERENCES players(id),
 message_id TEXT NOT NULL REFERENCES social_messages(id), reason TEXT NOT NULL, details TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'Open' CHECK(state IN ('Open','Resolved','Dismissed')),
 created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, UNIQUE(reporter_id,message_id));
CREATE TABLE social_moderators (
 credential_digest TEXT PRIMARY KEY REFERENCES credentials(digest), granted_at INTEGER NOT NULL);
CREATE TABLE social_moderation_actions (
 id TEXT PRIMARY KEY, moderator_id TEXT NOT NULL REFERENCES players(id), message_id TEXT NOT NULL REFERENCES social_messages(id),
 action TEXT NOT NULL, reason TEXT NOT NULL, created_at INTEGER NOT NULL);
'''
