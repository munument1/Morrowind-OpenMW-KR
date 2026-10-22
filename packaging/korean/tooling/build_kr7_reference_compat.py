#!/usr/bin/env python3
"""Build KR7 from the public, SHA-pinned KR6 ZIP. No master files are redistributed."""
import argparse
import collections
import copy
import hashlib
import json
import struct
import zipfile
from pathlib import Path

EXPECTED_KR6_SHA = "ce500bbea1d9527edc2304cd2dc214df6da4f9e90233604416a7b6fc61469e31"
ESP = "payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.esp"
REGIONS = {
    "Hirstaang Forest Region": ("솔스타임, 히르스탕 숲", "Solstheim, Hirstaang Forest"),
    "Isinfier Plains Region": ("솔스타임, 이신피어 평원", "Solstheim, Isinfier Plains"),
}
SCRIPTS = {
    "dbattackScript": ("세이다 닌, 인구조사 및 세무국", "Seyda Neen, Census and Excise Office"),
    "dbattackScriptOLD": ("세이다 닌, 인구조사 및 세무국", "Seyda Neen, Census and Excise Office"),
}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def records(data):
    pos = 0
    while pos < len(data):
        tag, size, reserved, flags = struct.unpack_from("<4sIII", data, pos)
        end = pos + 16 + size
        assert end <= len(data), "Truncated record"
        yield tag, data[pos+16:end], reserved, flags
        pos = end
    assert pos == len(data)

def fields(data):
    pos = 0
    while pos < len(data):
        tag, size = struct.unpack_from("<4sI", data, pos)
        end = pos + 8 + size
        assert end <= len(data), "Truncated subrecord"
        yield tag, data[pos+8:end]
        pos = end
    assert pos == len(data)

def pack_fields(fs):
    return b"".join(struct.pack("<4sI", k, len(v)) + v for k, v in fs)

