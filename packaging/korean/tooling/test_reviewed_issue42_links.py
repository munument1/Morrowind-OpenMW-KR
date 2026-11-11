import copy
import struct
import unittest

from repair_reviewed_issue42_links import rewrite, sha


def part(tag, value):
    return tag + struct.pack('<I', len(value)) + value


def record(tag, body):
    return part(tag, body)[:8] + b'\x12\x34\x56\x78' * 2 + body


class ReviewedLinkTests(unittest.TestCase):
    def setUp(self):
        self.body = part(b'INAM', b'42\0') + part(b'NAME', '상인이니'.encode() + b'\0') + part(b'BNAM', b'player->additem gold_001 50')
        self.dial = record(b'DIAL', part(b'NAME', '상인'.encode() + b'\0') + part(b'DATA', b'\0'))
        self.raw = self.dial + record(b'INFO', self.body) + record(b'SCPT', part(b'SCTX', b'unchanged'))
        self.top = b'\xef\xbb\xbfexisting\told\r\n'
        self.review = {'aliases': {'상인*': '상인'}, 'changes': [{'parent': '상인', 'info': '42', 'source_body_sha256': sha(self.body), 'before': '상인이니', 'after': '@상인\x7f#이니', 'targets': ['상인']}]}

    def test_only_reviewed_name_and_new_alias_change(self):
        updated, top = rewrite(self.raw, self.top, self.review)
        self.assertTrue(updated.startswith(self.dial))
        self.assertTrue(updated.endswith(record(b'SCPT', part(b'SCTX', b'unchanged'))))
        self.assertIn(part(b'BNAM', b'player->additem gold_001 50'), updated)
        self.assertTrue(top.startswith(self.top))
        self.assertIn('상인*\t상인'.encode(), top)

    def test_unknown_source_fails(self):
        with self.assertRaisesRegex(ValueError, 'source mismatch'):
            rewrite(self.raw.replace(b'gold_001', b'gold_002'), self.top, self.review)

    def test_display_change_fails(self):
        review = copy.deepcopy(self.review)
        review['changes'][0]['after'] = '@상인\x7f#이다'
        with self.assertRaisesRegex(ValueError, 'Visible text'):
            rewrite(self.raw, self.top, review)

    def test_alias_collision_fails(self):
        with self.assertRaisesRegex(ValueError, 'already exists'):
            rewrite(self.raw, self.top + '상인*\twrong\n'.encode(), self.review)

    def test_duplicate_info_and_truncated_input_fail(self):
        with self.assertRaisesRegex(ValueError, 'source mismatch'):
            rewrite(self.raw + record(b'INFO', self.body), self.top, self.review)
        with self.assertRaisesRegex(ValueError, 'Truncated'):
            rewrite(self.raw[:-1], self.top, self.review)


if __name__ == '__main__':
    unittest.main()
