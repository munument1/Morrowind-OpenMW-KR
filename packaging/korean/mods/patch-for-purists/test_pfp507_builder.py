#!/usr/bin/env python3
"""Synthetic structural regressions: never require or distribute game assets."""
import hashlib
import importlib.util
import pathlib
import struct
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "pfp507_builder", HERE / "pfp507_build_overwrite_kr124.py"
)
pfp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pfp)


def sub(tag, raw):
    return tag + struct.pack("<I", len(raw)) + raw


def rec(tag, body):
    return tag + struct.pack("<I", len(body)) + b"\x00" * 8 + body


class SourceAnchorTests(unittest.TestCase):
    def setUp(self):
        self.info_body = (
            sub(b"INAM", b"dlg\x00")
            + sub(b"NAME", b"Hello\x00")
            + sub(b"BNAM", b"\x01\x02")
        )
        self.info = rec(b"INFO", self.info_body)
        self.script = rec(
            b"SCPT",
            sub(b"NAME", b"myscript\x00")
            + sub(b"SCTX", b"Begin test\nEnd\x00")
            + sub(b"SCDT", b"\x05\x00\x99"),
        )
        self.source = self.info + self.script
        self.offset = 16 + len(sub(b"INAM", b"dlg\x00")) + 8
        raw = b"Hello\x00"
        self.rows = {
            self.offset: {
                "record_index": 0,
                "record_offset": 0,
                "record_size": len(self.info),
                "record_sha256": pfp.sha(self.info),
                "record_type": "INFO",
                "field_type": "NAME",
                "english_raw_sha256": pfp.sha(raw),
                "subrecord_data_size": len(raw),
                "ko": "안녕하세요",
            }
        }

    def build(self):
        with mock.patch.object(pfp, "ORIGINAL_SHA", pfp.sha(self.source)):
            return pfp.build(
                self.source, self.rows, expected_records=2, expected_fields=1
            )

    def test_translation_preserves_all_other_bytes(self):
        translated, stats = self.build()
        self.assertEqual(stats["translated_fields"], 1)
        self.assertEqual(stats["record_count"], 2)
        self.assertEqual(stats["protected_unmodified"]["INFO.BNAM"], 1)
        self.assertEqual(stats["protected_unmodified"]["SCPT.SCTX"], 1)
        self.assertEqual(stats["protected_unmodified"]["SCPT.SCDT"], 1)
        original = list(pfp.source_records(self.source, expected_records=2))
        output = list(pfp.source_records(translated, expected_records=2))
        self.assertEqual(len(original), len(output))
        for src, dst in zip(original, output):
            for a, b in zip(src[4], dst[4]):
                self.assertEqual(a[0], b[0])
                if a[1] == self.offset:
                    self.assertEqual(b[3], "안녕하세요".encode("utf-8") + b"\x00")
                else:
                    self.assertEqual(a[3], b[3])
        self.assertEqual(stats["independent_nontranslation_byte_check"], "PASS")

    def test_rejects_wrong_source_hash(self):
        with self.assertRaisesRegex(AssertionError, "Not the exact PFP"):
            pfp.build(self.source, self.rows, expected_records=2, expected_fields=1)

    def test_rejects_wrong_source_anchor(self):
        bad = dict(self.rows[self.offset])
        bad["english_raw_sha256"] = "0" * 64
        self.rows[self.offset] = bad
        with self.assertRaises(AssertionError):
            self.build()

    def test_rejects_bad_record_count_and_truncation(self):
        with self.assertRaises(AssertionError):
            list(pfp.source_records(self.source, expected_records=3))
        with self.assertRaises(AssertionError):
            list(pfp.source_records(self.source[:-1], expected_records=2))


if __name__ == "__main__":
    unittest.main()
