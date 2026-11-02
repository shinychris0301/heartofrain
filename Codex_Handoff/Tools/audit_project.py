#!/usr/bin/env python3
"""Read-only source inventory. Does not import Unity or prove gameplay solvability."""
import argparse, collections, csv, hashlib, json, re
from pathlib import Path

def digest(p):
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def run(unity, out):
    out.mkdir(parents=True, exist_ok=True)
    root = unity/'Assets/HeartOfTheRain'
    def csvout(name, rows):
        if not rows: return
        with (out/name).open('w', newline='', encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f, fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    files=sorted(p for p in unity.rglob('*') if p.is_file() and not any(x in p.relative_to(unity).parts for x in ['Library','Temp','Logs','obj','.git','Builds']))
    hashes={p.relative_to(unity).as_posix():digest(p) for p in files}
    (out/'Unity_Files_SHA256.json').write_text(json.dumps(hashes, indent=2)+'\n')
    scripts=[]; menus=[]
    for p in files:
        if p.suffix!='.cs': continue
        text=p.read_text(); rel=p.relative_to(unity).as_posix()
        scripts.append(dict(path=rel,namespace='; '.join(re.findall(r'namespace\s+([\w.]+)',text)),types='; '.join(re.findall(r'\b(?:class|struct|enum|interface)\s+(\w+)',text)),lines=len(text.splitlines()),sha256=hashes[rel]))
        for menu in re.findall(r'\[MenuItem\("([^"]+)"',text): menus.append(dict(menu=menu,source=rel))
    csvout('Code_Index.csv',scripts);csvout('Editor_Menus.csv',menus)
    levels=[];obstacles=[]; issues=[]; first={}
    for p in sorted((root/'M47/Data/Levels').glob('C01_L*.json')):
        d=json.loads(p.read_text()); active={(c['x'],c['y']) for c in d['activeCells']}; occupied={}
        assert len(active)==len(d['activeCells']),p
        for x,y in active: assert 0<=x<d['columns'] and 0<=y<d['rows'],p
        for o in d['obstacles']:
            family=o['family'];first.setdefault(family,d['globalLevel'])
            fp=o.get('footprint',{'width':1,'height':1})
            for dy in range(fp['height']):
                for dx in range(fp['width']):
                    cell=(o['x']+dx,o['y']+dy)
                    assert cell in active and cell not in occupied,(p,cell)
                    occupied[cell]=family
            obstacles.append(dict(level=d['globalLevel'],instance=o.get('instanceId',''),family=family,x=o['x'],y=o['y'],hp=o['hp'],width=fp['width'],height=fp['height'],motion=o.get('motion','')))
        gems={(c['x'],c['y']) for c in d['initialTiles']}
        assert len(gems)==len(d['initialTiles']) and not gems.intersection(occupied) and gems<=active,p
        assert 2<=len(d['goals'])<=4,p
        if d['globalLevel']==50 and any('40 moves' in x for x in d.get('integrationNotes',[])):
            issues.append('L50 integrationNotes still says 40 moves; effective movesProposal is 44. Runtime value takes precedence.')
        levels.append(dict(level=d['globalLevel'],id=d['id'],name=d['name'],columns=d['columns'],rows=d['rows'],active_cells=len(active),moves=d['movesProposal'],difficulty_intent=d.get('difficultyIntent',''),target_types=len(d['goals']),goals='; '.join(f"{g['family']}:{g['count']}" for g in d['goals']),obstacle_families='; '.join(sorted({o['family'] for o in d['obstacles']})),logical_obstacles=len(d['obstacles']),obstacle_cells=len(occupied),coverage_pct=round(len(occupied)/len(active)*100,1),seed=d['tileSeed'],introduces=d.get('introduces') or '',source=p.relative_to(unity).as_posix()))
    assert [d['level'] for d in levels]==list(range(1,51))
    csvout('Chapter01_Levels.csv',levels);csvout('Obstacle_Instances.csv',obstacles)
    catalog=json.loads((root/'App/Shop/Data/ShopCatalog.json').read_text())
    offers=[]
    for o in catalog['offers']:
        offers.append({**o,'status':'PREVIEW ONLY — not store products or approved live prices'})
    csvout('Shop_Preview_Catalog.csv',offers)
    journey=json.loads((root/'App/Journey/Data/JourneyCatalog.json').read_text())
    chapters=[dict(chapter=c['number'],title=c['title'],original_title=c.get('sourceTitle',''),source_page=c.get('sourcePage',''),art_key=c['art'],planned_level_start=(c['number']-1)*50+1,planned_level_end=c['number']*50,playable_levels='1–50' if c['number']==1 else 'NOT IMPLEMENTED',planning_note='50-level range is planning convention; not proof of produced levels') for c in journey['chapters']]
    csvout('Story_Chapter_Catalog.csv',chapters)
    from PIL import Image
    art=[]
    for p in files:
        if p.suffix.lower() not in ['.png','.jpg','.jpeg']: continue
        with Image.open(p) as im: w,h=im.size;mode=im.mode
        art.append(dict(path=p.relative_to(unity).as_posix(),width=w,height=h,source_mode=mode,file_bytes=p.stat().st_size,rgba32_base_bytes_estimate=w*h*4,sha256=hashes[p.relative_to(unity).as_posix()]))
    csvout('Raster_Asset_Index.csv',art)
    scenes=re.findall(r'path: (.+)',(unity/'ProjectSettings/EditorBuildSettings.asset').read_text())
    csvout('Scene_Index.csv',[dict(order=i,path=p,exists=(unity/p).is_file()) for i,p in enumerate(scenes)])
    source_docs=[p for p in files if p.suffix.lower() in ['.txt','.md','.pdf']]
    csvout('Embedded_Documents.csv',[dict(path=p.relative_to(unity).as_posix(),bytes=p.stat().st_size,sha256=hashes[p.relative_to(unity).as_posix()]) for p in source_docs])
    guid_index={}
    for p in files:
        if p.suffix=='.meta':
            match=re.search(r'^guid: (\w+)',p.read_text(),re.M)
            if match: guid_index[match[1]]=p.relative_to(unity).as_posix()[:-5]
    bindings=[]
    for p in files:
        if p.suffix!='.asset':continue
        for line_no,line in enumerate(p.read_text().splitlines(),1):
            for guid in re.findall(r'guid: ([0-9a-f]{32})',line):
                bindings.append(dict(owner=p.relative_to(unity).as_posix(),line=line_no,guid=guid,target=guid_index.get(guid,'UNRESOLVED_OR_BUILTIN')))
    csvout('Serialized_Asset_Bindings.csv',bindings)
    csvout('Resource_Key_Index.csv',[dict(key=Path(*p.relative_to(unity).parts[p.relative_to(unity).parts.index('Resources')+1:]).with_suffix('').as_posix(),path=p.relative_to(unity).as_posix()) for p in files if 'Resources' in p.relative_to(unity).parts and p.suffix!='.meta'])
    summary=dict(status='PASS_STATIC_SOURCE_AND_LEVEL_STRUCTURE',unity_files=len(files),csharp_scripts=len(scripts),levels=len(levels),story_chapters=len(chapters),raster_images=len(art),raster_rgba32_sum_bytes=sum(a['rgba32_base_bytes_estimate'] for a in art),memory_estimate_scope='Sum of every raster source, including duplicates and review assets; NOT simultaneous residency or measured GPU/RAM use.',dimension_counts=dict(collections.Counter(f"{a['columns']}x{a['rows']}" for a in levels)),target_type_counts=dict(collections.Counter(a['target_types'] for a in levels)),obstacle_first_level=first,scene_count=len(scenes),model_source_files=[p.relative_to(unity).as_posix() for p in files if p.suffix.lower() in ['.blend','.fbx','.obj','.glb','.gltf']],notes=issues,not_tested=['Unity import and API compile','Play Mode and touch input','Android/iOS builds','Device performance','Level solvability or human difficulty'])
    (out/'Audit_Summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--unity',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();run(args.unity.resolve(),args.out.resolve())
