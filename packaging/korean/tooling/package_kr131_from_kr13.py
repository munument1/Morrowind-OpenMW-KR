"""Reproducibly stage a Windows OpenMW 0.51.0 KR13.1 full installer ZIP.

Use the immutable, published 65-member KR13 ZIP and the independently
SHA-pinned 0019 executable / resources/version pair from ONE successful
0.51.0 Windows CI run. Retain all game-data, font, and 0001-0017 patch bytes.
Append source patches 0018-0019 and update source/license documentation.

Example (after the 0.51.0 + 0019 CI artifacts are available):
    python packaging/korean/tooling/package_kr131_from_kr13.py \
      --engine C:/qa/0019/openmw.exe \
      --resources-version C:/qa/0019/resources/version \
      --engine-sha256 <sha256-measured-from-the-verified-CI-artifact> \
      --ci-run-id <successful-run-id> --ci-head <exact-source-commit> \
      --output C:/qa/KR13.1/Morrowind-Korean-OpenMW-0.51.0-KR13.1-Full.zip \
      --dry-run

There is no Git, network, upload, release, or automatic overwrite operation.
"""

from __future__ import annotations

import argparse
import codecs
import copy
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
BASE_ZIP = REPO.parent / "OpenMW-Issue71-QA" / "Morrowind-Korean-OpenMW-0.51.0-KR13-Full.zip"
BASE_SHA256 = "40da1be66a346c86baa2a3024346b300284c68a73379c64c4e1647744158ac31"
OLD_EXE_SHA256 = "c94e4fe63d59220cb8151c8bdf1449743ea4531731ff7ed1fe1a149cac7cd312"
OLD_VERSION_SHA256 = "eec778cae898eb16f909bc8653258649f69e06a21d6af5091f4404fabf220f88"
OLD_SOURCE_SHA256 = "f4bec41444214a7903bebd178389ca22ca13f646"
WINDOWS_WORKFLOW_SHA256 = "e865c84b7fa8e98d31e0acf487f2ff88a48f42fe429cfc46288663989751b3ee"
PATCH_SHA256 = {
    "0018-korean-dialogue-topic-captions.patch": "1fc481e0daf4fae23e3b8bbd0b900dc524975c0e29d3b3e3cb5d2c49964ed5aa",
    "0019-korean-journal-topic-captions.patch": "4201b2da16ce3cbb200068a2f9a1129008afa99abe3436f403f4948449697821",
}
SUPERSEDED_EXE_SHA256 = {
    "d61f8d230473d5f37d478805cfe5a63ee290604eb0d3796e61f842823827fe3f",
    "d5eab322591800cd36954121c937a9de394d9822cdc7c4c4624fe6c0ed693064",
}
ZIP_NAME = "Morrowind-Korean-OpenMW-0.51.0-KR13.1-Full.zip"
EXE_MEMBER = "payload/openmw.exe"
VERSION_MEMBER = "payload/resources/version"
INSTALLER = "install-korean.ps1"
README = "README-KOREAN.txt"
OLD_NOTES = "KR13-RELEASE-NOTES-KO.txt"
NEW_NOTES = "KR13.1-RELEASE-NOTES-KO.txt"
SOURCE_DOC = "CORRESPONDING-SOURCE.txt"
PROVENANCE = "SOURCE-PROVENANCE.json"
THIRD_PARTY = "THIRD-PARTY-NOTICES.txt"
SOURCE_WORKFLOW = "source/build/windows.yml"
EXPECTED_PATCH_COUNT = 19
EXPECTED_MEMBER_COUNT = 67


def require(ok: bool, explanation: str) -> None:
    if not ok:
        raise ValueError(explanation)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def one(text: str, old: str, new: str, field: str) -> str:
    require(text.count(old) == 1, f"{field}: expected exactly one {old!r}")
    return text.replace(old, new)


def update_utf8_text(data: bytes, replacements: list[tuple[str, str]], member: str) -> bytes:
    has_bom = data.startswith(codecs.BOM_UTF8)
    value = data.decode("utf-8-sig" if has_bom else "utf-8")
    for old, new in replacements:
        value = one(value, old, new, member)
    return (codecs.BOM_UTF8 if has_bom else b"") + value.encode("utf-8")


