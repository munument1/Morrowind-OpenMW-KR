#!/usr/bin/env python3
"""Assemble KR12.4 full Windows release from immutable KR12.3.1 + 0.51.0 native build."""
import argparse
import hashlib
import json
import re
import struct
import zipfile
from pathlib import Path
from collections import Counter
from patch_issue42_explicit_markup import rewrite as patch79, plain
from patch_issue42_audenian_alias import patch_aliases
from audit_kr12_fighters_topic_candidates import dialogue
from patch_kr12_quest_entry_topics import chunks, fields, decoded, pack

BASE_ESP = "payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.esp"
BASE_TOP = "payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.top"
EXE = "payload/openmw.exe"
README = "README-KOREAN.txt"
ESP_SHA = "c0cb2f5702da067e11820e5a11ffb4b758ea28e101779fc43a721072783ed253"
TOP_SHA = "caf31e0703afcbcdb699c6df6e0d27f2250416821c18f6c12a711116de440730"
CANDIDATE_ESP_SHA = "2276384ad93fd3e56bc0d401aacc45418ba38993ee798e0e1a7e09564a375d3a"
CANDIDATE_TOP_SHA = "0516f17495afbdf5e3712d40aad9f11dc314edc7bd75ef33c9a8018b5fc60b16"
INSTALLER = "install-korean.ps1"
README_TEXT = """OpenMW 0.51.0 한국어 KR12.4 — Windows x64 정식 통합판

KR12.3.1에서 업데이트: 이슈 #42 한국어 대화 토픽 연결 보정.
- 공식 upstream OpenMW 0.51.0(f4bec41444214a7903bebd178389ca22ca13f646)에
  한국어 패치 0001~0016을 적용하여 Windows openmw.exe 재빌드.
- 79건의 잘못된 명시 토픽 링크 + 원문 대조를 거친 12건의 대화 링크 보정.
- 아우데니안 발리우스 별칭 3건을 원래 대상 토픽으로 수정.
- 다른 한국어 대사, 퀘스트 조건, 스크립트, 번역 자산은 KR12.3.1에서 유지.

설치:
1. 기존 OpenMW 설치, 사용자 설정, 게임 저장 데이터를 백업합니다.
2. 압축을 푼 뒤 Install-Korean.bat 실행 (관리자 권한 안내 시 확인).
3. Morrowind Data Files가 아니라 OpenMW의 openmw.exe가 있는 폴더를 선택합니다.
4. 정품 Morrowind 및 Tribunal/Bloodmoon 데이터는 별도로 필요합니다.

자동 구조 검사와 네이티브 토픽 회귀 테스트 통과. 실제 NPC 대화 및
퀘스트 진행을 플레이한 검증은 수행하지 못했습니다. 문제 재현 시
NPC·대화·퀘스트 단계·모드 목록·로그를 이슈 #42에 알려 주세요.
Android APK는 이 Windows ZIP에 포함되지 않으며 별도 빌드 대상입니다.
"""


def sha(b):
    return hashlib.sha256(b).hexdigest()


def update12(raw, manifest, top):
    specs = {x["INFO"]: x for x in manifest["cases"]}
    if len(specs) != 12 or len(manifest["cases"]) != 12:
        raise ValueError("Requires exactly 12 verified, distinct INFO IDs")
    topics, _ = dialogue(raw)
    topmap = dict(x.split("\t", 1) for x in top.decode("utf-8-sig").splitlines() if "\t" in x)
    records = list(chunks(raw, 16))
    result = []
    seen = set()
    for tag, header, payload in records:
        if tag != b"INFO":
            result.append(header + payload)
            continue
        parts = fields(payload)
        f = dict(parts)
        iid = decoded(f.get(b"INAM", b""))
        if iid not in specs:
            result.append(header + payload)
            continue
        if iid in seen:
            raise ValueError("Duplicate INFO id " + iid)
        seen.add(iid)
        task = specs[iid]
        word, replacement, target = task["source_phrase"], task["candidate_markup"], task["target"]
        before = decoded(f.get(b"NAME", b""))
        if target not in topics or topmap.get(target, target) != target:
            raise ValueError("Explicit target absent or alias redirected: " + target)
        if not replacement.startswith("@" + target + "#") or plain(replacement) != word:
            raise ValueError("Incorrect explicit link markup for " + iid)
        if before.count(word) != 1:
            raise ValueError("Not exactly one matched Korean phrase in " + iid)
        prefix = before[:before.index(word)]
        if prefix.count("@") > prefix.count("#"):
            raise ValueError("Source inside existing explicit link " + iid)
        after = before.replace(word, replacement, 1)
        if plain(before) != plain(after):
            raise ValueError("Displayed Korean changed " + iid)
        old = f[b"NAME"]
        new = after.encode("utf-8") + old[len(old.rstrip(b"\0")):]
        body = b"".join(struct.pack("<4sI", k, len(new if k == b"NAME" else v)) +
                        (new if k == b"NAME" else v) for k, v in parts)
        result.append(pack(tag, header, body))
    if seen != set(specs):
        raise ValueError("Unmatched INFO IDs: " + repr(set(specs)-seen))
    return b"".join(result)


