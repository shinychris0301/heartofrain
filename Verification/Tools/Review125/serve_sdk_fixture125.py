"""PRIVATE synthetic local SDK125 authority for native Unity HTTP verification."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Backend'))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-directory', type=Path, required=True)
    parser.add_argument('--descriptor', type=Path, required=True)
    parser.add_argument('--resume', action='store_true')
    options = parser.parse_args()
    data = options.data_directory.resolve()
    descriptor = options.descriptor.resolve()
    allowed = (ROOT / '.verification-cache/Review125').resolve()
    if not data.is_relative_to(allowed) or not descriptor.is_relative_to(allowed):
        raise RuntimeError('Private Review125 fixture paths required')
    from hotr_backend.api import create_app
    import uvicorn
    marker_path = data / '.sdk125-native-fixture.json'
    if options.resume:
        marker = json.loads(marker_path.read_text())
        if marker.get('kind') != 'HeartOfTheRainSyntheticSdk125NativeFixture':
            raise RuntimeError('Fixture marker required')
        catalog_path = data / 'commerce.json'
        if hashlib.sha256(catalog_path.read_bytes()).hexdigest() != marker['catalogSHA256']:
            raise RuntimeError('Fixture catalog changed')
    else:
        data.mkdir(parents=True, exist_ok=False)
        catalog = json.loads((ROOT / 'Release/RuStore/commerce.example.json').read_text('utf-8-sig'))
        catalog.update(enabled=True, sandbox=True, appId=123, verificationMode='sdk_client_reported')
        for product in catalog['products']:
            product['enabled'] = True
        catalog_path = data / 'commerce.json'
        catalog_path.write_text(json.dumps(catalog), encoding='utf-8')
        marker = {'kind': 'HeartOfTheRainSyntheticSdk125NativeFixture',
                  'fixtureId': uuid.uuid4().hex, 'catalogSHA256': hashlib.sha256(catalog_path.read_bytes()).hexdigest()}
    app = create_app(data / 'authority.sqlite3', ROOT / 'Backend/config',
                     commerce_config_path=catalog_path, identity_enabled=True,
                     notifications_enabled=False, social_enabled=False, replay_enabled=False)
    if not options.resume:
        identity = app.state.authority.provision(lifetime=3600)
        marker.update(playerId=identity['playerId'], token=identity['token'])
        marker_path.write_text(json.dumps(marker), encoding='utf-8')
    listener = socket.socket()
    if os.name == 'nt':
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    listener.bind(('127.0.0.1', 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    private = {'origin': 'http://127.0.0.1:' + str(port), 'appId': 123,
               'playerId': marker['playerId'], 'token': marker['token'],
               'verificationMode': 'sdk_client_reported', 'productionEnabled': False,
               'sandbox': True, 'pid': os.getpid(), 'fixtureId': marker['fixtureId'],
               'database': str(data / 'authority.sqlite3'), 'syntheticSdkObservationsOnly': True}
    descriptor.parent.mkdir(parents=True, exist_ok=True)
    temporary = descriptor.with_suffix('.tmp')
    temporary.write_text(json.dumps(private), encoding='utf-8')
    os.replace(temporary, descriptor)
    config = uvicorn.Config(app, host='127.0.0.1', port=port, access_log=False, log_level='warning')
    try:
        uvicorn.Server(config).run(sockets=[listener])
    finally:
        listener.close()

if __name__ == '__main__':
    main()

