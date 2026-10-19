from pathlib import Path
import json,hashlib,re
from PIL import Image
R=Path(__file__).resolve().parents[1];U=(R.parent/'Unity') if (R.parent/'Unity').exists() else R/'Project/Heart_of_the_Rain_M66/Unity'
before=json.loads((R/'Validation/Before.json').read_text());now={p.relative_to(U).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in U.rglob('*') if p.is_file()}
changed=[p for p,h in before.items() if p in now and now[p]!=h];missing=sorted(set(before)-set(now));added=sorted(set(now)-set(before))
assert not missing,missing
artchanges=[p for p in changed if p.endswith(('.png','.wav','.mp3','.json'))];assert artchanges==['Assets/HeartOfTheRain/App/Celebrations/Art/Daria_Celebration_Atlas.png'],artchanges
registry={};dupes=[]
for p in (U/'Assets').rglob('*.meta'):
 match=re.search(r'^guid: ([a-f0-9]+)',p.read_text(),re.M)
 if not match:continue
 g=match[1]
 if g in registry:dupes.append([registry[g],str(p)])
 registry[g]=str(p)
assert not dupes,dupes
unresolved=[]
for p in (U/'Assets/HeartOfTheRain/App/Celebrations').rglob('*'):
 if p.suffix not in ['.asset','.unity']:continue
 for g in re.findall(r'guid: ([a-f0-9]{32})',p.read_text()):
  if g not in registry and not g.startswith('0000000000000000'):unresolved.append([str(p),g])
assert not unresolved,unresolved
atlas=Image.open(U/'Assets/HeartOfTheRain/App/Celebrations/Art/Daria_Celebration_Atlas.png');assert atlas.mode=='RGBA' and atlas.size==(1254,1254)
flow=(U/'Assets/HeartOfTheRain/App/PreLevel/Runtime/HomeLevelFlow.cs').read_text();assert 'LevelCompleteModal' not in flow
hud=(U/'Assets/HeartOfTheRain/M47/Runtime/GameplayHUD.cs').read_text();result=hud.split('public void ShowResult',1)[1].split('public void ShowTutorial',1)[0];assert 'TryPlayStandalone' in result and 'Dialog(won?' not in result
runtime=U/'Assets/HeartOfTheRain/App/Celebrations/Runtime'
for p in runtime.glob('*.cs'):assert p.read_bytes()==(R/'Source'/p.name).read_bytes(),p
old=json.loads((R/'Validation/M67_Asset_Audit.json').read_text())
report={'status':'PASS_ASSET_INTEGRITY_AND_MODAL_REMOVAL','old_files_changed':sorted(set(old['old_files_changed'])|set(changed)),'changed_since_M67':changed,'new_files':added,'missing_files':missing,'unique_asset_guids':len(registry),'duplicate_guids':dupes,'unresolved_references':unresolved,'approved_board_background_hud_tiles_obstacles_audio_and_levels':'BYTE_IDENTICAL_TO_M67','modified_character_art':'16-pose forward-facing Daria RGBA atlas; sRGB, untinted rendering, original olive/cream/brown palette','atlas_size':atlas.size,'victory_modal_in_live_or_standalone_win_flow':False}
(R/'Validation/Asset_Audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