def build(baseline, engine, manifest):
    exe = engine.read_bytes()
    if len(exe) < 10_000_000 or not exe.startswith(b"MZ"):
        raise ValueError("New executable not a full Windows PE runtime")
    if b"0.51.0" not in exe and "0.51.0".encode("utf-16le") not in exe:
        raise ValueError("0.51.0 version marker missing from compiled executable")
    with zipfile.ZipFile(baseline) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate entries in published baseline")
        for name in (BASE_ESP, BASE_TOP, EXE, README, "Install-Korean.bat", INSTALLER):
            if names.count(name) != 1:
                raise ValueError("Missing baseline member: " + name)
        old_esp, old_top = archive.read(BASE_ESP), archive.read(BASE_TOP)
        if sha(old_esp) != ESP_SHA or sha(old_top) != TOP_SHA:
            raise ValueError("Published KR12.3.1 translation SHA drift")
        if sha(archive.read(EXE)) == sha(exe):
            raise ValueError("New engine identical to old engine; 0016 must be compiled")
        topics, _ = dialogue(old_esp)
        new_top, alias_changes = patch_aliases(old_top, topics)
        new79, physical = patch79(old_esp, old_top)
        if physical["changed_INFO_NAME_count"] != 79:
            raise ValueError("79-link QA count drift")
        new_esp = update12(new79, manifest, old_top)
        if sha(new_esp) != CANDIDATE_ESP_SHA or sha(new_top) != CANDIDATE_TOP_SHA:
            raise ValueError("Final source-locked 91+3 hash mismatch")
        original_records, final_records = list(chunks(old_esp, 16)), list(chunks(new_esp, 16))
        if len(original_records) != len(final_records):
            raise ValueError("Record count changed")
        changed = []
        for n, ((tag, header, before), (tag2, header2, after)) in enumerate(zip(original_records, final_records)):
            if tag != tag2 or header[8:] != header2[8:]:
                raise ValueError("TES3 non-size header drift")
            if before == after:
                continue
            if tag != b"INFO":
                raise ValueError("Non-INFO changed")
            a, b = fields(before), fields(after)
            if len(a) != len(b):
                raise ValueError("Field count changed")
            for (ak, av), (bk, bv) in zip(a, b):
                if ak != bk or (ak != b"NAME" and av != bv):
                    raise ValueError("INFO selectors or scripts changed")
                if ak == b"NAME" and plain(decoded(av)) != plain(decoded(bv)):
                    raise ValueError("Displayed Korean drift")
            changed.append(n)
        if len(changed) != 91:
            raise ValueError("91 distinct changed INFO expected")
        changes = {BASE_ESP: new_esp, BASE_TOP: new_top, EXE: exe,
                   README: README_TEXT.encode("utf-8")}
        allowed = set(changes)
        new_installer = archive.read(INSTALLER)
        # Installer's version label is metadata; keep backup logic and other text unchanged.
        for old, new in (("korean-kr4-backup-", "korean-kr12.4-backup-"),
                         ("OPENMW-KOREAN-KR4.txt", "OPENMW-KOREAN-KR12.4.txt")):
            new_installer = new_installer.replace(old.encode("utf-8"), new.encode("utf-8"))
        if new_installer != archive.read(INSTALLER):
            changes[INSTALLER] = new_installer
            allowed.add(INSTALLER)
        return names, [(i, changes.get(i.filename, archive.read(i.filename))) for i in archive.infolist()], allowed, {
            "version":"KR12.4", "source":"OpenMW/openmw@f4bec41444214a7903bebd178389ca22ca13f646",
            "source_baseline_zip_sha256":sha(baseline.read_bytes()),
            "original_esp_sha256":sha(old_esp), "patched_esp_sha256":sha(new_esp),
            "original_top_sha256":sha(old_top), "patched_top_sha256":sha(new_top),
            "compiled_windows_exe_sha256":sha(exe),
            "changed_INFO_NAME_count":len(changed), "changed_TOP_aliases":len(alias_changes),
            "zip_member_inventory_unchanged":True,
            "all_other_zip_members_byte_identical":True,
            "all_other_TES3_fields_byte_identical":True,
            "all_displayed_Korean_unchanged":True,
            "live_gameplay_verified":False, "android_build_included":False,
            "allowed_changed_zip_paths":sorted(allowed),
        }


def main():
    p = argparse.ArgumentParser()
    for key in ("baseline","engine","manifest","output","report"):
        p.add_argument("--" + key, required=True, type=Path)
    a=p.parse_args()
    if a.output.exists() or a.report.exists() or a.output.resolve()==a.baseline.resolve():
        raise ValueError("Output must be new and not the baseline")
    manifest=json.loads(a.manifest.read_text(encoding="utf-8"))
    if manifest.get("candidate_combined_91_esp_sha256") != CANDIDATE_ESP_SHA:
        raise ValueError("Unexpected reviewed manifest revision")
    names, members, allowed, qa=build(a.baseline,a.engine,manifest)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(a.output,"w") as dest:
        for info, value in members:
            dest.writestr(info,value)
    with zipfile.ZipFile(a.output) as final, zipfile.ZipFile(a.baseline) as old:
        if final.testzip() is not None or final.namelist()!=names:
            raise ValueError("Bad final ZIP CRC or member inventory")
        for name in names:
            if name not in allowed and final.read(name)!=old.read(name):
                raise ValueError("Unexpected modified ZIP member " + name)
        if sha(final.read(BASE_ESP))!=CANDIDATE_ESP_SHA or sha(final.read(BASE_TOP))!=CANDIDATE_TOP_SHA:
            raise ValueError("Final ESP / TOP invalid")
    qa["output_zip_sha256"]=sha(a.output.read_bytes())
    qa["zip_crc_integrity"]="PASS"
    a.report.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (a.output.parent/(a.output.name+".sha256")).write_text(qa["output_zip_sha256"]+"  "+a.output.name+"\n",encoding="utf-8")
    print(json.dumps(qa,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
