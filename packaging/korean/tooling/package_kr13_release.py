"""Build reproducible, isolated KR13 Windows internal or public-staging ZIPs.

This is deliberately not a release/publishing script. It consumes one immutable
KR12.9 full ZIP, a pinned 0.51.0+0017 OpenMW executable with its exact matching
resources/version, and the reviewed v10 core ESP/TOP. Only the engine, its
required 92-byte resources/version metadata, core ESP/TOP, installer labels
and in-ZIP KR13 notes may change. Regional archives are built separately.

Usage (from anywhere):
    python packaging/korean/tooling/package_kr13_release.py --check-only
    python packaging/korean/tooling/package_kr13_release.py
    python packaging/korean/tooling/package_kr13_release.py --verify-existing
    python packaging/korean/tooling/package_kr13_release.py --public-staging --check-only
    python packaging/korean/tooling/package_kr13_release.py --public-staging
    python packaging/korean/tooling/package_kr13_release.py --public-staging --verify-existing

Output locations are intentionally fixed; there is no --output, Git, network,
publishing action or automatic overwrite. The default KR13-CANDIDATE remains
bit-identical to the original verified internal build.
"""

from __future__ import annotations

import argparse
import codecs
import copy
import hashlib
import io
import json
import shutil
import zipfile
from pathlib import Path


WORK = Path(__file__).resolve().parents[4]
DEFAULT_BASE = WORK / "release-KR12.9" / "Morrowind-Korean-OpenMW-0.51.0-KR12.9-Full.zip"
DEFAULT_ENGINE = WORK.parent / "MWIssueQA_20261111" / "runtime-issue63-051" / "extracted" / "openmw.exe"
DEFAULT_RESOURCES = DEFAULT_ENGINE.parent / "resources"
DEFAULT_CORE = WORK / "issue63-reviewed-allsource-linked-v10-candidate-20261111" / "core"
NATIVE_REPORT = WORK / "issue63-reviewed-allsource-linked-v10-candidate-20261111" / "reviewed-regional-runtime-verification.json"
OUTPUT = WORK / "release-KR13-CANDIDATE"
PUBLIC_OUTPUT = WORK / "release-KR13-PUBLIC-STAGING"
ARCHIVE_NAME = "Morrowind-Korean-OpenMW-0.51.0-KR13-Full.zip"
MANIFEST_NAME = "KR13-CANDIDATE-VERIFICATION.json"
PUBLIC_MANIFEST_NAME = "KR13-PUBLIC-STAGING-VERIFICATION.json"
REPO = WORK / "Morrowind-OpenMW-KR"
PATCH_REPO = REPO / "korean" / "patches"
PATCH_AUDIT = REPO / "packaging/korean/reports/2026-11-11_regional_patch_check.json"
SOURCE_UPSTREAM = "f4bec41444214a7903bebd178389ca22ca13f646"
SHA_PATCH_AUDIT = "83711432ec324c2977a3765bed259abf4d7e7b18eae3865cfa490abc3a4c92d0"
SHA_GPL = "e1fd6953502833cdbf730a8b69f7791b91b829611983da4ec364926ece926ea6"
SHA_WINDOWS_WORKFLOW = "e865c84b7fa8e98d31e0acf487f2ff88a48f42fe429cfc46288663989751b3ee"
SOURCE_LICENSE = "LICENSE-GPL-3.0.txt"
SOURCE_INSTRUCTIONS = "CORRESPONDING-SOURCE.txt"
SOURCE_MANIFEST = "SOURCE-PROVENANCE.json"
THIRD_PARTY = "THIRD-PARTY-NOTICES.txt"
SOURCE_PATCH_PREFIX = "source/patches/"
SOURCE_BUILD_WORKFLOW = "source/build/windows.yml"

SHA_BASE = "f13574941ca699af479a2facbf87c06e5b9ae2cd4696d800c4b89e7ec4f88223"
SHA_OLD_EXE = "8e7073837146e4a8bcf064ccbf8627bbbc475dc09069f245b7acc6cb75a3878d"
SHA_OLD_ESP = "a5e2de56cf179193b1a0adeb90fc29bc8351cf29487b06cf71433f54f76a71f7"
SHA_OLD_TOP = "881513ca6976dde2a4f410dd35d412753d7c3b026f7c7fe4f787802bc44813ac"
SHA_OLD_INSTALLER = "ee81cd35f2e36df14ece3c4ed9972ff4b900a2342af37c0a2492282f2433dde8"
SHA_OLD_README = "c4e544f6b1fb83a5454c9287dc48cf53bd96e6a8a7c9400b60cd7f13c3c3da70"
SHA_EXE = "c94e4fe63d59220cb8151c8bdf1449743ea4531731ff7ed1fe1a149cac7cd312"
SHA_RESOURCE_VERSION = "eec778cae898eb16f909bc8653258649f69e06a21d6af5091f4404fabf220f88"
SHA_ESP = "9f94b1c96b10a491cec00d4931123ef1e0f52f52c6095da6b9b380eb9a617b1c"
SHA_TOP = "928ace2d7245edd01f8085737e76d4fc6e9d1343b1477e7c5ed9eebf78cc6f0b"
SHA_REPORT = "c0ebde2b148eb3e6f1cbbb5136fb7c192c1593f2d4d3afd580e624609783c01a"
SHA_RUNNER_0017 = "0cdf6563ffc5df7bd2d11a8639373a83dadba7a108534df411e8df123014adac"

CORE_PATH = "payload/mods/Morrowind_Korean_ReTranslation/"
VERSION_MEMBER = "payload/resources/version"
EXE_MEMBER = "payload/openmw.exe"
ESP_MEMBER = CORE_PATH + "Morrowind_Korean_ReTranslation.esp"
TOP_MEMBER = CORE_PATH + "Morrowind_Korean_ReTranslation.top"
INSTALLER_MEMBER = "install-korean.ps1"
README_MEMBER = "README-KOREAN.txt"
OLD_NOTE_MEMBER = "KR12.9-RELEASE-NOTES-KO.txt"
NEW_NOTE_MEMBER = "KR13-RELEASE-NOTES-KO.txt"
MOD_BASE = "Morrowind_Korean_ReTranslation"

