"""Run pinned Unity 2022 checks in the sealed isolated Review122 project."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
EDITOR = Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Unity.exe')
MANIFEST = ROOT / 'Verification/Evidence/Review122/NativeClient/SourceManifest122.json'
SUITES = {
    'production': ('HeartOfTheRain.App.ServerGameplay.Editor.ProductionClient122Verification.Run',
                   'HOTR_REVIEW122_OUT', 'ProductionClient122.json', 'PASS_NATIVE_PRODUCTION_CLIENT122'),
    'identity': ('HeartOfTheRain.Verification.Identity82Verification.Run', 'HOTR_IDENTITY82_OUTPUT',
                 'Native/Identity82.json', 'PASS_NATIVE_IDENTITY82'),
    'checkout': ('HeartOfTheRain.Verification.ShopCheckout86Verification.Run', 'HOTR_CHECKOUT86_OUTPUT',
                 'Native/ShopCheckout86.json', 'PASS_NATIVE_SHOP_CHECKOUT86'),
    'rustore': ('HeartOfTheRain.Verification.RuStore81Verification.Run', 'HOTR_RUSTORE81_OUTPUT',
                'Native/RuStore81.json', 'PASS_NATIVE_RUSTORE81_RELEASE_GUARD'),
    'configuration': ('HeartOfTheRain.Verification.ServerConfiguration104Verification.Run',
                      'HOTR_REVIEW104_OUT', 'Native/ServerConfiguration104.json', 'PASS_NATIVE_SERVER_CONFIGURATION104'),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('suite', choices=SUITES)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_]{1,32}', args.tag):
        parser.error('fresh safe tag required')
    manifest = json.loads(MANIFEST.read_bytes())
    project = Path(manifest['project'])
    if project.resolve() == (ROOT / 'Unity').resolve() or not EDITOR.is_file():
        parser.error('pinned isolated editor/project required')
    if 'm_EditorVersion: 2022.3.62f3' not in (project / 'ProjectSettings/ProjectVersion.txt').read_text():
        parser.error('pinned engine required')
    before = {name: digest(project / name) for name in manifest['inputs']}
    if before != manifest['inputs']:
        parser.error('isolated source does not match sealed source epoch')
    output = ROOT / 'Verification/Evidence/Review122/NativeClient' / (args.suite + '_' + args.tag)
    private = ROOT / '.verification-cache/Review122/NativeLogs' / (args.suite + '_' + args.tag)
    output.mkdir(parents=True, exist_ok=False)
    private.mkdir(parents=True, exist_ok=False)
    method, variable, filename, expected = SUITES[args.suite]
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith('HOTR_')}
    environment[variable] = str(output)
    environment['HOTR_REVIEW122_ISOLATED_PROJECT'] = str(project)
    command = [str(EDITOR), '-batchmode', '-projectPath', str(project), '-executeMethod', method,
               '-logFile', str(private / 'Unity.log')]
    receipt = {'status': 'RUNNING', 'startedUtc': datetime.now(timezone.utc).isoformat(),
               'method': method, 'project': str(project), 'editorVersion': '2022.3.62f3',
               'editorSHA256': digest(EDITOR), 'sourceManifestSHA256': digest(MANIFEST),
               'toolSHA256': digest(__file__), 'actualUnityEditor': True,
               'androidTestPerformed': False, 'providerAcceptanceVerified': False,
               'productionActivated': False}
    try:
        with (private / 'Console.log').open('xb') as console:
            completed = subprocess.run(command, cwd=project, env=environment, stdout=console,
                                       stderr=subprocess.STDOUT, timeout=1200,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
        receipt['exitCode'] = completed.returncode
        native = json.loads((output / filename).read_text('utf-8-sig')) if (output / filename).is_file() else {}
        receipt.update(nativeStatus=native.get('status', 'MISSING'), checks=native.get('checks', 0),
                       cases=native.get('cases', 0), errors=native.get('errors', []))
        after = {name: digest(project / name) for name in before}
        changed = [name for name in before if before[name] != after[name]]
        receipt['sourceUnchanged'] = not changed
        receipt['changedSourcePaths'] = changed
        receipt['status'] = ('PASS_UNITY_EDITOR_CLIENT122' if completed.returncode == 0
                             and native.get('status') == expected and not native.get('errors')
                             and not changed else 'FAIL_UNITY_EDITOR_CLIENT122')
        if (output / filename).is_file():
            receipt['nativeReportSHA256'] = digest(output / filename)
    except subprocess.TimeoutExpired:
        receipt['status'] = 'TIMEOUT_UNITY_EDITOR_CLIENT122'
    receipt['finishedUtc'] = datetime.now(timezone.utc).isoformat()
    (output / 'Invocation122.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt))
    return 0 if receipt['status'] == 'PASS_UNITY_EDITOR_CLIENT122' else 1


if __name__ == '__main__':
    raise SystemExit(main())
