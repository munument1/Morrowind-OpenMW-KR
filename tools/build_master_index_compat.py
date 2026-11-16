#!/usr/bin/env python3
"""Build an OpenMW Korean compatibility overlay for Bethesda's Master Index plugin.

The overlay is intentionally narrow:
- copy every Master Index DIAL/INFO record so its dialogue chains win after the
  main Korean translation ESP regardless of load order;
- copy only the Master Propylon Index MISC record, changing its display name to
  Korean;
- require the user's original master_index.esp as a master.

It does NOT copy GMST, NPC, CELL, or SCPT records. That lets the main Korean ESP
keep its translated NPC names and already-localized propylon scripts while the
original Bethesda plugin continues to supply its world edits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pack_subrecord(name: str, data: bytes) -> bytes:
    return name.encode("ascii") + struct.pack("<I", len(data)) + data


def parse_subrecords(payload: bytes):
    out = []
    pos = 0
    while pos + 8 <= len(payload):
        name = payload[pos:pos + 4].decode("ascii", errors="strict")
        size = struct.unpack_from("<I", payload, pos + 4)[0]
        pos += 8
        if pos + size > len(payload):
            raise ValueError(f"truncated subrecord {name}")
        out.append((name, payload[pos:pos + size]))
        pos += size
    if pos != len(payload):
        raise ValueError(f"trailing bytes in record payload: {len(payload) - pos}")
    return out


def parse_records(data: bytes):
    out = []
    pos = 0
    while pos + 16 <= len(data):
        rtype = data[pos:pos + 4].decode("ascii", errors="strict")
        size, unknown, flags = struct.unpack_from("<III", data, pos + 4)
        pos += 16
        if pos + size > len(data):
            raise ValueError(f"truncated {rtype} record")
        payload = data[pos:pos + size]
        pos += size
        out.append(
            {
                "type": rtype,
                "unknown": unknown,
                "flags": flags,
                "payload": payload,
                "subs": parse_subrecords(payload),
            }
        )
    if pos != len(data):
        raise ValueError(f"trailing bytes after final record: {len(data) - pos}")
    return out


def record_bytes(rec, payload: bytes | None = None) -> bytes:
    if payload is None:
        payload = rec["payload"]
    return (
        rec["type"].encode("ascii")
        + struct.pack("<III", len(payload), rec["unknown"], rec["flags"])
        + payload
    )


def text_value(raw: bytes) -> str:
    return raw.rstrip(b"\x00").decode("cp1252", errors="replace")


def first_sub(rec, name: str):
    for n, d in rec["subs"]:
        if n == name:
            return d
    return None


def patch_misc_display_name(rec, display_name: str) -> bytes:
    parts = []
    found = False
    for name, data in rec["subs"]:
        if name == "FNAM":
            # Morrowind string subrecords normally include a NUL terminator.
            data = display_name.encode("utf-8") + b"\x00"
            found = True
        parts.append(pack_subrecord(name, data))
    if not found:
        raise ValueError("index_master MISC record has no FNAM")
    return b"".join(parts)


def build_header(original_tes3, master_index_size: int, record_count: int) -> bytes:
    parts = []
    saw_hedr = False
    existing_masters = []
    for name, data in original_tes3["subs"]:
        if name == "HEDR":
            if len(data) < 300:
                raise ValueError(f"unexpected HEDR size: {len(data)}")
            patched = bytearray(data)
            # Last uint32 in HEDR is the number of records after TES3.
            struct.pack_into("<I", patched, len(patched) - 4, record_count)
            data = bytes(patched)
            saw_hedr = True
        elif name == "MAST":
            existing_masters.append(text_value(data).lower())
        parts.append(pack_subrecord(name, data))

    if not saw_hedr:
        raise ValueError("TES3 record has no HEDR")

    if "master_index.esp" not in existing_masters:
        parts.append(pack_subrecord("MAST", b"master_index.esp\x00"))
        parts.append(pack_subrecord("DATA", struct.pack("<Q", master_index_size)))

    payload = b"".join(parts)
    return record_bytes(original_tes3, payload)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master-index", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--master-item-name", default="마스터 프로필론 색인")
    args = ap.parse_args()

    source = args.master_index.read_bytes()
    records = parse_records(source)
    if not records or records[0]["type"] != "TES3":
        raise SystemExit("input is not a TES3 plugin")

    selected = []
    dial_count = info_count = 0
    index_master_count = 0

    for rec in records[1:]:
        if rec["type"] in ("DIAL", "INFO"):
            selected.append(record_bytes(rec))
            dial_count += rec["type"] == "DIAL"
            info_count += rec["type"] == "INFO"
            continue

        if rec["type"] == "MISC":
            name = first_sub(rec, "NAME")
            if name is not None and text_value(name).lower() == "index_master":
                payload = patch_misc_display_name(rec, args.master_item_name)
                selected.append(record_bytes(rec, payload))
                index_master_count += 1

    if dial_count != 14 or info_count != 99:
        raise SystemExit(
            f"unexpected Master Index dialogue shape: DIAL={dial_count}, INFO={info_count}"
        )
    if index_master_count != 1:
        raise SystemExit(f"expected one index_master record, got {index_master_count}")

    header = build_header(records[0], len(source), len(selected))
    output = header + b"".join(selected)

    # Reparse the generated overlay so structural errors fail the build.
    reparsed = parse_records(output)
    out_types = {}
    for rec in reparsed:
        out_types[rec["type"]] = out_types.get(rec["type"], 0) + 1
    expected = {"TES3": 1, "MISC": 1, "DIAL": 14, "INFO": 99}
    if out_types != expected:
        raise SystemExit(f"unexpected output record counts: {out_types!r}")

    # Validate dependency and the Korean master-index item name.
    masters = [
        text_value(data)
        for name, data in reparsed[0]["subs"]
        if name == "MAST"
    ]
    if not any(x.lower() == "master_index.esp" for x in masters):
        raise SystemExit("generated overlay does not depend on master_index.esp")

    misc = next(r for r in reparsed if r["type"] == "MISC")
    fnam = first_sub(misc, "FNAM") or b""
    if fnam.rstrip(b"\x00").decode("utf-8") != args.master_item_name:
        raise SystemExit("Master Propylon Index display-name patch failed")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(output)

    report = {
        "source": {
            "path": str(args.master_index),
            "size": len(source),
            "sha256": sha256(source),
        },
        "output": {
            "path": str(args.out),
            "size": len(output),
            "sha256": sha256(output),
            "type_counts": out_types,
            "masters": masters,
        },
        "copied_records": {
            "DIAL": dial_count,
            "INFO": info_count,
            "MISC_index_master": index_master_count,
        },
        "master_item_name": args.master_item_name,
        "excluded_record_types": ["GMST", "SCPT", "NPC_", "CELL"],
    }

    report_path = args.report or args.out.with_suffix(args.out.suffix + ".json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
