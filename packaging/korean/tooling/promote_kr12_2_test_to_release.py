#!/usr/bin/env python3
"""Promote exactly user-tested KR12.2 Run #5, without recompiling OpenMW.

Change only four stale KR6 installer labels and the README. Validate the
executable, ESP and all remaining ZIP members against the user-tested archive.
"""
import argparse
import copy
import hashlib
import io
import json
import pathlib
import zipfile

TEST_ZIP = "Morrowind-Korean-OpenMW-0.51.0-KR12.2-TEST.zip"
TEST_SHA = "6ef685f0ddbfcbb94e72526fa355a319e1d8f7b0fbeff70bc04a77e778f9d508"
ENGINE_SHA = "219df4c203c59021b515233de006eeb365b8362ac20f1dbcc2f69e73b24ec47f"
ESP_SHA = "0f04a21d69ecae16a1c2ae3bb0b739ac4e71cdb59054c809fc844128e2c12327"
ENGINE = "payload/openmw.exe"
ESP = "payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.esp"
FIXES = {
    "korean-kr6-backup-": "korean-kr12.2-backup-",
    "OPENMW-KOREAN-KR6.txt": "OPENMW-KOREAN-KR12.2.txt",
    "OpenMW 0.51.0 Korean Support KR6": "OpenMW 0.51.0 Korean Support KR12.2",
    "Korean OpenMW KR6 installation completed.": "Korean OpenMW KR12.2 installation completed.",
}
README = """OpenMW 0.51.0 Korean Support KR12.2 — Windows x64

공식 OpenMW 0.51.0 기반 한국어 엔진과 KR12.1 번역 데이터(ESP/CEL/TOP/MRK/JRN)를 포함합니다.
Windows 사용자 실기 테스트에서 게임 구동, NPC 한국어 대화 및 주제 링크가 정상이라고 확인되었습니다.
모든 퀘스트와 모드 조합의 호환성을 보증하지는 않습니다.

설치:
1. 기존 OpenMW 0.51.0 폴더, openmw.cfg 및 세이브를 백업합니다.
2. 압축 해제 후 Install-Korean.bat 실행, 기존 OpenMW 0.51.0 설치 폴더를 지정합니다.
   모로윈드 원본 게임 Data Files 폴더를 지정하지 마세요.
3. 설치 완료 메시지에 KR12.2가 표시되는지 확인합니다.
4. OpenMW Launcher에서 원본 Morrowind.esm/Tribunal.esm/Bloodmoon.esm 및
   해당 Morrowind.bsa/Tribunal.bsa/Bloodmoon.bsa의 설치·등록 상태를 확인합니다.
5. 게임 시작과 한국어 대화·일지·영상 자막·HUD·저장/불러오기를 확인합니다.

기존 설치기의 KR6 표기는 구형 설치 스크립트에서 발생한 것으로 엔진 버전과는 무관합니다.
기존 openmw.cfg에서 종료되지 않은 fallback 관리 블록을 복구하면 별도 백업을 생성합니다.
'meshes/base_anim.nif not found' 오류는 원본 게임 데이터/BSA 등록 상태부터 확인하세요.

엔진 출처: OpenMW/openmw@openmw-0.51.0 + 저장소의 한국어 패치
검증에 사용한 원본 Run: https://github.com/munument1/Morrowind-OpenMW-KR/actions/runs/40969072933
이 파일은 Windows x64 전용입니다. Android 별도 배포.
문제 보고: https://github.com/munument1/Morrowind-OpenMW-KR/issues
"""

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, type=pathlib.Path)
    ap.add_argument("--output", required=True, type=pathlib.Path)
    ap.add_argument("--report", required=True, type=pathlib.Path)
    args = ap.parse_args()
    source_bytes = args.source.read_bytes()
    # actions/download-artifact extracts the wrapper ZIP. Also accept wrapper for offline testing.
    with zipfile.ZipFile(io.BytesIO(source_bytes)) as outer:
        if TEST_ZIP in outer.namelist():
            source_bytes = outer.read(TEST_ZIP)
    if sha(source_bytes) != TEST_SHA:
        raise ValueError("The source is NOT the user-tested Run #5 artifact")
    with zipfile.ZipFile(io.BytesIO(source_bytes)) as original:
        if original.testzip() is not None:
            raise ValueError("Original ZIP CRC failed")
        names = original.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate ZIP entries")
        for expected in ("install-korean.ps1", "README-KOREAN.txt", ENGINE, ESP):
            if names.count(expected) != 1:
                raise ValueError("Required member absent or duplicated: " + expected)
        if sha(original.read(ENGINE)) != ENGINE_SHA or sha(original.read(ESP)) != ESP_SHA:
            raise ValueError("Original executable / translation ESP mismatch")
        installer = original.read("install-korean.ps1").decode("utf-8-sig")
        for old, new in FIXES.items():
            if installer.count(old) != 1:
                raise ValueError("Unexpected KR6 label cardinality: " + old)
            installer = installer.replace(old, new)
        if "kr6" in installer.lower():
            raise ValueError("KR6 marker remains in installer")
        edits = {
            "install-korean.ps1": installer.encode("utf-8-sig"),
            "README-KOREAN.txt": README.encode("utf-8")
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.output, "w") as result:
            for info in original.infolist():
                data = edits.get(info.filename)
                if data is None:
                    data = original.read(info.filename)
                result.writestr(copy.copy(info), data)
        with zipfile.ZipFile(args.output) as final:
            if final.testzip() is not None or final.namelist() != names:
                raise ValueError("Final ZIP integrity or member structure failed")
            for filename in names:
                if filename not in edits and final.read(filename) != original.read(filename):
                    raise ValueError("A user-tested file changed unexpectedly: " + filename)
            if sha(final.read(ENGINE)) != ENGINE_SHA or sha(final.read(ESP)) != ESP_SHA:
                raise ValueError("Final executable / translation ESP mismatch")
    report = {
        "version": "KR12.2 Windows x64",
        "test_run": 40969072933,
        "source_test_zip_sha256": TEST_SHA,
        "released_zip_sha256": sha(args.output.read_bytes()),
        "engine_sha256": ENGINE_SHA,
        "translation_esp_sha256": ESP_SHA,
        "zip_members": len(names),
        "modified_members": list(edits),
        "other_members_byte_identical": True,
        "archive_integrity": "PASS",
        "user_gameplay_report": "PASS: game and Korean dialogue/topics",
        "installer_label_retested_on_windows": False,
        "source_engine": "OpenMW/openmw@openmw-0.51.0 + Korean patches"
    }
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output.with_name(args.output.name + ".sha256").write_text(
        report["released_zip_sha256"] + "  " + args.output.name + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
