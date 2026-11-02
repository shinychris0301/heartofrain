"""Schema13: recipient-scoped messages issued by trusted internal services."""
TEAM_MAIL_V13_DDL = '''
CREATE TABLE team_mail (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
 team_id TEXT NOT NULL REFERENCES social_teams(id), player_id TEXT NOT NULL REFERENCES players(id),
 issuer TEXT NOT NULL, source_key TEXT NOT NULL, payload_digest TEXT NOT NULL,
 sender_label TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
 sent_at INTEGER NOT NULL, expires_at INTEGER NOT NULL DEFAULT 0,
 read_at INTEGER NOT NULL DEFAULT 0, claimed_at INTEGER NOT NULL DEFAULT 0,
 claim_receipt TEXT NOT NULL DEFAULT '',
 coins INTEGER NOT NULL DEFAULT 0 CHECK(coins BETWEEN 0 AND 1000000),
 lives INTEGER NOT NULL DEFAULT 0 CHECK(lives BETWEEN 0 AND 5),
 UNIQUE(issuer,source_key,player_id));
CREATE INDEX team_mail_recipient ON team_mail(player_id,team_id,sequence);
'''
