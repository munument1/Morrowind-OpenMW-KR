#!/usr/bin/env python3
"""Package an unreleased KR12.2 quest-topic test from official OpenMW 0.51.0.

CI must verify that the compiled engine comes from the exact upstream
openmw-0.51.0 commit, not the fork's 0.52.0 master. The published KR12.2
data is the baseline and only the four source-anchored quest INFO.NAME
strings may change. No original archives or saves are modified.
"""
import argparse
import hashlib
import json
import pathlib
import zipfile

from patch_kr12_quest_entry_topics import rewrite as rewrite_quest_topics

BASE_ESP = "payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.esp"
EXE = "payload/openmw.exe"
README = "README-KOREAN.txt"
KNOWN_ESP_SHA = "0f04a21d69ecae16a1c2ae3bb0b739ac4e71cdb59054c809fc844128e2c12327"
EXPECTED_QUEST_ESP_SHA = "c0cb2f5702da067e11820e5a11ffb4b758ea28e101779fc43a721072783ed253"

README_TEXT = """OpenMW 0.51.0 Korean Support KR12.2 — Quest Topic TEST CANDIDATE

이 파일은 Windows 비공개 시험용이며 공식 KR12.2/차기 릴리스가 아닙니다.
엔진은 공식 OpenMW/openmw 0.51.0 소스(f4bec41444214a7903bebd178389ca22ca13f646)에
한국어 패치를 적용해 빌드했습니다. 이 저장소 master의 0.52.0 소스는 사용하지 않았습니다.
번역 데이터는 공개 KR12.2 기준이고, 퀘스트 시작용 토픽 링크 4건만
조건과 스크립트를 변경하지 않고 수정했습니다.

1. 기존 게임 설치, 환경설정, 세이브를 백업하세요.
2. 별도 시험용 폴더에 풀고 설치 경로를 확인하세요.
3. 전사 길드 바스, 도둑 길드 이에니스, 메인 퀘스트 승진, 블러드문 결정 토픽을 확인하세요.
4. 다른 길드 및 대사 링크가 잘못 활성화되지 않는지도 검증하세요.
5. 오류는 log, 게임 버전, 모드 목록, 퀘스트 단계와 재현 절차를 제보하세요.

원본 Bethesda 게임 데이터가 별도로 필요합니다.
테스트 통과 전 공식 한국어판처럼 재배포하지 마세요.
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
        original_esp = src.read(BASE_ESP)
        if sha(original_esp) != KNOWN_ESP_SHA:
            raise ValueError("Original ESP is not the verified published KR12.2 release")
        candidate_esp, quest_qa = rewrite_quest_topics(original_esp)
        if sha(candidate_esp) != EXPECTED_QUEST_ESP_SHA:
            raise ValueError("Unexpected quest-topic candidate ESP hash")
        if not quest_qa["all_other_records_and_fields_unchanged"] or quest_qa["changed_info_count"] != 4:
            raise ValueError("Quest-topic source physical QA failed")
        if src.read(EXE) == exe:
            raise ValueError("0.51 candidate executable identical to published baseline")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.output, "w") as dst:
            for member in src.infolist():
                if member.filename == EXE:
                    value = exe
                elif member.filename == BASE_ESP:
                    value = candidate_esp
                elif member.filename == README:
                    value = README_TEXT.encode("utf-8")
                else:
                    value = src.read(member.filename)
                dst.writestr(member, value)
    with zipfile.ZipFile(args.baseline) as before, zipfile.ZipFile(args.output) as after:
        assert after.testzip() is None
        assert before.namelist() == after.namelist()
        for name in before.namelist():
            if name not in (EXE, BASE_ESP, README) and before.read(name) != after.read(name):
                raise ValueError("Unexpected published KR12.2 member change: " + name)
        assert after.read(EXE) == exe
        assert after.read(BASE_ESP) == candidate_esp
    result = {
        "candidate": "KR12.2 Windows quest-topic TEST (unreleased)",
        "engine_source": "OpenMW/openmw@openmw-0.51.0 + Korean patchset",
        "pinned_source_commit": "f4bec41444214a7903bebd178389ca22ca13f646",
        "engine_sha256": sha(exe),
        "source_kr12_2_esp_sha256": sha(original_esp),
        "candidate_quest_esp_sha256": sha(candidate_esp),
        "quest_info_physical_qa": quest_qa,
        "other_kr12_2_translation_assets_preserved": True,
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
