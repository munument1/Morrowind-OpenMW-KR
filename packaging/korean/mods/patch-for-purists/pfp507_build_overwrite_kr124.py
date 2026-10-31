#!/usr/bin/env python3
"""Build an overwrite-only PFP 5.0.7 Korean ESM from explicitly supplied private KR12.4 drafts.

Usage:
 python packaging/korean/mods/patch-for-purists/pfp507_build_overwrite_kr124.py --source "Patch for Purists.esm" --draft "<private-draft.jsonl.gz>" --report "<private-migration-report.json>"

Creates an OUTSIDE-original-folder private test archive with exactly one
installable member: Patch for Purists.esm. No ESP, installer or runtime hook.
The original file and all historical translations are read-only.
"""
from __future__ import annotations
import argparse
import collections
import gzip
import hashlib
import json
import pathlib
import struct
import zipfile

ORIGINAL_SHA = "8593e1446e2e569a356f0d9a4b69582d1e113ffcdcc25ba953bee3524d286818"
DEFERRED_OFFSETS = {1706649,2177943,2184319,2190359,2278201,2278314,2306076,2626689}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def source_records(data):
    pos = 0
    ordinal = 0
    while pos < len(data):
        assert pos + 16 <= len(data), "Truncated TES3 record"
        header = data[pos:pos + 16]
        size = struct.unpack_from("<I", data, pos + 4)[0]
        end = pos + 16 + size
        assert end <= len(data)
        children = []
        cursor = pos + 16
        while cursor < end:
            assert cursor + 8 <= end
            tag = data[cursor:cursor + 4]
            length = struct.unpack_from("<I", data, cursor + 4)[0]
            field = cursor + 8
            finish = field + length
            assert finish <= end
            children.append((tag, field, cursor, data[field:finish], finish))
            cursor = finish
        assert cursor == end
        yield ordinal, pos, header, data[pos:end], children
        pos = end
        ordinal += 1
    assert ordinal == 10202

