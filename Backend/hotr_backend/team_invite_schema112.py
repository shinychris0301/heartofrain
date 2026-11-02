"""Schema14: recipient-scoped direct team invitations and public team codes."""
TEAM_INVITES_V14_DDL = '''
CREATE TABLE team_public_codes (
 team_id TEXT PRIMARY KEY REFERENCES social_teams(id),
 code TEXT NOT NULL UNIQUE);
CREATE TABLE team_invitations (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT,
 id TEXT NOT NULL UNIQUE, team_id TEXT NOT NULL REFERENCES social_teams(id),
 sender_id TEXT NOT NULL REFERENCES players(id), recipient_id TEXT NOT NULL REFERENCES players(id),
 created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
 CHECK(sender_id != recipient_id));
CREATE INDEX team_invites_recipient ON team_invitations(recipient_id,sequence);
CREATE INDEX team_invites_sender ON team_invitations(sender_id,created_at);
CREATE INDEX team_invites_pair ON team_invitations(team_id,recipient_id,expires_at);
'''
