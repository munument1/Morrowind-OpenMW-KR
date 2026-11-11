"""Deterministic, offline, read-only KR13 public-staging release contract tests.

Tests never launch OpenMW, alter release-KR13-CANDIDATE, commit, publish or
require internet access. Copied mutable source fixtures exist only in a
temporary test directory and are automatically deleted.
"""

import copy
import hashlib
import io
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

import package_kr13_release as pkg


class PublicKR13PackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.internal = pkg.preflight(pkg.DEFAULT_BASE, pkg.DEFAULT_ENGINE,
                                     pkg.DEFAULT_CORE, pkg.DEFAULT_RESOURCES)
        cls.public = pkg.make_public_assets(cls.internal)

    def test_public_includes_gpl_build_script_and_all_exact_patches(self):
        extras = self.public["extra_members"]
        self.assertEqual(len(extras), 22)
        self.assertEqual(pkg.digest(extras[pkg.SOURCE_LICENSE]), pkg.SHA_GPL)
        self.assertEqual(pkg.digest(extras[pkg.SOURCE_BUILD_WORKFLOW]),
                         pkg.SHA_WINDOWS_WORKFLOW)
        self.assertEqual(len([x for x in extras if
                              x.startswith(pkg.SOURCE_PATCH_PREFIX)]), 17)
        for entry in self.public["source_provenance"]["korean_patches"]:
            self.assertEqual(pkg.digest(extras[entry["bundle_member"]]),
                             entry["sha256_lf"])
        self.assertEqual(self.public["source_provenance"]["upstream_source"]["commit"],
                         pkg.SOURCE_UPSTREAM)

    def test_exact_public_notes_and_font_notice(self):
        self.assertEqual(self.public["changed"][pkg.README_MEMBER],
                         self.public["changed"][pkg.NEW_NOTE_MEMBER])
        self.assertIn("GNU GPLv3", pkg.PUBLIC_NOTES)
        self.assertNotIn("내부 검증용", pkg.PUBLIC_NOTES)
        self.assertNotIn("내부 검증용", self.public["changed"][pkg.README_MEMBER]
                         .decode("utf-8-sig"))
        self.assertIn(pkg.SOURCE_INSTRUCTIONS,
                      self.public["changed"][pkg.README_MEMBER].decode("utf-8-sig"))
        self.assertIn("SIL Open Font License",
                      self.public["extra_members"][pkg.THIRD_PARTY].decode("utf-8"))
        pkg.verify_korean_font_payload(self.internal["original"])

    def test_public_zip_determinism_crc_member_allowlist_and_provenance(self):
        first = pkg.create_zip_bytes(self.public)
        self.assertEqual(first, pkg.create_zip_bytes(self.public))
        check = pkg.verify_zip_bytes(self.public, first)
        self.assertEqual(check["member_count"], 65)  # 43 baseline + 22 sources
        self.assertEqual(check["changed_member_count"], 29)
        self.assertEqual(check["unchanged_member_count"], 36)
        self.assertEqual(check["crc"], "PASS")
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn(pkg.SOURCE_LICENSE, archive.namelist())
            self.assertIn(pkg.SOURCE_BUILD_WORKFLOW, archive.namelist())
            self.assertEqual(archive.read(pkg.VERSION_MEMBER),
                             pkg.EXPECTED_RESOURCE_VERSION)
            self.assertEqual(archive.read(pkg.ESP_MEMBER),
                             self.internal["changed"][pkg.ESP_MEMBER])
            self.assertEqual(archive.read(pkg.TOP_MEMBER),
                             self.internal["changed"][pkg.TOP_MEMBER])
            self.assertEqual(archive.read(pkg.EXE_MEMBER),
                             self.internal["changed"][pkg.EXE_MEMBER])
            self.assertEqual(archive.read(pkg.SOURCE_MANIFEST),
                             self.public["extra_members"][pkg.SOURCE_MANIFEST])

    def test_original_candidate_is_bit_identical_and_still_verifies(self):
        old_zip = pkg.OUTPUT / pkg.ARCHIVE_NAME
        expected = "cc2917833a9e94ef3439a12e76abc51e1eb1b169a09ad01e479c3c3bd374ae0a"
        self.assertEqual(pkg.digest(old_zip.read_bytes()), expected)
        self.assertEqual(pkg.check_existing(self.internal)["output"]["sha256"], expected)
        self.assertNotEqual(self.public["changed"][pkg.README_MEMBER],
                            self.internal["changed"][pkg.README_MEMBER])

    def test_public_manifest_not_claim_published_or_all_qa(self):
        raw = pkg.create_zip_bytes(self.public)
        manifest = pkg.make_manifest(self.public, raw,
                                     pkg.verify_zip_bytes(self.public, raw))
        self.assertTrue(manifest["public_staging_only"])
        self.assertFalse(manifest["published"])
        self.assertFalse(manifest["in_game_quest_and_save_reload_verified"])
        self.assertEqual(manifest["corresponding_source"]["included_patch_count"], 17)
        self.assertFalse(manifest["corresponding_source"]["external_url_reachability_verified"])

    def test_reject_invalid_upstream_source_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "audit.json"
            original = json.loads(pkg.PATCH_AUDIT.read_text(encoding="utf-8"))
            original["source_commit"] = "0" * 40
            bad.write_text(json.dumps(original), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "patch audit changed"):
                pkg.make_public_assets(self.internal, audit=bad)

    def test_reject_missing_or_modified_patches_and_gpl(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            patches = repo / "korean/patches"
            patches.mkdir(parents=True)
            workflow = repo / ".github/workflows"
            workflow.mkdir(parents=True)
            shutil.copyfile(pkg.REPO / "LICENSE", repo / "LICENSE")
            shutil.copyfile(pkg.REPO / ".github/workflows/windows.yml",
                            workflow / "windows.yml")
            for p in (pkg.REPO / "korean/patches").glob("*.patch"):
                shutil.copyfile(p, patches / p.name)
            self.assertEqual(len(pkg.make_public_assets(
                self.internal, repo=repo)["extra_members"]), 22)
            target = patches / "0017-regional-core-topic-aliases.patch"
            target.write_bytes(target.read_bytes() + b"\nCORRUPTED\n")
            with self.assertRaisesRegex(ValueError, "patch 0017 SHA256 mismatch"):
                pkg.make_public_assets(self.internal, repo=repo)
            shutil.copyfile(pkg.REPO / "korean/patches" / target.name, target)
            target.unlink()
            with self.assertRaisesRegex(ValueError, "Unexpected, missing"):
                pkg.make_public_assets(self.internal, repo=repo)
            shutil.copyfile(pkg.REPO / "korean/patches" / target.name, target)
            (repo / "LICENSE").write_text("fake GPL", encoding="utf8")
            with self.assertRaisesRegex(ValueError, "license SHA256 mismatch"):
                pkg.make_public_assets(self.internal, repo=repo)

    def test_reject_missing_gpl_or_corrupted_public_provenance(self):
        broken = dict(self.public)
        broken["extra_members"] = dict(self.public["extra_members"])
        broken["extra_members"].pop(pkg.SOURCE_LICENSE)
        with self.assertRaises((ValueError, KeyError)):
            pkg.verify_zip_bytes(broken, pkg.create_zip_bytes(broken))

        good = pkg.create_zip_bytes(self.public)
        damaged = bytearray(good)
        damaged[-135] ^= 1
        with self.assertRaises((ValueError, zipfile.BadZipFile, OSError)):
            pkg.verify_zip_bytes(self.public, bytes(damaged))

    def test_reject_older_runtime_version_and_missing_galmuri(self):
        old_resource_version = pkg.EXPECTED_RESOURCE_VERSION.replace(
            b"4ff261bf7c0d42a6cc06dd1ebc5d451802cff055",
            b"f4bec41444214a7903bebd178389ca22ca13f646",
        )
        with self.assertRaisesRegex(ValueError, "resources/version does not match"):
            pkg.verify_matching_resource_version(old_resource_version)
        fonts = dict(self.internal["original"])
        fonts.pop("payload/resources/vfs/fonts/Galmuri11.ttf")
        with self.assertRaisesRegex(ValueError, "Galmuri11.ttf"):
            pkg.verify_korean_font_payload(fonts)

    def test_generic_release_workflow_excludes_kr13_but_not_other_tags(self):
        raw = (pkg.REPO / ".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertIn("- openmw-**", raw)
        self.assertIn("- '!openmw-0.51.0-kr13'", raw)
        self.assertLess(raw.index("- openmw-**"),
                        raw.index("- '!openmw-0.51.0-kr13'"))
        self.assertIn("Windows:", raw)
        self.assertIn("MacOS:", raw)
        import fnmatch
        patterns = ["openmw-**", "!openmw-0.51.0-kr13"]

        def triggers(tag):
            enabled = False
            for pattern in patterns:
                excluded = pattern.startswith("!")
                if fnmatch.fnmatchcase(tag, pattern.lstrip("!")):
                    enabled = not excluded
            return enabled

        self.assertFalse(triggers("openmw-0.51.0-kr13"))
        self.assertTrue(triggers("openmw-0.51.0-kr12.9"))
        self.assertTrue(triggers("openmw-0.52.0"))
        self.assertFalse(triggers("v1.0.0"))


if __name__ == "__main__":
    unittest.main()