# Strict allowlist: the pre-existing release is immutable and no extra game
# masters, fonts or other copyrighted material may enter this archive.
BASE_MEMBERS = (
    "payload/mods/",
    "payload/resources/",
    EXE_MEMBER,
    CORE_PATH + "l10n/",
    CORE_PATH + MOD_BASE + ".cel",
    ESP_MEMBER,
    CORE_PATH + MOD_BASE + ".jrn",
    CORE_PATH + MOD_BASE + ".mrk",
    TOP_MEMBER,
    CORE_PATH + "l10n/Calendar/ko.yaml",
    CORE_PATH + "l10n/Interface/ko.yaml",
    CORE_PATH + "l10n/OMWCamera/ko.yaml",
    CORE_PATH + "l10n/OMWCombat/ko.yaml",
    CORE_PATH + "l10n/OMWControls/ko.yaml",
    CORE_PATH + "l10n/OMWEngine/ko.yaml",
    CORE_PATH + "l10n/OMWMusic/ko.yaml",
    CORE_PATH + "l10n/OMWShaders/ko.yaml",
    CORE_PATH + "video/bm_bearhunt1.srt",
    CORE_PATH + "video/bm_bearhunt2.srt",
    CORE_PATH + "video/bm_ceremony1.srt",
    CORE_PATH + "video/bm_ceremony2.srt",
    CORE_PATH + "video/bm_endgame.srt",
    CORE_PATH + "video/bm_frostgiant1.srt",
    CORE_PATH + "video/bm_frostgiant2.srt",
    CORE_PATH + "video/mw_cavern.srt",
    CORE_PATH + "video/mw_end.srt",
    CORE_PATH + "video/mw_intro.srt",
    "payload/resources/vfs/",
    "payload/resources/vfs/fonts/DejaVuLGCSansMono.omwfont",
    "payload/resources/vfs/fonts/Galmuri11-OFL-1.1.md",
    "payload/resources/vfs/fonts/Galmuri11.ttf",
    "payload/resources/vfs/fonts/MysticCards.omwfont",
    "install-korean-config.ps1",
    "Install-Korean.bat",
    INSTALLER_MEMBER,
    "korean-fallbacks.cfg",
    README_MEMBER,
    CORE_PATH + "Siege at Firemoth.cel",
    "KR12.5-CHANGES.txt",
    "KR12.6-CHANGES.txt",
    "KR12.8-CHANGES.txt",
    OLD_NOTE_MEMBER,
)
assert len(BASE_MEMBERS) == 42 and len(set(BASE_MEMBERS)) == 42
FINAL_MEMBERS = tuple(
    member
    for old_name in BASE_MEMBERS
    for member in (
        (old_name, VERSION_MEMBER) if old_name == "payload/resources/" else
        (NEW_NOTE_MEMBER if old_name == OLD_NOTE_MEMBER else old_name,)
    )
)
assert len(FINAL_MEMBERS) == 43 and len(set(FINAL_MEMBERS)) == 43

EXPECTED_RESOURCE_VERSION = (
    b"0.51.0\r\n"
    b"f4bec41444214a7903bebd178389ca22ca13f646\r\n"
    b"4ff261bf7c0d42a6cc06dd1ebc5d451802cff055\r\n"
)
FONT_MEMBERS = {
    "payload/resources/vfs/fonts/Galmuri11.ttf":
        "e24256f42e43713d2ea086a1e1669d78b968f5b3cc547e5c157f0606ffa5def1",
    "payload/resources/vfs/fonts/Galmuri11-OFL-1.1.md":
        "9a9e5a342c430c3fcf01a408b680f4405d5bf4ac659c931be35f8a1b27ea69c9",
    "payload/resources/vfs/fonts/DejaVuLGCSansMono.omwfont":
        "ce3df35c64f0ae96c3739cb216a99fe53c027ba4c354258a1c764ee37e310761",
    "payload/resources/vfs/fonts/MysticCards.omwfont":
        "ba50c99a45cf41e6b6fd044ffb3a9f7bffee91d020189be9a454356802276dc4",
}

NOTES = """OpenMW 0.51.0 한국어판 KR13 — 내부 검증용 후보 (2026-11-11)

이 ZIP은 정식 배포본이 아닌 KR13 Windows x64 검증 후보입니다.
정식 KR13 릴리스가 게시되기 전에는 일반 사용자에게 설치를 권장하지 않습니다.
이 후보는 기존 KR12.9 전체 설치본을 기반으로 하며 누적 데이터 수정이 포함되어 있습니다.

변경 범위
- 0.51.0 한국어 OpenMW 엔진의 패치 0001~0017 적용 실행 파일.
- 엔진 빌드와 일치하는 OpenMW resources/version을 함께 설치합니다.
- 본편 한국어 ESP: KR12.9 대비 검수된 INFO.NAME 105개 링크 교정.
- 본편 .top: 기존 53개 추가 별칭 및 2,087개 공통 주제 영문/한글 대응 추가.
- 배경(background), 최근 소문(latest rumors), 작은 비밀(little secret),
  내 직업(my trade) 등 지역 NPC의 기본 주제 탐색과 정식 한국어 응답 연결을 개선합니다.
- 다른 본편 CEL/MRK/JRN, 기존 Galmuri11 한글 폰트·라이선스·
  한국어 글꼴 설정, 자막·l10n 데이터, 게임 마스터는 변경하지 않습니다.
- 새 ESP/ESM 플러그인을 추가하지 않습니다.

필수 순서
Morrowind.esm → Tribunal.esm → Bloodmoon.esm →
Morrowind_Korean_ReTranslation.esp → (사용 시 Patch for Purists) →
Tamriel_Data.esm → 사용 지역 모드 → 해당 TR_Factions/Rebirth 호환 모드.
Rebirth 교체 Cyr/Sky ESM과 일반 Cyr/Sky ESM을 동시에 활성화하지 마십시오.
원본 게임과 지역 모드 리소스는 사용자 본인이 따로 설치해야 합니다.

설치 절차
1. 실제 OpenMW 0.51.0 설치 폴더, openmw.cfg, 세이브를 먼저 백업하십시오.
2. 이 전체 ZIP을 별도 폴더에 풀고 Install-Korean.bat을 실행하십시오.
3. 'Morrowind Data Files'가 아니라 openmw.exe가 설치된 폴더를 지정하십시오.
4. 설치기는 기존 실행 파일·한국어 폴더·설정을 백업한 후 변경합니다.
5. 이 ZIP에는 별도 지역 번역 업데이트 ZIP이 들어 있지 않습니다.
   #66 전체 수정을 검증하려면 동일 검증 세대의 지역 데이터 ZIP이 필요합니다.

검증 한계
- 원문/바이트 보존과 네이티브 토픽 12개 구성 × 두 모드 검사를 통과한
  자료를 입력으로 사용했지만, 실제 NPC 퀘스트 진행과 세이브 재불러오기는
  별도의 KR13 통합 게임 검증이 필요합니다.
- Windows x64 전용이며 Android APK를 갱신하지 않습니다.
- #63 지역 모드의 모든 미번역 문장이 해결되었다고 주장하지 않습니다.
- 이 후보를 GitHub 또는 Nexus에 자동 업로드하지 않습니다.
"""

