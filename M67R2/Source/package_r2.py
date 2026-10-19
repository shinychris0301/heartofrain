from pathlib import Path
import json,zipfile,tarfile,io,re,hashlib,shutil
R=Path(__file__).resolve().parents[1];U=(R.parent/'Unity') if (R.parent/'Unity').exists() else R/'Project/Heart_of_the_Rain_M66/Unity';D=R/'Downloads';D.mkdir(exist_ok=True)
audit=json.loads((R/'Validation/Asset_Audit.json').read_text())
for name in ['Completion_Checks.json','Celebration_Checks.json','Completion_Flow_Checks.json','Syntax.json','Playback.json','Asset_Audit.json','Victory_Checks.json']:
 assert json.loads((R/'Validation'/name).read_text())['status'].startswith('PASS'),name
paths=[U/p for p in audit['old_files_changed'] if p.startswith('Assets/')]
new=U/'Assets/HeartOfTheRain/App/Celebrations'
paths += [new]+[p for p in new.rglob('*') if p.suffix!='.meta'];paths=list(set(paths))
package=D/'Heart_of_the_Rain_M67R2_Celebrations.unitypackage'
with tarfile.open(package,'w:gz') as tar:
 for p in sorted(paths):
  meta=Path(str(p)+'.meta');g=re.search(r'^guid: (\w+)',meta.read_text(),re.M)[1]
  for name,data in [('pathname',p.relative_to(U).as_posix().encode()),('asset.meta',meta.read_bytes())]+([] if p.is_dir() else [('asset',p.read_bytes())]):
   info=tarfile.TarInfo(g+'/'+name);info.size=len(data);info.mtime=0;tar.addfile(info,io.BytesIO(data))
with tarfile.open(package) as tar:
 names=tar.getnames();assert len(names)==len(set(names));assert sum(n.endswith('/pathname') for n in names)==len(paths)

# The supporting folder has the same layout in the review ZIP and full project.
support={}
for folder in ['Source','Documentation','Previews']:
 for p in (R/folder).rglob('*'):
  if p.is_file() and '__pycache__' not in p.parts:support['M67R2/'+p.relative_to(R).as_posix()]=p
for p in (R/'Validation').iterdir():
 if p.is_file() and p.suffix in ['.json','.txt'] and p.name!='Package_Verification.json':support['M67R2/Validation/'+p.name]=p
for name in ['Source/CompletionChecks.cs','Source/CompletionFlowChecks.cs','Source/FlowFakes.cs','Validation/Sprite_Bindings.json']:
 support['M67R2/M66Reference/'+name]=R/'M66Reference'/name
for name in ['Source/render_ui.py','Source/approved_atlas_reader.py','Tests/UnityMathShim.cs','Previews/Level50_Initial.png']:
 support['M67R2/CoreReference/'+name]=R/'CoreReference'/name
for p in (R/'CoreReference/Data/Levels').glob('*.json'):support['M67R2/CoreReference/Data/Levels/'+p.name]=p
support['M67R2/README.txt']=R/'Documentation/M67R2_Start_Here.txt'
support['M67R2/'+package.name]=package

full=D/'Heart_of_the_Rain_Unity_Project.zip'
inventory={}
with zipfile.ZipFile(full,'w',zipfile.ZIP_DEFLATED,6) as z:
 for p in sorted(U.rglob('*')):
  if p.is_file():
   relative=p.relative_to(U).as_posix();inventory[relative]=hashlib.sha256(p.read_bytes()).hexdigest();z.write(p,'Heart_of_the_Rain/Unity/'+relative)
 for name,p in sorted(support.items()):z.write(p,'Heart_of_the_Rain/'+name)
 z.write(R/'Documentation/M67R2_Start_Here.txt','Heart_of_the_Rain/START_HERE.txt')
 z.writestr('Heart_of_the_Rain/Unity_Files_SHA256.json',json.dumps(inventory,indent=2))
print('Full Unity project:',full.stat().st_size,flush=True)

review=D/'Heart_of_the_Rain_M67R2_Celebration_Review.zip'
with zipfile.ZipFile(review,'w',zipfile.ZIP_DEFLATED,6) as z:
 for name,p in sorted(support.items()):z.write(p,name)
 # All new artwork and editable runtime code are present in the unitypackage.
 # The original Daria reference is retained for identity checks, outside Unity.
 z.write(R/'Recovered/Daria’s muted olive toolmaker sprite.png','M67R2/References/Daria_Approved_Reference.png')
for archive in [full,review]:
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  assert len(z.namelist())==len(set(z.namelist()))
  assert not [f.filename for f in z.infolist() if f.file_size==0 and f.filename.endswith(('.png','.cs','.json','.wav','.mp4'))]
  assert json.loads(z.read(('Heart_of_the_Rain/' if archive==full else '')+'M67R2/Validation/Celebration_Checks.json'))['status'].startswith('PASS')
with zipfile.ZipFile(full) as z:
 for relative,h in inventory.items():assert hashlib.sha256(z.read('Heart_of_the_Rain/Unity/'+relative)).hexdigest()==h
 assert 'Heart_of_the_Rain/Unity/Packages/manifest.json' in z.namelist()
 assert 'Heart_of_the_Rain/Unity/ProjectSettings/ProjectVersion.txt' in z.namelist()
report={'status':'PASS_PACKAGES_AND_COMPLETE_PROJECT_BYTES','unity_files':len(inventory),'incremental_asset_records':len(paths),'outputs':[{'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()} for p in [full,package,review]],'UnityEditor':'NOT_RUN'}
(R/'Validation/Package_Verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
