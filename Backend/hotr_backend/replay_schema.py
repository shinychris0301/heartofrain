"""Additive schema6 for authenticated model replay; activation stays explicit."""

REPLAY_V6_DDL = '''
CREATE TABLE replay_attempts (
 attempt_id TEXT PRIMARY KEY REFERENCES gameplay_attempts(id), player_id TEXT NOT NULL REFERENCES players(id),
 start_receipt_id TEXT NOT NULL REFERENCES wallet_ledger(id), pins_sha TEXT NOT NULL, level_sha TEXT NOT NULL,
 frozen_json TEXT NOT NULL, prefix_json TEXT NOT NULL DEFAULT '[]', receipts_json TEXT NOT NULL DEFAULT '[]',
 revision INTEGER NOT NULL DEFAULT 0, checkpoint_sha TEXT NOT NULL DEFAULT '', outcome TEXT NOT NULL DEFAULT 'Playing',
 moves INTEGER NOT NULL, turn INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL);
CREATE TABLE replay_operations (
 id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL REFERENCES replay_attempts(attempt_id),
 player_id TEXT NOT NULL REFERENCES players(id), command_id TEXT NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('Verify','Tool','Continue')), request_hash TEXT NOT NULL, request_json TEXT NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('Pending','Running','Committed','Rejected')),
 lease_token TEXT, lease_until INTEGER NOT NULL DEFAULT 0, base_revision INTEGER NOT NULL,
 candidate_json TEXT, snapshot_json TEXT, result_json TEXT, response_json TEXT,
 error_code TEXT NOT NULL DEFAULT '', created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
 UNIQUE(player_id,command_id));
CREATE UNIQUE INDEX replay_one_unfinished ON replay_operations(attempt_id) WHERE state IN ('Pending','Running');
CREATE TABLE replay_paid_bindings (
 receipt_id TEXT PRIMARY KEY REFERENCES wallet_ledger(id), attempt_id TEXT NOT NULL REFERENCES replay_attempts(attempt_id),
 operation_id TEXT NOT NULL UNIQUE REFERENCES replay_operations(id), action_index INTEGER NOT NULL,
 kind TEXT NOT NULL CHECK(kind IN ('Tool','Continue')), tool INTEGER NOT NULL, x INTEGER NOT NULL, y INTEGER NOT NULL,
 moves_after INTEGER NOT NULL, UNIQUE(attempt_id,action_index));
CREATE TABLE replay_worker_slot (
 id INTEGER PRIMARY KEY CHECK(id=1), operation_id TEXT REFERENCES replay_operations(id),
 lease_token TEXT, lease_until INTEGER NOT NULL DEFAULT 0);
INSERT INTO replay_worker_slot(id) VALUES(1);
'''
