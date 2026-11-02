"""Prepare, but never activate, the owned Windows VPS staging deployment.

The generated files contain no credentials. A server operator must install the
services, restrict ACLs, and verify the public TLS endpoint separately.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from . import staging105


ORIGIN = 'https://api.novamind-it.ru'
SCOPE = 'review-novamind-vps-1'
DEPLOYMENT = 'novamind-vps-staging-1'


def _absolute_local(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute() or str(path).startswith(('\\\\', '//')):
        raise ValueError('absolute_local_path_required')
    staging105._plain(path)
    return path.resolve()


def _xml_service(service_id: str, name: str, executable: Path, arguments: str,
                 working_directory: Path, log_directory: Path, *, caddy_state: Path | None = None) -> bytes:
    root = ET.Element('service')
    for key, value in (
        ('id', service_id), ('name', name), ('description', 'Heart of the Rain controlled staging service'),
        ('executable', str(executable)), ('arguments', arguments),
        ('workingdirectory', str(working_directory)), ('logpath', str(log_directory)),
        ('startmode', 'Automatic'), ('stoptimeout', '30sec'),
    ):
        ET.SubElement(root, key).text = value
    account = ET.SubElement(root, 'serviceaccount')
    ET.SubElement(account, 'domain').text = 'NT AUTHORITY'
    ET.SubElement(account, 'user').text = 'LocalService'
    if caddy_state is not None:
        ET.SubElement(root, 'env', name='XDG_DATA_HOME', value=str(caddy_state / 'data'))
        ET.SubElement(root, 'env', name='XDG_CONFIG_HOME', value=str(caddy_state / 'config'))
    log = ET.SubElement(root, 'log', mode='roll-by-size')
    ET.SubElement(log, 'sizeThreshold').text = '10240'
    ET.SubElement(log, 'keepFiles').text = '8'
    ET.SubElement(root, 'onfailure', action='restart', delay='15 sec')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True) + b'\n'


def prepare(*, backend_root: str, python_exe: str, caddy_exe: str,
            output_root: str, data_root: str) -> dict:
    backend, python, caddy = map(_absolute_local, (backend_root, python_exe, caddy_exe))
    output, data = map(_absolute_local, (output_root, data_root))
    if not (backend / 'hotr_backend/staging105.py').is_file() or not (backend / 'requirements.lock').is_file():
        raise ValueError('backend_source_required')
    if not python.is_file() or not caddy.is_file():
        raise ValueError('installed_python_and_caddy_required')
    if output == data or output.is_relative_to(data) or data.is_relative_to(output):
        raise ValueError('service_and_data_roots_must_be_separate')
    if output.is_relative_to(backend) or data.is_relative_to(backend):
        raise ValueError('private_roots_outside_backend_required')
    if output.exists() or data.exists() or not output.parent.is_dir() or not data.parent.is_dir():
        raise ValueError('fresh_roots_and_existing_parents_required')
    staging105._private_path(data)
    staging105._private_path(output)

    manifest = {
        'version': 1, 'mode': 'staging', 'publicOrigin': ORIGIN,
        'identityScope': SCOPE, 'deploymentId': DEPLOYMENT,
        'dataDirectory': str(data), 'port': 8751, 'rewardedAdsEnabled': False,
        'vk': {'enabled': False, 'clientId': '', 'redirectUri': ''},
        'replay': {'enabled': False, 'bundle': '', 'approvalFile': '', 'approvalSHA256': ''},
    }
    app_config = {
        'version': 1, 'mode': 'ManagedGuestServer', 'origin': ORIGIN,
        'identityScope': SCOPE, 'allowDevelopmentLoopback': False, 'socialEnabled': True,
    }
    caddyfile = '''api.novamind-it.ru {
    # Operator-only routes stay available through a local management tunnel.
    @private path /internal /internal/* /docs* /redoc* /openapi.json*
    handle @private {
        respond 404
    }
    handle {
        reverse_proxy 127.0.0.1:8751 {
            # Overwrite, never append or copy an incoming identity header.
            header_up X-Hotr-Verified-Client-IP {remote_host}
            header_up -Forwarded
            header_up -X-Forwarded-For
            header_up -X-Real-IP
        }
    }
}
'''
    service_log = output / 'logs'
    files = {
        'staging-manifest.json': (json.dumps(manifest, indent=2) + '\n').encode('utf-8'),
        'staging-build.json': (json.dumps(app_config, indent=2) + '\n').encode('utf-8'),
        'Caddyfile': caddyfile.encode('utf-8'),
        'HOTRStaging.xml': _xml_service(
            'HOTRStaging', 'Heart of the Rain Staging API', python,
            f'-B -m hotr_backend.staging105 start --manifest "{output / "staging-manifest.json"}"',
            backend, service_log),
        'HOTRCaddy.xml': _xml_service(
            'HOTRCaddy', 'Heart of the Rain HTTPS Proxy', caddy,
            f'run --config "{output / "Caddyfile"}"', output, service_log,
            caddy_state=output / 'caddy-state'),
    }
    output.mkdir()
    try:
        for name, body in files.items():
            (output / name).write_bytes(body)
        (output / 'logs').mkdir()
        (output / 'caddy-state').mkdir()
        (output / 'caddy-state/data').mkdir()
        (output / 'caddy-state/config').mkdir()
        staging105.read_manifest(output / 'staging-manifest.json')
    except Exception:
        # Preserve partial output for diagnosis; never remove an unknown file.
        raise
    return {'status': 'prepared_only', 'origin': ORIGIN, 'serviceDirectory': str(output),
            'dataDirectory': str(data), 'productionEnabled': False, 'servicesInstalled': False,
            'networkContacted': False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Generate non-secret Windows staging service files.')
    for name in ('backend-root', 'python-exe', 'caddy-exe', 'output-root', 'data-root'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare(**vars(args))
    except (OSError, ValueError, staging105.StagingError):
        print(json.dumps({'status': 'blocked_windows_vps_prepare'}))
        return 1
    print(json.dumps(result, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
