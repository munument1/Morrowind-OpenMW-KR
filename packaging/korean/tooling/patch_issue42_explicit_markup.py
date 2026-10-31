#!/usr/bin/env python3
"""Exact KR12.3.1 INFO.NAME-only malformed explicit link candidate (NOT RELEASED).

No original ESM/ESP/ZIP, quest scripts, actor filters, saves or installed mods are
overwritten. Creates a new candidate ESP and independent JSON physical QA.
"""
import argparse
import hashlib
import json
import re
import struct
import zipfile
from collections import Counter
from pathlib import Path

from patch_kr12_quest_entry_topics import chunks, fields, decoded, pack

ESP_NAME = "Morrowind_Korean_ReTranslation.esp"
TOP_NAME = "Morrowind_Korean_ReTranslation.top"
SOURCE_SHA = "c0cb2f5702da067e11820e5a11ffb4b758ea28e101779fc43a721072783ed253"
# Exact displayed text is unchanged. "설원" .top currently targets "눈", not snow animals.
REPLACEMENTS = {
    "@설원#곰": ("@설원곰#", 37),
    "@설원#늑대": ("@설원늑대#", 37),
    "정@말#": ("정말", 3),
    "@말입니까?#": ("말입니까?", 1),
    "@이나 다른#": ("이나 다른", 1),
}
REQUIRED_TOP_TARGETS = {
    "설원": "눈",
    "말": "대화",
    "말입니까?": "은신",
    "이나 다른": "인구조사 및 세무국 요원",
}
REQUIRED_DIALS = {"설원곰", "설원늑대"}
TAG_RE = re.compile(r"@([^@#]+)#")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def plain(text: str) -> str:
    return TAG_RE.sub(lambda m: m.group(1).replace("\x7f", ""), text)


def read_top(raw: bytes) -> dict:
    result = {}
    for line in raw.decode("utf-8-sig").splitlines():
        if "\t" not in line:
            continue
        key, value = line.split("\t", 1)
        result.setdefault(key, value)  # OpenMW first-wins
    return result


