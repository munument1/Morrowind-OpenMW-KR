#!/usr/bin/env python3
"""Synthetic Rebirth fixtures. No Rebirth or Morrowind assets required."""
import base64
import gzip
import hashlib
import importlib.util
import json
import pathlib
import struct
import tempfile
import unittest
import zipfile
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("rbv56", HERE / "rebirth_v56_consolidate.py")
rb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rb)


def sub(tag, value):
    return tag + struct.pack("<I", len(value)) + value


def record(tag, *subs):
    body = b"".join(subs)
    return tag + struct.pack("<I", len(body)) + b"\x00" * 8 + body


def info(value=b"English\x00"):
    return record(b"INFO", sub(b"INAM", b"test-id\x00"),
                  sub(b"NAME", value), sub(b"BNAM", b'Journal "Quest" 1\x00'))


def script(value=b'MessageBox "Start"\x00', compiled=b"\x07\x08"):
    return record(b"SCPT", sub(b"SCTX", value), sub(b"SCDT", compiled))


class RebirthV56Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.original_dir = self.root / "original"
        self.original_dir.mkdir()
        self.zip_path = self.root / "rebirth-v56.zip"
        self.content = {}
        self.all_paths = (
            ["Data Files/Morrowind Rebirth [Main].ESP",
             "Alternate Version/Morrowind Rebirth [Main].ESP"]
            + [f"Data Files/Morrowind Rebirth - {x} [Addon].ESP"
               for x in ("Birthsigns", "Mercenaries", "Races", "Skills", "Tools", "Game Settings")]
            + [f"Compability Patches/Comp Patch {i}.ESP" for i in range(1, 8)]
        )
        with zipfile.ZipFile(self.zip_path, "w") as z:
            for i, path in enumerate(self.all_paths):
                base = info() + script()
                changed = (info("한글".encode() + b"\x00") + script()) if i == 0 else base
                if i == 1:
                    changed = info() + script('MessageBox "대화"'.encode() + b"\x00")
                original = self.original_dir / path
                original.parent.mkdir(parents=True, exist_ok=True)
                original.write_bytes(base)
                z.writestr("Complete Rebirth v56/" + path, changed)
                self.content[rb.canonical_path(path)] = changed
        self.sidecars = {
            "Alternate Version/Morrowind Rebirth [Main].top": b"hello\\tworld\\r\\n",
            "Data Files/Morrowind Rebirth - Mercenaries [Addon].top": b"Mercenary\\tTopic\\r\\n",
            "Data Files/Morrowind Rebirth [Main].top": b"Main\\tTopic\\r\\n",
        }
        with zipfile.ZipFile(self.zip_path, "a") as archive:
            for path, payload in self.sidecars.items():
                archive.writestr("Complete Rebirth v56/" + path, payload)

    def capture_apply(self):
        dest = self.root / "corpus"
        restored = self.root / "restored"
        with mock.patch.object(rb, "FINAL_V56_SHA256", rb.digest(self.zip_path.read_bytes())):
            rb.capture(type("Args", (), {"v56_zip": str(self.zip_path),
                                         "source_root": str(self.original_dir),
                                         "out": str(dest)})())
            with gzip.open(dest / rb.CORPUS_FILENAME, "rt", encoding="utf-8") as f:
                rows = [json.loads(x) for x in f]
            rb.apply(type("Args", (), {"corpus": str(dest),
                                       "source_root": str(self.original_dir),
                                       "out": str(restored)})())
        return dest, restored, rows

    def test_v56_fifteen_plugin_single_corpus_roundtrip(self):
        dest, restored, rows = self.capture_apply()
        self.assertEqual(len(rows), 5)
        manifest = json.loads((dest / rb.MANIFEST_FILENAME).read_text("utf-8"))
        self.assertEqual(manifest["plugin_count"], 15)
        self.assertEqual(manifest["changed_fields"], 2)
        self.assertEqual(manifest["sidecar_top_count"], 3)
        self.assertTrue(manifest["complete_binary_roundtrip"])
        self.assertFalse(manifest["kr124_game_verified"])
        self.assertEqual(sum(f["changed_fields"] for f in manifest["plugins"]), 2)
        self.assertEqual(
            sorted([r["review_flag"] for r in rows if r.get("review_flag")]), 
            ["source_only_script_requires_KR124_runtime_check"]
        )
        for path, expected in {**self.content, **self.sidecars}.items():
            self.assertEqual((restored / path).read_bytes(), expected)

    def test_reject_nontext_binary_change(self):
        base = script()
        changed = script(compiled=b"\x00\x00")
        with self.assertRaisesRegex(AssertionError, "Unexpected edited non-text"):
            rb.collect(base, changed, "Data Files/Morrowind Rebirth [Main].ESP")

    def test_reject_wrong_v56_zip_hash(self):
        with self.assertRaisesRegex(AssertionError, "Not exact v56"):
            rb.scan_final_zip(self.zip_path)

    def test_reject_unsafe_relative_path(self):
        for path in ("../escape.esp", "C:/external.esp", "/absolute.esp"):
            with self.assertRaises(ValueError):
                rb.canonical_path(path)

    def test_reject_existing_output(self):
        self.capture_apply()
        with self.assertRaisesRegex(AssertionError, "existing output"):
            rb.ensure_fresh_output(self.root / "corpus", [self.zip_path, self.original_dir])

    def test_reject_source_anchor_collision(self):
        src = info()
        translated = info("한글".encode() + b"\x00")
        rows, _ = rb.collect(src, translated, "Morrowind Rebirth [Main].ESP")
        rows.append(rows[0])
        with self.assertRaisesRegex(AssertionError, "duplicate source anchor"):
            rb.build_from_rows(src, rows, "Morrowind Rebirth [Main].ESP")


if __name__ == "__main__":
    unittest.main()