def valid_version(version: bytes) -> None:
    require(len(version) == 92 and re.fullmatch(
        rb"0\.51\.0\r\nf4bec41444214a7903bebd178389ca22ca13f646\r\n[a-f0-9]{40}\r\n",
        version) is not None, "resources/version must be exact 0.51.0 source plus 40-char revision")


def load_baseline(path: Path) -> tuple[list[zipfile.ZipInfo], dict[str, bytes], dict]:
    raw = path.read_bytes()
    require(sha256(raw) == BASE_SHA256,
            f"KR13 baseline SHA256 mismatch: {sha256(raw)}")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        require(archive.testzip() is None and not archive.comment,
                "Published KR13 ZIP CRC or archive comment mismatch")
        infos = archive.infolist()
        names = [info.filename for info in infos]
        require(len(names) == 65 and len(set(names)) == 65, "Expected precisely 65 KR13 ZIP members")
        require(all(not info.flag_bits & 1 and not info.filename.startswith("/")
                    and "\\" not in info.filename and ".." not in Path(info.filename).parts
                    for info in infos), "Unsafe/encrypted path in KR13 ZIP")
        contents = {info.filename: archive.read(info) for info in infos}

    expected_fixed = {EXE_MEMBER, VERSION_MEMBER, INSTALLER, README, OLD_NOTES,
                      SOURCE_DOC, PROVENANCE, THIRD_PARTY, SOURCE_WORKFLOW,
                      "LICENSE-GPL-3.0.txt",
                      "payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.esp",
                      "payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.top",
                      "payload/resources/vfs/fonts/Galmuri11.ttf",
                      "payload/resources/vfs/fonts/Galmuri11-OFL-1.1.md"}
    require(expected_fixed <= contents.keys(), "KR13 ZIP missing mandatory runtime/source/font members")
    require(sha256(contents[EXE_MEMBER]) == OLD_EXE_SHA256,
            "Unexpected KR13 embedded engine")
    require(sha256(contents[VERSION_MEMBER]) == OLD_VERSION_SHA256,
            "Unexpected KR13 resources/version")
    valid_version(contents[VERSION_MEMBER])
    require(contents[README] == contents[OLD_NOTES] and
            contents[README].startswith(codecs.BOM_UTF8) and
            contents[INSTALLER].startswith(codecs.BOM_UTF8),
            "KR13 release notes/installer encoding mismatch")
    require(sha256(contents[SOURCE_WORKFLOW]) == WINDOWS_WORKFLOW_SHA256,
            "Original corresponding-source Windows workflow SHA changed")
    require(b"GNU GENERAL PUBLIC LICENSE" in contents["LICENSE-GPL-3.0.txt"] and
            b"SIL OPEN FONT LICENSE" in contents["payload/resources/vfs/fonts/Galmuri11-OFL-1.1.md"].upper(),
            "GPL/font license is missing from published baseline")

    provenance = json.loads(contents[PROVENANCE].decode("utf-8"))
    patches = provenance.get("korean_patches", [])
    require(len(patches) == 17, "Existing source provenance has no 17-patch index")
    require(provenance.get("binary_sha256") == OLD_EXE_SHA256 and
            provenance.get("matched_resources_version_sha256") == OLD_VERSION_SHA256 and
            provenance.get("upstream_source", {}).get("commit") == OLD_SOURCE_SHA256 and
            provenance.get("windows_build_workflow", {}).get("sha256") == WINDOWS_WORKFLOW_SHA256,
            "Baseline GPL source provenance disagrees with embedded runtime")
    for n, patch in enumerate(patches, 1):
        member = patch["bundle_member"]
        require(patch.get("order") == n and
                member.startswith(f"source/patches/{n:04d}-") and
                member in contents and patch.get("sha256_lf") == sha256(contents[member]) and
                patch.get("bytes") == len(contents[member]),
                f"Baseline corresponding source patch {n:04d} mismatch")
    require(sum(name.startswith("source/patches/") for name in contents) == 17,
            "Unindexed old patch in KR13 ZIP")
    return infos, contents, provenance


