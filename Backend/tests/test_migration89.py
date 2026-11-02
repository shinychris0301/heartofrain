"""Actual legacy SQLite upgrade, rollback and snapshot recovery; no providers."""
import contextlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hotr_backend.discovery_schema import DISCOVERY_V5_DDL
from hotr_backend.identity_schema import IDENTITY_V4_DDL
from hotr_backend.messaging_schema import MESSAGING_V5_DDL
from hotr_backend.newads_schema import NEWADS_V7_DDL, NEWADS_V8_DDL
from hotr_backend.notification_schema import NOTIFICATIONS_V4_DDL
from hotr_backend.operations import backup_database, restore_database
from hotr_backend.records_schema import RECORDS_V5_DDL
from hotr_backend.replay_schema import REPLAY_V6_DDL
from hotr_backend.social_schema import SOCIAL_V5_DDL
from hotr_backend.storage import COMMERCE_V2, DDL, SCHEMA_VERSION, WALLET_V3, Database
from hotr_backend.ugc_schema import UGC_V5_DDL


class Migration89Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hotr-migration89-')
        self.root = Path(self.temp.name)
        self.path = self.root / 'legacy7.sqlite3'
        with contextlib.closing(sqlite3.connect(self.path)) as db:
            db.executescript(''.join((DDL, COMMERCE_V2, WALLET_V3, IDENTITY_V4_DDL,
                NOTIFICATIONS_V4_DDL, SOCIAL_V5_DDL, MESSAGING_V5_DDL, RECORDS_V5_DDL,
                DISCOVERY_V5_DDL, UGC_V5_DDL, REPLAY_V6_DDL, NEWADS_V7_DDL)))
            db.execute('UPDATE schema_info SET version=7')
            db.execute('INSERT INTO players VALUES(?,7,1,199,?,?)', ('legacy-player', '{}', 100))
            db.execute('INSERT INTO wallets VALUES(?,1,9,?,0)', ('legacy-player', '{"coins":1234}'))
            db.execute('INSERT INTO rewards(id,player_id,source,source_key,grant_json,created_at) VALUES(?,?,?,?,?,?)',
                       ('old-reward', 'legacy-player', 'rewarded_ad', 'old-ad', '{"coins":400}', 200))
            db.execute('INSERT INTO wallet_ledger(id,player_id,origin,delta_json,revision,created_at) VALUES(?,?,?,?,?,?)',
                       ('old-ledger', 'legacy-player', 'old-reward', '{"coins":400}', 9, 200))
            db.execute('INSERT INTO commands VALUES(?,?,?,?,?)',
                       ('legacy-player', 'old-operation', 'old-command', 'old-digest', '{"unchanged":true}'))
            for identifier, state in (('old-ad', 'Claimed'), ('pending-ad', 'Reserved')):
                db.execute('''INSERT INTO rewarded_ad_opportunities
                    (id,player_id,placement,config_version,completion_mode,verification_mode,coins,daily_limit,
                     utc_offset,cooldown,reserved_day,created_at,expires_at,state,claimed_at,claimed_day,reward_id)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (identifier, 'legacy-player', 'shop_coins', 'legacy', 'trusted_completion', 'none',
                     400, 3, 36000, 600, 200, 100, 1000, state,
                     200 if state == 'Claimed' else 0, 200 if state == 'Claimed' else None,
                     'old-reward' if state == 'Claimed' else None))
            db.commit()
        self.before = self.retained_rows(self.path)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def retained_rows(path):
        with contextlib.closing(sqlite3.connect(path)) as db:
            return {table: db.execute('SELECT * FROM ' + table).fetchall()
                    for table in ('players', 'wallets', 'rewards', 'wallet_ledger', 'commands')}

    def test_upgrade_preserves_wallet_receipts_and_pending_reservation(self):
        database = Database(self.path)
        self.assertEqual(self.retained_rows(self.path), self.before)
        with database.connect() as db:
            self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], SCHEMA_VERSION)
            self.assertEqual([(r['id'], r['state'], r['utc_offset'], r['local_utc_offset'], r['claim_utc_offset'])
                for r in db.execute('SELECT * FROM rewarded_ad_opportunities ORDER BY id')],
                [('old-ad', 'Claimed', 36000, 36000, 36000), ('pending-ad', 'Reserved', 36000, 36000, 36000)])
            for table in ('player_regions', 'account_provider_links', 'account_provider_flows', 'rewarded_ad_calendars'):
                self.assertEqual(db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0], 0)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
        Database(self.path)  # A second process/open must not duplicate grants or schema.
        self.assertEqual(self.retained_rows(self.path), self.before)

    def test_partially_applied_schema8_rolls_back_completely(self):
        with patch('hotr_backend.newads_schema.NEWADS_V8_DDL', NEWADS_V8_DDL + '\nINVALID MIGRATION STATEMENT;'):
            with self.assertRaises(sqlite3.Error):
                Database(self.path)
        self.assertEqual(self.retained_rows(self.path), self.before)
        with contextlib.closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], 7)
            self.assertNotIn('local_utc_offset', [row[1] for row in db.execute('PRAGMA table_info(rewarded_ad_opportunities)')])
            self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name='player_regions'").fetchone())
        # A failed upgrade must leave a valid, independently restorable schema7.
        report = backup_database(self.path, self.root / 'failed-upgrade-backup.sqlite3')
        self.assertEqual(report['schemaVersion'], 7)
        self.assertTrue(report['requiresMigration'])
        Database(self.path)
        self.assertEqual(self.retained_rows(self.path), self.before)

    def test_schema7_and_schema8_snapshots_restore_without_implicit_mutation(self):
        old_snapshot, restored = self.root / 'old-backup.sqlite3', self.root / 'restored.sqlite3'
        self.assertEqual(backup_database(self.path, old_snapshot)['schemaVersion'], 7)
        self.assertTrue(restore_database(old_snapshot, restored)['requiresMigration'])
        with contextlib.closing(sqlite3.connect(restored)) as db:
            self.assertEqual(db.execute('SELECT version FROM schema_info').fetchone()[0], 7)
        Database(restored)
        current_snapshot, current_restore = self.root / 'current-backup.sqlite3', self.root / 'current-restore.sqlite3'
        report = backup_database(restored, current_snapshot)
        self.assertEqual(report['schemaVersion'], SCHEMA_VERSION)
        self.assertFalse(report['requiresMigration'])
        self.assertEqual(restore_database(current_snapshot, current_restore)['schemaVersion'], SCHEMA_VERSION)
        self.assertEqual(self.retained_rows(current_restore), self.before)