PUBLIC_NOTES = """OpenMW 0.51.0 한국어판 KR13 — Windows x64

설치 순서
Morrowind.esm → Tribunal.esm → Bloodmoon.esm →
Morrowind_Korean_ReTranslation.esp → (선택: Patch for Purists) →
Tamriel_Data.esm → 해당 지역 모드 → 해당 TR_Factions/Rebirth 호환 모드.
Rebirth 전용 Cyr/Sky 교체 ESM과 일반 Cyr/Sky ESM을 동시에 활성화하지 마십시오.
사용자는 정품 Morrowind와 확장팩, 필요한 지역 모드 리소스를 직접 준비해야 합니다.

설치 방법
1. 기존 OpenMW 설치 폴더, openmw.cfg, 세이브를 백업하십시오.
2. ZIP을 별도 폴더에 압축 해제하고 Install-Korean.bat을 실행하십시오.
3. openmw.exe가 들어 있는 OpenMW 0.51.0 설치 폴더를 선택하십시오.
4. 설치기는 기존 런타임·resources/version·한국어 모드·설정을 백업하고
   새 실행 파일, 정확히 대응하는 resources/version 및 번역 데이터를 설치합니다.
5. 지역 모드는 이 ZIP에 포함되지 않습니다. 대응하는 지역 번역 업데이트
   패키지를 별도로 설치하고 OpenMW 런처에서 로드 순서를 확인하십시오.

KR12.9 대비 주요 변경
- OpenMW 0.51.0의 한국어 런타임 수정 패치 0001~0017.
- 검수한 본편 INFO.NAME 105건에서 연결 대상만 교정. 화면 문구와
  화자·퀘스트·스크립트·다른 레코드의 원본 값은 보존.
- TOP 별칭 53건과 영문/한국어 공통 주제 대응 2,087건 추가.
- 지역 신규 NPC의 배경, 최근 소문, 작은 비밀, 내 직업 등 기본 주제
  습득 및 한국어 대사 연결을 개선.
- 기존 Galmuri11 폰트, OFL 라이선스, 자막, 번역용 CEL/MRK/JRN 유지.

검증 범위
- KR12.9 공개 ZIP 대비 데이터/원문 SHA와 네이티브 파서 12개 구성×2모드
  회귀 검사를 바탕으로 작성했습니다.
- NPC 대화 경로의 개별 실행 검증은 전체 퀘스트·기존 세이브의 완전한
  무결성 검증을 의미하지 않습니다.
- 모로윈드 지역 모드 #63의 모든 미번역 구간을 완역했다는 뜻은 아닙니다.
- Android APK를 대체하거나 갱신하지 않습니다.

오픈소스 및 제3자 고지
- OpenMW 엔진은 GNU GPLv3 조건에 따릅니다.
- 이 ZIP에 포함된 LICENSE-GPL-3.0.txt와 CORRESPONDING-SOURCE.txt에서
  원본 OpenMW 소스의 정확한 커밋, 한국어 수정 패치 17개 및
  재현을 위한 Windows 빌드 출처를 확인할 수 있습니다.
- source/patches/0001~0017 패치가 모두 함께 포함되어 있습니다.
- Galmuri11 글꼴은 별도의 SIL Open Font License 1.1 적용 대상입니다.
  전문: payload/resources/vfs/fonts/Galmuri11-OFL-1.1.md.
  자세한 내용: THIRD-PARTY-NOTICES.txt.

소스 안내 및 프로젝트: https://github.com/munument1/Morrowind-OpenMW-KR
"""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_pinned(path: Path, expected: str, description: str) -> bytes:
    require(path.is_file(), f"{description} missing: {path}")
    data = path.read_bytes()
    actual = digest(data)
    require(actual == expected, f"{description} SHA256 mismatch ({actual} != {expected}): {path}")
    return data


def verify_matching_resource_version(data: bytes) -> None:
    require(digest(data) == SHA_RESOURCE_VERSION,
            "OpenMW resources/version does not match the bundled 0017 engine")
    require(data == EXPECTED_RESOURCE_VERSION, "OpenMW resource revision text mismatch")


def verify_korean_font_payload(contents: dict[str, bytes]) -> None:
    """Prevent a fatal missing Galmuri.ttf and silent stock-font overwrite."""
    for name, expected in FONT_MEMBERS.items():
        require(name in contents, f"Mandatory Korean font/descriptor/license missing: {name}")
        require(digest(contents[name]) == expected,
                f"Korean font/descriptor/license SHA mismatch: {name}")


