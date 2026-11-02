"""Read-only authorization for the existing QA or sealed checkpoint79 clone.

This module never connects to Android or modifies a target record. An explicit
clone serial is accepted only with the canonical parent-authored record.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QA79 = ROOT / 'Verification/Evidence/Gameplay79'
TARGET = QA79 / 'QA_Target.json'
DEFAULT_SERIAL = 'emulator-5556'
CLONE_SERIAL = 'emulator-5558'


def validate_qa_target(serial, out=None):
    if serial == DEFAULT_SERIAL:
        return {'serial': serial, 'isolated_clone': False,
                'scope': 'Existing dedicated QA target; all active-attempt and saved-data guards still apply.'}
    assert serial == CLONE_SERIAL, 'Only the existing QA or explicitly authorized QA79 clone may be targeted'
    assert TARGET.is_file(), 'QA79 clone requires the canonical QA_Target.json authorization'
    raw = TARGET.read_bytes()
    record = json.loads(raw.decode('utf-8-sig'))
    assert record['status'] == 'AUTHORIZED_ISOLATED_QA79_TARGET' and type(record['checkpoint']) is int and record['checkpoint'] == 79, 'Wrong clone authorization status/checkpoint'
    assert type(record['target']['index']) is int and type(record['protectedOriginal']['index']) is int, 'Clone/original indices must be integers'
    assert record['target'] == {'index': 2, 'serial': CLONE_SERIAL, 'name': 'Heart of the Rain QA79 isolated'}, 'Wrong clone identity'
    assert record['protectedOriginal'] == {'index': 1, 'serial': DEFAULT_SERIAL, 'preserved': True}, 'Original QA protection is not sealed'
    assert record['protectedOriginal']['preserved'] is True, 'Original QA protection must be explicit boolean true'
    if out is not None:
        assert Path(out).resolve().is_relative_to(QA79.resolve()), 'QA79 clone evidence must stay within Gameplay79'
    return {'serial': serial, 'isolated_clone': True,
            'target_record': TARGET.relative_to(ROOT).as_posix(),
            'target_record_sha256': hashlib.sha256(raw).hexdigest(),
            'scope': 'Explicit sealed QA79 clone index2 only. Original QA index1/5556 and the main emulator are protected; existing save/attempt guards remain required.'}


def assert_no_active_attempt(adb, package='com.heartoftherain.verification'):
    """Read the durable profile before install/stop/launch/fixture mutations."""
    path = f'/sdcard/Android/data/{package}/files/Profiles/Development-v1/profile.json'
    envelope = json.loads(adb('shell', 'cat', path))
    profile = json.loads(envelope['payload'])
    assert isinstance(profile['attempts'], list), 'QA attempt state is unavailable'
    active = sum(attempt['state'] in ('Started', 'Reserved') for attempt in profile['attempts'])
    assert active == 0, 'Preserve the active QA attempt; do not stop, install or launch this target'
    return {'activeAttempts': active, 'profileRevision': profile['revision']}


def adb_endpoint(serial):
    if serial.startswith('emulator-') and serial.removeprefix('emulator-').isdigit():
        return '127.0.0.1:' + str(int(serial.removeprefix('emulator-')) + 1)
    return serial
