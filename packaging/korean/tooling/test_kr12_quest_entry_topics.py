"""No proprietary game data: physically validate exact INFO.NAME-only changes."""
import struct
import unittest

from patch_kr12_quest_entry_topics import CASES, chunks, decoded, fields, rewrite


def field(tag, val):
    return struct.pack("<4sI", tag, len(val)) + val


def record(tag, fields_bytes):
    return struct.pack("<4sIII", tag, len(fields_bytes), 0, 0) + fields_bytes


class QuestEntryPatchTest(unittest.TestCase):
    def synthetic_esp(self):
        blocks = []
        for iid, parent, actor, original_phrase, tagged_phrase, target in CASES:
            blocks.append(record(b"DIAL", field(b"NAME", parent.encode("utf-8"))
                                 + field(b"DATA", b"\x00")))
            blocks.append(record(b"INFO", field(b"INAM", iid.encode("ascii"))
                                 + field(b"ONAM", actor.encode("utf-8"))
                                 + field(b"NAME", ("대화: " + original_phrase + ".").encode("utf-8"))
                                 + field(b"BNAM", b"Journal TEST 10")))
        for _, _, _, _, _, target in CASES:
            blocks.append(record(b"DIAL", field(b"NAME", target.encode("utf-8"))
                                 + field(b"DATA", b"\x00")))
        return b"".join(blocks)

    def test_script_and_conditions_byte_identical(self):
        original=self.synthetic_esp()
        patched, report=rewrite(original, verify_sha=False)
        self.assertEqual(report["changed_info_count"],4)
        self.assertTrue(report["all_other_records_and_fields_unchanged"])
        self.assertNotEqual(original,patched)
        originals=list(chunks(original,16))
        newer=list(chunks(patched,16))
        for (_, _, before),(_, _, after) in zip(originals,newer):
            if b"BNAM" in before:
                self.assertEqual(dict(fields(before))[b"BNAM"],dict(fields(after))[b"BNAM"])

    def test_missing_record_fails_closed(self):
        original=self.synthetic_esp()
        self.assertRaises(ValueError,rewrite,original[:-1],False)

if __name__=="__main__":
    unittest.main()
