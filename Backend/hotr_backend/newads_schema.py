"""Additive, provider-independent rewarded-ad authority tables."""

NEWADS_V7_DDL = '''
CREATE TABLE rewarded_ad_opportunities (
 id TEXT PRIMARY KEY, player_id TEXT NOT NULL REFERENCES players(id),
 placement TEXT NOT NULL, config_version TEXT NOT NULL,
 completion_mode TEXT NOT NULL CHECK(completion_mode IN ('trusted_completion','sdk_client_reported_capped')),
 verification_mode TEXT NOT NULL,
 coins INTEGER NOT NULL CHECK(coins=400), daily_limit INTEGER NOT NULL CHECK(daily_limit=3),
 utc_offset INTEGER NOT NULL CHECK(utc_offset=36000), cooldown INTEGER NOT NULL CHECK(cooldown=600),
 reserved_day INTEGER NOT NULL, created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('Reserved','AwaitingVerification','CompletedReported','Verified','Claimed','Cancelled','Expired')),
 completion_source TEXT NOT NULL DEFAULT 'none' CHECK(completion_source IN ('none','sdk_client_reported_capped','provider_verified')),
 client_reported_at INTEGER NOT NULL DEFAULT 0, verified_at INTEGER NOT NULL DEFAULT 0,
 completed_at INTEGER NOT NULL DEFAULT 0, claimed_at INTEGER NOT NULL DEFAULT 0,
 claimed_day INTEGER, reward_id TEXT REFERENCES rewards(id));
CREATE UNIQUE INDEX rewarded_ad_one_pending ON rewarded_ad_opportunities(player_id)
 WHERE state IN ('Reserved','AwaitingVerification','CompletedReported','Verified');
CREATE INDEX rewarded_ad_daily ON rewarded_ad_opportunities(player_id,claimed_day) WHERE state='Claimed';
CREATE TABLE rewarded_ad_completions (
 provider TEXT NOT NULL, event_id TEXT NOT NULL, opportunity_id TEXT NOT NULL UNIQUE REFERENCES rewarded_ad_opportunities(id),
 payload_digest TEXT NOT NULL, received_at INTEGER NOT NULL, completed_at INTEGER NOT NULL,
 PRIMARY KEY(provider,event_id));
'''

# Preserve existing reservations, receipts and their legacy CHECK constraint.
# The new column records each opportunity's local calendar without rewriting
# any financial row or its externally referenced identifier.
NEWADS_V8_DDL = '''
ALTER TABLE rewarded_ad_opportunities ADD COLUMN local_utc_offset INTEGER NOT NULL DEFAULT 36000
 CHECK(local_utc_offset BETWEEN -43200 AND 50400 AND local_utc_offset%900=0);
ALTER TABLE rewarded_ad_opportunities ADD COLUMN claim_utc_offset INTEGER NOT NULL DEFAULT 36000
 CHECK(claim_utc_offset BETWEEN -43200 AND 50400 AND claim_utc_offset%900=0);
CREATE TABLE rewarded_ad_calendars (
 player_id TEXT PRIMARY KEY REFERENCES players(id),
 utc_offset INTEGER NOT NULL CHECK(utc_offset BETWEEN -43200 AND 50400 AND utc_offset%900=0),
 pending_offset INTEGER NOT NULL CHECK(pending_offset BETWEEN -43200 AND 50400 AND pending_offset%900=0),
 time_zone TEXT NOT NULL DEFAULT '', pending_zone TEXT NOT NULL DEFAULT '',
 starts_at INTEGER NOT NULL, ends_at INTEGER NOT NULL CHECK(ends_at>starts_at));
CREATE INDEX rewarded_ad_claim_time ON rewarded_ad_opportunities(player_id,claimed_at) WHERE state='Claimed';
'''