def read_new_patches() -> dict[str, bytes]:
    patch_dir = REPO / "korean" / "patches"
    names = sorted(path.name for path in patch_dir.glob("*.patch"))
    require(len(names) == EXPECTED_PATCH_COUNT and
            names[-2:] == list(PATCH_SHA256),
            "Source patch directory must be exactly the 0019 patch series")
    result: dict[str, bytes] = {}
    for filename, expected in PATCH_SHA256.items():
        source = (patch_dir / filename).read_bytes()
        normalized = source.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        require(sha256(normalized) == expected and normalized.startswith(b"diff --git ")
                and b"@@ " in normalized,
                f"Unreviewed or changed source patch: {filename}")
        result["source/patches/" + filename] = normalized
    return result


def make_notes(original: bytes) -> bytes:
    notes = original.decode("utf-8-sig")
    notes = one(notes, "OpenMW 0.51.0 한국어판 KR13 — Windows x64",
                "OpenMW 0.51.0 한국어판 KR13.1 — Windows x64", README)
    notes = one(notes, "수정 패치 0001~0017", "수정 패치 0001~0019", README)
    notes = one(notes, "한국어 수정 패치 17개", "한국어 수정 패치 19개", README)
    notes = one(notes, "source/patches/0001~0017", "source/patches/0001~0019", README)
    newline = "\r\n" if "\r\n" in notes else "\n"
    section = newline.join([
        "KR13.1 변경 사항 (이슈 #71)",
        "- 지역 모드 대화 목록에서 영어 내부 주제 ID를 표시용 한국어 이름으로 출력합니다.",
        "  기존 DIAL ID와 선택·세이브 호환성은 유지합니다.",
        "- 일반 음성 자막/HUD 메시지에 남던 @주제 표식과 제어 바이트를 화면에서 제거합니다.",
        "- 일지 주제 제목 및 색인을 표시 이름으로 정리합니다.",
        "- TR_Mainland.dsp는 별도의 대응 지역 모드 덮어쓰기 ZIP에 포함해야 합니다.",
        "  이 Windows 통합 ZIP에 지역 ESM/ESP를 동봉하지 않습니다.",
        "- Windows 0.51.0 + 한국어 패치 0001~0019, 64비트 전용입니다.",
        "- 개별 NPC/일지 실제 GUI 동작 및 기존 세이브 검증은 별도 수행해야 합니다.",
        "", "",
    ])
    # Preserve the original newline style and all prior installation guidance.
    require(notes.count("설치 순서" + newline) == 1, "KR13 README layout unexpectedly changed")
    notes = notes.replace("설치 순서" + newline, section + "설치 순서" + newline, 1)
    return codecs.BOM_UTF8 + notes.encode("utf-8")


def make_installer(original: bytes) -> bytes:
    require(original.startswith(codecs.BOM_UTF8), "Installer UTF-8 BOM missing")
    text = original.decode("utf-8-sig")
    require(text.count("KR13") == 3 and text.count("kr13") == 1,
            "Installer's four KR13 version markers unexpectedly changed")
    require('"resources\\version"' in text,
            "KR13 installer must install engine-matched resources/version")
    text = text.replace("KR13", "KR13.1").replace("kr13", "kr13.1")
    return codecs.BOM_UTF8 + text.encode("utf-8")


