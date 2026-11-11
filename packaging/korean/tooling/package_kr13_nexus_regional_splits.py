#!/usr/bin/env python3
"""Split the immutable KR13 regional BSDIFF40 bundle into five Nexus candidates.

No full ESM, ESP, BSA, font or third-party resource is distributed. This tool
copies seven source-pinned delta streams and EET sidecars without editing them.
Only small manifest/README/SHA metadata are generated. It deliberately does
NOT publish to Nexus or GitHub and refuses to overwrite an existing output.

Run:
    python -B packaging/korean/tooling/package_kr13_nexus_regional_splits.py
    python -B packaging/korean/tooling/package_kr13_nexus_regional_splits.py --verify-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import zipfile

TOOL = Path(__file__).resolve()
WORKSPACE = TOOL.parents[4]  # D:/Codex_Trans/버그 수정
SOURCE = WORKSPACE / "release-KR13-REGIONAL-PATCHONLY-CANDIDATE-v2" / (
    "Morrowind-KR13-Regional-PatchOnly-kr0.4.zip"
)
OUTPUT = WORKSPACE / "release-KR13-NEXUS-SPLIT-STAGING"
PUBLIC_OUTPUT = WORKSPACE / "release-KR13-NEXUS-SPLIT-PUBLIC"
EXPECTED_SOURCE_SHA256 = "7f5f1a242f91ac422537598e330465fd1e7f2b6cbc1f92ef2c265da5d0650d92"
STAMP = (2026, 11, 11, 12, 0, 0)
REPORT = "NEXUS-SPLIT-STAGING-VERIFICATION.json"
SHA_MANIFEST = "PATCH-SHA256-MANIFEST.json"
APP = "apply_regional_deltas.py"
COMPRESSION_LEVEL = 9

# Member ownership is an exact allowlist: no accidental original/game master,
# cross-module patch, document, or asset can slip into a modular ZIP.
SPECS = (
    {
        "name": "TR_Mainland-kr0.4.zip",
        "label": "Tamriel Rebuilt TR_Mainland 원본 v26.08a Hotfix 1 → 한국어 결과 v26.11 / kr0.4",
        "version": "kr0.4",
        "nexus_mod_id": 60844,
        "group": "common",
        "patches": ("patches/TR_Mainland.esm.bsdiff", "patches/TR_Factions.esp.bsdiff"),
        "main": ("TR_Mainland.esm",),
        "optional_manifests": {"manifest-factions.json": ("TR_Factions.esp",)},
        "sidecar_group": "TR_Mainland",
        "sidecar_stems": ("TR_Mainland",),
    },
    {
        "name": "Tamriel_Data-kr0.4.zip",
        "label": "Tamriel Data HD 26.08 kr0.4",
        "version": "kr0.4",
        "nexus_mod_id": 60845,
        "group": "common",
        "patches": ("patches/Tamriel_Data.esm.bsdiff",),
        "main": ("Tamriel_Data.esm",),
        "optional_manifests": {},
        "sidecar_group": "Tamriel_Data",
        "sidecar_stems": ("Tamriel_Data",),
    },
    {
        "name": "Cyr_Main-kr0.4.zip",
        "label": "Project Cyrodiil 26.09a kr0.4",
        "version": "kr0.4",
        "nexus_mod_id": 60846,
        "group": "standard",
        "patches": ("patches/Cyr_Main.ESM.bsdiff",),
        "main": ("Cyr_Main.ESM",),
        "optional_manifests": {},
        "sidecar_group": "Cyr_Main",
        "sidecar_stems": ("Cyr_Main",),
    },
    {
        "name": "Sky_Main-kr0.3.zip",
        "label": "Skyrim: Home of the Nords 원본 v26.09 Hotfix 1 / kr0.3",
        "version": "kr0.3",
        "nexus_mod_id": 60847,
        "group": "standard",
        "patches": ("patches/Sky_Main.ESM.bsdiff",),
        "main": ("Sky_Main.ESM",),
        "optional_manifests": {},
        "sidecar_group": "Sky_Main",
        "sidecar_stems": ("Sky_Main",),
    },
    {
        "name": "Rebirth7.2-Cyr_Sky_Compatibility-kr0.4.zip",
        "label": "Morrowind Rebirth 7.2 — Cyr/Sky compatibility kr0.4",
        "version": "kr0.4",
        "nexus_mod_id": 60805,
        "group": "rebirth",
        "patches": (
            "patches/Rebirth_Cyrodiil.esm.bsdiff",
            "patches/Rebirth_Skyrim.esm.bsdiff",
        ),
        "main": (
            "Project Cyrodiil [For Rebirth].esm",
            "Skyrim Home of the Nords [For Rebirth].esm",
        ),
        "optional_manifests": {
            "manifest-cyrodiil.json": ("Project Cyrodiil [For Rebirth].esm",),
            "manifest-skyrim.json": ("Skyrim Home of the Nords [For Rebirth].esm",),
        },
        "sidecar_group": "RebirthCompat",
        "sidecar_stems": (
            "Project Cyrodiil [For Rebirth]",
            "Skyrim Home of the Nords [For Rebirth]",
        ),
    },
)
SIDECAR_SUFFIXES = (".cel", ".jrn", ".mrk", ".top")
FORBIDDEN_SUFFIXES = {
    ".esm", ".esp", ".bsa", ".ba2", ".exe", ".dll", ".ttf", ".otf",
    ".woff", ".woff2", ".dds", ".nif",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for piece in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(piece)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def check(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def safe_member(name: str) -> None:
    path = PurePosixPath(name)
    check(
        bool(name) and not name.startswith("/") and "\\" not in name
        and "//" not in name and "\x00" not in name
        and ":" not in name and not any(p in {".", ".."} for p in path.parts),
        f"Unsafe archive path {name!r}",
    )
    check(path.suffix.lower() not in FORBIDDEN_SUFFIXES, f"Forbidden full asset {name!r}")


def original_entry_id(entry: dict) -> str:
    return entry["original"]["path"]


def associated_sidecars(spec: dict) -> tuple[str, ...]:
    return tuple(
        f"sidecars/{spec['sidecar_group']}/{stem}{suffix}"
        for stem in spec["sidecar_stems"]
        for suffix in SIDECAR_SUFFIXES
    )


def patch_names() -> set[str]:
    return {name for spec in SPECS for name in spec["patches"]}


def load_original_source(path: Path = SOURCE) -> tuple[dict[str, bytes], dict]:
    check(path.is_file(), f"Missing immutable combined source {path}")
    check(file_sha(path) == EXPECTED_SOURCE_SHA256, "Combined source ZIP SHA256 mismatch")
    members: dict[str, bytes] = {}
    with zipfile.ZipFile(path, "r") as source:
        check(source.testzip() is None, "Combined source ZIP failed CRC")
        names = source.namelist()
        check(len(names) == len(set(n.casefold() for n in names)), "Duplicate source members")
        check(len(names) == 35, f"Expected 35 source members; got {len(names)}")
        for name in names:
            safe_member(name)
            check(not name.endswith("/"), f"Unexpected source directory {name}")
            members[name] = source.read(name)
    meta = json.loads(members["KR13-REGIONAL-PATCHONLY-MANIFEST.json"].decode("utf-8"))
    master = json.loads(members["manifest.json"].decode("utf-8"))
    expected = {
        "KR13-REGIONAL-PATCHONLY-MANIFEST.json", "README_KO.md", APP, "manifest.json",
    } | patch_names() | {n for spec in SPECS for n in associated_sidecars(spec)}
    check(set(members) == expected, f"Unexpected/missing combined-source files: {set(members) ^ expected}")
    check(meta["patch_format"] == "BSDIFF40" and meta["delta_count"] == 7, "Source patch format/count")
    check(meta["published"] is False and meta["original_master_bytes_included"] is False,
          "Source must be internal patch-only")
    check(set(meta["sha256"]) == set(members) - {"KR13-REGIONAL-PATCHONLY-MANIFEST.json"},
          "Source SHA metadata membership mismatch")
    for name, expected_sha in meta["sha256"].items():
        check(sha(members[name]) == expected_sha, f"Combined source internal SHA mismatch: {name}")
    check(master.get("schema_version") == 1 and master.get("format") == "BSDIFF40",
          "Source master manifest schema or format changed")
    entries = master.get("entries")
    check(isinstance(entries, list) and len(entries) == 7, "Exactly 7 delta entries required")
    check({original_entry_id(e) for e in entries} == {
        e for spec in SPECS for e in spec["main"]
    } | {"TR_Factions.esp"}, "Unexpected original master selection")
    check({e["patch"]["path"] for e in entries} == patch_names(), "Source patch names disagree")
    for entry in entries:
        check(set(entry) == {"group", "original", "output", "patch"}, "Unexpected entry structure")
        for field in ("original", "output", "patch"):
            check(set(entry[field]) == {"path", "sha256"}, "Unexpected source fields")
            check(re.fullmatch(r"[a-f0-9]{64}", entry[field]["sha256"]) is not None,
                  f"Bad SHA in {field}")
        patch = entry["patch"]["path"]
        check(members[patch][:8] == b"BSDIFF40", f"Invalid BSDIFF40 header: {patch}")
        check(sha(members[patch]) == entry["patch"]["sha256"],
              f"Delta changed: {patch}")
    check(sha(members[APP]) == "5b858f4441c7dc5536611bf9c9c89de98808715df2c33cbe4ec3657a94b00437",
          "Source standard-library applier SHA pin failed")
    return members, master


def filtered_manifest(master: dict, names: tuple[str, ...]) -> bytes:
    chosen = [entry for entry in master["entries"] if original_entry_id(entry) in names]
    check(len(chosen) == len(names) and {original_entry_id(e) for e in chosen} == set(names),
          f"Cannot select exact manifest entries: {names}")
    return canonical({
        "schema_version": 1, "format": "BSDIFF40", "entries": chosen,
    })


def readme(spec: dict, selected: tuple[dict, ...], *, public: bool = False) -> bytes:
    version = spec["version"]
    originals = "\n".join(
        f"- `originals/{e['original']['path']}` — SHA-256 `{e['original']['sha256']}`"
        for e in selected
    )
    is_rebirth = spec["group"] == "rebirth"
    is_tr = spec["name"].startswith("TR_Mainland")
    mode = "rebirth" if is_rebirth else "standard"
    variants = ""
    if is_tr:
        variants = (
            "\n### 선택 사항: TR_Factions.esp\n"
            "TR 팩션 통합 모드를 사용하는 경우 **별도 공식 영문 TR_Factions.esp**를 "
            "`originals/TR_Factions.esp`에 제공하고 같은 ZIP의 `manifest-factions.json`으로 "
            "추가 적용합니다. 기본 `manifest.json`에는 TR_Mainland.esm 한 개만 포함됩니다.\n"
            "```powershell\n"
            "python apply_regional_deltas.py --manifest manifest-factions.json "
            "--originals-dir originals --output-dir output --mode standard\n"
            "```\n"
            "원본 `TR_Factions.esp`와 변경된 `TR_Mainland.esm`의 종속성을 지키세요.\n"
        )
    if is_rebirth:
        variants = (
            "\n### 하나만 사용할 때\n"
            "이 패키지의 기본 `manifest.json`은 Rebirth용 Cyrodiil/Skyrim 호환 ESM **2개**를 생성합니다. "
            "모드 하나만 쓰려면 각각 `manifest-cyrodiil.json` 또는 `manifest-skyrim.json`을 지정하고 "
            "필요한 공식 원본 하나만 준비하세요. 각 매니페스트는 해당 델타 하나만 참조합니다.\n"
            "```powershell\n"
            "python apply_regional_deltas.py --manifest manifest-cyrodiil.json "
            "--originals-dir originals --output-dir output --mode rebirth\n"
            "python apply_regional_deltas.py --manifest manifest-skyrim.json "
            "--originals-dir originals --output-dir output --mode rebirth\n"
            "```\n"
            "**둘을 모두 실행하려면 별도의 빈 output 디렉터리를 사용하거나, 두 항목이 모두 포함된 기본 manifest를 "
            "한 번 실행하세요.**\n"
            "Rebirth 본체 7.2와 호환 패치는 서로 다른 파일입니다. "
            "**일반 Cyr_Main.ESM/Sky_Main.ESM과 [For Rebirth] ESM을 동시에 활성화하지 마세요.**\n"
        )
    if is_tr:
        load = (
            "Morrowind.esm → Tribunal.esm → Bloodmoon.esm → "
            "Morrowind_Korean_ReTranslation.esp (KR13) → Tamriel_Data.esm → "
            "TR_Mainland.esm → TR_Factions.esp (선택)"
        )
    elif spec["name"].startswith("Tamriel"):
        load = (
            "Morrowind.esm → Tribunal.esm → Bloodmoon.esm → "
            "Morrowind_Korean_ReTranslation.esp (KR13) → Tamriel_Data.esm → 사용 지역 ESM"
        )
    elif is_rebirth:
        load = (
            "Morrowind.esm → Tribunal.esm → Bloodmoon.esm → "
            "Morrowind_Korean_ReTranslation.esp (KR13) → Tamriel_Data.esm → "
            "TR_Mainland.esm (설치한 경우) → Project Cyrodiil [For Rebirth].esm → "
            "Skyrim Home of the Nords [For Rebirth].esm → "
            "TR_Factions.esp (선택) → 별도 Morrowind Rebirth [Main].ESP"
        )
    else:
        load = (
            "Morrowind.esm → Tribunal.esm → Bloodmoon.esm → "
            "Morrowind_Korean_ReTranslation.esp (KR13) → Tamriel_Data.esm → "
            "TR_Mainland.esm (설치한 경우) → Cyr_Main.ESM → Sky_Main.ESM (설치한 경우) → "
            "TR_Factions.esp (설치한 경우)"
        )
    heading = ("OpenMW KR13 한국어 패치" if public else "OpenMW KR13 패치 전용 후보")
    status = (
        f"**버전 {version} / 기존 Nexus 모드 페이지 {spec['nexus_mod_id']}용 한국어 패치**"
        if public else
        f"**버전 {version} / Nexus 기존 모드 페이지 {spec['nexus_mod_id']}의 업로드 준비용 (아직 업로드·공개 안 함)**"
    )
    rights = (
        "원본 모드/게임 및 리소스의 저작권은 각각의 원저작자에게 있습니다. "
        "이 번역 델타 패치는 원본 모드와 별도이며 원본 파일을 포함하지 않습니다. "
        "원본 제작자의 다운로드 경로·이용 약관·라이선스를 준수하세요."
        if public else
        "원본 제작자·지역 모드 자료의 배포권은 별도로 확인해야 하며, "
        "이 분리 작업 자체가 Nexus 게시 허가를 뜻하지 않습니다."
    )
    credits = (
        "\n## 원작 및 저작권 표기\n"
        "- Morrowind 및 공식 확장팩: Bethesda Softworks / Bethesda Game Studios\n"
        "- Tamriel Rebuilt와 TR_Factions: Tamriel Rebuilt Team\n"
        "- Tamriel Data: Tamriel Data / Cross-Project Coordination\n"
        "- Project Cyrodiil: Project Tamriel Team\n"
        "- Skyrim: Home of the Nords: 해당 프로젝트 제작팀\n"
        "- Morrowind Rebirth 및 전용 호환 패치: 해당 모드 제작자\n"
        "이 자료는 위 원본 콘텐츠를 재포장한 전체 모드가 아니라 "
        "사용자 보유 영문 원본에 적용하는 BSDIFF40 한국어 변경분입니다.\n"
        if public else ""
    )
    final_note = (
        "이 패치는 KR13 완역을 주장하지 않습니다. 모든 퀘스트의 완주나 "
        "기존 개인 세이브 호환성을 보장하는 것도 아닙니다."
        if public else
        "이 패치는 KR13 완역을 주장하지 않습니다. 모든 퀘스트의 최종 진행과 개인 세이브에 "
        "대한 호환성 검증도 아닙니다. 외부 배포 전에 제작자 사용허가·플랫폼 정책과 실제 "
        "모드 조합을 다시 검토하세요."
    )
    text = f"""# {spec['label']} — {heading}

