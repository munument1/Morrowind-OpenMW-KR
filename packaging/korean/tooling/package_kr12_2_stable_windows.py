#!/usr/bin/env python3
"""Create a private KR12.2 TEST candidate from a real OpenMW 0.51.0 build.

Only used by the dedicated CI workflow that checks out OpenMW/openmw
tag openmw-0.51.0 and applies Korean runtime patches. This does NOT
publish a release or assert live game compatibility.
"""
import argparse
import hashlib
import json
import pathlib
import zipfile

BASE_ESP = "payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.esp"
EXE = "payload/openmw.exe"
README = "README-KOREAN.txt"
KNOWN_ESP_SHA = "0f04a21d69ecae16a1c2ae3bb0b739ac4e71cdb59054c809fc844128e2c12327"

README_TEXT = """OpenMW 0.51.0 Korean Support KR12.2 — Windows TEST CANDIDATE

이 파일은 Windows 시험용이며 공식 KR12.2 릴리스가 아닙니다.
공식 OpenMW 0.51.0 소스에 한국어 엔진 패치를 적용하여 빌드한
openmw.exe 및 KR12.1의 번역 데이터를 포함합니다.

필수: 정품 Morrowind 및 공식 OpenMW 0.51.0 Windows x64 설치본.

1. 기존 OpenMW 설치 폴더와 설정, 세이브를 먼저 백업하세요.
2. 별도 폴더에 ZIP을 풀고 Install-Korean.bat을 실행하세요.
3. 실행할 OpenMW 설치 폴더를 직접 확인하고 선택하세요.
4. HUD, 커서, 한국어 대화, 영상 자막, 새 게임 시작을 확인하세요.
5. 오류가 발생하면 openmw.log, openmw.cfg, 재현 절차를 제보하세요.

주의: 'meshes/base_anim.nif not found'는 원본 Morrowind.bsa 또는
Data Files 등록 문제일 수 있습니다. 별도로 확인하세요.

ESP/CEL/MRK/TOP/JRN 번역 데이터는 KR12.1 그대로 유지합니다.
실제 Windows 게임 플레이 테스트는 아직 수행되지 않았습니다.
이 후보 파일을 정식 배포본처럼 재배포하지 마세요.
"""

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    p = argparse.ArgumentParser()
    for item in ("baseline", "engine", "output", "report"):
        p.add_argument("--" + item, type=pathlib.Path, required=True)
    args = p.parse_args()
    if args.baseline.resolve() == args.output.resolve():
        raise ValueError("Cannot overwrite the KR12.1 baseline")
    exe = args.engine.read_bytes()
    if not exe.startswith(b"MZ") or len(exe) < 10_000_000:
        raise ValueError("Not a valid Windows OpenMW executable")
    # The executable's release version must agree with the locked build source.
    if not any(v in exe for v in (b"0.51.0", "0.51.0".encode("utf-16le"))):
        raise ValueError("OpenMW executable lacks a 0.51.0 version marker")
    with zipfile.ZipFile(args.baseline) as src:
        names = src.namelist()
        if len(set(names)) != len(names):
            raise ValueError("Duplicate members in original KR12.1 ZIP")
        for name in (EXE, BASE_ESP, "Install-Korean.bat", "install-korean.ps1", README):
            if names.count(name) != 1:
                raise ValueError("Missing required entry " + name)
        if sha(src.read(BASE_ESP)) != KNOWN_ESP_SHA:
            raise ValueError("Original ESP is not the verified KR12.1 release")
        if src.read(EXE) == exe:
            raise ValueError("0.51 candidate binary equals the KR12.1 0.52 binary")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.output, "w") as dst:
            for member in src.infolist():
                if member.filename == EXE:
                    value = exe
                elif member.filename == README:
                    value = README_TEXT.encode("utf-8")
                else:
                    value = src.read(member.filename)
                dst.writestr(member, value)
    with zipfile.ZipFile(args.baseline) as before, zipfile.ZipFile(args.output) as after:
        assert after.testzip() is None
        assert before.namelist() == after.namelist()
        for name in before.namelist():
            if name not in (EXE, README) and before.read(name) != after.read(name):
                raise ValueError("Unexpected original KR12.1 member change: " + name)
        assert after.read(EXE) == exe
    result = {
        "candidate": "KR12.2 Windows TEST",
        "engine_source": "OpenMW/openmw@openmw-0.51.0 + Korean patchset",
        "engine_sha256": sha(exe),
        "kr12_1_esp_preserved": True,
        "kr12_1_other_translation_assets_preserved": True,
        "baseline_sha256": sha(args.baseline.read_bytes()),
        "output_sha256": sha(args.output.read_bytes()),
        "zip_integrity": "PASS",
        "live_gameplay_verified": False,
        "release_ready": False,
    }
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output.parent / (args.output.name + ".sha256")).write_text(
        result["output_sha256"] + "  " + args.output.name + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
