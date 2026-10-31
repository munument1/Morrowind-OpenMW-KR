"""Exact-replacement tests for malformed KR12.3.1 INFO.NAME hyperlinks."""
import struct
import unittest

from patch_issue42_explicit_markup import (
    REPLACEMENTS, REQUIRED_TOP_TARGETS, plain, rewrite,
)
from patch_kr12_quest_entry_topics import chunks, fields


def item(kind, subfields):
    body = b"".join(struct.pack("<4sI", tag, len(data)) + data
                    for tag, data in subfields)
    return struct.pack("<4sI8s", kind, len(body), b"\0"*8) + body


def source():
    dial1 = item(b"DIAL", [(b"NAME", "설원곰".encode()), (b"DATA", b"\0")])
    dial2 = item(b"DIAL", [(b"NAME", "설원늑대".encode()), (b"DATA", b"\0")])
    text = ("정@말# @설원#곰과 @설원#늑대 @말입니까?# "
            "@이나 다른# 건가? @그대로# 두시오.")
    info = item(b"INFO", [(b"INAM", b"issue42-test"), (b"ONAM", b"actor-test"),
                          (b"NAME", text.encode() + b"\0"),
                          (b"BNAM", b"AddItem something\0")])
    other = item(b"GMST", [(b"NAME", b"unchanged-field"), (b"STRV", b"unchanged")])
    return dial1 + dial2 + info + other, text


def sidecar():
    return (b"\xef\xbb\xbf" + "".join(
        f"{label}\t{target}\r\n" for label, target in REQUIRED_TOP_TARGETS.items()
    ).encode())


class ExplicitMarkupTest(unittest.TestCase):
    def test_five_strict_replacements_no_other_record_changes(self):
        original, text = source()
        expected = {old: (new, 1) for old,(new,_) in REPLACEMENTS.items()}
        patched, evidence = rewrite(original, sidecar(), expected, verify_source=False)
        self.assertEqual(evidence["total_replacements"], 5)
        self.assertEqual(evidence["changed_INFO_NAME_count"], 1)
        self.assertTrue(evidence["all_visible_text_unchanged"])
        self.assertTrue(evidence["all_other_records_and_subfields_byte_identical"])
        self.assertEqual(len(list(chunks(patched, 16))), 4)
        orig = list(chunks(original, 16))
        changed = list(chunks(patched, 16))
        self.assertEqual(orig[0], changed[0])
        self.assertEqual(orig[1], changed[1])
        self.assertEqual(orig[3], changed[3])
        old_fields = dict(fields(orig[2][2]))
        new_fields = dict(fields(changed[2][2]))
        self.assertEqual(old_fields[b"BNAM"], new_fields[b"BNAM"])
        after = new_fields[b"NAME"].rstrip(b"\0").decode()
        self.assertEqual(plain(text), plain(after))
        self.assertIn("@설원곰#", after)
        self.assertIn("@설원늑대#", after)
        self.assertIn("정말", after)
        self.assertIn("말입니까?", after)
        self.assertIn("이나 다른", after)
        self.assertIn("@그대로#", after)
        self.assertNotIn("@설원#곰", after)

    def test_exact_count_prevents_silent_drift(self):
        old, _ = source()
        with self.assertRaises(ValueError):
            rewrite(old, sidecar(), verify_source=False)

    def test_wrong_alias_source_fails_closed(self):
        original, _ = source()
        wrong = sidecar().replace(b"\t" + "눈".encode(),
                                  b"\t" + "다른".encode(), 1)
        with self.assertRaises(ValueError):
            rewrite(original, wrong,
                    {old:(new,1) for old,(new,_) in REPLACEMENTS.items()},
                    verify_source=False)

    def test_unknown_dial_fails_closed(self):
        old, _ = source()
        bad = old.replace("설원늑대".encode(), "늑대들은".encode(), 1)
        with self.assertRaises(ValueError):
            rewrite(bad, sidecar(),
                    {old:(new,1) for old,(new,_) in REPLACEMENTS.items()},
                    verify_source=False)


if __name__ == "__main__":
    unittest.main()
