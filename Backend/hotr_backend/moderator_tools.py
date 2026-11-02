"""Explicit local operator grants; no HTTP path can promote a moderator.

Credential input is a server-only ignored file, never a command-line token.
Grant/revoke summaries contain no token, digest, password or request contents.
Existing credential expiry/revocation and account deletion still apply.
"""
import argparse
import json
import os
from pathlib import Path

from .guards import require_actor
from .service import ServiceError


def set_moderator(authority, token, grant):
    if type(grant) is not bool:
        raise ValueError('Explicit grant action required')
    # Grant requires a currently authenticated player-role credential. A
    # financial verifier credential cannot be repurposed for moderation.
    if grant:
        actor = authority.authenticate(token)
        with authority.database.transaction() as db:
            require_actor(db, actor)
            db.execute('INSERT OR IGNORE INTO social_moderators VALUES(?,?)', (actor.credential_digest, actor.now))
    else:
        if not isinstance(token, str):
            raise ServiceError(401, 'unauthorized')
        digest = authority._digest(token)
        with authority.database.transaction() as db:
            row = db.execute('SELECT player_id FROM credentials WHERE digest=?', (digest,)).fetchone()
            if row is None:
                raise ServiceError(401, 'unauthorized')
            db.execute('DELETE FROM social_moderators WHERE credential_digest=?', (digest,))
    return {'status': 'granted' if grant else 'revoked', 'scope': 'moderation_only',
            'credentialExported': False, 'productionEnabled': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('grant', 'revoke'))
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--credential-file', required=True, type=Path)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    source = args.credential_file.resolve()
    allowed = (root / '.verification-cache', root / 'Backend/.local')
    if not any(source.is_relative_to(path) for path in allowed):
        raise SystemExit('Use an ignored local server-only credential file')
    if os.getenv('HOTR_BACKEND_MODE', 'local') not in ('local', 'staging'):
        raise SystemExit('Production activation remains unavailable')
    if not args.database.is_file():
        raise SystemExit('An existing operator-selected database is required')
    try:
        with source.open('rb') as stream:
            data = stream.read(8193)
        if len(data) > 8192:
            raise ValueError()
        credential = json.loads(data)
        from .api import create_app
        app = create_app(args.database)
        result = set_moderator(app.state.authority, credential['token'], args.action == 'grant')
    except ServiceError as error:
        raise SystemExit(error.code) from None
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        raise SystemExit('Moderator configuration unavailable') from None
    print(json.dumps(result))


if __name__ == '__main__':
    main()