def pack_record(r):
    tag, body, reserved, flags = r
    return struct.pack("<4sIII", tag, len(body), reserved, flags) + body

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-zip", type=Path, required=True)
    ap.add_argument("--output-zip", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    a = ap.parse_args()
    source = a.source_zip.read_bytes()
    assert sha(source) == EXPECTED_KR6_SHA, "Unrecognized KR6 release asset SHA"
    with zipfile.ZipFile(a.source_zip) as z:
        assert z.testzip() is None
        original = {info.filename: z.read(info.filename) for info in z.infolist()}
        esp_paths = [name for name in original if name.endswith("/Morrowind_Korean_ReTranslation.esp")]
        assert len(esp_paths) == 1, f"ESP paths: {esp_paths}; ZIP entries: {list(original)[:30]}"
        esp_path = esp_paths[0]
        old_esp = original[esp_path]
        old = list(records(old_esp))
        new = []
        changed = []
        seen = collections.Counter()
        for typ, body, unk, flags in old:
            if typ in (b"REGN", b"SCPT"):
                fs = list(fields(body))
                dd = dict(fs)
                if typ == b"REGN":
                    name = dd[b"NAME"].rstrip(b"\0").decode("ascii")
                    if name in REGIONS:
                        before, after = REGIONS[name]
                        if dd[b"FNAM"] == before.encode("utf8") + b"\0":
                            assert not seen[(typ, name)]
                            fs = [(key, after.encode("ascii")+b"\0" if key == b"FNAM" else val) for key, val in fs]
                            body = pack_fields(fs)
                            seen[(typ, name)] += 1
                            changed.append(dict(type="REGN", record=name, field="FNAM"))
                else:
                    name = dd[b"SCHD"][:32].split(b"\0")[0].decode("ascii")
                    if name in SCRIPTS:
                        before, after = SCRIPTS[name]
                        old_arg = ('GetPCCell "'+before+'"').encode("utf8")
                        new_arg = ('GetPCCell "'+after+'"').encode("ascii")
                        src = dd[b"SCTX"]
                        if src.count(old_arg) == 1:
                            assert not seen[(typ, name)]
                            fs = [(key, src.replace(old_arg,new_arg) if key == b"SCTX" else val) for key, val in fs]
                            body = pack_fields(fs)
                            seen[(typ, name)] += 1
                            changed.append(dict(type="SCPT", record=name, field="SCTX:GetPCCell"))
                        else:
                            assert src.count(new_arg) == 1, "Unexpected script target"
            new.append((typ, body, unk, flags))
        required = {(b"REGN", name) for name in REGIONS} | {(b"SCPT", name) for name in SCRIPTS}
        assert set(seen) == required and set(seen.values()) == {1}, "Target record coverage"
        assert len(old) == len(new)
        diffs = [i for i, (before, after) in enumerate(zip(old,new)) if before != after]
        assert len(diffs) == 4, "Unexpected ESP changes"
        for i in diffs:
            before, after = old[i], new[i]
            assert before[0] == after[0] and before[2:] == after[2:]
            keep = b"FNAM" if before[0] == b"REGN" else b"SCTX"
            assert [(k,v) for k,v in fields(before[1]) if k != keep] == [(k,v) for k,v in fields(after[1]) if k != keep]
        new_esp = b"".join(pack_record(r) for r in new)
        assert len(list(records(new_esp))) == len(old)
        cel_paths = [name for name in original if name.endswith("/Morrowind_Korean_ReTranslation.cel")]
        assert len(cel_paths) == 1, f"CEL paths: {cel_paths}"
        cel = original[cel_paths[0]]
        for _, destination in REGIONS.values():
            assert (destination + "\t").encode("utf8") in cel
        report = {
            "status": "PASS (static)", "base": "openmw-0.51.0-kr6", "tag": "openmw-0.51.0-kr7",
            "source_zip_sha256": sha(source), "old_esp_sha256": sha(old_esp),
            "new_esp_sha256": sha(new_esp), "record_count": len(new),
            "record_changes": changed, "unchanged_other_esp_records": True,
            "unchanged_binary_and_other_assets": True, "in_game_test": "not_performed",
        }
        notes = """OpenMW Korean Support KR7 — 퀘스트·스크립트 내부 참조 오류 수정

KR6의 데이드릭 문자·신전 음성 자막과 기존 저널·폰트·실행 파일·번역을 유지합니다.

- Bloodmoon 「Race Against the Clock」: 카르니우스가 사무실에 남는 원인이었던 REGN 지명 참조 2건 복구.
- Tribunal 다크 브라더후드 습격: dbattackScript, dbattackScriptOLD의 GetPCCell 내부 셀 이름 복구.
- ESP 48,146개 중 4개 레코드만 수정, 나머지 ESP 레코드/기타 콘텐츠 유지.
- 지역 표시용 .cel 한국어 번역 유지. AddTopic 번역 105건은 DIAL과 대조해 누락 없음.
- 정적 검증 PASS. 실제 게임 내 퀘스트 재현·플레이 테스트는 아직 미실시.

KR6 설치 방식 그대로 압축 해제 후 Install-Korean.bat 실행. 원본 Morrowind 필요.
"""
        modified = {
            esp_path: new_esp,
            "KR7-CHANGES.txt": notes.encode("utf8"),
            "KR7-reference-audit.json": (json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode("utf8"),
            "README-KOREAN.txt": ("OpenMW 0.51.0 Korean Support KR7\nKR7-CHANGES.txt 참조.\n\n"+original["README-KOREAN.txt"].decode("utf-8-sig")).encode("utf8"),
        }
        all_files = dict(original)
        all_files.update(modified)
        all_files.pop("SHA256SUMS.txt", None)
        all_files["SHA256SUMS.txt"] = "".join(sha(data)+"  "+name+"\n" for name,data in sorted(all_files.items())).encode("ascii")
        with zipfile.ZipFile(a.output_zip,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as out:
            for info in z.infolist():
                out.writestr(copy.copy(info),all_files.pop(info.filename))
            for name,data in sorted(all_files.items()):
                out.writestr(name,data)
    with zipfile.ZipFile(a.output_zip) as out:
        assert out.testzip() is None
        manifest = out.read("SHA256SUMS.txt").decode("ascii").splitlines()
        assert len(manifest) == len(out.namelist())-1
        for line in manifest:
            checksum,name = line.split("  ",1)
            assert sha(out.read(name)) == checksum, "Bad manifest: "+name
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("PASS",a.output_zip,"SHA-256",sha(a.output_zip.read_bytes()))

if __name__ == "__main__":
    main()
