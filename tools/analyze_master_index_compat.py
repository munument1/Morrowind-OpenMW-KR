#!/usr/bin/env python3
"""Analyze compatibility between Bethesda's Master Index plugin and the Korean ESP.

This tool intentionally writes only metadata/text reports. It does not copy or
redistribute Bethesda's plugin or the Korean release payload.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from collections import Counter, defaultdict
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_text(data: bytes, mode: str) -> str:
    data = data.rstrip(b"\x00")
    encodings = (
        ["utf-8-sig", "utf-8", "cp949", "cp1252", "latin1"]
        if mode == "translation"
        else ["cp1252", "latin1", "utf-8"]
    )
    for enc in encodings:
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("latin1", errors="replace")


def parse_subrecords(payload: bytes):
    out = []
    pos = 0
    while pos + 8 <= len(payload):
        name = payload[pos : pos + 4].decode("ascii", errors="replace")
        size = struct.unpack_from("<I", payload, pos + 4)[0]
        pos += 8
        if pos + size > len(payload):
            out.append(("BROKEN", payload[pos:]))
            break
        out.append((name, payload[pos : pos + size]))
        pos += size
    return out


def parse_records(path: Path):
    data = path.read_bytes()
    pos = 0
    records = []
    while pos + 16 <= len(data):
        rtype_b = data[pos : pos + 4]
        try:
            rtype = rtype_b.decode("ascii")
        except UnicodeDecodeError:
            break
        size, unknown, flags = struct.unpack_from("<III", data, pos + 4)
        start = pos
        pos += 16
        if pos + size > len(data):
            raise ValueError(f"truncated record at {start}: {rtype} size={size}")
        payload = data[pos : pos + size]
        pos += size
        records.append(
            {
                "type": rtype,
                "size": size,
                "unknown": unknown,
                "flags": flags,
                "subs": parse_subrecords(payload),
                "raw_sha256": sha256(payload),
                "offset": start,
            }
        )
    return data, records


def sub_all(rec, name):
    return [d for n, d in rec["subs"] if n == name]


def sub_first(rec, name):
    vals = sub_all(rec, name)
    return vals[0] if vals else None


def record_id(rec, mode: str) -> str:
    if rec["type"] == "SCPT":
        schd = sub_first(rec, "SCHD") or b""
        return decode_text(schd[:32].split(b"\x00", 1)[0], mode)
    return decode_text(sub_first(rec, "NAME") or b"", mode)


def display_name(rec, mode: str) -> str:
    for field in ("FNAM", "NAME"):
        raw = sub_first(rec, field)
        if raw is not None:
            return decode_text(raw, mode)
    return ""


def build_model(path: Path, mode: str):
    data, records = parse_records(path)
    dials = []
    infos = []
    current_dial = None
    type_counts = Counter()
    keyed = defaultdict(list)

    for rec_index, rec in enumerate(records):
        rtype = rec["type"]
        type_counts[rtype] += 1

        if rtype == "DIAL":
            name = decode_text(sub_first(rec, "NAME") or b"", mode)
            current_dial = name
            dial = {
                "record_index": rec_index,
                "name": name,
                "data_hex": (sub_first(rec, "DATA") or b"").hex(),
                "raw_sha256": rec["raw_sha256"],
            }
            dials.append(dial)
            keyed[(rtype, name.lower())].append(dial)
            continue

        if rtype == "INFO":
            inam = decode_text(sub_first(rec, "INAM") or b"", mode)
            fields = {}
            for fn in (
                "PNAM",
                "NNAM",
                "DATA",
                "ONAM",
                "RNAM",
                "CNAM",
                "FNAM",
                "ANAM",
                "DNAM",
                "SCVR",
                "INTV",
                "FLTV",
                "QSTN",
                "QSTF",
                "QSTR",
            ):
                vals = sub_all(rec, fn)
                if vals:
                    if fn in ("DATA", "INTV", "FLTV"):
                        fields[fn] = [v.hex() for v in vals]
                    else:
                        fields[fn] = [decode_text(v, mode) for v in vals]
            info = {
                "record_index": rec_index,
                "parent_dial": current_dial,
                "inam": inam,
                "response": decode_text(sub_first(rec, "NAME") or b"", mode),
                "result": decode_text(sub_first(rec, "BNAM") or b"", mode),
                "fields": fields,
                "raw_sha256": rec["raw_sha256"],
            }
            infos.append(info)
            keyed[(rtype, inam.lower())].append(info)
            continue

        rid = record_id(rec, mode)
        if rid:
            entry = {
                "record_index": rec_index,
                "id": rid,
                "display_name": decode_text(sub_first(rec, "FNAM") or b"", mode),
                "raw_sha256": rec["raw_sha256"],
            }
            if rtype == "SCPT":
                entry["sctx"] = decode_text(sub_first(rec, "SCTX") or b"", mode)
            keyed[(rtype, rid.lower())].append(entry)

    return {
        "path": str(path),
        "size": len(data),
        "sha256": sha256(data),
        "record_count": len(records),
        "type_counts": dict(type_counts),
        "dials": dials,
        "infos": infos,
        "keyed": keyed,
    }


def load_sidecar(path: Path | None):
    if not path or not path.exists():
        return []
    raw = path.read_bytes()
    text = None
    for enc in ("utf-8-sig", "utf-8", "cp949", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = raw.decode("latin1", errors="replace")
    out = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not line.strip() or "\t" not in line:
            continue
        key, value = line.split("\t", 1)
        out.append({"line": lineno, "key": key, "value": value})
    return out


def logic_signature(info):
    return {
        "parent_dial": (info.get("parent_dial") or "").lower(),
        "fields": info.get("fields", {}),
        "result": info.get("result", ""),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master-index", required=True, type=Path)
    ap.add_argument("--translation", required=True, type=Path)
    ap.add_argument("--mrk", type=Path)
    ap.add_argument("--top", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    official = build_model(args.master_index, "official")
    korean = build_model(args.translation, "translation")
    mrk = load_sidecar(args.mrk)
    top = load_sidecar(args.top)

    korean_info = defaultdict(list)
    for info in korean["infos"]:
        if info["inam"]:
            korean_info[info["inam"].lower()].append(info)

    coverage = []
    missing_infos = []
    logic_mismatches = []
    response_matches = 0
    for info in official["infos"]:
        matches = korean_info.get(info["inam"].lower(), []) if info["inam"] else []
        row = {
            "parent_dial": info["parent_dial"],
            "inam": info["inam"],
            "official_response": info["response"],
            "official_result": info["result"],
            "official_fields": info["fields"],
            "translation_match_count": len(matches),
            "translation_matches": matches,
        }
        coverage.append(row)
        if not matches:
            missing_infos.append(row)
            continue
        if any(m.get("response") == info["response"] for m in matches):
            response_matches += 1
        if not any(logic_signature(m) == logic_signature(info) for m in matches):
            logic_mismatches.append(row)

    dial_stats = []
    for dial in official["dials"]:
        name = dial["name"]
        rows = [r for r in coverage if r["parent_dial"] == name]
        dial_stats.append(
            {
                "dial": name,
                "official_info_count": len(rows),
                "covered_info_count": sum(1 for r in rows if r["translation_match_count"]),
                "missing_info_count": sum(1 for r in rows if not r["translation_match_count"]),
                "translation_exact_dial_records": len(korean["keyed"].get(("DIAL", name.lower()), [])),
            }
        )

    # Compare non-dialogue records touched by the official plugin against the Korean ESP.
    record_coverage = []
    for (rtype, rid_lower), rows in official["keyed"].items():
        if rtype in ("DIAL", "INFO", "TES3"):
            continue
        for row in rows:
            kmatches = korean["keyed"].get((rtype, rid_lower), [])
            record_coverage.append(
                {
                    "type": rtype,
                    "id": row.get("id"),
                    "official_display_name": row.get("display_name", ""),
                    "translation_match_count": len(kmatches),
                    "translation_matches": kmatches,
                }
            )

    relevant_terms = (
        "work",
        "propylon",
        "index",
        "일",
        "일거리",
        "프로필론",
        "색인",
        "인덱스",
    )

    def sidecar_hits(rows):
        out = []
        for row in rows:
            hay = (row["key"] + "\n" + row["value"]).lower()
            if any(term.lower() in hay for term in relevant_terms):
                out.append(row)
        return out

    report = {
        "official_master_index": {
            k: v
            for k, v in official.items()
            if k not in ("keyed", "infos")
        },
        "translation": {
            k: v
            for k, v in korean.items()
            if k not in ("keyed", "infos", "dials")
        },
        "summary": {
            "official_dial_count": len(official["dials"]),
            "official_info_count": len(official["infos"]),
            "covered_info_count": len(official["infos"]) - len(missing_infos),
            "missing_info_count": len(missing_infos),
            "logic_mismatch_count": len(logic_mismatches),
            "identical_response_match_count": response_matches,
        },
        "dial_stats": dial_stats,
        "official_info_coverage": coverage,
        "missing_official_infos": missing_infos,
        "logic_mismatches": logic_mismatches,
        "record_coverage": record_coverage,
        "sidecar_hits": {
            "mrk": sidecar_hits(mrk),
            "top": sidecar_hits(top),
        },
    }

    # JSON cannot serialize defaultdicts hidden in build_model; report is plain structures.
    (args.out / "master_index_compat_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    key_dials = {
        "work",
        "propylon index",
        "greeting 5",
        "ms_master_index",
    }
    summary_lines = [
        "Master Index compatibility analysis",
        "===================================",
        f"Official plugin: {official['path']}",
        f"  sha256={official['sha256']} size={official['size']}",
        f"Korean ESP: {korean['path']}",
        f"  sha256={korean['sha256']} size={korean['size']}",
        "",
        f"Official DIAL records: {len(official['dials'])}",
        f"Official INFO records: {len(official['infos'])}",
        f"INFO IDs present in Korean ESP: {len(official['infos']) - len(missing_infos)}",
        f"INFO IDs missing from Korean ESP: {len(missing_infos)}",
        f"INFO logic mismatches among matched IDs: {len(logic_mismatches)}",
        "",
        "Official dialogue sections:",
    ]
    for ds in dial_stats:
        marker = " *" if ds["dial"].lower() in key_dials or "propylon" in ds["dial"].lower() else ""
        summary_lines.append(
            f"- {ds['dial']!r}{marker}: INFO={ds['official_info_count']} "
            f"covered={ds['covered_info_count']} missing={ds['missing_info_count']} "
            f"same-name Korean DIAL records={ds['translation_exact_dial_records']}"
        )

    summary_lines += ["", "Relevant sidecar mappings (.mrk):"]
    for row in report["sidecar_hits"]["mrk"]:
        summary_lines.append(f"- L{row['line']}: {row['key']} -> {row['value']}")
    if not report["sidecar_hits"]["mrk"]:
        summary_lines.append("- none")

    summary_lines += ["", "Relevant sidecar mappings (.top):"]
    for row in report["sidecar_hits"]["top"][:200]:
        summary_lines.append(f"- L{row['line']}: {row['key']} -> {row['value']}")
    if not report["sidecar_hits"]["top"]:
        summary_lines.append("- none")

    summary_lines += ["", "Plugin records involving Folms/Index/Propylon:"]
    for row in record_coverage:
        hay = f"{row.get('id','')} {row.get('official_display_name','')}".lower()
        if any(x in hay for x in ("folms", "index", "propylon")):
            km = row["translation_matches"]
            names = [m.get("display_name", "") for m in km]
            summary_lines.append(
                f"- {row['type']} {row['id']!r}: official={row['official_display_name']!r}; "
                f"Korean matches={len(km)} names={names!r}"
            )

    (args.out / "master_index_compat_summary.txt").write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
