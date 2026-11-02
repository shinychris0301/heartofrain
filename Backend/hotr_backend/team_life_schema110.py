"""Schema12: durable team-help entitlements, not a mailbox or premium reward."""
TEAM_LIFE_V12_DDL = '''
CREATE TABLE team_life_requests (
 sequence INTEGER PRIMARY KEY REFERENCES social_messages(sequence),
 id TEXT NOT NULL UNIQUE, team_id TEXT NOT NULL REFERENCES social_teams(id),
 player_id TEXT NOT NULL REFERENCES players(id),
 message_id TEXT NOT NULL UNIQUE REFERENCES social_messages(id), event_id TEXT NOT NULL UNIQUE,
 created_at INTEGER NOT NULL, closes_at INTEGER NOT NULL, next_request_at INTEGER NOT NULL,
 required INTEGER NOT NULL CHECK(required BETWEEN 1 AND 5),
 received INTEGER NOT NULL DEFAULT 0 CHECK(received BETWEEN 0 AND required),
 claimed INTEGER NOT NULL DEFAULT 0 CHECK(claimed BETWEEN 0 AND received),
 close_reason TEXT NOT NULL DEFAULT 'None' CHECK(close_reason IN ('None','Full','Expired','MembershipEnded','TeamClosed','Moderated')),
 closed_at INTEGER NOT NULL DEFAULT 0, receipt_json TEXT NOT NULL,
 CHECK(closes_at>created_at), CHECK(next_request_at>=created_at));
CREATE UNIQUE INDEX team_life_one_open ON team_life_requests(player_id) WHERE close_reason='None';
CREATE INDEX team_life_by_team ON team_life_requests(team_id,sequence);
CREATE INDEX team_life_by_owner ON team_life_requests(player_id,sequence);
CREATE TABLE team_life_donations (
 request_id TEXT NOT NULL REFERENCES team_life_requests(id),
 player_id TEXT NOT NULL REFERENCES players(id), event_id TEXT NOT NULL UNIQUE,
 created_at INTEGER NOT NULL, receipt_json TEXT NOT NULL,
 PRIMARY KEY(request_id,player_id));
'''