def make_installer(original: bytes) -> bytes:
    require(original.startswith(codecs.BOM_UTF8), "Installer BOM changed from KR12.9")
    text = original[len(codecs.BOM_UTF8):].decode("utf-8")
    require(text.count("\r\n") > 100, "Unexpected installer line-ending format")
    replacements = (
        ("korean-kr12.3.1-backup-$timestamp", "korean-kr13-backup-$timestamp"),
        ("OpenMW 0.51.0 Korean Support KR12.9", "OpenMW 0.51.0 Korean Support KR13"),
        ("OPENMW-KOREAN-KR12.9.txt", "OPENMW-KOREAN-KR13.txt"),
        ("Korean OpenMW KR12.9 installation completed.", "Korean OpenMW KR13 installation completed."),
    )
    for old, new in replacements:
        require(text.count(old) == 1, f"Installer version marker is not unique: {old}")
        text = text.replace(old, new)
    old_files = '    "openmw.exe",\r\n    "resources\\vfs\\fonts\\Galmuri11.ttf",'
    new_files = '    "openmw.exe",\r\n    "resources\\version",\r\n    "resources\\vfs\\fonts\\Galmuri11.ttf",'
    require(text.count(old_files) == 1,
            "Original installer runtime file list changed; cannot stage resources/version safely")
    text = text.replace(old_files, new_files)
    require("KR12.9" not in text and "kr12.3.1" not in text,
            "Unexpected legacy version label remains in installer")
    require(text.count("KR13") == 3 and text.count("kr13") == 1,
            "Unexpected number of KR13 installer labels")
    require(text.count('"resources\\version"') == 1,
            "Installer must install exactly one engine-matched resources/version")
    return codecs.BOM_UTF8 + text.encode("utf-8")


def make_notes(original: bytes) -> bytes:
    require(original.startswith(codecs.BOM_UTF8), "Release README BOM changed from KR12.9")
    require("KR12.9" in original.decode("utf-8-sig"), "Source README is not the KR12.9 notes")
    return codecs.BOM_UTF8 + NOTES.encode("utf-8")


