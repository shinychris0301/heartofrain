"""Schema11: approved cosmetic team badge metadata; no economy or access rule."""
from typing import Literal


TeamBadge109 = Literal['drop', 'lantern', 'well', 'sun', 'wave', 'crystal',
                       'book', 'oak', 'moon', 'cottage', 'banners', 'raincloud']

TEAMS_V11_DDL = """
ALTER TABLE social_teams ADD COLUMN badge_id TEXT NOT NULL DEFAULT 'drop'
 CHECK(badge_id IN ('drop','lantern','well','sun','wave','crystal',
                   'book','oak','moon','cottage','banners','raincloud'));
"""