def rewrite(original: bytes, top_raw: bytes, expected=REPLACEMENTS,
            verify_source=True):
    if verify_source and sha(original) != SOURCE_SHA:
        raise ValueError("Refusing to modify unknown source: published KR12.3.1 SHA mismatch")
    aliases = read_top(top_raw)
    for label, target in REQUIRED_TOP_TARGETS.items():
        if aliases.get(label) != target:
            raise ValueError(f"Known incorrect .top source mapping changed: {label!r}")
    records = list(chunks(original, 16))
    topics = {
        decoded(dict(fields(payload))[b"NAME"])
        for tag, _head, payload in records if tag == b"DIAL"
        and dict(fields(payload)).get(b"DATA", b"\xff")[:1] == b"\0"
        and b"DELE" not in dict(fields(payload))
    }
    if not REQUIRED_DIALS.issubset(topics):
        raise ValueError("Correct full snow-bear / snow-wolf DIALs are absent")
    if any(aliases.get(t, t) != t for t in REQUIRED_DIALS):
        raise ValueError("A corrected explicit topic would resolve to another DIAL")

    changed_info = []
    applied = Counter()
    output_records = []
    active_parent = None
    for record_index, (tag, header, payload) in enumerate(records):
        if tag == b"DIAL":
            active_parent = decoded(dict(fields(payload)).get(b"NAME", b""))
        if tag != b"INFO":
            output_records.append(header + payload)
            continue
        original_fields = fields(payload)
        info_fields = dict(original_fields)
        iid = decoded(info_fields.get(b"INAM", b""))
        if b"NAME" not in info_fields:
            output_records.append(header + payload)
            continue
        raw_name = info_fields[b"NAME"]
        before = decoded(raw_name)
        after = before
        per_info = Counter()
        for prior, (updated, _count) in expected.items():
            occurrences = after.count(prior)
            if not occurrences:
                continue
            if plain(prior) != plain(updated):
                raise ValueError("Candidate changes visible text: " + prior)
            after = after.replace(prior, updated)
            applied[prior] += occurrences
            per_info[prior] += occurrences
        if after == before:
            output_records.append(header + payload)
            continue
        if plain(before) != plain(after):
            raise ValueError("Visible INFO content changed in " + iid)
        nulls = raw_name[len(raw_name.rstrip(b"\0")):]
        new_name = after.encode("utf-8") + nulls
        rebuilt = b"".join(
            struct.pack("<4sI", field, len(new_name if field == b"NAME" else value))
            + (new_name if field == b"NAME" else value)
            for field, value in original_fields
        )
        output_records.append(pack(tag, header, rebuilt))
        changed_info.append({
            "record_index": record_index,
            "INFO": iid,
            "DIAL": active_parent,
            "actor": decoded(info_fields.get(b"ONAM", b"")),
            "source_name_sha256": sha(raw_name),
            "candidate_name_sha256": sha(new_name),
            "replacement_counts": dict(per_info),
            "visible_text_unchanged": True,
        })

    for prior, (_updated, required_count) in expected.items():
        if applied[prior] != required_count:
            raise ValueError(f"Count for {prior} differs from released source: "
                             f"{applied[prior]} != {required_count}")

    patched = b"".join(output_records)
    new_records = list(chunks(patched, 16))
    if len(new_records) != len(records):
        raise ValueError("TES3 record count drift")
    change_indices = {x["record_index"] for x in changed_info}
    for idx, ((kind, old_header, old_payload), (new_kind, new_header, new_payload)) in enumerate(
            zip(records, new_records)):
        if kind != new_kind or old_header[8:] != new_header[8:]:
            raise ValueError(f"TES3 record header mismatch at {idx}")
        if idx not in change_indices:
            if old_header + old_payload != new_header + new_payload:
                raise ValueError(f"Non-target record modified at {idx}")
            continue
        old_fields, new_fields = fields(old_payload), fields(new_payload)
        if len(old_fields) != len(new_fields):
            raise ValueError(f"INFO subrecord drift at {idx}")
        for (old_tag, old_value), (new_tag, new_value) in zip(old_fields, new_fields):
            if old_tag != new_tag or (old_value != new_value and old_tag != b"NAME"):
                raise ValueError(f"Non-NAME INFO field changed at {idx}")

    return patched, {
        "status": "EXACT_REVIEW_ONLY_DATA_CANDIDATE_NOT_RELEASED",
        "published_source_sha256": sha(original),
        "candidate_esp_sha256": sha(patched),
        "source_top_sha256": sha(top_raw),
        "record_count": len(records),
        "changed_INFO_NAME_count": len(changed_info),
        "total_replacements": sum(applied.values()),
        "applied_by_fragment": dict(applied),
        "target_DIALs_present": sorted(REQUIRED_DIALS),
        "all_other_records_and_subfields_byte_identical": True,
        "all_visible_text_unchanged": True,
        "changed_INFO_records": changed_info,
        "gameplay_review_required": True,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-zip", type=Path, required=True)
    p.add_argument("--output-esp", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    if args.output_esp.exists() or args.report.exists():
        raise ValueError("Write to new paths only")
    with zipfile.ZipFile(args.source_zip) as z:
        esp_paths = [x for x in z.namelist() if x.endswith(ESP_NAME)]
        top_paths = [x for x in z.namelist() if x.endswith(TOP_NAME)]
        if len(esp_paths) != 1 or len(top_paths) != 1:
            raise ValueError("Missing or duplicate Korean translation files in ZIP")
        original, top = z.read(esp_paths[0]), z.read(top_paths[0])
    patched, report = rewrite(original, top)
    args.output_esp.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output_esp.write_bytes(patched)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k,v in report.items() if k != "changed_INFO_records"},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
