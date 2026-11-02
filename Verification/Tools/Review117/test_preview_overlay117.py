"""Read-only preview fixture and malformed-PNG checks; no Unity or device."""
import importlib.util
import struct
import unittest
import zlib
from pathlib import Path

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('preview_overlay117',HERE/'preview_overlay117.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


def chunk(kind,payload): return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',zlib.crc32(kind+payload)&0xffffffff)
def sample_mask(set_pixel):
    size=9*64+30;row=bytearray(size*4);data=[]
    for y in range(size):
        line=bytearray(row)
        if y==15+8*64+32 and set_pixel:line[(15+32)*4+3]=255
        data.append(b'\x00'+line)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(data)))+chunk(b'IEND',b'')

class PreviewOverlayTests(unittest.TestCase):
    def test_all_50_bindings_and_originals_are_checked_read_only(self):
        value=mod.inspect(ROOT)
        self.assertEqual(len(value['bindings']),50);self.assertEqual(value['widthCounts'],{9:30,10:10,11:10})
        self.assertEqual((len(value['overrides']),len(value['extras'])),(50,160))
        self.assertTrue(all('Assets/HeartOfTheRain/M47/Data/Levels/C01_L'+str(n).zfill(3)+'.json' in value['overrides'] for n in range(1,10)))
        self.assertNotIn('Assets/HeartOfTheRain/M47/Data/Levels/C01_L010.json',value['overrides'])
        self.assertFalse(any('HOTR_LegacyLevels117' in p or '/M48Textures/' in p for p in value['overrides']))
        generated=[mod._guid(v) for k,v in value['extras'].items() if k.endswith('.meta')]
        self.assertEqual(len(set(generated)),80)
        old={mod._guid(p.read_bytes()) for p in (ROOT/'Unity/Assets').rglob('*.meta')}
        self.assertFalse(set(generated)&old)
    def test_mask_centers_and_crc_are_enforced(self):
        mod._png_alpha(sample_mask(True),9,9,{(0,0)})
        with self.assertRaisesRegex(ValueError,'PreviewMaskCenterMismatch'):mod._png_alpha(sample_mask(False),9,9,{(0,0)})
        raw=bytearray(sample_mask(True));raw[45]^=1
        with self.assertRaises(ValueError):mod._png_alpha(bytes(raw),9,9,{(0,0)})

if __name__=='__main__': unittest.main()
