"""Additive, optional country selection; no GPS, IP, language or wallet data."""

REGIONS_V8_DDL = '''
CREATE TABLE player_regions (
 player_id TEXT PRIMARY KEY REFERENCES players(id), country_code TEXT NOT NULL,
 created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
CREATE INDEX player_regions_country ON player_regions(country_code,player_id);
'''
