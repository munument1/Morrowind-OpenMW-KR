import hashlib
import unittest
from repair_reviewed_book_text import rewrite


def patch(raw, old, target):
    start = raw.index(old)
    return {'start': start, 'end': start + len(old), 'source_sha256': hashlib.sha256(old).hexdigest(), 'target': target}


class ReviewedBookTextTest(unittest.TestCase):
    def test_markup_glyphs_images_and_original_line_breaks_preserved(self):
        source = b'<FONT FACE="Daedric">CODE\r\n<FONT COLOR="red">GLYPHS</FONT></FONT><BR>\r\nReport ends.<IMG SRC="book.dds">\0'
        change = patch(source, b'Report ends.', '보고서는 여기서 끝난다.')
        self.assertEqual(rewrite(source, [change]), source.replace(b'Report ends.', change['target'].encode()))
        for protected in (b'CODE', b'GLYPHS', b'book.dds'):
            with self.assertRaisesRegex(ValueError, 'markup or a Daedric'):
                rewrite(source, [patch(source, protected, '바꾸면 안 됨')])

    def test_overlaps_source_drift_and_layout_changes_fail(self):
        source = b'Two\r\nlines\0'
        change = patch(source, b'Two\r\nlines', '두\r\n줄')
        self.assertEqual(rewrite(source, [change]), '두\r\n줄\0'.encode())
        with self.assertRaisesRegex(ValueError, 'Overlapping'):
            rewrite(source, [change, change])
        change['target'] = '한 줄'
        with self.assertRaisesRegex(ValueError, 'line breaks'):
            rewrite(source, [change])
        change['source_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'source hash'):
            rewrite(source, [change])

    def test_legacy_non_utf8_bytes_cannot_create_a_mixed_encoding_field(self):
        source = b'<FONT FACE="Daedric">\xff</FONT>English\0'
        with self.assertRaisesRegex(ValueError, 'complete UTF-8'):
            rewrite(source, [patch(source, b'English', '한국어')])


if __name__ == '__main__':
    unittest.main()
