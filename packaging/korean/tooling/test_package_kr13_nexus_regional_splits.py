#!/usr/bin/env python3
"""Self-contained integrity/negative tests for 5 private regional Nexus splits."""

from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import package_kr13_nexus_regional_splits as subject


class NexusRegionalSplitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contents, cls.source_manifest = subject.load_original_source()

    def test_original_combined_bundle_exact(self):
        self.assertEqual(subject.file_sha(subject.SOURCE), subject.EXPECTED_SOURCE_SHA256)
        self.assertEqual(len(self.contents), 35)
        self.assertEqual(len(self.source_manifest["entries"]), 7)
        self.assertEqual(len(subject.patch_names()), 7)
        sidecars = {name for name in self.contents if name.startswith("sidecars/")}
        self.assertEqual(len(sidecars), 24)
        self.assertEqual({e["group"] for e in self.source_manifest["entries"]},
                         {"common", "standard", "rebirth"})

    def test_five_main_manifests_select_only_owned_patch(self):
        expected_counts = (1, 1, 1, 1, 2)
        for spec, count in zip(subject.SPECS, expected_counts):
            with self.subTest(asset=spec["name"]):
                files = subject.member_map(spec, self.contents, self.source_manifest)
                manifest = json.loads(files["manifest.json"])
                self.assertEqual(manifest["format"], "BSDIFF40")
                self.assertEqual(len(manifest["entries"]), count)
                self.assertEqual(
                    {x["original"]["path"] for x in manifest["entries"]},
                    set(spec["main"]),
                )
                self.assertEqual(
                    {x["group"] for x in manifest["entries"]},
                    {spec["group"]},
                )
                self.assertEqual(
                    {x["patch"]["path"] for x in manifest["entries"]},
                    set(spec["patches"]) if not spec["optional_manifests"] else
                    {x for x in spec["patches"] if x in {
                        e["patch"]["path"] for e in manifest["entries"]}},
                )

    def test_tr_factions_is_optional_not_in_main(self):
        spec = subject.SPECS[0]
        files = subject.member_map(spec, self.contents, self.source_manifest)
        main = json.loads(files["manifest.json"])["entries"]
        extra = json.loads(files["manifest-factions.json"])["entries"]
        self.assertEqual([r["original"]["path"] for r in main], ["TR_Mainland.esm"])
        self.assertEqual([r["original"]["path"] for r in extra], ["TR_Factions.esp"])
        self.assertEqual(extra[0]["output"]["path"], "TR_Factions/TR_Factions.esp")
        self.assertEqual(len([x for x in files if x.endswith(".bsdiff")]), 2)

    def test_rebirth_has_two_main_and_independent_optional_manifest_files(self):
        spec = subject.SPECS[4]
        files = subject.member_map(spec, self.contents, self.source_manifest)
        main = json.loads(files["manifest.json"])["entries"]
        cyr = json.loads(files["manifest-cyrodiil.json"])["entries"]
        sky = json.loads(files["manifest-skyrim.json"])["entries"]
        self.assertEqual(len(main), 2)
        self.assertEqual(len(cyr), len(sky), 1)
        self.assertEqual(
            [e["original"]["path"] for e in cyr],
            ["Project Cyrodiil [For Rebirth].esm"],
        )
        self.assertEqual(
            [e["original"]["path"] for e in sky],
            ["Skyrim Home of the Nords [For Rebirth].esm"],
        )
        self.assertEqual({e["group"] for e in (*main, *cyr, *sky)}, {"rebirth"})

    def test_exact_source_patches_sidecars_and_applier_per_split(self):
        for spec in subject.SPECS:
            with self.subTest(asset=spec["name"]):
                files = subject.member_map(spec, self.contents, self.source_manifest)
                to_copy = (*spec["patches"], *subject.associated_sidecars(spec),
                           subject.APP)
                for name in to_copy:
                    self.assertIn(name, files)
                    self.assertEqual(files[name], self.contents[name])
                    self.assertEqual(subject.sha(files[name]), subject.sha(self.contents[name]))
                self.assertEqual(
                    {n for n in files if n.startswith("sidecars/")},
                    set(subject.associated_sidecars(spec)),
                )
                self.assertFalse(
                    {Path(n).suffix.lower() for n in files} & subject.FORBIDDEN_SUFFIXES
                )

    def test_readmes_explain_sha_originals_korean_kr13_and_rebirth_rules(self):
        for spec in subject.SPECS:
            with self.subTest(asset=spec["name"]):
                files = subject.member_map(spec, self.contents, self.source_manifest)
                note = files["README_KO.md"].decode("utf-8")
                self.assertIn("KR13", note)
                self.assertIn(spec["version"], note)
                self.assertIn("공식 영문 원본", note)
                self.assertIn("SHA-256", note)
                self.assertIn("sidecars/", note)
                self.assertIn("--originals-dir originals", note)
                self.assertIn("--output-dir output", note)
                self.assertIn("아직 업로드·공개 안 함", note)
                if spec["group"] == "rebirth":
                    self.assertIn("--mode rebirth", note)
                    self.assertIn("동시에 활성화하지 마세요", note)
                    self.assertIn("manifest-cyrodiil.json", note)
                else:
                    self.assertIn("--mode standard", note)

    def test_public_readme_has_neutral_wording_source_credits_and_scope(self):
        for spec in subject.SPECS:
            with self.subTest(asset=spec["name"]):
                files = subject.member_map(spec, self.contents, self.source_manifest,
                                           public=True)
                note = files["README_KO.md"].decode("utf-8")
                for banned in ("후보", "비공개", "내부 검증", "아직 업로드", "업로드 준비용"):
                    self.assertNotIn(banned, note)
                self.assertIn("원작 및 저작권 표기", note)
                self.assertIn("Bethesda Softworks", note)
                self.assertIn("공식 영문 원본", note)
                self.assertIn("KR13", note)
                self.assertIn("SHA-256", note)
                self.assertIn("모든 퀘스트", note)
                proof = json.loads(files[subject.SHA_MANIFEST])
                self.assertEqual(proof["distribution"], "nexus_patch_only_asset")
                self.assertFalse(proof["full_esm_esp_bsa_fonts_included"])
                for member in (*spec["patches"], *subject.associated_sidecars(spec),
                               subject.APP):
                    self.assertEqual(files[member], self.contents[member])

    def test_public_archive_determinism_in_memory(self):
        for spec in subject.SPECS:
            with self.subTest(asset=spec["name"]):
                files = subject.member_map(spec, self.contents, self.source_manifest,
                                           public=True)
                digests = []
                for _ in range(2):
                    output = io.BytesIO()
                    with zipfile.ZipFile(output, "w", allowZip64=True) as archive:
                        for name in sorted(files):
                            subject.add_deterministic(archive, name, files[name])
                    digests.append(subject.sha(output.getvalue()))
                self.assertEqual(digests[0], digests[1])

    def test_member_SHA_manifest_self_consistent(self):
        for spec in subject.SPECS:
            with self.subTest(asset=spec["name"]):
                files = subject.member_map(spec, self.contents, self.source_manifest)
                audit = json.loads(files[subject.SHA_MANIFEST])
                self.assertFalse(audit["full_esm_esp_bsa_fonts_included"])
                self.assertEqual(set(audit["sha256"]), set(files) - {subject.SHA_MANIFEST})
                self.assertEqual(
                    {k: subject.sha(v) for k, v in files.items() if k != subject.SHA_MANIFEST},
                    audit["sha256"],
                )
                self.assertEqual(set(audit["patch_sha256"]), set(spec["patches"]))

    def test_two_independent_in_memory_zips_deterministic(self):
        # Builds entirely in RAM, leaves no scratch ZIP, Git change, or output.
        for spec in subject.SPECS:
            with self.subTest(asset=spec["name"]):
                files = subject.member_map(spec, self.contents, self.source_manifest)
                built = []
                for _ in range(2):
                    buf = io.BytesIO()
                    with zipfile.ZipFile(buf, "w", allowZip64=True) as dst:
                        for name in sorted(files):
                            subject.add_deterministic(dst, name, files[name])
                    built.append(buf.getvalue())
                self.assertEqual(subject.sha(built[0]), subject.sha(built[1]))
                with zipfile.ZipFile(io.BytesIO(built[0])) as candidate:
                    self.assertIsNone(candidate.testzip())
                    self.assertEqual(candidate.namelist(), sorted(files))
                    for member in candidate.infolist():
                        self.assertEqual(member.date_time, subject.STAMP)
                        self.assertEqual(candidate.read(member.filename), files[member.filename])

    def test_invalid_paths_rejected(self):
        for name in ("../bad.bsdiff", "/absolute", "C:/windows/bad", "x\\..\\y",
                     "source/evil.ESM", "font.ttf"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    subject.safe_member(name)

    def test_source_sha_mismatch_rejected_before_packaging(self):
        with patch.object(subject, "file_sha", return_value="0" * 64):
            with self.assertRaisesRegex(ValueError, "Combined source ZIP SHA256 mismatch"):
                subject.load_original_source()

    def test_existing_output_refused_before_any_mutation(self):
        with tempfile.TemporaryDirectory(prefix="w7-exists-output-") as folder:
            with self.assertRaisesRegex(ValueError, "Output exists; refusing overwrite"):
                subject.build(subject.SOURCE, Path(folder))
            self.assertEqual(list(Path(folder).iterdir()), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