def load_drafts(draft_path, report_path):
    draft_path = draft_path.resolve(strict=True)
    report_path = report_path.resolve(strict=True)
    report = json.loads(report_path.read_text("utf-8"))
    assert report["original_pfp_esm_sha256"] == ORIGINAL_SHA
    assert report["reference"] == "OpenMW 0.51.0 KR12.4"
    assert report["preserved_effective_v19_draft_fields"] == 8815
    assert report["remaining_untranslated_v19_fields"] == 8
    assert report["prior_v19_translations_overwritten"] is False
    assert report["manual_final_qa"] is False
    assert report["game_verified"] is False
    assert report["release_ready"] is False
    rows = {}
    with gzip.open(draft_path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            off = r["subrecord_data_offset"]
            assert off not in rows and off not in DEFERRED_OFFSETS
            assert r["row_key"] == f"Patch for Purists.esm@{off}"
            assert r["source_sha256"] == ORIGINAL_SHA
            assert r["status"] == "ai_draft"
            for field in ("human_editorial_verified", "in_game_verified", "release_ready"):
                assert r[field] is False
            assert r["ko"] and "티베르 셉팀" not in r["ko"]
            assert sha(r["ko"].encode("utf-8")) == r["ko_effective_sha256"]
            rows[off] = r
    assert len(rows) == 8815, len(rows)
    return rows, sha(draft_path.read_bytes()), sha(report_path.read_bytes())

def build(original, rows):
    assert sha(original) == ORIGINAL_SHA, "Not the exact PFP 5.0.7 original"
    parts = []
    used = set()
    untouched = 0
    protected = collections.Counter()
    for ordinal, offset, head, parent, children in source_records(original):
        rebuilt = bytearray()
        parent_sha = sha(parent)
        for tag, field, sub, raw, end in children:
            row = rows.get(field)
            if row is None:
                rebuilt += original[sub:end]
                untouched += 1
                if (head[:4],tag) in ((b"INFO",b"BNAM"),(b"SCPT",b"SCDT"),(b"SCPT",b"SCTX")):
                    protected[head[:4].decode() + "." + tag.decode()] += 1
                continue
            assert field not in used
            used.add(field)
            assert row["record_index"] == ordinal
            assert row["record_offset"] == offset
            assert row["record_size"] == len(parent)
            assert row["record_sha256"] == parent_sha
            assert row["record_type"].encode("ascii") == head[:4]
            assert row["field_type"].encode("ascii") == tag
            assert row["english_raw_sha256"] == sha(raw)
            assert row["subrecord_data_size"] == len(raw)
            nuls = len(raw) - len(raw.rstrip(b"\x00"))
            translated = row["ko"].encode("utf-8") + b"\x00" * nuls
            assert translated != raw and len(translated) < 2**32
            rebuilt += tag + struct.pack("<I",len(translated)) + translated
        assert len(rebuilt) < 2**32
        parts.append(head[:4] + struct.pack("<I",len(rebuilt)) + head[8:16] + rebuilt)
    assert used == set(rows) and len(used) == 8815
    result = b"".join(parts)
    # All non-translation bytes must round-trip without changes, including scripts.
    checked = 0
    original_iter = source_records(original)
    rebuilt_iter = source_records(result)
    for old,new in zip(original_iter,rebuilt_iter):
        ori,op,oh,oraw,osub=old
        newri,np,nh,nraw,nsub=new
        assert ori == newri
        assert oh[:4] == nh[:4] and oh[8:16] == nh[8:16]
        assert len(osub) == len(nsub)
        for (t,off,_,raw,_),(nt,n_off,_,nr,_) in zip(osub,nsub):
            assert t == nt
            if off not in rows:
                assert raw == nr,("Nontranslated field altered",off)
            else:
                nuls=len(raw)-len(raw.rstrip(b"\x00"))
                assert nr == rows[off]["ko"].encode("utf-8") + b"\x00"*nuls
                checked += 1
    assert checked == 8815
    return result,{"translated_fields":checked,"untouched_subrecords":untouched,
                   "protected_unmodified":dict(protected),"record_count":10202,
                   "independent_nontranslation_byte_check":"PASS"}

def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--source", type=pathlib.Path, required=True)
    cli.add_argument("--draft", type=pathlib.Path, required=True, help="Private PFP507_KR124_EFFECTIVE_8815_PRIVATE_DRAFT.jsonl.gz")
    cli.add_argument("--report", type=pathlib.Path, required=True, help="Private PFP_KR124_MIGRATION_REPORT.json")
    cli.add_argument("--out-dir", type=pathlib.Path)
    opts=cli.parse_args()
    source=opts.source.resolve(strict=True)
    assert source.name.lower()=="patch for purists.esm"
    out=(opts.out_dir or source.parent/"_PFP507_KR124_OVERWRITE_PRIVATE_NOT_FOR_RELEASE").resolve()
    assert out != source.parent and not out.exists(), "Refusing overwrite or existing output directory"
    original=source.read_bytes()
    assert sha(original)==ORIGINAL_SHA, "PFP source SHA does not match 5.0.7"
    rows,draft_sha,report_sha=load_drafts(opts.draft,opts.report)
    result,stats=build(original,rows)
    out.mkdir(parents=True,exist_ok=False)
    plugin=out/"Patch for Purists.esm"
    plugin.write_bytes(result)
    name=out/"PFP507_KR124_OVERWRITE_PRIVATE_TEST.zip"
    with zipfile.ZipFile(name,"x",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        z.write(plugin,"Patch for Purists.esm")
    with zipfile.ZipFile(name) as z:
        assert z.namelist()==["Patch for Purists.esm"]
        assert sha(z.read("Patch for Purists.esm"))==sha(result)
    qa={"status":"PASS_OVERWRITE_ESM_PHYSICAL_QA_PRIVATE_TEST_ONLY",
        "original_sha256":ORIGINAL_SHA,"output_esm_sha256":sha(result),
        "output_zip_sha256":sha(name.read_bytes()),"draft_sha256":draft_sha,
        "migration_report_sha256":report_sha,"deferred_original_fields_unchanged":8,
        "archive_members":["Patch for Purists.esm"],**stats,
        "human_editorial_verified":False,"in_game_verified":False,"release_ready":False}
    (out/"PFP507_KR124_OVERWRITE_QA.json").write_text(
        json.dumps(qa,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(qa,ensure_ascii=False,indent=2))
    print(name)

if __name__=="__main__":
    main()
