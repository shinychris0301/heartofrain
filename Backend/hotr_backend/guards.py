"""Transaction-bound account/session checks, including callers authenticated earlier."""


def require_active_player(db, player):
    from .service import ServiceError
    row = db.execute('SELECT state FROM account_states WHERE player_id=?', (player,)).fetchone()
    if row is not None and row['state'] != 'Active':
        raise ServiceError(410, 'account_deletion_requested')


def require_actor(db, actor):
    from .service import ServiceError
    require_active_player(db, actor.player)
    digest = getattr(actor, 'credential_digest', None)
    if digest is None:
        # Internal workers/verifiers bind actors from stored server records.
        # Their target still has to be active in this exact transaction.
        return
    row = db.execute('SELECT player_id,revoked,expires_at FROM credentials WHERE digest=?', (digest,)).fetchone()
    high_water = db.execute('SELECT high_water FROM clock_state WHERE id=1').fetchone()[0]
    current = max(actor.now, high_water)
    clock = getattr(actor, '_clock', None)
    if clock is not None:
        # Authentication precedes handler writer waits and external requests.
        # Neither a quiet database nor a captured Actor may extend expiry.
        try:
            sampled = int(clock())
        except Exception:
            raise ServiceError(503, 'clock_unavailable') from None
        if not 0 <= sampled <= 253_402_300_799:
            raise ServiceError(503, 'clock_unavailable')
        current = max(current, sampled)
    if row is None or row['player_id'] != actor.player or row['revoked'] or row['expires_at'] <= current:
        raise ServiceError(401, 'unauthorized')