def make_public_assets(source: dict, repo: Path = REPO,
                       audit: Path = PATCH_AUDIT) -> dict:
    """Add licensed corresponding-source material; never modify repository."""
    repo = Path(repo)
    require(not source.get("public"), "Public provenance already appended")
    require(digest(audit.read_bytes()) == SHA_PATCH_AUDIT,
            "Authoritative 0001–0017 source patch audit changed")
    review = json.loads(audit.read_text(encoding="utf-8"))
    require(review.get("source_commit") == SOURCE_UPSTREAM,
            "Patch audit upstream OpenMW source revision differs")
    patch_index = review.get("patches", [])
    require(len(patch_index) == 17, "Source manifest must enumerate 17 Korean patches")
    require(sorted(path.name for path in (repo / "korean/patches").glob("*.patch")) ==
            sorted(row["patch"] for row in patch_index),
            "Unexpected, missing or added Korean patch source")

    license_data = read_pinned(repo / "LICENSE", SHA_GPL, "OpenMW GPLv3 license")
    workflow_data = read_pinned(repo / ".github/workflows/windows.yml",
                                SHA_WINDOWS_WORKFLOW, "0.51 Windows overlay build workflow")
    require(b"GNU GENERAL PUBLIC LICENSE" in license_data and
            b"Version 3, 29 June 2007" in license_data,
            "GPLv3 license content is not recognized")
    require(b"source_repository" in workflow_data and b"korean_overlay" in workflow_data,
            "Windows build source/overlay instructions are incomplete")

    patches = []
    additional = {
        SOURCE_LICENSE: license_data,
        SOURCE_BUILD_WORKFLOW: workflow_data,
    }
    for number, row in enumerate(patch_index, start=1):
        patch = row["patch"]
        require(patch.startswith(f"{number:04d}-") and patch.endswith(".patch") and
                "/" not in patch and "\\" not in patch, f"Wrong patch sequence: {patch}")
        raw = (repo / "korean/patches" / patch).read_bytes()
        # The audit is LF-normalized. Bundle those exact bytes, not an
        # unverified CRLF copy that could apply differently on Windows.
        normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        require(digest(normalized) == row["lf_sha256"],
                f"Source patch {number:04d} SHA256 mismatch: {patch}")
        require((normalized.startswith(b"diff --git ") or
                 (number == 5 and normalized.startswith(b"--- a/"))) and
                b"@@ " in normalized,
                f"Source patch lacks expected Git unified diff: {patch}")
        member = SOURCE_PATCH_PREFIX + patch
        additional[member] = normalized
        patches.append({
            "order": number,
            "bundle_member": member,
            "sha256_lf": digest(normalized),
            "bytes": len(normalized),
            "repo_path": "korean/patches/" + patch,
            "repo_raw_sha256": digest(raw),
        })
    require(len(patches) == 17, "Corresponding source patch count is not 17")

    upstream_url = (
        "https://github.com/OpenMW/openmw/tree/" + SOURCE_UPSTREAM
    )
    upstream_download = (
        "https://github.com/OpenMW/openmw/archive/" + SOURCE_UPSTREAM + ".zip"
    )
    origin = "https://github.com/munument1/Morrowind-OpenMW-KR"
    ci_url = origin + "/actions/runs/42965852650"
    instructions = f"""KR13 Windows — GPLv3 corresponding source and build instructions

OpenMW game engine license: GNU General Public License, version 3.
Complete license: {SOURCE_LICENSE} (SHA256 {SHA_GPL}).
The original Morrowind/Bethesda game files are NOT part of the engine source.

EXACT OPENMW ENGINE BASE
  Project: OpenMW/openmw
  Original repository: https://github.com/OpenMW/openmw
  Source revision: {SOURCE_UPSTREAM}
  Browse immutable revision: {upstream_url}
  Download source at exact revision: {upstream_download}
  Tag used for the Windows 0.51.0 build: openmw-0.51.0
  The source revision and compilation patch order are SHA-locked below.

EXACT KOREAN ENGINE MODIFICATIONS (INCLUDING 0017)
  Apply source/patches/0001-*.patch through 0017-*.patch in numeric order.
  Every patch file is included in THIS ZIP and its normalized LF SHA256
  is listed in {SOURCE_MANIFEST}. No future branch or moving tag is
  required to recover those exact patch bytes.
  Patch audit: packaging/korean/reports/2026-11-11_regional_patch_check.json
  Base revision checked by audit: {SOURCE_UPSTREAM}

WINDOWS BUILD / CORRESPONDING BUILD SCRIPT
  Original CI build workflow included: {SOURCE_BUILD_WORKFLOW}
  Upstream Windows build prerequisites, vcpkg/CMake build settings and
  dependency acquisition are documented by the OpenMW 0.51 source and
  the included workflow. Build the original OpenMW source at the revision
  above, apply all seventeen included patches, add the Korean fonts and
  configurations from the OpenMW Korean repository, then run the 0.51
  Windows toolchain (MSVC 2022, CMake/Ninja, vcpkg) as in the workflow.
  Pseudocode:
      git clone https://github.com/OpenMW/openmw.git
      cd openmw
      git checkout {SOURCE_UPSTREAM}
      git apply --check /path/to/source/patches/0001-*.patch
      git apply /path/to/source/patches/0001-*.patch
      ... repeat sequentially for patch files 0002 through 0017
  Windows build details: source/build/windows.yml

  Korean port repository: {origin}
  Runtime build evidence (Windows 0.51.0):
      {ci_url}
  Expected bundled openmw.exe SHA256: {SHA_EXE}
  Expected runtime resources/version SHA256: {SHA_RESOURCE_VERSION}
  Expected Korean ESP SHA256: {SHA_ESP}
  Expected Korean TOP SHA256: {SHA_TOP}

SOURCE AVAILABILITY NOTICE
  The upstream source repository and the embedded full Korean patchset
  constitute the engine source reconstruction inputs. To provide binary
  downloads publicly under GPLv3, keep this exact upstream revision
  downloadable free of charge, retain these patches and build instructions,
  and provide equivalent public access to the corresponding source.
  Merely linking to a moving branch or a transient CI artifact is not a
  substitute for stable corresponding-source distribution.

THIRD-PARTY FONT
  Galmuri11 is NOT relicensed as GPLv3. Its separate SIL OFL 1.1 notice
  is at payload/resources/vfs/fonts/Galmuri11-OFL-1.1.md.
  See {THIRD_PARTY}. No extra third-party font file is added by KR13.
"""
    third_party = """KR13 third-party and font license notices

OpenMW engine: GNU GPLv3; see LICENSE-GPL-3.0.txt and CORRESPONDING-SOURCE.txt.
Galmuri11.ttf (2019–2025 Lee Minseo): SIL Open Font License 1.1.
The complete copyright notice and OFL 1.1 terms accompany the included font:
  payload/resources/vfs/fonts/Galmuri11-OFL-1.1.md
No Galmuri font binary was added beyond the immutable KR12.9 package.
DejaVuLGCSansMono.omwfont and MysticCards.omwfont are existing Korean
configuration descriptors from that same immutable package; no additional
DejaVu, MysticCards, Gowun, or other third-party font binaries are bundled.
"""

    provenance = {
        "schema": "openmw_051_kr13_corresponding_source_v1",
        "license": {"name": SOURCE_LICENSE, "sha256": digest(license_data),
                    "spdx": "GPL-3.0-only"},
        "upstream_source": {"repository": "OpenMW/openmw",
                            "commit": SOURCE_UPSTREAM, "browse_url": upstream_url,
                            "download_url": upstream_download},
        "korean_patches": patches,
        "patch_audit_sha256": SHA_PATCH_AUDIT,
        "windows_build_workflow": {"member": SOURCE_BUILD_WORKFLOW,
                                   "sha256": digest(workflow_data),
                                   "ci_run_url": ci_url},
        "binary_sha256": SHA_EXE,
        "matched_resources_version_sha256": SHA_RESOURCE_VERSION,
        "translation_esp_sha256": SHA_ESP,
        "translation_top_sha256": SHA_TOP,
        "korean_font_license_member":
            "payload/resources/vfs/fonts/Galmuri11-OFL-1.1.md",
        "note": "OpenMW base source is located by immutable upstream commit; "
                "the exact 17 Korean patch bytes and build workflow are inside this ZIP. "
                "External URL reachability must be confirmed before publishing.",
    }
    additional[SOURCE_INSTRUCTIONS] = instructions.encode("utf-8")
    additional[THIRD_PARTY] = third_party.encode("utf-8")
    additional[SOURCE_MANIFEST] = (
        json.dumps(provenance, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode("utf-8")

    # Append in one documented, source-independent order.
    ordered = {
        SOURCE_LICENSE: additional[SOURCE_LICENSE],
        SOURCE_INSTRUCTIONS: additional[SOURCE_INSTRUCTIONS],
        SOURCE_MANIFEST: additional[SOURCE_MANIFEST],
        THIRD_PARTY: additional[THIRD_PARTY],
        SOURCE_BUILD_WORKFLOW: additional[SOURCE_BUILD_WORKFLOW],
    }
    for row in patches:
        ordered[row["bundle_member"]] = additional[row["bundle_member"]]
    require(len(ordered) == 22, "Public source/license bundle size changed")

    # Existing default (internal) candidate state must not be modified by
    # call-site reuse; public fields belong only to a distinct source dict.
    ready = dict(source)
    ready["changed"] = dict(source["changed"])
    ready["changed"][README_MEMBER] = codecs.BOM_UTF8 + PUBLIC_NOTES.encode("utf-8")
    ready["changed"][NEW_NOTE_MEMBER] = ready["changed"][README_MEMBER]
    ready["extra_members"] = ordered
    ready["public"] = True
    ready["source_provenance"] = provenance
    return ready


def preflight(base_zip: Path, engine: Path, core_dir: Path, resources_dir: Path) -> dict:
    base_zip = base_zip.resolve(strict=True)
    engine = engine.resolve(strict=True)
    core_dir = core_dir.resolve(strict=True)
    resources_dir = resources_dir.resolve(strict=True)
    require(base_zip != OUTPUT and not OUTPUT.is_file(), "Invalid candidate output path")
    baseline = read_pinned(base_zip, SHA_BASE, "Immutable public KR12.9 full ZIP")
    executable = read_pinned(engine, SHA_EXE, "OpenMW 0.51.0 + 0017 runtime")
    version = read_pinned(resources_dir / "version", SHA_RESOURCE_VERSION,
                          "Matching OpenMW 0.51.0 + 0017 resources/version")
    verify_matching_resource_version(version)
    esp = read_pinned(core_dir / (MOD_BASE + ".esp"), SHA_ESP, "Reviewed v10 core ESP")
    top = read_pinned(core_dir / (MOD_BASE + ".top"), SHA_TOP, "Reviewed v10 core TOP")
    require(executable.startswith(b"MZ") and len(executable) > 20_000_000, "Invalid Windows PE executable")
    require(esp.startswith(b"TES3") and top.startswith(codecs.BOM_UTF8), "Invalid ESP/TOP signatures")

    report_raw = read_pinned(NATIVE_REPORT, SHA_REPORT, "Authoritative v10 native report")
    report = json.loads(report_raw.decode("utf-8"))
    configs = report.get("configurations", [])
    require(bool(report.get("pfp_included")), "v10 report omitted Patch for Purists")
    require(len(configs) == 24 and len({x["configuration"] for x in configs}) == 12,
            "Authoritative v10 12-by-2 configurations changed")
    require(all(x["mode"] in ("discovery", "display") and
                x.get("unreviewed_link_losses") == 0 for x in configs),
            "v10 native regression report has unreviewed link losses")
    require(report.get("unreviewed_losses") == [], "v10 native report has unreviewed losses")
    require(report.get("runner_sha256") == SHA_RUNNER_0017,
            "v10 verifier was not compiled with the expected 0017 runner")

    with zipfile.ZipFile(io.BytesIO(baseline), "r") as src:
        infos = src.infolist()
        names = tuple(info.filename for info in infos)
        require(names == BASE_MEMBERS, "KR12.9 ZIP member names/order differ from pinned allowlist")
        require(src.testzip() is None, "KR12.9 ZIP CRC validation failed")
        require(not src.comment, "Unexpected source ZIP comment")
        for info in infos:
            require(not info.flag_bits & 1, f"Encrypted source ZIP member: {info.filename}")
            require(info.is_dir() == info.filename.endswith("/"),
                    f"Source ZIP path metadata mismatch: {info.filename}")
        original = {info.filename: src.read(info) for info in infos}

    for name, expected in (
        (EXE_MEMBER, SHA_OLD_EXE),
        (ESP_MEMBER, SHA_OLD_ESP),
        (TOP_MEMBER, SHA_OLD_TOP),
        (INSTALLER_MEMBER, SHA_OLD_INSTALLER),
        (README_MEMBER, SHA_OLD_README),
        (OLD_NOTE_MEMBER, SHA_OLD_README),
    ):
        require(digest(original[name]) == expected, f"Public ZIP member SHA changed: {name}")
    verify_korean_font_payload(original)
    require(original[README_MEMBER] == original[OLD_NOTE_MEMBER],
            "KR12.9 release notes/README no longer match")

    for extension in (".cel", ".jrn", ".mrk"):
        name = MOD_BASE + extension
        require(read_pinned(core_dir / name, digest(original[CORE_PATH + name]),
                            f"v10 unchanged {name}") == original[CORE_PATH + name],
                f"Unexpected core companion file change: {name}")

    installer = make_installer(original[INSTALLER_MEMBER])
    notes = make_notes(original[README_MEMBER])
    changes = {
        EXE_MEMBER: executable,
        VERSION_MEMBER: version,
        ESP_MEMBER: esp,
        TOP_MEMBER: top,
        INSTALLER_MEMBER: installer,
        README_MEMBER: notes,
        NEW_NOTE_MEMBER: notes,
    }
    require(set(changes) == {EXE_MEMBER, VERSION_MEMBER, ESP_MEMBER, TOP_MEMBER,
                            INSTALLER_MEMBER, README_MEMBER, NEW_NOTE_MEMBER},
            "Candidate change allowlist drifted")
    return {
        "infos": infos,
        "original": original,
        "changed": changes,
        "inputs": {
            "public_kr12_9_zip": {"name": base_zip.name, "sha256": SHA_BASE, "bytes": len(baseline)},
            "windows_051_0017_exe": {"name": engine.name, "sha256": SHA_EXE, "bytes": len(executable)},
            "runtime_resources_version": {
                "name": "resources/version", "sha256": SHA_RESOURCE_VERSION, "bytes": len(version),
                "source_revision": "f4bec41444214a7903bebd178389ca22ca13f646",
                "patched_revision": "4ff261bf7c0d42a6cc06dd1ebc5d451802cff055",
            },
            "v10_core_esp": {"name": ESP_MEMBER, "sha256": SHA_ESP, "bytes": len(esp)},
            "v10_core_top": {"name": TOP_MEMBER, "sha256": SHA_TOP, "bytes": len(top)},
            "native_24_mode_report_sha256": SHA_REPORT,
        },
    }


def create_zip_bytes(source: dict) -> bytes:
    """Rebuild in memory: no temp release or writes outside the selected output."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for source_info in source["infos"]:
            name = source_info.filename
            final_name = NEW_NOTE_MEMBER if name == OLD_NOTE_MEMBER else name
            data = source["changed"].get(final_name, source["original"][name])
            info = copy.copy(source_info)
            if final_name != name:
                info.filename = final_name
                info.orig_filename = final_name
            archive.writestr(info, data)
            if name == "payload/resources/":
                # Generated 92-byte OpenMW build metadata only. Do NOT copy
                # stock fonts, game masters or the full upstream resources tree.
                version_info = zipfile.ZipInfo(VERSION_MEMBER, date_time=source_info.date_time)
                version_info.compress_type = zipfile.ZIP_DEFLATED
                version_info.external_attr = 0o100644 << 16
                archive.writestr(version_info, source["changed"][VERSION_MEMBER])
        for name, data in source.get("extra_members", {}).items():
            require(name not in FINAL_MEMBERS and not name.endswith("/") and
                    "\\" not in name and ".." not in Path(name).parts,
                    f"Unapproved public source member name: {name}")
            # Explicitly set metadata to ensure identical bytes across builds.
            source_info = zipfile.ZipInfo(name, date_time=(2026, 11, 11, 0, 0, 0))
            source_info.compress_type = zipfile.ZIP_DEFLATED
            source_info.external_attr = 0o100644 << 16
            archive.writestr(source_info, data)
    return buffer.getvalue()


def verify_zip_bytes(source: dict, data: bytes) -> dict:
    extras = source.get("extra_members", {})
    require(bool(extras) == bool(source.get("public")),
            "Internal/public source asset mode mismatch")
    with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
        names = tuple(archive.namelist())
        wanted = FINAL_MEMBERS + tuple(extras)
        require(names == wanted and len(names) == len(set(names)) == 43 + len(extras),
                "KR13 ZIP member names/count/order failed")
        require(archive.testzip() is None, "KR13 ZIP CRC validation failed")
        require(not archive.comment, "KR13 ZIP has unexpected comment")
        changed_rows = []
        unchanged_count = 0
        old_infos = {x.filename: x for x in source["infos"]}
        for dst_info in archive.infolist():
            final_name = dst_info.filename
            if final_name in extras:
                current = archive.read(dst_info)
                require(current == extras[final_name],
                        f"Corresponding source/license bytes modified: {final_name}")
                require(dst_info.date_time == (2026, 11, 11, 0, 0, 0),
                        f"Source member timestamp non-deterministic: {final_name}")
                changed_rows.append({
                    "source_member": None,
                    "candidate_member": final_name,
                    "original_sha256": None,
                    "candidate_sha256": digest(current),
                    "original_bytes": 0,
                    "candidate_bytes": len(current),
                })
                continue
            if final_name == VERSION_MEMBER:
                current = archive.read(dst_info)
                require(current == source["changed"][VERSION_MEMBER],
                        "Packaged resources/version does not match engine")
                verify_matching_resource_version(current)
                changed_rows.append({
                    "source_member": None,
                    "candidate_member": VERSION_MEMBER,
                    "original_sha256": None,
                    "candidate_sha256": digest(current),
                    "original_bytes": 0,
                    "candidate_bytes": len(current),
                })
                continue
            name = OLD_NOTE_MEMBER if final_name == NEW_NOTE_MEMBER else final_name
            require(name in old_infos, f"KR13 member not derived from KR12.9: {final_name}")
            src_info = old_infos[name]
            previous = source["original"][name]
            current = archive.read(dst_info)
            expected = source["changed"].get(final_name, previous)
            require(current == expected, f"KR13 ZIP payload differs from approved byte source: {final_name}")
            require(dst_info.date_time == src_info.date_time and
                    dst_info.compress_type == src_info.compress_type,
                    f"KR13 member metadata drift: {final_name}")
            if name != final_name or previous != current:
                require(final_name in source["changed"], f"Unapproved member changed: {final_name}")
                changed_rows.append({
                    "source_member": name,
                    "candidate_member": final_name,
                    "original_sha256": digest(previous),
                    "candidate_sha256": digest(current),
                    "original_bytes": len(previous),
                    "candidate_bytes": len(current),
                })
            else:
                unchanged_count += 1
        require(len(changed_rows) == 7 + len(extras) and unchanged_count == 36,
                "KR13 change scope must be exactly the approved payload/version/source members")
        verify_korean_font_payload({
            member: archive.read(member) for member in FONT_MEMBERS
        })
        require(b'"resources\\version"' in archive.read(INSTALLER_MEMBER),
                "Installer omits matched resources/version installation")
        require(not any(n.lower().endswith((".esm", ".bsa")) for n in names),
                "Original copyrighted game masters/archives may not be bundled")
        if source.get("public"):
            require(len(extras) == 22 and
                    len([x for x in names if x.startswith(SOURCE_PATCH_PREFIX)]) == 17,
                    "Public archive must include GPL license and all 17 source patches")
            require(digest(archive.read(SOURCE_LICENSE)) == SHA_GPL,
                    "Public GPLv3 license was altered")
            require(digest(archive.read(SOURCE_BUILD_WORKFLOW)) == SHA_WINDOWS_WORKFLOW,
                    "Build script provenance changed")
            require(b"GPLv3" in archive.read(README_MEMBER) and
                    b"GNU GENERAL PUBLIC LICENSE" in archive.read(SOURCE_LICENSE),
                    "Public release copyright notice missing")
            require(b"\xeb\x82\xb4\xeb\xb6\x80 \xea\xb2\x80\xec\xa6\x9d\xec\x9a\xa9" not in
                    archive.read(README_MEMBER),
                    "Internal-only label must not appear in public-facing README")
            require(b"OpenMW source revision:" not in archive.read(SOURCE_MANIFEST),
                    "Public source provenance must use structured JSON")
            source_rows = json.loads(archive.read(SOURCE_MANIFEST))
            require(source_rows == source["source_provenance"],
                    "Public provenance manifest and patch hashes disagree")
        return {"member_count": len(names), "changed_member_count": len(changed_rows),
                "unchanged_member_count": unchanged_count, "changed_members": changed_rows,
                "crc": "PASS", "member_allowlist": "PASS", "unchanged_payloads": "PASS"}


def make_manifest(source: dict, zip_data: bytes, checks: dict) -> dict:
    is_public = bool(source.get("public"))
    return {
        "schema": "openmw_kr13_windows_public_staging_v1" if is_public else
                  "openmw_kr13_windows_candidate_v1",
        "candidate_only": True,
        **({"public_staging_only": True} if is_public else {}),
        "published": False,
        "commit_or_upload_performed": False,
        "windows_target": "OpenMW 0.51.0 x64 / Korean patches 0001-0017",
        "tag_if_eventually_approved": "openmw-0.51.0-kr13",
        "regional_zips_included": False,
        "engine_resources_version_installed": True,
        "korean_font_and_license_preserved": True,
        "in_game_quest_and_save_reload_verified": False,
        "source_inputs": source["inputs"],
        **({"corresponding_source": {
            "license_sha256": SHA_GPL,
            "upstream_commit": SOURCE_UPSTREAM,
            "source_manifest_sha256": digest(source["extra_members"][SOURCE_MANIFEST]),
            "included_patch_count": 17,
            "build_workflow_sha256": SHA_WINDOWS_WORKFLOW,
            "upstream_source_url": source["source_provenance"]["upstream_source"]["download_url"],
            "external_url_reachability_verified": False,
        }} if is_public else {}),
        "output": {
            "zip_name": ARCHIVE_NAME, "sha256": digest(zip_data), "bytes": len(zip_data),
            "sha256_sidecar": ARCHIVE_NAME + ".sha256",
        },
        "validation": checks,
        "blockers": ([
            "Check network access and enduring availability of the immutable upstream corresponding-source URL before publication",
            "Public KR13 tag must carry the generic release.yml tag exclusion at tag creation",
        ] if is_public else []) + [
            "Actual 0.51.0 + 0017 GUI NPC acquisition/click and save/reload not verified by this packager",
            "Region kr0.3 follow-up ZIPs must be built, distinctly versioned, and integration-tested separately",
            "Patch for Purists and alternate Rebirth combinations still require matched in-game smoke tests",
            "This local candidate must not be published until release approval",
        ],
    }


def check_existing(source: dict) -> dict:
    target = PUBLIC_OUTPUT if source.get("public") else OUTPUT
    manifest_filename = PUBLIC_MANIFEST_NAME if source.get("public") else MANIFEST_NAME
    path = target / ARCHIVE_NAME
    manifest_path = target / manifest_filename
    sha_path = target / (ARCHIVE_NAME + ".sha256")
    require(path.is_file() and sha_path.is_file() and manifest_path.is_file(),
            "Incomplete KR13 candidate output directory")
    rebuilt = create_zip_bytes(source)
    actual = path.read_bytes()
    require(actual == rebuilt, "Candidate ZIP is not bit-for-bit reproducible")
    checks = verify_zip_bytes(source, actual)
    expected = make_manifest(source, actual, checks)
    stored = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(stored == expected, "Candidate manifest does not match pinned inputs")
    require(sha_path.read_bytes() ==
            f"{digest(actual)}  {ARCHIVE_NAME}\n".encode("ascii"), "Candidate .sha256 sidecar mismatch")
    return expected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-staging", action="store_true",
                        help="Build public-facing staging ZIP with GPL/source patches; "
                             "never modifies the internal KR13 candidate")
    parser.add_argument("--base-zip", type=Path, default=DEFAULT_BASE,
                        help="Immutable KR12.9 full ZIP (exact SHA required)")
    parser.add_argument("--engine", type=Path, default=DEFAULT_ENGINE,
                        help="OpenMW 0.51.0 + 0017 executable (exact SHA required)")
    parser.add_argument("--resources-dir", type=Path, default=DEFAULT_RESOURCES,
                        help="Matched 0.51.0 + 0017 resources directory; only version is bundled")
    parser.add_argument("--core-dir", type=Path, default=DEFAULT_CORE,
                        help="v10 core ESP/TOP/CEL/MRK/JRN folder (exact SHA required)")
    exclusive = parser.add_mutually_exclusive_group()
    exclusive.add_argument("--check-only", action="store_true", help="Read-only input preflight")
    exclusive.add_argument("--verify-existing", action="store_true",
                           help="Read-only, byte-for-byte candidate re-build/verification")
    args = parser.parse_args()
    source = preflight(args.base_zip, args.engine, args.core_dir, args.resources_dir)
    if args.public_staging:
        source = make_public_assets(source)
    target = PUBLIC_OUTPUT if args.public_staging else OUTPUT
    manifest_filename = PUBLIC_MANIFEST_NAME if args.public_staging else MANIFEST_NAME
    if args.check_only:
        print(json.dumps({"result": "PASS", "mode": "preflight",
                          "output": str(target), "inputs": source["inputs"],
                          "public_source_patches": len(source.get("extra_members", {})) - 5
                          if args.public_staging else 0},
                         indent=2, ensure_ascii=False))
        return 0
    if args.verify_existing:
        report = check_existing(source)
        print(json.dumps({"result": "PASS", "mode": "verify-existing",
                          "zip_sha256": report["output"]["sha256"],
                          "manifest": str(target / manifest_filename)},
                         indent=2, ensure_ascii=False))
        return 0

    # Never overwrite existing artifacts. A directory containing ONLY the
    # explicitly quarantined pre-resource INTERNAL candidate can be reused.
    # Public staging MUST be a completely new, exclusive output directory.
    preexisting_output = target.exists()
    if preexisting_output:
        require(target.is_dir(), f"Candidate output path is not a directory: {target}")
        unexpected = {p.name for p in target.iterdir()} - (
            set() if args.public_staging else {"superseded-incomplete-resources-v1"}
        )
        require(not unexpected,
                f"Output directory already has files; refuse overwrite: {sorted(unexpected)}")
        require(not args.public_staging, "Never reuse an existing public staging directory")
    zip_data = create_zip_bytes(source)
    checks = verify_zip_bytes(source, zip_data)
    # An independent second in-memory ZIP build catches accidental unstable
    # metadata, timestamps, unordered member generation or compression choices.
    require(zip_data == create_zip_bytes(source), "Non-deterministic ZIP build")
    manifest = make_manifest(source, zip_data, checks)
    require(target.parent == WORK and target.name in
            ("release-KR13-CANDIDATE", "release-KR13-PUBLIC-STAGING"),
            "Refusing output path outside fixed workspace")
    if not preexisting_output:
        target.mkdir(parents=False, exist_ok=False)
    try:
        (target / ARCHIVE_NAME).write_bytes(zip_data)
        (target / (ARCHIVE_NAME + ".sha256")).write_bytes(
            f"{digest(zip_data)}  {ARCHIVE_NAME}\n".encode("ascii"))
        (target / manifest_filename).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        require(check_existing(source) == manifest, "Post-write candidate verification failed")
    except Exception:
        # Only clean newly-created artifacts, never the quarantined candidate.
        if preexisting_output:
            for name in (ARCHIVE_NAME, ARCHIVE_NAME + ".sha256", manifest_filename):
                (target / name).unlink(missing_ok=True)
        else:
            shutil.rmtree(target)
        raise
    print(json.dumps({"result": "PASS", "mode": "candidate-build",
                      "zip": str(target / ARCHIVE_NAME),
                      "sha256": digest(zip_data),
                      "manifest": str(target / manifest_filename),
                      "members": checks["member_count"],
                      "changed": checks["changed_member_count"],
                      "unchanged": checks["unchanged_member_count"]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
