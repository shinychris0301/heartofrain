"""Read-only 50-level preview input audit; overlays apply only to a new candidate."""
import hashlib
import json
import re
import struct
import uuid
import zlib
from pathlib import Path

PITCH=64; PAD=15


def need(ok, code):
    if not ok: raise ValueError(code)


def digest(data): return hashlib.sha256(data).hexdigest()


def sha(path): return digest(path.read_bytes())


def _plain(path):
    for item in (path,*path.parents):
        if item.exists():need(not item.is_symlink() and not getattr(item.stat(),'st_file_attributes',0)&0x400,'PreviewLinkedPathRejected')
    need(path.is_file() and path.stat().st_nlink==1,'PreviewSourceFileRequired')
    return path


def _section(text,name):
    match=re.search(r'(?m)^  '+re.escape(name)+r':\r?\n((?:  - [^\r\n]+\r?\n){50})',text)
    need(match is not None,'BoardAssetSectionInvalid')
    return match,match.group(1).splitlines()


def _guid(meta):
    values=re.findall(rb'(?m)^guid:\s*([0-9a-f]{32})\s*$',meta)
    need(len(values)==1,'SourceMetaGuidInvalid')
    return values[0].decode('ascii')


def _png_alpha(raw, cols, rows, active):
    need(raw[:8]==b'\x89PNG\r\n\x1a\n','PreviewPngInvalid')
    offset=8; data=[];ihdr=None;ended=False
    while offset<len(raw):
        need(offset+12<=len(raw),'PreviewPngInvalid')
        size=struct.unpack_from('>I',raw,offset)[0];kind=raw[offset+4:offset+8];end=offset+12+size
        need(end<=len(raw),'PreviewPngInvalid')
        payload=raw[offset+8:offset+8+size]
        need((zlib.crc32(kind+payload)&0xffffffff)==struct.unpack_from('>I',raw,offset+8+size)[0],'PreviewPngCrcInvalid')
        if kind==b'IHDR': need(ihdr is None and offset==8 and len(payload)==13,'PreviewPngInvalid');ihdr=struct.unpack('>IIBBBBB',payload)
        elif kind==b'IDAT':data.append(payload)
        elif kind==b'IEND': need(size==0,'PreviewPngInvalid');ended=True;offset=end;break
        offset=end
    need(ended and offset==len(raw) and ihdr==(cols*PITCH+2*PAD,rows*PITCH+2*PAD,8,6,0,0,0) and data,'PreviewPngShapeInvalid')
    if active is None:return
    width,height=ihdr[:2];stride=width*4;expected=(stride+1)*height
    stream=zlib.decompressobj();decoded=stream.decompress(b''.join(data),expected+1)
    need(len(decoded)==expected and stream.eof and not stream.unused_data,'PreviewPngDataInvalid')
    previous=bytearray(width); checks=0
    for y in range(height):
        start=y*(stride+1);kind=decoded[start];need(kind<5,'PreviewPngFilterInvalid')
        alpha=bytearray(decoded[start+4:start+1+stride:4])
        if kind==1:
            for x in range(1,width):alpha[x]=(alpha[x]+alpha[x-1])&255
        elif kind==2:
            for x in range(width):alpha[x]=(alpha[x]+previous[x])&255
        elif kind in (3,4):
            for x in range(width):
                a=alpha[x-1] if x else 0;b=previous[x];c=previous[x-1] if x else 0
                if kind==3: value=(a+b)//2
                else:
                    pred=a+b-c;pa=abs(pred-a);pb=abs(pred-b);pc=abs(pred-c)
                    value=a if pa<=pb and pa<=pc else b if pb<=pc else c
                alpha[x]=(alpha[x]+value)&255
        if y>=PAD+PITCH//2 and (y-PAD-PITCH//2)%PITCH==0:
            gy=rows-1-(y-PAD-PITCH//2)//PITCH
            if 0<=gy<rows:
                for x in range(cols):
                    opacity=alpha[PAD+x*PITCH+PITCH//2]
                    need((opacity==255)==((x,gy) in active),'PreviewMaskCenterMismatch');checks+=1
        previous=alpha
    need(checks==cols*rows,'PreviewMaskCenterCountInvalid')


def inspect(root):
    """Return candidate-only overrides/additions; read-only against all inputs."""
    root=Path(root).resolve(); manifest_path=_plain(root/'.verification-cache/Review117/CampaignRepaired117/Report.json')
    manifest_raw=manifest_path.read_bytes();manifest=json.loads(manifest_raw);items=manifest.get('levels')
    need(type(items) is list and len(items)==50 and [v.get('level') for v in items]==list(range(1,51)) and manifest.get('growthOptInLevels')==[27,44],'PreviewManifestInvalid')
    board_path='Assets/HeartOfTheRain/M48/M48Chapter01Boards.asset';board=_plain(root/'Unity'/board_path).read_bytes();text=board.decode('utf-8')
    level_match,level_lines=_section(text,'levels');surface_match,surface_lines=_section(text,'surfaceResources');mask_match,mask_lines=_section(text,'maskResources')
    legacy_dir=root/'Unity/Assets/HeartOfTheRain/Resources/HOTR_LegacyLevels117'
    legacy=json.loads(_plain(legacy_dir/'Graphics.json').read_text(encoding='utf-8-sig')).get('entries')
    need(type(legacy) is list and len(legacy)==50,'LegacyGraphicsInvalid')
    overrides={};extras={};bindings=[];counts={9:0,10:0,11:0}
    for i,item in enumerate(items):
        n=i+1;name=f'C01_L{n:03}';cols=item.get('columns');rows=item.get('rows')
        need(type(cols) is int and cols in counts and type(rows) is int and rows==9,'PreviewDimensionsInvalid');counts[cols]+=1
        old=legacy[i];need(old.get('level')==n,'LegacyGraphicsInvalid')
        old_level=legacy_dir/(name+'.json');active_level='Assets/HeartOfTheRain/M47/Data/Levels/'+name+'.json'
        active_raw=_plain(root/'Unity'/active_level).read_bytes();old_raw=_plain(old_level).read_bytes()
        need(digest(active_raw)==digest(old_raw)==old.get('config'),'OriginalLevelIdentityChanged')
        expected_guid=_guid(_plain(root/'Unity'/(active_level+'.meta')).read_bytes())
        found=re.fullmatch(r'  - \{fileID: 4900000, guid: ([0-9a-f]{32}), type: 3\}',level_lines[i])
        need(found is not None and found.group(1)==expected_guid,'LevelGuidBindingMismatch')
        source_level=root/'.verification-cache/Review117/CampaignRepaired117/Levels'/(name+'.json')
        source_art=root/'.verification-cache/Review117/CampaignRepaired117/Art'
        surface_path=source_art/(name+'_Surface.png');mask_path=source_art/(name+'_AlphaMask.png')
        arts=item.get('art');need(type(arts) is list and len(arts)==2 and all(type(v) is dict for v in arts),'PreviewSourcePathMismatch')
        need(Path(arts[0].get('path',''))==surface_path and Path(arts[1].get('path',''))==mask_path,'PreviewSourcePathMismatch')
        level_raw=_plain(source_level).read_bytes();surface_raw=_plain(surface_path).read_bytes();mask_raw=_plain(mask_path).read_bytes()
        need(digest(level_raw)==item.get('levelSHA256') and digest(surface_raw)==arts[0].get('sha256') and digest(mask_raw)==arts[1].get('sha256'),'PreviewSourceHashMismatch')
        level=json.loads(level_raw.decode('utf-8-sig'))
        need(level.get('id')==name and level.get('globalLevel')==n and level.get('columns')==cols and level.get('rows')==rows,'PreviewLevelInvalid')
        active={(c['x'],c['y']) for c in level['activeCells']};need(len(active)==len(level['activeCells']) and all(type(x) is int and type(y) is int and 0<=x<cols and 0<=y<rows for x,y in active),'PreviewMaskCellsInvalid')
        _png_alpha(surface_raw,cols,rows,None);_png_alpha(mask_raw,cols,rows,active)
        for key,lines,raw,sha_key in [('surface',surface_lines,surface_raw,'surfaceSHA256'),('mask',mask_lines,mask_raw,'maskSHA256')]:
            old_key=old.get(key);need(re.fullmatch(r'M48Textures/[0-9a-f]{32}',old_key or '') is not None and lines[i]=='  - '+old_key,'OriginalResourceBindingMismatch')
            original='Assets/HeartOfTheRain/M48/Resources/'+old_key+'.png';orig_raw=_plain(root/'Unity'/original).read_bytes()
            need(digest(orig_raw)==old[sha_key],'LegacyResourceHashMismatch')
            if digest(orig_raw)!=digest(raw):
                variant='_Surface' if key=='surface' else '_AlphaMask';resource='M48Preview117/'+name+variant
                destination='Assets/HeartOfTheRain/M48/Resources/'+resource+'.png';need(destination not in extras,'PreviewResourceCollision')
                meta=_plain(root/'Unity'/(original+'.meta')).read_bytes();old_guid=_guid(meta)
                new_guid=uuid.uuid5(uuid.NAMESPACE_URL,'heart-rain-preview117/'+destination).hex
                replaced=meta.replace(('guid: '+old_guid).encode(),('guid: '+new_guid).encode(),1);need(_guid(replaced)==new_guid,'PreviewMetaGuidInvalid')
                extras[destination]=raw;extras[destination+'.meta']=replaced;lines[i]='  - '+resource
        if digest(active_raw)!=digest(level_raw):overrides[active_level]=level_raw
        bindings.append({'level':n,'columns':cols,'rows':rows,'levelSHA256':digest(level_raw),'surfaceSHA256':digest(surface_raw),'maskSHA256':digest(mask_raw),'levelGuid':expected_guid,'surfaceResource':surface_lines[i].removeprefix('  - '),'maskResource':mask_lines[i].removeprefix('  - ')})
    need(counts=={9:30,10:10,11:10},'PreviewWidthDistributionChanged')
    # Apply edits from later to earlier positions to preserve exact offsets.
    sections=[(surface_match,surface_lines),(mask_match,mask_lines)]
    for match,lines in sorted(sections,key=lambda item:item[0].start(1),reverse=True):
        nl='\r\n' if '\r\n' in match.group(1) else '\n'
        text=text[:match.start(1)]+nl.join(lines)+nl+text[match.end(1):]
    overrides[board_path]=text.encode('utf-8')
    return {'manifestSHA256':digest(manifest_raw),'legacyGraphicsSHA256':sha(legacy_dir/'Graphics.json'),'widthCounts':counts,'bindings':bindings,'overrides':overrides,'extras':extras,'scope':'Read-only source inspection and PNG cell-center check; no Unity, player, device, balance or performance acceptance.'}
