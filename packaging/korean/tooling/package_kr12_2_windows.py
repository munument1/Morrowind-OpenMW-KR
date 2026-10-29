#!/usr/bin/env python3
"""Build a KR12.2 release candidate from the immutable KR12.1 Windows ZIP.

KR12.1 ships a newer openmw.exe but does not install the matching default
settings, HUD layout/skin, and mouse-cursor texture.  This packages the
matching assets from the *same Git tag* as the KR12.1 executable source.
It deliberately keeps the executable, translation ESP, and all other
unrelated ZIP members byte-identical.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[3]
SOURCE_REF = "openmw-0.51.0-kr12.1"
BASE_EXE = "payload/openmw.exe"
BASE_ESP = "payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.esp"
ESP_SHA256 = "0f04a21d69ecae16a1c2ae3bb0b739ac4e71cdb59054c809fc844128e2c12327"
INSTALLER = "install-korean.ps1"
README = "README-KOREAN.txt"

RUNTIME_ASSETS = {
    "payload/settings-default.cfg": "files/settings-default.cfg",
    "payload/resources/vfs/mygui/openmw_hud.layout": "files/data/mygui/openmw_hud.layout",
    "payload/resources/vfs/mygui/openmw_hud_box.skin.xml": "files/data/mygui/openmw_hud_box.skin.xml",
    "payload/resources/vfs/textures/omw_mouse_emulation_cursor.dds": "files/data/textures/omw_mouse_emulation_cursor.dds",
}
REQUIRED_INSTALLER_PATHS = (
    "settings-default.cfg",
    r"resources\vfs\mygui\openmw_hud.layout",
    r"resources\vfs\mygui\openmw_hud_box.skin.xml",
    r"resources\vfs\textures\omw_mouse_emulation_cursor.dds",
)

README_TEXT = """OpenMW 0.51.0 한국어 KR12.2 Windows 호환성 수정 후보

정품 Morrowind 데이터 및 공식 OpenMW 0.51.0 Windows x64 설치본이 필요합니다.

설치:
1. 기존 세이브와 OpenMW 설정을 백업하세요.
2. 이 ZIP을 별도 폴더에 압축 해제하세요.
3. Install-Korean.bat을 실행해 OpenMW 설치 위치를 지정하세요.
4. 실행 및 새 게임 시작을 확인하세요.

KR12.2 변경:
- KR12.1과 동일한 openmw.exe 및 번역 ESP를 유지합니다.
- 엔진과 짝이 맞는 settings-default.cfg, HUD 레이아웃/스킨,
  mouse emulation cursor 텍스처를 함께 설치합니다.
- 설치 시 덮어쓰는 기존 파일을 백업합니다.
- KR12.1의 퀘스트/마법 표시/Firemoth 셀 데이터는 유지합니다.

주의: 'meshes/base_anim.nif not found'는 원본 게임 Data Files 또는
Morrowind.bsa 등록 문제일 수 있습니다. OpenMW Launcher에서 정품
Morrowind 데이터 경로와 BSA 설정을 별도로 확인하세요.

소스 및 배포 파일의 구조 검증과 실제 Windows 게임 실행 검증은
서로 다릅니다. 게임 실행 검증을 통과하기 전에는 정식 배포하지 않습니다.
"""

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def pinned_file(path: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{SOURCE_REF}:{path}"], cwd=REPO
    )

def verify_assets(assets: dict[str, bytes], installer: bytes) -> None:
    settings = assets["payload/settings-default.cfg"].decode("utf-8")
    layout = assets["payload/resources/vfs/mygui/openmw_hud.layout"].decode("utf-8")
    skin = assets["payload/resources/vfs/mygui/openmw_hud_box.skin.xml"].decode("utf-8")
    cursor = assets["payload/resources/vfs/textures/omw_mouse_emulation_cursor.dds"]
    script = installer.decode("utf-8")
    if "[HUD]" not in settings or "mouse emulation cursor = true" not in settings:
        raise ValueError("KR12.1 native HUD setting missing in default configuration")
    if 'name="MouseEmulationCursor"' not in layout:
        raise ValueError("KR12.1 HUD layout missing the cursor widget")
    if 'name="HUD_MouseEmulationCursor"' not in skin:
        raise ValueError("KR12.1 HUD skin missing the cursor resource")
    if "omw_mouse_emulation_cursor.dds" not in skin or not cursor.startswith(b"DDS "):
        raise ValueError("KR12.1 mouse cursor texture missing or invalid")
    ET.fromstring(layout)
    ET.fromstring(skin)
    for target in REQUIRED_INSTALLER_PATHS:
        if f'"{target}"' not in script:
            raise ValueError("Installer does not copy runtime asset: " + target)

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    if args.baseline.resolve() == args.output.resolve():
        raise ValueError("Baseline and output ZIP paths must differ")

    installer = (REPO / "packaging/korean/install-korean.ps1").read_bytes()
    assets = {dest: pinned_file(src) for dest, src in RUNTIME_ASSETS.items()}
    verify_assets(assets, installer)
    readme = README_TEXT.encode("utf-8")
    replacement = {**assets, INSTALLER: installer, README: readme}

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.baseline, "r") as base:
        names = base.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate member in KR12.1 baseline")
        for name in (BASE_EXE, BASE_ESP, INSTALLER, README, "Install-Korean.bat"):
            if names.count(name) != 1:
                raise ValueError("KR12.1 member missing or duplicated: " + name)
        exe = base.read(BASE_EXE)
        if not exe.startswith(b"MZ") or len(exe) < 10_000_000:
            raise ValueError("Invalid KR12.1 Windows executable")
        if sha256(base.read(BASE_ESP)) != ESP_SHA256:
            raise ValueError("Translation ESP is not the verified KR12.1 ESP")
        with zipfile.ZipFile(args.output, "w") as dst:
            for item in base.infolist():
                dst.writestr(item, replacement.get(item.filename, base.read(item.filename)))
            for name, value in assets.items():
                if name not in names:
                    dst.writestr(name, value, compress_type=zipfile.ZIP_DEFLATED)

    with zipfile.ZipFile(args.baseline, "r") as base, zipfile.ZipFile(args.output, "r") as built:
        if built.testzip() is not None:
            raise ValueError("Output ZIP failed CRC verification")
        expected_names = base.namelist() + [n for n in assets if n not in base.namelist()]
        if built.namelist() != expected_names:
            raise ValueError("Output ZIP member order/inventory mismatch")
        for name in base.namelist():
            if name not in replacement and base.read(name) != built.read(name):
                raise ValueError("Unexpected change to KR12.1 member: " + name)
        for name, value in replacement.items():
            if built.read(name) != value:
                raise ValueError("Expected replacement was not packaged: " + name)
        if base.read(BASE_EXE) != built.read(BASE_EXE) or base.read(BASE_ESP) != built.read(BASE_ESP):
            raise ValueError("KR12.1 executable or ESP changed")

    digest = sha256(args.output.read_bytes())
    report = {
        "candidate_version": "KR12.2",
        "source_tag_for_engine_assets": SOURCE_REF,
        "baseline_kr12_1_zip_sha256": sha256(args.baseline.read_bytes()),
        "candidate_zip_sha256": digest,
        "executable_unchanged": True,
        "translation_esp_unchanged": True,
        "installer_updated_with_backups": True,
        "runtime_assets": {name: sha256(blob) for name, blob in assets.items()},
        "other_members_byte_identical": True,
        "package_integrity": "PASS",
        "live_windows_gameplay_tested": False,
        "release_ready": False,
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output.parent / (args.output.name + ".sha256")).write_text(
        digest + "  " + args.output.name + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
