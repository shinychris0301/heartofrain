"""Verify the local development artifact without publishing or installing it."""
import hashlib
import json
import struct
import subprocess
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
ANDROID=Path(r'C:\Program Files\Unity\Hub\Editor\2022.3.62f3\Editor\Data\PlaybackEngines\AndroidPlayer')
APK=ROOT/'Unity/Builds/Verification/HeartOfTheRain_Development.apk'
OUT=ROOT/'Verification/Evidence/Native'


def run():
    tools=ANDROID/'SDK/build-tools/34.0.0'
    def command(args):
        result=subprocess.run([str(v) for v in args],capture_output=True,text=True,encoding='utf-8',errors='replace',check=True)
        return result.stdout.strip().splitlines()
    signature=command([ANDROID/'OpenJDK/bin/java.exe','-jar',tools/'lib/apksigner.jar','verify','--verbose',APK])
    command([tools/'zipalign.exe','-c','-v','4',APK])
    libraries=[]
    with zipfile.ZipFile(APK) as archive:
        assert archive.testzip() is None, 'APK CRC failure'
        for name in archive.namelist():
            if not (name.startswith('lib/') and name.endswith('.so')):continue
            body=archive.read(name)
            assert body[:6]==b'\x7fELF\x02\x01', 'Expected little-endian ELF64'
            offset=struct.unpack_from('<Q',body,32)[0]
            size,count=struct.unpack_from('<HH',body,54)
            loads=[]
            for i in range(count):
                kind,flags,file_offset,address,physical,file_size,memory_size,alignment=struct.unpack_from('<IIQQQQQQ',body,offset+i*size)
                if kind==1:loads.append({'offset':file_offset,'address':address,'alignment':alignment})
            assert loads and all(p['alignment']>=16384 and (p['offset']-p['address'])%16384==0 for p in loads), name
            libraries.append({'file':name,'load_segments':loads})
    result={'path':str(APK),'bytes':APK.stat().st_size,'sha256':hashlib.sha256(APK.read_bytes()).hexdigest(),
            'zipalign4KiBPass':True,'developmentSignatureVerifies':True,'signatureNotes':signature,
            'elf16KiBLoadSegmentsPass':True,'libraries':libraries,
            'scope':'Internal signed development APK, ZIP CRC/alignment and static ELF checks; not store compliance or physical-device certification.'}
    path=OUT/'APK_Artifact.json'
    if path.exists() and not (OUT/'APK_Artifact_Initial.json').exists():
        (OUT/'APK_Artifact_Initial.json').write_bytes(path.read_bytes())
    path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('signatureNotes','libraries')},indent=2))


if __name__=='__main__':run()