{status}

이 ZIP에는 **완성된 ESM/ESP/BSA, 원본 게임 데이터, 폰트가 없습니다.** 기존 지역 모드에 덮어써서 바로 실행하는 ZIP이 아닙니다. Python 3 표준 라이브러리만으로 BSDIFF40 델타를 적용합니다.
원본 제작자의 **공식 영문 원본 파일을 이용자 본인이 별도로 제공**해야 하며, SHA-256이 정확히 일치하지 않으면 적용기가 중단합니다.
{rights}

## 지원 원본과 SHA
{originals}

원본 모드의 메쉬·텍스처·음원·기타 자원은 원래 제작자의 공식 설치본이 별도로 필요합니다.
**OpenMW 0.51.0 한국어판 KR13 본편과 함께 사용해야 합니다.** 호환성은 정확한 원본 SHA에 제한됩니다.

## 적용 절차
1. 이 ZIP만 **새 작업 폴더**에 압축 해제합니다. 기존 게임/Data Files 원본 폴더에 직접 해제하지 마세요.
2. 공식 영문 ESM/ESP 원본을 `originals/`에 위 이름 그대로 복사합니다. 원본 설치본은 변경하지 않습니다.
3. 원본과 별도 위치에 빈 `output/`을 만들고 아래 명령을 실행합니다.

