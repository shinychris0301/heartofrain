"""Read-only Unity111 filesystem audit against final110; never invoke Unity."""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'Verification/Tools/Ads85'))
import run_ads85_native as native


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bind(path):
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(path), 'bytes': path.stat().st_size}


def guids():
    found = {}
    for path in (ROOT / 'Unity/Assets').rglob('*.meta'):
        hits = re.findall(rb'(?m)^guid:\s*([a-fA-F0-9]{32})\s*$', path.read_bytes())
        if len(hits) != 1:
            raise RuntimeError('Invalid Unity meta: ' + str(path))
        found[path.relative_to(ROOT/'Unity').as_posix()] = hits[0].decode('ascii').lower()
    if len(set(found.values())) != len(found):
        raise RuntimeError('Duplicate Unity GUID')
    return dict(sorted(found.items()))


def main():
    out = ROOT/'Verification/Evidence/Review111'
    before_path = ROOT/'Verification/Evidence/Review110/MainSourcesFinal110_04.json'
    prior_guid_path = ROOT/'Verification/Evidence/Review110/AssetGuidsFinal110_04.json'
    source = json.loads(before_path.read_text(encoding='utf-8-sig'))
    before, old_guids = source['files'], json.loads(prior_guid_path.read_text(encoding='utf-8-sig'))
    current = native.freeze(); first_guids = guids()
    second = native.freeze(); second_guids = guids()
    if current != second or first_guids != second_guids:
        raise RuntimeError('Concurrent Unity inputs changed during audit')
    after = current['files']; old, new = set(before), set(after)
    added, removed = sorted(new-old), sorted(old-new)
    changed = sorted(p for p in old&new if before[p] != after[p])
    old_meta = [p for p in old if p.endswith('.meta')]
    changed_meta = [p for p in old_meta if p not in after or before[p] != after[p]]
    guid_changed = [p for p in old_guids if first_guids.get(p) != old_guids[p]]
    original_art = [p for p in old if p.lower().endswith(('.png','.jpg','.jpeg','.psd','.svg','.prefab','.unity','.asset','.mat'))]
    art_changed = [p for p in original_art if p not in after or before[p] != after[p]]
    other_config = [p for p in changed+removed+added if p.startswith(('Unity/Packages/','Unity/ProjectSettings/'))]
    freezes = sorted(out.glob('ClientFreeze[0-9][0-9]_111.json'))
    if not freezes: raise RuntimeError('ClientFreezeRequired')
    freeze = freezes[-1]
    freeze_data = json.loads(freeze.read_text(encoding='utf-8-sig'))
    frozen_runtime = freeze_data['runtimeFiles']
    freeze_mismatch = [r['path'] for r in frozen_runtime if r['path'] not in after or r['sha256'] != after[r['path']]['sha256']]
    package = ROOT/'.verification-cache/Teams111/Package/Heart_of_the_Rain_Teams_Mail_R1/Unity'
    package_items = []
    for sub in ('Art/TM_Coin.png','Art/TM_Letter_Closed.png','Art/TM_Letter_Open.png',
                'Data/MailComponentManifest.json','Data/TeamsMail_AssetRoles.json','Data/TeamsMail_Layout.json',
                'Data/TeamsMail_Motion.json','Data/TeamsMail_StateContract.json','Data/TeamsMail_Strings.json'):
        rel = Path('Assets/HeartOfTheRain/App/TeamsMail')/sub
        target = ROOT/'Unity'/rel; supplied = package/rel
        supplied_guid = re.findall(rb'(?m)^guid:\s*([a-fA-F0-9]{32})\s*$', Path(str(supplied)+'.meta').read_bytes())
        actual_guid = first_guids.get(rel.as_posix()+'.meta')
        if len(supplied_guid)!=1: raise RuntimeError('Invalid supplied meta: '+str(supplied))
        package_items.append({'target':target.relative_to(ROOT).as_posix(),'sha256':digest(target),
                              'packageByteMatch':target.read_bytes()==supplied.read_bytes(),
                              'packageGuidMatch':actual_guid==supplied_guid[0].decode('ascii').lower()})
    checks = {'noRemovedInputs':not removed,'oldMetaBytesPreserved':not changed_meta,'oldGuidsPreserved':not guid_changed,
              'oldArtBytesPreserved':not art_changed,'packagesAndProjectSettingsUnchanged':not other_config,
              'latestClientFreezeMatches':not freeze_mismatch,'packageBytesAndGuidsMatch':all(x['packageByteMatch'] and x['packageGuidMatch'] for x in package_items)}
    (out/'MainSourcesFinal111.json').write_text(json.dumps(current,indent=2)+'\n',encoding='utf-8')
    (out/'AssetGuidsFinal111.json').write_text(json.dumps(first_guids,indent=2)+'\n',encoding='utf-8')
    result = {'status':'PASS' if all(checks.values()) else 'FAIL','utc':datetime.now(timezone.utc).isoformat(),
              'scope':'Read-only double scan of Unity Assets/Packages/ProjectSettings and package bytes; no Unity/compiler/device/service action.',
              'baseline':bind(before_path),'baselineGuids':bind(prior_guid_path),'clientFreeze':bind(freeze),
              'final':bind(out/'MainSourcesFinal111.json'),'finalGuids':bind(out/'AssetGuidsFinal111.json'),
              'baselineInputCount':len(old),'finalInputCount':len(new),'oldGuids':len(old_guids),'finalGuidsCount':len(first_guids),
              'changed':[{'path':p,'before':before[p],'after':after[p]} for p in changed],
              'added':[{'path':p,**after[p]} for p in added],'removed':removed,
              'originalMetaCount':len(old_meta),'originalArtCount':len(original_art),'changedOriginalMeta':changed_meta,
              'changedOriginalGuids':guid_changed,'changedOriginalArt':art_changed,'changedPackagesOrSettings':other_config,
              'clientFreezeMismatch':freeze_mismatch,'packageItems':package_items,'checks':checks}
    (out/'SourceDelta111.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':result['status'],'changed':len(changed),'added':len(added),'removed':len(removed),
                      'oldGuids':len(old_guids),'finalGuids':len(first_guids),'checks':checks}))
    if result['status']!='PASS': raise SystemExit(1)


if __name__=='__main__':
    main()
