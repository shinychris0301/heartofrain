"""Recover the truncated M68 PNG using its supplied authoring formula/masters.

No art redesign: reproduce the export's float32 eye mask and premultiplied
round-trip. Compare every fully decoded row still present in the delivery.
"""
import hashlib
import json
import struct
import zlib
import zipfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageFile

ROOT = Path(__file__).resolve().parents[2]


def run():
    folder = ROOT/'Unity/Assets/HeartOfTheRain/M68Celebration'
    target = folder/'Mesh/Dariya_Blink_Texture.png'
    evidence = ROOT/'Verification/Evidence/Fluidity'
    original = target.read_bytes()
    expected = '6e8a9e903226502c821bb2982cf2b242'
    assert expected in target.with_suffix('.png.meta').read_text()
    record=evidence/'M68_Blink_Repair.json'
    if record.exists() and hashlib.sha256(original).hexdigest()==json.loads(record.read_text())['repaired_sha256']:
        with Image.open(target) as image:image.load()
        print('Already recovered; authored pixels and GUID retained.');return
    with zipfile.ZipFile('C:/Users/shiny/Downloads/Dariya_Celebration_M68_Complete_Assets.zip') as archive:
        delivered=archive.read('Dariya_Celebration_M68/UnityAssets/Assets/HeartOfTheRain/M68Celebration/Mesh/Dariya_Blink_Texture.png')
    assert original==delivered, 'Repair is only for the exact original truncated delivery.'
    backup=ROOT/'.verification-cache/M68_Original_Blink.png'
    backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(original)
    offset, chunks = 8, []
    while offset+8 <= len(original):
        count = struct.unpack('>I', original[offset:offset+4])[0]
        if original[offset+4:offset+8] == b'IDAT':
            chunks.append(original[offset+8:min(offset+8+count,len(original))])
        offset += count+12
    decoder = zlib.decompressobj()
    decoded = decoder.decompress(b''.join(chunks))
    assert not decoder.eof
    source = np.array(Image.open(folder/'Art/Dariya_Master.png').convert('RGBA'),np.float32)/255
    h,w = source.shape[:2]
    blink = np.array(Image.open(folder/'Art/Dariya_Blink_Source.png').convert('RGBA').resize((w,h),Image.Resampling.LANCZOS),np.float32)/255
    y,x = np.mgrid[0:h,0:w].astype(np.float32); x/=w; y/=h
    mask = np.zeros((h,w),np.float32)
    for cx,cy,rx,ry in ((.475,.249,.042,.026),(.575,.260,.044,.026)):
        d=((x-cx)/rx)**2+((y-cy)/ry)**2
        u=np.clip((d-.40)/.60,0,1)
        mask=np.maximum(mask,1-u*u*(3-2*u))
    alpha=source[:,:,3:]
    texture=source.copy()
    texture[:,:,:3]=source[:,:,:3]*(1-mask[:,:,None])+blink[:,:,:3]*mask[:,:,None]
    texture[:,:,:3]*=alpha
    texture[:,:,:3]/=np.maximum(texture[:,:,3:],1e-8)
    texture[texture[:,:,3]<.002]=0
    pixels=np.uint8(np.clip(texture,0,1)*255)
    ImageFile.LOAD_TRUNCATED_IMAGES=True
    partial=np.array(Image.open(target).convert('RGBA'))
    rows=len(decoded)//(1+w*4)
    mismatches=int(np.count_nonzero(partial[:rows]!=pixels[:rows]))
    assert mismatches==0, 'Authoring reconstruction differs from surviving pixels.'
    Image.fromarray(pixels,'RGBA').save(target)
    ImageFile.LOAD_TRUNCATED_IMAGES=False
    with Image.open(target) as image:image.load()
    report={'status':'PASS_RECOVERED_AUTHORED_PIXELS','reason':'Delivered PNG IDAT stream is truncated before its final238 rows and has no zlib end/IEND.',
            'method':'Exact supplied author_animation.py eye-mask/export arithmetic; source masters unchanged.',
            'original_sha256':hashlib.sha256(original).hexdigest(),'repaired_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'complete_original_rows_compared':rows,'surviving_channel_mismatches':mismatches,'guid_preserved':expected}
    (evidence/'M68_Blink_Repair.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':run()
