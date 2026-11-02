"""Owner-selected country used by standings, independent of ad time zones.

The country is a preference, not verified residency. It is never inferred from
the UI language, device clock or precise location, nor exported in a public
profile. Only the authenticated owner can read or change it.
"""
from pydantic import Field, field_validator

from .guards import require_actor
from .schemas import Command
from .service import ServiceError


COUNTRY_CODES = frozenset('''AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW'''.split())


class RegionUpdate(Command):
    regionCode: str = Field(min_length=2, max_length=2)

    @field_validator('regionCode')
    @classmethod
    def known_country(cls, value):
        if value not in COUNTRY_CODES:
            raise ValueError('Select an ISO 3166-1 alpha-2 country code')
        return value


def owner_region(db, player):
    row = db.execute('SELECT country_code FROM player_regions WHERE player_id=?', (player,)).fetchone()
    return row['country_code'] if row else ''


class Regions:
    def __init__(self, authority, enabled=False):
        if type(enabled) is not bool:
            raise ValueError('Explicit social activation required')
        self.authority, self.database, self.enabled = authority, authority.database, enabled

    def _guard(self, db, actor):
        require_actor(db, actor)
        if not self.enabled:
            raise ServiceError(503, 'social_not_configured')

    @staticmethod
    def _view(db, actor):
        return {'playerId': actor.player, 'regionCode': owner_region(db, actor.player),
                'regionSource': 'player_selected_country', 'locationVerified': False}

    def mine(self, actor):
        with self.database.read() as db:
            self._guard(db, actor)
            return self._view(db, actor)

    def update(self, actor, request):
        def run(db):
            self._guard(db, actor)
            def apply():
                db.execute('''INSERT INTO player_regions VALUES(?,?,?,?) ON CONFLICT(player_id)
                    DO UPDATE SET country_code=excluded.country_code,updated_at=excluded.updated_at''',
                           (actor.player, request.regionCode, actor.now, actor.now))
                return self._view(db, actor)
            return self.authority._command(db, actor, 'social.region.set', request.commandId,
                                           request.model_dump(), apply)
        return self.authority._transaction(run)
