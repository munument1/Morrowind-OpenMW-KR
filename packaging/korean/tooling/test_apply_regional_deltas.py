#!/usr/bin/env python3
"""Offline stdlib-only regression/security tests for apply_regional_deltas.py.

No real game or mod assets are used. Files live solely in TemporaryDirectory.
If optional developer-only bsdiff4 happens to be installed, also check its
genuine generated patches. The application module never imports bsdiff4.
"""

from __future__ import annotations

import bz2
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import apply_regional_deltas as tool


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def offout(n: int) -> bytes:
    """BSDIFF40 signed sign-magnitude 64-bit integer (std lib only)."""
    positive = abs(n)
    if positive >= 1 << 63:
        raise ValueError(n)
    result = bytearray(8)
    for i in range(8):
        result[i] = positive & 0xFF
        positive >>= 8
    if n < 0:
        result[7] |= 0x80
    return bytes(result)


def build_patch(old: bytes, new: bytes) -> bytes:
    """Create an actual BSDIFF40 patch without depending on bsdiff4."""
    shared = min(len(old), len(new))
    ctrl = offout(shared) + offout(len(new) - shared) + offout(0) if new else b""
    diff = bytes((new[i] - old[i]) & 0xFF for i in range(shared))
    extra = new[shared:]
    c, d, e = bz2.compress(ctrl), bz2.compress(diff), bz2.compress(extra)
    return b"BSDIFF40" + offout(len(c)) + offout(len(d)) + offout(len(new)) + c + d + e


def custom_patch(old: bytes, new: bytes, ctrl: bytes, diff: bytes, extra: bytes) -> bytes:
    c, d, e = bz2.compress(ctrl), bz2.compress(diff), bz2.compress(extra)
    return b"BSDIFF40" + offout(len(c)) + offout(len(d)) + offout(len(new)) + c + d + e


class ApplyRegionalDeltasTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="regional-deltas-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.originals = self.root / "user-owned-originals"
        self.pkg = self.root / "patch-only"
        self.output = self.root / "new-patched-outputs"
        self.originals.mkdir()
        self.pkg.mkdir()
        self.manifest = self.pkg / "manifest.json"

    def fixture(self, old: bytes, new: bytes, *,
                source="TR_Mainland.esm",
                patch_name="patches/tr-mainland.bsdiff",
                dest="standard/TR_Mainland.esm",
                patch_data: bytes | None = None,
                expected_sha: str | None = None,
                group: str | None = None):
        data = patch_data if patch_data is not None else build_patch(old, new)
        src_file = self.originals / source
        patch_file = self.pkg / patch_name
        src_file.parent.mkdir(exist_ok=True, parents=True)
        patch_file.parent.mkdir(exist_ok=True, parents=True)
        src_file.write_bytes(old)
        patch_file.write_bytes(data)
        entry = {
            "original": {"path": source, "sha256": sha(old)},
            "patch": {"path": patch_name, "sha256": sha(data)},
            "output": {"path": dest, "sha256": expected_sha or sha(new)},
        }
        if group is not None:
            entry["group"] = group
        return entry

    def write_manifest(self, *entries):
        self.manifest.write_text(
            json.dumps({"schema_version": 1, "format": "BSDIFF40",
                        "entries": list(entries)}, indent=2),
            encoding="utf-8",
        )

    def apply(self, mode="standard"):
        return tool.apply(self.manifest, self.originals, self.output, mode=mode)

    def assert_no_outputs(self):
        if self.output.exists():
            self.assertEqual(list(self.output.rglob("*.esm")), [])
            self.assertEqual(list(self.output.rglob("*.esp")), [])
            self.assertEqual(list(self.output.rglob("*.tmp")), [])

    def test_exact_roundtrip_small_binary(self):
        old = bytes(range(256)) + b"TR English\x00metadata\xff"
        new = bytes(range(255, -1, -1)) + b"TR Korean\x00\xfe\x02"
        entry = self.fixture(old, new)
        self.write_manifest(entry)
        generated = self.apply()
        self.assertEqual(generated, [self.output / "standard/TR_Mainland.esm"])
        self.assertEqual(generated[0].read_bytes(), new)
        self.assertEqual(sha(generated[0].read_bytes()), entry["output"]["sha256"])
        self.assertEqual((self.originals / "TR_Mainland.esm").read_bytes(), old)
        with self.assertRaisesRegex(tool.DeltaError, "already exists"):
            self.apply()
        self.assertEqual(generated[0].read_bytes(), new)

    def test_real_bsdiff4_patch_if_available(self):
        try:
            import bsdiff4  # developer-only optional dependency; NOT application
        except ImportError:
            self.skipTest("bsdiff4 not installed (application still pure stdlib)")
        old = b"ABCDEF" * 100 + bytes(range(128)) + b"OMEGA"
        new = b"ABCDXY" * 83 + b"X" * 17 + bytes(range(70)) + b"FINISH"
        patch = bsdiff4.diff(old, new)
        self.assertTrue(patch.startswith(b"BSDIFF40"))
        e = self.fixture(old, new, patch_data=patch)
        self.write_manifest(e)
        self.assertEqual(self.apply()[0].read_bytes(), new)

    def test_streaming_multi_megabyte_and_negative_oldseek(self):
        old = bytes(range(251)) * 9000  # 2.25 MB; reconstruction chunk boundary
        new = old[:1500000] + b"KOREAN-REPLACEMENT" * 10000 + old[-500000:]
        self.write_manifest(self.fixture(old, new))
        self.assertEqual(sha(self.apply()[0].read_bytes()), sha(new))

        # Separate fixture for signed negative ctrl old seek (BSDIFF sign/magnitude).
        with tempfile.TemporaryDirectory(prefix="negative-oldseek-") as d:
            self.output = Path(d) / "output"
            self.pkg = Path(d) / "package"
            self.originals = Path(d) / "originals"
            self.pkg.mkdir()
            self.originals.mkdir()
            self.manifest = self.pkg / "manifest.json"
            source = b"abcdefghijklm"
            target = b"abcdefcde!!"
            first = b"".join([offout(6), offout(0), offout(-4)])
            second = b"".join([offout(3), offout(2), offout(0)])
            e = self.fixture(source, target,
                             patch_data=custom_patch(source, target, first + second,
                                                     bytes(9), b"!!"))
            self.write_manifest(e)
            self.assertEqual(self.apply()[0].read_bytes(), target)

    def test_valid_seek_only_control_triples_from_real_bsdiff4(self):
        """Real seven-master patches contain (0,0,+/-seek), sometimes twice."""
        original = b"0123456789"
        target = b"AB"
        # Seek forward to original byte '8', backward to original byte '3',
        # then add the delta against bytes '34'; no output until final triple.
        control = (offout(0) + offout(0) + offout(8) +
                   offout(0) + offout(0) + offout(-5) +
                   offout(2) + offout(0) + offout(0))
        delta = bytes([(target[i] - original[3+i]) & 255 for i in range(2)])
        entry = self.fixture(
            original, target, patch_data=custom_patch(original, target, control, delta, b"")
        )
        self.write_manifest(entry)
        self.assertEqual(self.apply()[0].read_bytes(), target)
        self.assertEqual((self.originals / entry["original"]["path"]).read_bytes(), original)

    def test_zero_seek_and_pathological_seek_only_runs_rejected(self):
        original = b"old original"
        target = b"X"
        final_triple = offout(0) + offout(1) + offout(0)
        no_op = offout(0) + offout(0) + offout(0)
        malicious_cases = (
            (no_op + final_triple, "no progress"),
            ((offout(0) + offout(0) + offout(1)) *
             (tool.MAX_CONSECUTIVE_SEEKS + 1) + final_triple,
             "excessive consecutive seek-only"),
        )
        for ctrl, error in malicious_cases:
            with self.subTest(reason=error):
                patch = custom_patch(original, target, ctrl, b"", target)
                e = self.fixture(original, target, patch_data=patch)
                self.write_manifest(e)
                with self.assertRaisesRegex(tool.DeltaError, error):
                    self.apply()
                self.assert_no_outputs()

    def test_empty_output_and_zero_length_input(self):
        e = self.fixture(b"not empty", b"")
        self.write_manifest(e)
        self.assertEqual(self.apply()[0].read_bytes(), b"")
        with tempfile.TemporaryDirectory(prefix="empty-source-") as d:
            self.output = Path(d) / "o"
            self.pkg = Path(d) / "p"
            self.originals = Path(d) / "s"
            self.pkg.mkdir()
            self.originals.mkdir()
            self.manifest = self.pkg / "manifest.json"
            e = self.fixture(b"", b"nothing existing\x00tail")
            self.write_manifest(e)
            self.assertEqual(self.apply()[0].read_bytes(), b"nothing existing\x00tail")

    def test_corrupt_patch_rejected_even_with_recomputed_patch_sha(self):
        old, new = b"source binary", b"patched Korean binary"
        valid = build_patch(old, new)
        corrupt = valid[:32] + b"BAD!" + valid[36:]
        entry = self.fixture(old, new, patch_data=corrupt)
        self.write_manifest(entry)
        with self.assertRaisesRegex(tool.DeltaError, "bz2|truncated|compressed"):
            self.apply()
        self.assert_no_outputs()
        self.assertEqual((self.originals / "TR_Mainland.esm").read_bytes(), old)

    def test_patch_hash_mismatch_and_wrong_source(self):
        old, new = b"tr original", b"tr patched"
        entry = self.fixture(old, new)
        self.write_manifest(entry)
        (self.pkg / entry["patch"]["path"]).write_bytes(b"MODIFIED" + build_patch(old, new))
        with self.assertRaisesRegex(tool.DeltaError, "Wrong or modified BSDIFF40 patch"):
            self.apply()
        self.assert_no_outputs()
        (self.pkg / entry["patch"]["path"]).write_bytes(build_patch(old, new))
        (self.originals / entry["original"]["path"]).write_bytes(b"WRONG original")
        with self.assertRaisesRegex(tool.DeltaError, "Wrong or modified user-owned original"):
            self.apply()
        self.assert_no_outputs()

    def test_wrong_final_hash_prevents_publication(self):
        old, new = b"old original", b"output new"
        e = self.fixture(old, new, expected_sha=sha(b"FORGED"))
        self.write_manifest(e)
        with self.assertRaisesRegex(tool.DeltaError, "Reconstructed output SHA256 mismatch"):
            self.apply()
        self.assert_no_outputs()

    def test_atomic_all_or_nothing_when_second_entry_is_bad(self):
        first = self.fixture(b"td source", b"td translated",
                             source="Tamriel_Data.esm",
                             patch_name="deltas/td.bsdiff",
                             dest="standard/Tamriel_Data.esm")
        second = self.fixture(b"sky source", b"sky translated",
                              source="Sky_Main.ESM",
                              patch_name="deltas/sky.bsdiff",
                              dest="standard/Sky_Main.ESM",
                              expected_sha=sha(b"WRONG"))
        self.write_manifest(first, second)
        with self.assertRaisesRegex(tool.DeltaError, "output SHA256 mismatch"):
            self.apply()
        self.assert_no_outputs()

    def test_duplicate_destination_case_insensitive(self):
        a = self.fixture(b"a", b"one", source="Cyr_Main.ESM",
                         patch_name="deltas/cyr.bsdiff", dest="standard/Cyr_Main.ESM")
        b = self.fixture(b"b", b"two", source="Sky_Main.ESM",
                         patch_name="deltas/sky.bsdiff", dest="standard/cyr_main.esm")
        self.write_manifest(a, b)
        with self.assertRaisesRegex(tool.DeltaError, "duplicate output entry"):
            self.apply()
        self.assert_no_outputs()

    def test_duplicate_source_entry_rejected(self):
        a = self.fixture(b"a", b"one")
        b = json.loads(json.dumps(a))
        b["patch"]["path"] = "patches/copy.bsdiff"
        (self.pkg / b["patch"]["path"]).write_bytes((self.pkg / a["patch"]["path"]).read_bytes())
        b["output"]["path"] = "another/TR_Mainland.esm"
        self.write_manifest(a, b)
        with self.assertRaisesRegex(tool.DeltaError, "duplicate original entry"):
            self.apply()

    def test_seven_region_masters_with_standard_and_rebirth_namespaces(self):
        masters = [
            ("TR_Mainland.esm", "deltas/tr.bsdiff", "common/TR_Mainland.esm", "common"),
            ("Tamriel_Data.esm", "deltas/td.bsdiff", "common/Tamriel_Data.esm", "common"),
            ("Cyr_Main.ESM", "deltas/cyr.bsdiff", "standard/Cyr_Main.ESM", "standard"),
            ("Sky_Main.ESM", "deltas/sky.bsdiff", "standard/Sky_Main.ESM", "standard"),
            ("TR_Factions.esp", "deltas/factions.bsdiff", "common/TR_Factions.esp", "common"),
            ("Project Cyrodiil [For Rebirth].esm", "deltas/cyr-rebirth.bsdiff",
             "rebirth/Project Cyrodiil [For Rebirth].esm", "rebirth"),
            ("Skyrim Home of the Nords [For Rebirth].esm", "deltas/sky-rebirth.bsdiff",
             "rebirth/Skyrim Home of the Nords [For Rebirth].esm", "rebirth"),
        ]
        records = []
        expected = {}
        for i, (src, patch, target, group) in enumerate(masters):
            old = ("ORIGINAL-%d\\0" % i).encode() * 32
            new = ("TRANSLATED-%d\\0" % i).encode() * 21
            records.append(self.fixture(old, new, source=src, patch_name=patch,
                                        dest=target, group=group))
            expected[target] = new
        self.write_manifest(*records)
        created = self.apply(mode="all")
        self.assertEqual(len(created), 7)
        for target, result in expected.items():
            self.assertEqual((self.output / target).read_bytes(), result)
            original_source_path = masters[list(expected).index(target)][0]
            self.assertEqual((self.originals / original_source_path).read_bytes(),
                             ("ORIGINAL-%d\\0" % list(expected).index(target)).encode() * 32)

    def test_group_selection_ignores_unselected_originals_and_patches(self):
        common = self.fixture(b"td source", b"td Korean", source="Tamriel_Data.esm",
                              patch_name="deltas/common-td.bsdiff",
                              dest="common/Tamriel_Data.esm", group="common")
        standard = self.fixture(b"cyr source", b"cyr Korean", source="Cyr_Main.ESM",
                                patch_name="deltas/standard-cyr.bsdiff",
                                dest="standard/Cyr_Main.ESM", group="standard")
        rebirth = self.fixture(b"reb source", b"reb Korean",
                               source="Project Cyrodiil [For Rebirth].esm",
                               patch_name="deltas/rebirth-cyr.bsdiff",
                               dest="rebirth/Project Cyrodiil [For Rebirth].esm",
                               group="rebirth")
        self.write_manifest(common, standard, rebirth)

        reb_src = self.originals / rebirth["original"]["path"]
        reb_patch = self.pkg / rebirth["patch"]["path"]
        reb_original_bytes, reb_patch_bytes = reb_src.read_bytes(), reb_patch.read_bytes()
        reb_src.unlink()
        reb_patch.unlink()
        self.output = self.root / "standard-only-output"
        created = self.apply(mode="standard")
        self.assertEqual({x.relative_to(self.output).as_posix() for x in created},
                         {"common/Tamriel_Data.esm", "standard/Cyr_Main.ESM"})
        self.assertFalse((self.output / "rebirth").exists())

        reb_src.write_bytes(reb_original_bytes)
        reb_patch.write_bytes(reb_patch_bytes)
        std_src = self.originals / standard["original"]["path"]
        std_patch = self.pkg / standard["patch"]["path"]
        std_original_bytes, std_patch_bytes = std_src.read_bytes(), std_patch.read_bytes()
        std_src.unlink()
        std_patch.unlink()
        self.output = self.root / "rebirth-only-output"
        created = self.apply(mode="rebirth")
        self.assertEqual({x.relative_to(self.output).as_posix() for x in created},
                         {"common/Tamriel_Data.esm",
                          "rebirth/Project Cyrodiil [For Rebirth].esm"})
        self.assertFalse((self.output / "standard").exists())

        std_src.write_bytes(std_original_bytes)
        std_patch.write_bytes(std_patch_bytes)
        self.output = self.root / "all-output"
        created = self.apply(mode="all")
        self.assertEqual(len(created), 3)

    def test_group_validation_even_in_inactive_entries(self):
        common = self.fixture(b"old", b"new", group="common")
        rebirth = self.fixture(b"reb", b"reb-translated", group="rebirth",
                               source="Project Cyrodiil [For Rebirth].esm",
                               patch_name="deltas/rebirth.bsdiff",
                               dest="rebirth/Project Cyrodiil [For Rebirth].esm")
        rebirth["original"]["path"] = "../BAD.esm"
        self.write_manifest(common, rebirth)
        with self.assertRaises(tool.DeltaError):
            self.apply(mode="standard")
        rebirth["original"]["path"] = "Project Cyrodiil [For Rebirth].esm"
        rebirth["group"] = "invalid"
        self.write_manifest(common, rebirth)
        with self.assertRaisesRegex(tool.DeltaError, "group must be"):
            self.apply(mode="standard")

    def test_mode_cli_default_standard_and_all_requires_rebirth(self):
        common = self.fixture(b"td", b"td-out", source="Tamriel_Data.esm",
                              dest="common/Tamriel_Data.esm",
                              patch_name="deltas/td.bsdiff", group="common")
        standard = self.fixture(b"std", b"std-out", source="Cyr_Main.ESM",
                                dest="standard/Cyr_Main.ESM",
                                patch_name="deltas/cyr.bsdiff", group="standard")
        rebirth = self.fixture(b"reb", b"reb-out",
                               source="Project Cyrodiil [For Rebirth].esm",
                               dest="rebirth/Project Cyrodiil [For Rebirth].esm",
                               patch_name="deltas/rebirth.bsdiff", group="rebirth")
        self.write_manifest(common, standard, rebirth)
        (self.originals / rebirth["original"]["path"]).unlink()
        self.assertEqual(tool.main([
            "--manifest", str(self.manifest),
            "--originals-dir", str(self.originals),
            "--output-dir", str(self.output),
        ]), 0)
        self.assertTrue((self.output / "standard/Cyr_Main.ESM").is_file())
        self.assertFalse((self.output / "rebirth").exists())
        self.output = self.root / "fresh-all"
        with mock.patch("sys.stderr"):
            self.assertEqual(tool.main([
                "--manifest", str(self.manifest),
                "--originals-dir", str(self.originals),
                "--output-dir", str(self.output),
                "--mode", "all",
            ]), 2)
        self.assert_no_outputs()

    def test_path_traversal_and_absolute_paths(self):
        for malicious in (
            "../outside.esm", "standard/../../outside.esm", "/tmp/outside.esm",
            "C:/Windows/System32/outside.esm", r"..\outside.esm", "foo//bar.esm",
            "standard/./file.esm", "standard/NUL.esm", "standard/foo:bar.esm",
        ):
            with self.subTest(path=malicious):
                e = self.fixture(b"original", b"patched")
                e["output"]["path"] = malicious
                self.write_manifest(e)
                with self.assertRaisesRegex(tool.DeltaError, "path|unsafe|forbidden|reserved"):
                    self.apply()
                self.assert_no_outputs()

    def test_bad_original_and_patch_relative_paths(self):
        e = self.fixture(b"source", b"patched")
        e["original"]["path"] = "../TR_Mainland.esm"
        self.write_manifest(e)
        with self.assertRaises(tool.DeltaError):
            self.apply()
        e["original"]["path"] = "TR_Mainland.esm"
        e["patch"]["path"] = "../../original.esm.bsdiff"
        self.write_manifest(e)
        with self.assertRaises(tool.DeltaError):
            self.apply()

    def test_existing_output_refused_and_preserved(self):
        e = self.fixture(b"a", b"b")
        self.write_manifest(e)
        dest = self.output / "standard/TR_Mainland.esm"
        dest.parent.mkdir(parents=True)
        dest.write_bytes(b"PREEXISTING")
        with self.assertRaisesRegex(tool.DeltaError, "target already exists"):
            self.apply()
        self.assertEqual(dest.read_bytes(), b"PREEXISTING")

    def test_atomic_link_race_refuses_overwrite(self):
        e = self.fixture(b"original", b"new output")
        self.write_manifest(e)
        final = self.output / e["output"]["path"]

        def collide(_staging, destination):
            self.assertEqual(Path(destination), final)
            final.write_bytes(b"EXTERNAL RACE")
            raise FileExistsError("competing writer")

        with mock.patch.object(tool.os, "link", side_effect=collide):
            with self.assertRaisesRegex(tool.DeltaError, "Refusing to overwrite"):
                self.apply()
        self.assertEqual(final.read_bytes(), b"EXTERNAL RACE")
        self.assertEqual(list(self.output.rglob(".regional-delta-*.tmp")), [])

    def test_commit_rollback_when_second_target_races(self):
        first = self.fixture(b"first original", b"first new",
                             source="TR_Factions.esp", patch_name="deltas/factions.bsdiff",
                             dest="standard/TR_Factions.esp")
        second = self.fixture(b"second original", b"second new",
                              source="TR_Mainland.esm", patch_name="deltas/mainland.bsdiff",
                              dest="standard/TR_Mainland.esm")
        self.write_manifest(first, second)
        real_link = os.link
        calls = 0
        target_two = self.output / second["output"]["path"]

        def link_with_race(staging, output):
            nonlocal calls
            calls += 1
            if calls == 2:
                target_two.write_bytes(b"EXTERNAL SECOND TARGET")
                raise FileExistsError("raced")
            real_link(staging, output)

        with mock.patch.object(tool.os, "link", side_effect=link_with_race):
            with self.assertRaisesRegex(tool.DeltaError, "Refusing to overwrite"):
                self.apply()
        self.assertFalse((self.output / first["output"]["path"]).exists())
        self.assertEqual(target_two.read_bytes(), b"EXTERNAL SECOND TARGET")
        self.assertFalse(list(self.output.rglob(".regional-delta-*.tmp")))

    def test_symlink_detection_mock_without_os_privileges(self):
        e = self.fixture(b"source", b"output")
        self.write_manifest(e)
        source = self.originals / e["original"]["path"]
        real_is_link = Path.is_symlink

        def simulated_symlink(p):
            return Path(p) == source or real_is_link(p)

        with mock.patch.object(Path, "is_symlink", autospec=True, side_effect=simulated_symlink):
            with self.assertRaisesRegex(tool.DeltaError, "symbolic links"):
                self.apply()
        self.assert_no_outputs()

    def test_symlink_original_and_output_parent_rejected_if_supported(self):
        e = self.fixture(b"original", b"patched")
        self.write_manifest(e)
        source = self.originals / "TR_Mainland.esm"
        outside = self.root / "external-original.esm"
        outside.write_bytes(source.read_bytes())
        source.unlink()
        try:
            source.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Cannot create symlinks on this OS")
        with self.assertRaisesRegex(tool.DeltaError, "symbolic link|escaped"):
            self.apply()
        source.unlink()
        source.write_bytes(outside.read_bytes())
        unsafe_root = self.root / "outside-output"
        unsafe_root.mkdir()
        (self.output / "standard").parent.mkdir(parents=True, exist_ok=True)
        (self.output / "standard").symlink_to(unsafe_root, target_is_directory=True)
        with self.assertRaisesRegex(tool.DeltaError, "symbolic link|escaped"):
            self.apply()
        self.assertFalse((unsafe_root / "TR_Mainland.esm").exists())

    def test_duplicated_json_keys_rejected(self):
        e = self.fixture(b"source", b"new")
        serialized = json.dumps({"schema_version": 1, "format": "BSDIFF40",
                                 "entries": [e]})
        self.manifest.write_text(serialized.replace(
            '"schema_version": 1,', '"schema_version": 1, "schema_version": 1,', 1
        ), encoding="utf8")
        with self.assertRaisesRegex(tool.DeltaError, "Duplicate JSON object key"):
            self.apply()

    def test_original_output_overlap_refused(self):
        e = self.fixture(b"a", b"b")
        self.write_manifest(e)
        with self.assertRaisesRegex(tool.DeltaError, "disjoint"):
            tool.apply(self.manifest, self.originals, self.originals)
        with self.assertRaisesRegex(tool.DeltaError, "disjoint"):
            tool.apply(self.manifest, self.originals, self.originals / "new")

    def test_invalid_sign_and_trailing_extra_compressed_data(self):
        source, new = b"original", b"changed"
        good = build_patch(source, new)
        for variant in (
            b"BADMAGIC" + good[8:],
            good[:24] + offout(-1) + good[32:],
            good + b"appended garbage",
            good[:8] + offout(1 << 40) + good[16:],
        ):
            with self.subTest(variant=variant[:32]):
                item = self.fixture(source, new, patch_data=variant)
                self.write_manifest(item)
                with self.assertRaises(tool.DeltaError):
                    self.apply()
                self.assert_no_outputs()

    def test_cli_returns_nonzero_without_writing_original(self):
        old, new = b"tr English", b"tr Korean"
        e = self.fixture(old, new)
        self.write_manifest(e)
        self.assertEqual(tool.main([
            "--manifest", str(self.manifest),
            "--originals-dir", str(self.originals),
            "--output-dir", str(self.output),
        ]), 0)
        self.assertEqual((self.originals / "TR_Mainland.esm").read_bytes(), old)
        with mock.patch("sys.stderr"):
            self.assertEqual(tool.main([
                "--manifest", str(self.manifest),
                "--originals-dir", str(self.originals),
                "--output-dir", str(self.output),
            ]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
