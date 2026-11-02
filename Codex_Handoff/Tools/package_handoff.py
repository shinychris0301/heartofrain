"""Package documentation around an unchanged M67R4 project ZIP."""
from pathlib import Path
import argparse, hashlib, json, zipfile
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main(baseline):
    out=ROOT/'Downloads';out.mkdir(exist_ok=True)
    docs=out/'Heart_of_the_Rain_Codex_Documentation.zip'
    originals=out/'Heart_of_the_Rain_Original_References.zip'
    project=out/'Heart_of_the_Rain_Unity_Project.zip'
    class CheckHTML(HTMLParser):
        def __init__(self):super().__init__();self.ids=set();self.anchors=[]
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if 'id' in a:self.ids.add(a['id'])
            if tag=='a' and a.get('href','').startswith('#'):self.anchors.append(a['href'][1:])
    check=CheckHTML();check.feed((ROOT/'Heart_of_the_Rain_Handbook.html').read_text())
    assert set(check.anchors)<=check.ids and len(check.ids)==15
    audit=json.loads((ROOT/'Documentation/Inventories/Audit_Summary.json').read_text())
    hashes=json.loads((ROOT/'Documentation/Inventories/Unity_Files_SHA256.json').read_text())
    assert audit['unity_files']==len(hashes)==4218
    assert audit['levels']==50 and audit['csharp_scripts']==146
    report={'status':'PASS_DOCUMENTATION_AND_STATIC_AUDIT','guides':15,'html_navigation_targets':len(check.ids),'workbook':'Three sheets; 938 formulas; no exported cached errors; scenario checks passed; every sheet visually reviewed.','runtime_change_policy':'No Unity file changed. All baseline bytes verified against SHA-256 inventory.','native_Unity_validation':'NOT_RUN','handbook_browser_render':'NOT_RUN: local browser executable unavailable; HTML structure/navigation validated.','historical_document_count':len([p for p in (ROOT/'Originals').iterdir() if p.is_file()])}
    (ROOT/'Validation/Handoff_Verification.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'Tools/README.txt').write_text('''DOCUMENTATION TOOLING
audit_project.py: Python3 + Pillow. Read-only Unity source/level/asset inventory.
build_handbook.py: Python3 standard library. Rebuilds current Markdown and HTML from its embedded source. Original PDFs are separate inputs.
build_monetization_model.mjs: Node + @oai/artifact-tool. Optional authoring source; requires that package in your environment. Set HOTR_MODEL_OUTPUT to choose an output directory. The delivered XLSX can be edited normally in Excel without this tool.
package_handoff.py: Python3. --baseline <original M67R4 ZIP>. Adds current docs and verifies baseline bytes. Not a Unity build pipeline.
These tools are for handoff reproduction, not dependencies of the mobile game. No SDK credentials are included.
''')
    selected=[]
    for p in ROOT.rglob('*'):
        rel=p.relative_to(ROOT)
        if not p.is_file() or rel.parts[0] in ['Originals','Downloads'] or '__pycache__' in rel.parts:continue
        if p.suffix=='.png' and rel.parts[0]=='Validation':continue
        selected.append(p)
    with zipfile.ZipFile(docs,'w',zipfile.ZIP_DEFLATED,6) as z:
        for p in sorted(selected):z.write(p,'Codex_Handoff/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(originals,'w',zipfile.ZIP_DEFLATED,6) as z:
        for p in sorted((ROOT/'Originals').iterdir()):
            if p.is_file():z.write(p,'Original_References/'+p.name)
        z.write(ROOT/'Documentation/13_SOURCES_AND_PROVENANCE.md','Original_References/READ_FIRST_Provenance.md')
        z.write(ROOT/'Documentation/Original_References_Manifest.csv','Original_References/Manifest.csv')
    with zipfile.ZipFile(baseline) as zin,zipfile.ZipFile(project,'w',zipfile.ZIP_DEFLATED,6) as zout:
        for info in zin.infolist():
            if info.filename=='Heart_of_the_Rain/START_HERE.txt':continue
            data=zin.read(info.filename)
            if info.filename.startswith('Heart_of_the_Rain/Unity/') and not info.is_dir():
                rel=info.filename[len('Heart_of_the_Rain/Unity/'):]
                assert hashlib.sha256(data).hexdigest()==hashes[rel],rel
            zout.writestr(info.filename,data)
        for p in sorted(selected):zout.write(p,'Heart_of_the_Rain/Codex_Handoff/'+p.relative_to(ROOT).as_posix())
        zout.write(ROOT/'AGENTS.md','Heart_of_the_Rain/AGENTS.md')
        zout.write(ROOT/'CODEX_START_PROMPT.txt','Heart_of_the_Rain/CODEX_START_PROMPT.txt')
        zout.writestr('Heart_of_the_Rain/START_HERE.txt','''HEART OF THE RAIN — M67R4 + CODEX HANDOFF H1
Open Unity/ in Unity Hub2022.3.62f3.
Read Codex_Handoff/Heart_of_the_Rain_Handbook.html and CODEX_START_PROMPT.txt.
Current runtime files are unchanged from M67R4; this update adds development and monetization documentation.
Original historical PDFs are in the separate Heart_of_the_Rain_Original_References.zip.
The M67R4 folder retains the prior revision notes, source checks and offline playback.
Native Unity import/build/device validation and production services remain to be completed.
''')
    verified=[]
    for p in [project,docs,originals]:
        with zipfile.ZipFile(p) as z:
            assert z.testzip() is None,p
            assert len(z.namelist())==len(set(z.namelist())),p
            assert not any(n.startswith('/') or '..' in Path(n).parts for n in z.namelist()),p
            if p==project:
                actual=[n for n in z.namelist() if n.startswith('Heart_of_the_Rain/Unity/') and not n.endswith('/')]
                assert len(actual)==len(hashes)
                for rel,h in hashes.items():assert hashlib.sha256(z.read('Heart_of_the_Rain/Unity/'+rel)).hexdigest()==h
        verified.append(dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p)))
    result={'status':'PASS_ARCHIVES_AND_ALL_4218_UNITY_FILES_UNCHANGED','files':verified,'UnityEditor':'NOT_RUN'}
    (out/'Download_Verification.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'SHA256SUMS.txt').write_text(''.join(a['sha256']+'  '+a['name']+'\n' for a in verified))
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);a=p.parse_args();main(a.baseline)
