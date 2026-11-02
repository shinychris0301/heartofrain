"""Ephemeral, actor-bound opaque search cursors; no raw cursor is returned."""
FRIEND_SEARCH_V15_DDL = '''
CREATE TABLE friend_search_cursors (
 digest TEXT PRIMARY KEY, player_id TEXT NOT NULL REFERENCES players(id),
 query_digest TEXT NOT NULL, last_id TEXT NOT NULL, expires_at INTEGER NOT NULL);
CREATE INDEX friend_search_cursor_expiry ON friend_search_cursors(expires_at);
CREATE INDEX friend_search_cursor_owner ON friend_search_cursors(player_id);
'''
