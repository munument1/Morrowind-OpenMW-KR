"""Offline regressions for issue #42 English master evidence reader.

All fixtures are synthetic; no copyrighted game data is uploaded.
"""
import tempfile
import struct
import unittest
from pathlib import Path

from audit_issue42_original_masters import (
    parse_original_masters, literal_english, topic_mapping,
)


def sub(tag, text):
    if isinstance(text, str):
        text = text.encode('cp1252')
    return struct.pack('<4sI', tag.encode(), len(text)) + text


def rec(tag, *fld):
    payload = b''.join(fld)
    return struct.pack('<4sI8s', tag.encode(), len(payload), b'\0' * 8) + payload


class Issue42OriginalMasterTests(unittest.TestCase):
    def test_real_structural_english_records_and_addtopic(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'Morrowind.esm'
            p.write_bytes(
                rec('DIAL', sub('NAME', 'lockpick'), sub('DATA', bytes([0]))) +
                rec('INFO', sub('INAM', '123'), sub('NAME', 'Ask about lockpick.'),
                    sub('BNAM', 'AddTopic "secret route"'), sub('SCVR', b'cond')) +
                rec('SCPT', sub('SCTX', 'AddTopic "lockpick"'))
            )
            info, topics, refs, sha = parse_original_masters([p])
            self.assertEqual(info['123']['english_parent'], 'lockpick')
            self.assertTrue(info['123']['SCVR_present'])
            self.assertIn('lockpick', topics)
            self.assertEqual(len(refs['lockpick']), 1)
            self.assertEqual(len(refs['secret route']), 1)
            votes = topic_mapping(
                [{'info': '123', 'kind': 0, 'parent': '자물쇠 따개'}], info
            )
            self.assertEqual(votes['자물쇠 따개']['english_topic'], 'lockpick')
            self.assertTrue(literal_english(info['123']['english_text'], 'lockpick'))

    def test_no_compound_false_english(self):
        self.assertFalse(literal_english('Ask about lockpicks', 'lockpick'))
        self.assertTrue(literal_english('@lockpick# works', 'lockpick'))
        self.assertFalse(literal_english('No such word', 'lockpick'))

    def test_mapping_conflict_must_be_ambiguous(self):
        en = {
            '1': {'english_parent': 'castle', 'kind': 0},
            '2': {'english_parent': 'keep', 'kind': 0},
        }
        votes = topic_mapping([
            {'info': '1', 'kind': 0, 'parent': '성'},
            {'info': '2', 'kind': 0, 'parent': '성'},
        ], en)
        self.assertIsNone(votes['성']['english_topic'])


if __name__ == '__main__':
    unittest.main()