def make_source_docs(original: bytes, old_provenance: dict, exe_sha: str,
                     version_sha: str, run_id: int) -> bytes:
    prior_run_url = old_provenance["windows_build_workflow"]["ci_run_url"]
    replacements = [
        ("KR13 Windows — GPLv3", "KR13.1 Windows — GPLv3"),
        ("INCLUDING 0017", "INCLUDING 0019"),
        ("0001-*.patch through 0017-*.patch", "0001-*.patch through 0019-*.patch"),
        ("Patch audit: packaging/korean/reports/2026-11-11_regional_patch_check.json",
         "Original KR13 audit (0001-0017): packaging/korean/reports/2026-11-11_regional_patch_check.json"),
        ("all seventeen included patches", "all nineteen included patches"),
        ("patch files 0002 through 0017", "patch files 0002 through 0019"),
        (prior_run_url, f"https://github.com/munument1/Morrowind-OpenMW-KR/actions/runs/{run_id}"),
        (f"Expected bundled openmw.exe SHA256: {OLD_EXE_SHA256}",
         f"Expected bundled openmw.exe SHA256: {exe_sha}"),
        (f"Expected runtime resources/version SHA256: {OLD_VERSION_SHA256}",
         f"Expected runtime resources/version SHA256: {version_sha}"),
        ("No extra third-party font file is added by KR13.",
         "No extra third-party font file is added by KR13.1."),
    ]
    text = update_utf8_text(original, replacements, SOURCE_DOC).decode("utf-8")
    text = one(text,
        "  Base revision checked by audit: " + OLD_SOURCE_SHA256,
        "  Base revision checked by original KR13 audit: " + OLD_SOURCE_SHA256 +
        "\n  Additional 0018-0019 patches: SHA256 in SOURCE-PROVENANCE.json.\n"
        "  Compare this ZIP's source/build/windows.yml with the referenced CI run.", SOURCE_DOC)
    return text.encode("utf-8")


