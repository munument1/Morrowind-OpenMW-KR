import struct
import unittest

from repair_reviewed_regional_display import append_aliases, module_for, rewrite, row_key, sha
from test_reviewed_book_text import patch as book_patch


def field(tag, value):
    return tag + struct.pack('<I', len(value)) + value


def record(tag, body):
    return field(tag, body)[:8] + bytes(8) + body


class RegionalDisplayTests(unittest.TestCase):
    def patch(self, tag='MISC', rid='key', fld='FNAM', raw=b'Key\0', target='열쇠', **extra):
        return {'record_tag': tag, 'record_id': rid, 'field': fld,
                'source_raw_sha256': sha(raw), 'target': target, **extra}

    def test_only_reviewed_name_changes(self):
        body = field(b'NAME', b'key\0') + field(b'FNAM', b'Key\0') + field(b'SCRI', b'do_not_change')
        updated, counts = rewrite(record(b'MISC', body), [self.patch()])
        self.assertIn(field(b'FNAM', '열쇠'.encode() + b'\0'), updated)
        self.assertIn(field(b'NAME', b'key\0'), updated)
        self.assertIn(field(b'SCRI', b'do_not_change'), updated)
        self.assertEqual(sum(counts.values()), 1)

    def test_copied_common_info_and_distinct_parent(self):
        raw = b''
        for parent in ('background', '배경', 'unrelated'):
            raw += record(b'DIAL', field(b'NAME', parent.encode() + b'\0'))
            raw += record(b'INFO', field(b'INAM', b'42\0') + field(b'NAME', b'Hello\0'))
        patch = self.patch('INFO', '42', 'NAME', b'Hello\0', '안녕', parent='background')
        updated, counts = rewrite(raw, [patch])
        self.assertEqual(counts[row_key(patch)], 2)
        self.assertEqual(updated.count(field(b'NAME', '안녕'.encode() + b'\0')), 2)
        self.assertEqual(updated.count(field(b'NAME', b'Hello\0')), 1)

    def test_rank_ordinal_and_fixed_width(self):
        body = field(b'NAME', b'guild\0') + field(b'RNAM', b'A\0'.ljust(32, b'\0')) + field(b'RNAM', b'B\0'.ljust(32, b'\0'))
        patch = self.patch('FACT', 'guild', 'RNAM', b'B\0'.ljust(32, b'\0'), '준회원', field_ordinal=1)
        updated, counts = rewrite(record(b'FACT', body), [patch])
        self.assertIn(field(b'RNAM', b'A\0'.ljust(32, b'\0')), updated)
        self.assertIn(field(b'RNAM', ('준회원'.encode() + b'\0').ljust(32, b'\0')), updated)
        patch['target'] = '가' * 11
        with self.assertRaisesRegex(ValueError, '32-byte'):
            rewrite(record(b'FACT', body), [patch])

    def test_unknown_input_and_duplicate_review_fail(self):
        body = field(b'NAME', b'key\0') + field(b'FNAM', b'Other\0')
        with self.assertRaisesRegex(ValueError, 'source mismatch'):
            rewrite(record(b'MISC', body), [self.patch()])
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            rewrite(record(b'MISC', body), [self.patch(), self.patch()])
        with self.assertRaisesRegex(ValueError, 'Truncated'):
            rewrite(record(b'MISC', body)[:-1], [])

    def test_rebirth_replacement_module_selection(self):
        self.assertEqual(module_for('Compability Patches/Project Cyrodiil [For Rebirth].esm'), 'Cyr_Main')
        self.assertEqual(module_for('Data Files/Sky_Main.ESM'), 'Sky_Main')
        self.assertIsNone(module_for('TR_Factions.esp'))

    def test_explicit_aliases_preserve_existing_bytes_and_fail_on_collision(self):
        raw = b'\xef\xbb\xbf' + '기존\texisting\r\r\n'.encode()
        self.assertEqual(append_aliases(raw, {'새 별칭*': 'regional topic'}), raw + '새 별칭*\tregional topic\r\n'.encode())
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            append_aliases(raw, {'기존': 'different topic'})

    def test_book_spans_apply_without_republishing_original_glyph_payload(self):
        text = b'<FONT FACE="Daedric">CODE</FONT> English prose.\0'
        body = field(b'NAME', b'book\0') + field(b'FNAM', b'Existing title\0') + field(b'TEXT', text) + field(b'SCRI', b'quest_script\0')
        patch = {'record_tag': 'BOOK', 'record_id': 'book', 'field': 'TEXT',
                 'source_raw_sha256': sha(text), 'book_patches': [book_patch(text, b'English prose.', '한국어 본문.')]}
        updated, counts = rewrite(record(b'BOOK', body), [patch])
        self.assertEqual(sum(counts.values()), 1)
        self.assertIn(field(b'TEXT', text.replace(b'English prose.', '한국어 본문.'.encode())), updated)
        self.assertIn(field(b'SCRI', b'quest_script\0'), updated)


if __name__ == '__main__':
    unittest.main()