```powershell
python apply_regional_deltas.py --manifest manifest.json --originals-dir originals --output-dir output --mode {mode}
```

4. 도구는 패치 파일/원본 SHA를 검증하고 `output/<모드명>/` 아래 새 ESM/ESP를 만듭니다. 패치 결과 SHA까지 반드시 검증하며, 기존 파일을 덮어쓰지 않습니다.
5. 본 ZIP의 `sidecars/{spec['sidecar_group']}/`에서 **실제로 활성화하는 플러그인에 대응하는** .cel/.top/.mrk/.jrn을 `output/<모드명>/`로 복사합니다. 정확한 플러그인별 출력 폴더 이름은 `manifest.json`의 `output.path`를 따르세요.
6. OpenMW에는 생성된 ESM/ESP와 동일 폴더에 놓인 sidecar만 연결하고 중복 플러그인을 활성화하지 않습니다. 게임 원본 및 공식 지역 모드 자원은 별도로 유지합니다.

원본/출력 디렉터리는 서로 분리하며, 기존 사용자 세이브나 설치 파일을 직접 수정하지 않습니다.
{variants}
## 권장 로드 순서
{load}

## 패키지 확인
- `manifest.json`: 본 ZIP의 기본 패치만 참조하는 표준 적용 매니페스트
- `{SHA_MANIFEST}`: 원본 결합 ZIP provenance, 이 ZIP의 패치/sidecar/스크립트/문서 SHA
- `patches/*.bsdiff`: 결합 패키지의 **원본 바이트 그대로**인 BSDIFF40 델타
- `apply_regional_deltas.py`: 원본 바이트 그대로 복사한 Python 표준 라이브러리 적용기