def make_provenance(original: dict, original_bytes: bytes, patches: dict[str, bytes],
                    exe_sha: str, version_sha: str, run_id: int, ci_head: str) -> bytes:
    value = copy.deepcopy(original)
    value["schema"] = "openmw_051_kr131_corresponding_source_v1"
    value["base_kr13_provenance_sha256"] = sha256(original_bytes)
    value["original_kr13_patch_audit_sha256"] = value.pop("patch_audit_sha256")
    value["binary_sha256"] = exe_sha
    value["matched_resources_version_sha256"] = version_sha
    value["windows_build_workflow"]["ci_run_url"] = (
        f"https://github.com/munument1/Morrowind-OpenMW-KR/actions/runs/{run_id}")
    value["windows_build_workflow"]["ci_head_commit"] = ci_head
    value["windows_build_workflow"]["source_ref"] = "OpenMW/openmw:openmw-0.51.0"
    for n, (member, data) in enumerate(patches.items(), 18):
        filename = member.removeprefix("source/patches/")
        raw = (REPO / "korean" / "patches" / filename).read_bytes()
        value["korean_patches"].append({
            "order": n,
            "bundle_member": member,
            "sha256_lf": sha256(data),
            "bytes": len(data),
            "repo_path": "korean/patches/" + filename,
            "repo_raw_sha256": sha256(raw),
        })
    value["included_patch_count"] = EXPECTED_PATCH_COUNT
    value["included_patch_index_sha256"] = sha256("".join(
        f"{item['order']} {item['bundle_member']} {item['sha256_lf']}\n"
        for item in value["korean_patches"]
    ).encode("ascii"))
    value["note"] = (
        "Full 0.51.0 upstream source is referenced at the immutable pinned revision; "
        "all 19 Korean patches and the exact build workflow are in this ZIP. "
        "The prior KR13 patch audit covers 0001-0017 only; new patches have "
        "their own exact SHA256 entries. Verify the CI run and external source "
        "URL remain accessible before publishing."
    )
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def assemble(infos: list[zipfile.ZipInfo], original: dict[str, bytes], provenance: dict,
             new_patches: dict[str, bytes], engine: bytes, version: bytes,
             run_id: int, ci_head: str) -> bytes:
    engine_sha = sha256(engine)
    version_sha = sha256(version)
    notes = make_notes(original[README])
    changed = {
        EXE_MEMBER: engine,
        VERSION_MEMBER: version,
        INSTALLER: make_installer(original[INSTALLER]),
        README: notes,
        NEW_NOTES: notes,
        SOURCE_DOC: make_source_docs(original[SOURCE_DOC], provenance,
                                     engine_sha, version_sha, run_id),
        PROVENANCE: make_provenance(provenance, original[PROVENANCE],
                                    new_patches, engine_sha, version_sha, run_id, ci_head),
        THIRD_PARTY: update_utf8_text(original[THIRD_PARTY],
                                      [("KR13 third-party", "KR13.1 third-party")], THIRD_PARTY),
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as dst:
        for src_info in infos:
            name = src_info.filename
            dest_name = NEW_NOTES if name == OLD_NOTES else name
            data = changed.get(dest_name, original[name])
            info = copy.copy(src_info)
            if dest_name != name:
                info.filename = dest_name
                info.orig_filename = dest_name
            dst.writestr(info, data)
        for member, data in new_patches.items():
            info = zipfile.ZipInfo(member, date_time=(2026, 11, 15, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            dst.writestr(info, data)
    zip_data = buf.getvalue()
    verify_package(zip_data, infos, original, new_patches, changed, version)
    return zip_data


def verify_package(zip_data: bytes, old_infos: list[zipfile.ZipInfo],
                   original: dict[str, bytes], patches: dict[str, bytes],
                   changed: dict[str, bytes], version: bytes) -> None:
    with zipfile.ZipFile(io.BytesIO(zip_data)) as dst:
        new_names = dst.namelist()
        expected_names = [NEW_NOTES if item.filename == OLD_NOTES else item.filename
                          for item in old_infos] + list(patches)
        require(new_names == expected_names and len(set(new_names)) == EXPECTED_MEMBER_COUNT,
                "KR13.1 ZIP members/order differ from immutable KR13 + two patches")
        require(dst.testzip() is None and not dst.comment, "KR13.1 ZIP CRC or comment failed")
        for item in old_infos:
            target = NEW_NOTES if item.filename == OLD_NOTES else item.filename
            actual = dst.read(target)
            expected = changed.get(target, original[item.filename])
            require(actual == expected, f"Unapproved changes in ZIP: {target}")
            copied = dst.getinfo(target)
            require(copied.date_time == item.date_time and
                    copied.compress_type == item.compress_type,
                    f"KR13.1 ZIP metadata changed unexpectedly: {target}")
        for member, data in patches.items():
            require(dst.read(member) == data, f"Patch payload differs: {member}")
        require(dst.read(README) == dst.read(NEW_NOTES), "KR13.1 public notes differ")
        require(dst.read(VERSION_MEMBER) == version and
                b'"resources\\version"' in dst.read(INSTALLER),
                "KR13.1 installer omits matching runtime version")
        require(not any(name.lower().endswith((".esm", ".bsa")) for name in new_names),
                "Game master / BSA illegally included")
        require(not any(name == OLD_NOTES for name in new_names),
                "Outdated KR13 release note retained")
        source = json.loads(dst.read(PROVENANCE))
        require(source["included_patch_count"] == EXPECTED_PATCH_COUNT and
                len(source["korean_patches"]) == EXPECTED_PATCH_COUNT,
                "Public KR13.1 source manifest does not enumerate 19 patches")
        for index, row in enumerate(source["korean_patches"], 1):
            member = row["bundle_member"]
            require(index == row["order"] and sha256(dst.read(member)) == row["sha256_lf"],
                    f"Public source provenance does not match {member}")
        require(sha256(dst.read(SOURCE_WORKFLOW)) == WINDOWS_WORKFLOW_SHA256,
                "Corresponding-source build workflow drifted")
        require(source["binary_sha256"] == sha256(dst.read(EXE_MEMBER)) and
                source["matched_resources_version_sha256"] == sha256(version),
                "Provenance does not match newly embedded engine/version")


def build(args: argparse.Namespace) -> dict:
    require(re.fullmatch(r"[a-fA-F0-9]{64}", args.engine_sha256) is not None,
            "Explicit CI executable SHA256 (--engine-sha256) is mandatory")
    require(re.fullmatch(r"[a-fA-F0-9]{40}", args.ci_head) is not None,
            "CI head source commit must have 40 hex characters")
    require(args.ci_run_id > 0, "A positive original 0.51.0 CI run ID is mandatory")
    require(args.output.name == ZIP_NAME, f"Output name must be {ZIP_NAME}")
    require(args.output.resolve() != args.baseline.resolve(), "Cannot overwrite immutable KR13 ZIP")
    require(args.output.resolve() != args.engine.resolve(), "Cannot overwrite the runtime input")

    infos, original, provenance = load_baseline(args.baseline)
    patches = read_new_patches()
    engine = args.engine.read_bytes()
    version = args.resources_version.read_bytes()
    expected_sha = args.engine_sha256.casefold()
    require(sha256(engine) == expected_sha, "CI engine SHA256 disagrees with the supplied pin")
    require(expected_sha not in {OLD_EXE_SHA256, *SUPERSEDED_EXE_SHA256},
            "Refusing an obsolete executable that omits the selected-response heading fix")
    require(engine.startswith(b"MZ") and len(engine) > 20_000_000,
            "The new executable is not a plausible Windows OpenMW PE binary")
    valid_version(version)
    blob = assemble(infos, original, provenance, patches, engine, version,
                    args.ci_run_id, args.ci_head.casefold())
    digest = sha256(blob)
    output = args.output
    checksum = output.with_name(output.name + ".sha256")
    manifest_path = output.with_name("KR13.1-Windows-Verification.json")
    result = {
        "schema": "openmw_kr131_public_staging_v1",
        "status": "DRY_RUN_VERIFIED" if args.dry_run else "STAGED_NOT_PUBLISHED",
        "published": False,
        "original_kr13_sha256": BASE_SHA256,
        "windows_upstream_commit": OLD_SOURCE_SHA256,
        "windows_ci_run_url": f"https://github.com/munument1/Morrowind-OpenMW-KR/actions/runs/{args.ci_run_id}",
        "windows_ci_head_commit_claim": args.ci_head.casefold(),
        "windows_ci_artifact_sha256_supplied": expected_sha,
        "windows_resources_version_sha256": sha256(version),
        "source_patches_included": 19,
        "prior_payload_members_retained": 65,
        "final_member_count": EXPECTED_MEMBER_COUNT,
        "zip_crc": "PASS",
        "game_assets_copied": False,
        "regional_mod_plugins_included": False,
        "actual_gui_quest_save_test_done": False,
        "output_zip": str(output.resolve()),
        "output_sha256_sidecar": str(checksum.resolve()),
        "output_verification_json": str(manifest_path.resolve()),
        "output_zip_bytes": len(blob),
        "output_zip_sha256": digest,
        "notice": "Verify CI artifact origin and in-game GUI separately before publishing.",
    }
    if not args.dry_run:
        require(all(not path.exists() for path in (output, checksum, manifest_path)),
                "An output ZIP/checksum/report already exists; refusing to overwrite")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as f:
            f.write(blob)
        with checksum.open("x", encoding="ascii", newline="\n") as f:
            f.write(f"{digest}  {ZIP_NAME}\n")
        with manifest_path.open("x", encoding="utf-8", newline="\n") as f:
            json.dump(result, f, ensure_ascii=False, sort_keys=True, indent=2)
            f.write("\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=BASE_ZIP,
                        help="Immutable official KR13 Full ZIP, SHA-pinned")
    parser.add_argument("--engine", type=Path, required=True,
                        help="Exact openmw.exe downloaded from a successful 0019 Windows CI run")
    parser.add_argument("--resources-version", type=Path, required=True,
                        help="resources/version from that SAME 0019 Windows CI run")
    parser.add_argument("--engine-sha256", required=True,
                        help="Independently verified SHA256 of the CI build openmw.exe")
    parser.add_argument("--ci-run-id", type=int, required=True,
                        help="Authoritative OpenMW 0.51.0 0019 Windows build run")
    parser.add_argument("--ci-head", required=True,
                        help="Exact Korean patch branch head associated with the CI run")
    parser.add_argument("--output", type=Path, required=True,
                        help="New, explicit KR13.1 Full ZIP destination; never overwritten")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preflight and assemble/verify bytes in memory without writing any files")
    args = parser.parse_args()
    print(json.dumps(build(args), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
