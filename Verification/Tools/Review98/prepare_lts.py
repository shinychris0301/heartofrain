"""Ordinary source copy plus explicit private LTS configuration for98 only."""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'Verification/Tools/Ads85'))
import run_ads85_native as api
sys.path.insert(0, str(ROOT/'Verification/Tools/PageBackdrop90'))
from process90 import unity_pids


def isolated_dependencies(raw):
    data=json.loads(raw)
    dependencies=data['dependencies']
    version=dependencies.get('com.unity.modules.tilemap')
    if version not in (None,'1.0.0'):
        raise ValueError('Unexpected built-in Tilemap version; no automatic package upgrade')
    dependencies['com.unity.modules.tilemap']='1.0.0'
    return (json.dumps(data,indent=2)+'\n').encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    project = ROOT/'.verification-cache/Review98/Game'
    output = ROOT/'Verification/Evidence/Review98/Preparation'
    if not args.execute or project.exists() or output.exists() or unity_pids():
        parser.error('Explicit fresh copy and idle Editor required')
    before = api.freeze()
    output.mkdir(parents=True)
    api.write(output/'MainSources_before.json', before)
    result = {'schemaVersion':1,'status':'RUNNING_CURRENT_SOURCE_COPY98','startedUtc':api.utc(),
              'runnerSHA256':api.sha(Path(__file__)), 'mainInputCount':before['inputCount'],
              'scope':'Exact ordinary source copies, then isolated engine/company/package, the installed built-in Tilemap1.0.0 SpriteMask dependency and one new Editor fixture. No main promotion, automatic package upgrade, vendor change, Unity build or device operation.'}
    try:
        project.mkdir(parents=True)
        for relative, expected in before['files'].items():
            source = ROOT/relative
            if source.is_symlink() or source.stat().st_file_attributes & 0x400:
                raise ValueError('Linked source rejected')
            target = project/Path(relative).relative_to('Unity')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source,target)
            if api.sha(target) != expected['sha256'] or target.stat().st_size != expected['bytes'] or target.stat().st_nlink != 1:
                raise ValueError('Exact ordinary source copy failed')
        settings = project/'ProjectSettings/ProjectSettings.asset'
        raw = settings.read_bytes()
        raw, company = re.subn(rb'(?m)^  companyName: [^\r\n]*', b'  companyName: HeartRainReview98', raw)
        raw, package = re.subn(rb'(?m)^(  applicationIdentifier:\r?\n)    Android: [^\r\n]*', rb'\1    Android: com.heartoftherain.review98', raw)
        if company != 1 or package != 1:
            raise ValueError('Exact pre-import identity fields required')
        settings.write_bytes(raw)
        (project/'ProjectSettings/ProjectVersion.txt').write_text('m_EditorVersion: 6000.3.27f1\nm_EditorVersionWithRevision: 6000.3.27f1 (672d562a42a7)\n')
        manifest=project/'Packages/manifest.json'
        manifest_before=api.sha(manifest)
        manifest.write_bytes(isolated_dependencies(manifest.read_bytes()))
        result['isolatedDependencyConfiguration']={'addedOrRetained':{'com.unity.modules.tilemap':'1.0.0'},'manifestBeforeSHA256':manifest_before,'manifestAfterSHA256':api.sha(manifest),'reason':'Retain required native SpriteMask class with engine stripping enabled; reproduced Android failure and official Unity Tilemap dependency workaround.'}
        fixture = project/'Assets/Review98Editor/Editor/Unity6Build98.cs'
        fixture.parent.mkdir(parents=True)
        shutil.copy2(Path(__file__).with_name('Unity6Build98.cs'),fixture)
        fixture.with_suffix('.cs.meta').write_text('fileFormatVersion: 2\nguid: '+uuid.uuid4().hex+'\n')
        after = api.freeze()
        api.write(output/'MainSources_after.json',after)
        if after != before:
            raise ValueError('Main source changed during copy; no native execution authorized')
        result.update(status='PASS_CURRENT_SOURCE_COPY98',mainInputsUnchanged=True,
                      project=project.relative_to(ROOT).as_posix(), fixtureSHA256=api.sha(fixture),
                      mainSourceSHA256=api.sha(output/'MainSources_before.json'),
                      packagesCopiedUnchanged=manifest_before==api.sha(manifest), originalPackageBytesCopiedBeforeIsolatedConfiguration=True,
                      originalAssetsAndGuidBytesCopiedExactly=True)
    except Exception as error:
        result.update(status='FAIL_CURRENT_SOURCE_COPY98',errorType=type(error).__name__,error=str(error))
    finally:
        result['finishedUtc']=api.utc()
        api.write(output/'Preparation.json',result)
    print(json.dumps({'status':result['status'],'report':(output/'Preparation.json').relative_to(ROOT).as_posix()}))
    return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