{credits}**주의:** {final_note}
"""
    return text.encode("utf-8")


def member_map(
    spec: dict, source_members: dict[str, bytes], master: dict, *, public: bool = False
) -> dict[str, bytes]:
    name_set = set(spec["main"])
    main = [e for e in master["entries"] if original_entry_id(e) in name_set]
    check(len(main) == len(name_set), "Main manifest must select only expected sources")
    check(all(e["group"] == spec["group"] for e in main),
          f"Unexpected patch-mode group for {spec['name']}")
    allowed_patch = {e["patch"]["path"] for e in main}
    for variants in spec["optional_manifests"].values():
        variant_entries = [e for e in master["entries"] if original_entry_id(e) in variants]
        check(len(variant_entries) == len(variants), "Optional manifest entries missing")
        allowed_patch.update(e["patch"]["path"] for e in variant_entries)
    check(allowed_patch == set(spec["patches"]), f"Patch selection mismatch {spec['name']}")
    sidecars = associated_sidecars(spec)
    result = {
        APP: source_members[APP],
        "manifest.json": filtered_manifest(master, spec["main"]),
        "README_KO.md": readme(spec, tuple(main), public=public),
    }
    for variant, originals in spec["optional_manifests"].items():
        result[variant] = filtered_manifest(master, originals)
    for member in (*spec["patches"], *sidecars):
        result[member] = source_members[member]
    check({x for x in result if x.endswith(".bsdiff")} == allowed_patch,
          "Unexpected package patches")
    check({x for x in result if x.startswith("sidecars/")} == set(sidecars),
          "Unexpected package sidecars")
    check(not any(PurePosixPath(x).suffix.lower() in FORBIDDEN_SUFFIXES for x in result),
          "Forbidden packaged game/resource bytes")
    hashes = {n: sha(raw) for n, raw in sorted(result.items())}
    check(all(hashes[n] == sha(source_members[n]) for n in (*spec["patches"], *sidecars, APP)),
          "Data copied from immutable bundle did not match")
    provenance = {
        "schema": "kr13-nexus-regional-split/v1",
        "distribution": "nexus_patch_only_asset" if public else "staging_only_not_uploaded",
        "asset": spec["name"],
        "package_version": spec["version"],
        "nexus_expected_owned_mod_id": spec["nexus_mod_id"],
        "source_combined_zip": SOURCE.name,
        "source_combined_sha256": EXPECTED_SOURCE_SHA256,
        "full_esm_esp_bsa_fonts_included": False,
        "patch_format": "BSDIFF40",
        "patch_sha256": {p: sha(source_members[p]) for p in spec["patches"]},
        "source_original_and_output_sha256": {
            e["original"]["path"]: {
                "original_sha256": e["original"]["sha256"],
                "output_sha256": e["output"]["sha256"],
                "output_path": e["output"]["path"],
            }
            for e in master["entries"] if e["patch"]["path"] in allowed_patch
        },
        "sha256": hashes,
    }
    result[SHA_MANIFEST] = canonical(provenance)
    return result


def add_deterministic(target: zipfile.ZipFile, name: str, data: bytes) -> None:
    safe_member(name)
    info = zipfile.ZipInfo(name, date_time=STAMP)
    info.create_system = 3
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    info.extra = b""
    info.comment = b""
    target.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED,
                    compresslevel=COMPRESSION_LEVEL)


def verify_archive(path: Path, spec: dict, expected: dict[str, bytes]) -> dict:
    with zipfile.ZipFile(path, "r") as z:
        check(z.testzip() is None, f"Output ZIP CRC failed: {path.name}")
        infos = z.infolist()
        names = z.namelist()
        check(names == sorted(expected), f"Non-deterministic member ordering: {path.name}")
        check(len(names) == len(set(n.casefold() for n in names)),
              f"Case-insensitive ZIP collision in {path.name}")
        check(set(names) == set(expected), f"Unexpected output ZIP member: {path.name}")
        for info in infos:
            safe_member(info.filename)
            check(info.date_time == STAMP and info.compress_type == zipfile.ZIP_DEFLATED,
                  "ZIP timestamps or compression metadata invalid")
            raw = z.read(info.filename)
            check(raw == expected[info.filename], f"ZIP raw payload altered: {info.filename}")
        record = json.loads(z.read(SHA_MANIFEST).decode("utf-8"))
        check(record["asset"] == spec["name"], "Archive SHA manifest asset mismatch")
        check(set(record["sha256"]) == set(names) - {SHA_MANIFEST},
              "Archive SHA manifest list mismatch")
        for name, expected_hash in record["sha256"].items():
            check(sha(z.read(name)) == expected_hash, f"Archive SHA manifest mismatch: {name}")
        check(not any(PurePosixPath(n).suffix.lower() in FORBIDDEN_SUFFIXES for n in names),
              f"Forbidden game/resource asset: {path.name}")
    return {
        "asset": spec["name"],
        "sha256": file_sha(path),
        "bytes": path.stat().st_size,
        "member_count": len(expected),
        "patch_count": len(spec["patches"]),
        "patch_sha256": {p: sha(expected[p]) for p in spec["patches"]},
        "sidecar_count": len(associated_sidecars(spec)),
        "manifest_entry_count": len(json.loads(expected["manifest.json"])["entries"]),
        "optional_manifests": list(spec["optional_manifests"]),
        "nexus_expected_owned_mod_id": spec["nexus_mod_id"],
        "crc_and_member_sha_verified": True,
        "source_patch_sidecar_applier_byte_identical": True,
        "contains_full_game_masters_or_fonts": False,
    }


def build(source: Path = SOURCE, output: Path = OUTPUT, *, public: bool = False) -> dict:
    check(not output.exists() and not output.is_symlink(),
          f"Output exists; refusing overwrite: {output}")
    members, master = load_original_source(source)
    # Split by ownership only; never derive a new delta from original masters.
    expected = [(spec, member_map(spec, members, master, public=public)) for spec in SPECS]
    check(not output.exists(), f"Output appeared while building: {output}")
    output.mkdir(parents=False, exist_ok=False)
    try:
        results = []
        for spec, contents in expected:
            path = output / spec["name"]
            with zipfile.ZipFile(path, "x", allowZip64=True) as dst:
                for name in sorted(contents):
                    add_deterministic(dst, name, contents[name])
            results.append(verify_archive(path, spec, contents))
        report = {
            "schema": "kr13-nexus-regional-split-staging/v1",
            "source_combined_zip": SOURCE.name,
            "source_combined_sha256": EXPECTED_SOURCE_SHA256,
            "output": str(output),
            "staging_only": True,
            "public_facing_readme": public,
            "nexus_uploaded": False,
            "original_master_bytes_included": False,
            "all_patches_source_byte_identical": True,
            "patch_file_count_unique": len(patch_names()),
            "all_source_sidecars_preserved": True,
            "python_stdlib_applicator_sha256": sha(members[APP]),
            "archives": results,
        }
        (output / REPORT).write_bytes(canonical(report))
        verify_staging(source, output, public=public)
    except BaseException:
        # Only the new output owned by this invocation is safe to clean up.
        shutil.rmtree(output)
        raise
    return report


def verify_staging(
    source: Path = SOURCE, output: Path = OUTPUT, *, public: bool = False
) -> dict:
    members, master = load_original_source(source)
    check(output.is_dir() and not output.is_symlink(),
          f"Staging folder absent or redirected: {output}")
    check({f.name for f in output.iterdir()} ==
          {spec["name"] for spec in SPECS} | {REPORT},
          "Staging must contain exactly 5 ZIPs and the verification JSON")
    actual_report = json.loads((output / REPORT).read_text(encoding="utf-8"))
    check(actual_report["schema"] == "kr13-nexus-regional-split-staging/v1",
          "Wrong staging schema")
    check(actual_report.get("public_facing_readme", False) is public,
          "Archive README audience/mode mismatch")
    actual = []
    for spec in SPECS:
        expected = member_map(spec, members, master, public=public)
        actual.append(verify_archive(output / spec["name"], spec, expected))
    check(actual_report["archives"] == actual, "Staging verification JSON not current")
    check(actual_report["source_combined_sha256"] == EXPECTED_SOURCE_SHA256,
          "Source SHA changed")
    return actual_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", type=Path, default=SOURCE)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--public", action="store_true",
                        help="New public-facing asset staging with neutral README; never uploads")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    destination = args.output_dir or (PUBLIC_OUTPUT if args.public else OUTPUT)
    try:
        result = (verify_staging(args.source_zip, destination, public=args.public)
                  if args.verify_only else build(args.source_zip, destination, public=args.public))
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "status": "VERIFIED" if args.verify_only else "BUILT",
        "source_sha256": result["source_combined_sha256"],
        "assets": [{"zip": r["asset"], "sha256": r["sha256"], "bytes": r["bytes"]}
                   for r in result["archives"]],
        "output": str(destination),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
