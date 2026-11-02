"""Pure profile/team UGC-report DDL; no activation or database side effect."""
UGC_V5_DDL = '''
CREATE TABLE social_ugc_reports (
 id TEXT PRIMARY KEY, reporter_id TEXT NOT NULL REFERENCES players(id),
 kind TEXT NOT NULL CHECK(kind IN ('Profile','Team')), target_id TEXT NOT NULL,
 reason TEXT NOT NULL, details TEXT NOT NULL, content_digest TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('Open','Resolved','Dismissed')),
 created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
 UNIQUE(reporter_id,kind,target_id));
CREATE INDEX social_ugc_open_cursor ON social_ugc_reports(state,id);
CREATE TABLE social_ugc_actions (
 id TEXT PRIMARY KEY, moderator_id TEXT NOT NULL REFERENCES players(id),
 kind TEXT NOT NULL CHECK(kind IN ('Profile','Team')), target_id TEXT NOT NULL,
 action TEXT NOT NULL CHECK(action IN ('ResetProfileName','ResetTeamText','DismissReports')),
 reason TEXT NOT NULL, created_at INTEGER NOT NULL);
'''
