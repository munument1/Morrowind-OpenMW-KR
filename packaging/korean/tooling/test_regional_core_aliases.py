import unittest
from repair_regional_core_aliases import rewrite


class CoreAliasTests(unittest.TestCase):
    def test_regional_keyword_variants_stay_available(self):
        mapping = {'caius cosades': '카이우스 코사데스'}
        raw = b'\xef\xbb\xbf' + 'Caius Cosades\t카이우스 코사데스\r\nUnique\t지역 주제\r\n'.encode()
        result, changes = rewrite(raw, 'mrk', mapping)
        self.assertEqual(result, raw)
        self.assertEqual(changes, [])

    def test_explicit_aliases_and_padding_keep_spelling_and_line_endings(self):
        raw = '카이우스***\tCaius Cosades\r\r\n별칭\tregional topic\n'.encode()
        result, changes = rewrite(raw, 'top', {'caius cosades': '카이우스 코사데스'})
        self.assertEqual(result, '카이우스***\t카이우스 코사데스\r\r\n별칭\tregional topic\n'.encode())
        self.assertEqual(len(changes), 1)
        self.assertEqual(rewrite(result, 'top', {'caius cosades': '카이우스 코사데스'}), (result, []))

    def test_adds_only_present_normal_topic_ids_and_refuses_conflict(self):
        mapping = {'talos': '탈로스', 'unloaded': '다른 주제'}
        result, changes = rewrite(b'\xef\xbb\xbf', 'top', mapping, {'talos'})
        self.assertEqual(result, b'\xef\xbb\xbf' + 'talos\t탈로스\n'.encode())
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            rewrite(b'talos\twrong\n', 'top', mapping, {'talos'})


if __name__ == '__main__':
    unittest.main()
