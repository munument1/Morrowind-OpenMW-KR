"""Regression checks for the Roman glyphs observed missing in real MyGUI books."""
import unittest
from pathlib import Path
from package_kr11_fonts import covered, patch_font, ranges, ROMAN

ROOT=Path(__file__).resolve().parents[3]

class FontCoverage(unittest.TestCase):
    def test_active_korean_font_resources_include_roman_and_hangul(self):
        for name in ('MysticCards','DejaVuLGCSansMono','Galmuri11'):
            raw=(ROOT/'files/data/fonts'/(name+'.omwfont')).read_bytes()
            with self.subTest(font=name):
                self.assertTrue(all(covered(raw,n) for n in ROMAN))
                self.assertTrue(covered(raw,ord('가')))
                self.assertTrue(covered(raw,ord('힣')))
                self.assertIn(b'Galmuri11.ttf',raw)

    def test_update_adds_only_missing_roman_range(self):
        raw=(ROOT/'files/data/fonts/MysticCards.omwfont').read_bytes()
        old=raw.replace(b'            <Code range="8544 8575"/>\r\n',b'').replace(b'            <Code range="8544 8575"/>\n',b'')
        self.assertFalse(covered(old,0x216b))
        new=patch_font(old)
        self.assertEqual(set(ranges(new))-set(ranges(old)),{(8544,8575)})
        self.assertEqual(patch_font(new),new)

if __name__=='__main__':unittest.main()
