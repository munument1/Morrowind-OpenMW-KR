#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reproducibly replay source-hash-pinned native-verified TES3 INFO/TOP edits.

NO automatic release. Read-only source plugin and TOP; writes to a NEW output
directory, never overwriting or editing an installed/released file.
Only INFO.NAME subrecords and appended TOP aliases can change. Strict hashes
for original whole plugin, TOP, each old/new field, and final outputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
from pathlib import Path

HEADER = struct.Struct("<4sIII")
SUB = struct.Struct("<4sI")
MAX_RECORD_BYTES = 256 * 1024 * 1024


def digest_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode_info(original, change):
    parts = []
    position = 0
    seen_name = 0
    inam = None
    while position < len(original):
        if position + 8 > len(original):
            raise ValueError("INFO: truncated subrecord")
        key, length = SUB.unpack_from(original, position)
        end = position + 8 + length
        if end > len(original):
            raise ValueError("INFO: invalid subrecord bounds")
        old = original[position + 8:end]
        value = old
        if key == b"INAM":
            inam = old.rstrip(b"\0").decode("utf-8", "strict")
        elif key == b"NAME":
            seen_name += 1
            if digest(old) != change["expected_old_INFO_NAME_sha256"]:
                raise ValueError("INFO.NAME source SHA mismatch")
            if old.rstrip(b"\0").decode("utf-8", "strict") != change["old_korean_text"]:
                raise ValueError("INFO.NAME original text mismatch")
            value = (
                change["new_korean_text"].encode("utf-8")
                + old[len(old.rstrip(b"\0")):]
            )
            if digest(value) != change["verified_new_INFO_NAME_sha256"]:
                raise ValueError("INFO.NAME output SHA mismatch")
            if value == old:
                raise ValueError("No-op INFO.NAME change")
        parts.append(SUB.pack(key, len(value)) + value)
        position = end
    if seen_name != 1:
        raise ValueError(f"INFO has {seen_name} NAME subrecords")
    if inam != change["INFO_INAM"]:
        raise ValueError(f"INFO identity drift: {inam!r}")
    return b"".join(parts)


def replay_plugin(src, dst, changes):
    targets = {r["record_index"]: r for r in changes}
    if len(targets) != len(changes):
        raise ValueError("Duplicate TES3 record_index in manifest")
    seen = set()
    count = 0
    with src.open("rb") as inf, dst.open("xb") as out:
        while True:
            head = inf.read(16)
            if not head:
                break
            if len(head) != 16:
                raise ValueError("Truncated TES3 record header")
            tag, length, unk, flags = HEADER.unpack(head)
            if length > MAX_RECORD_BYTES:
                raise ValueError("TES3 record unreasonably large")
            payload = inf.read(length)
            if len(payload) != length:
                raise ValueError("Truncated TES3 record payload")
            target = targets.get(count)
            if target:
                if tag != b"INFO":
                    raise ValueError("Manifest targets non-INFO record")
                new_payload = encode_info(payload, target)
                out.write(HEADER.pack(tag, len(new_payload), unk, flags))
                out.write(new_payload)
                seen.add(count)
            else:
                out.write(head)
                out.write(payload)
            count += 1
    if seen != set(targets):
        raise ValueError("Unmatched INFO record indexes: " + repr(set(targets) - seen))
    return count


def replay_top(src, dst, module):
    data = src.read_bytes()
    if digest(data) != module["baseline_TOP_sha256"]:
        raise ValueError("TOP source SHA mismatch")
    if not data.startswith(b"\xef\xbb\xbf"):
        raise ValueError("Expected UTF8 BOM in published TOP")
    old = {}
    for line in data.decode("utf-8-sig", "strict").splitlines():
        if "\t" not in line:
            continue
        key, target = line.split("\t", 1)
        if key in old and old[key] != target:
            raise ValueError("Input TOP ambiguous mapping")
        old.setdefault(key, target)
    new_map = module["new_TOP_aliases"]
    if set(old) & set(new_map):
        raise ValueError("TOP patch tries to overwrite an existing alias")
    tail = b"" if data.endswith((b"\n", b"\r")) else b"\r\n"
    # Original fixed-source builders used alphabetical order for regional
    # TOP aliases but insertion order for TR_Mainland. Validate exact SHA,
    # never silently accept an arbitrary ordering.
    candidates = (
        list(sorted(new_map.items())),
        list(new_map.items()),
    )
    result = None
    for pairs in candidates:
        addon = tail + b"".join((k + "\t" + v + "\r\n").encode("utf-8")
                                 for k, v in pairs)
        trial = data + addon
        if digest(trial) == module["candidate_TOP_sha256"]:
            result = trial
            break
    if result is None:
        raise ValueError("Replayed TOP SHA mismatch for both verified orders")
    dst.write_bytes(result)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--module", required=True)
    ap.add_argument("--source-plugin", required=True, type=Path)
    ap.add_argument("--source-top", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    a = ap.parse_args()
    manifest = json.loads(a.manifest.read_text("utf-8"))
    if manifest.get("status") != "35_NATIVE_VERIFIED_TOPIC_FIXES_STAGED_UNRELEASED":
        raise ValueError("Unknown/unverified source manifest")
    matched = [m for m in manifest["modules"] if m["id"] == a.module]
    if len(matched) != 1:
        raise ValueError("Unknown/ambiguous module: " + a.module)
    m = matched[0]
    if a.out_dir.exists():
        raise FileExistsError("Refusing to overwrite output dir: " + str(a.out_dir))
    if digest_file(a.source_plugin) != m["baseline_plugin_sha256"]:
        raise ValueError("Input ESM/ESP SHA does not match pinned released source")
    if digest_file(a.source_top) != m["baseline_TOP_sha256"]:
        raise ValueError("Input TOP SHA does not match pinned released source")
    a.out_dir.mkdir(parents=True, exist_ok=False)
    dst_plugin = a.out_dir / a.source_plugin.name
    dst_top = a.out_dir / a.source_top.name
    try:
        n_records = replay_plugin(a.source_plugin, dst_plugin, m["INFO_changes"])
        replay_top(a.source_top, dst_top, m)
        if digest_file(dst_plugin) != m["candidate_plugin_sha256"]:
            raise ValueError("Full candidate plugin SHA mismatch")
        if digest_file(dst_top) != m["candidate_TOP_sha256"]:
            raise ValueError("Full candidate TOP SHA mismatch")
        qa = {
            "status": "PINNED_SOURCE_REPLAY_PASS_NO_RELEASE",
            "module":a.module,
            "source_plugin_sha256":m["baseline_plugin_sha256"],
            "candidate_plugin_sha256":m["candidate_plugin_sha256"],
            "source_top_sha256":m["baseline_TOP_sha256"],
            "candidate_top_sha256":m["candidate_TOP_sha256"],
            "records_scanned":n_records,
            "INFO_NAME_changed":len(m["INFO_changes"]),
            "TOP_aliases_added":len(m["new_TOP_aliases"]),
            "source_files_modified":False,
            "published":False,
        }
        (a.out_dir / "source_pinned_replay_qa.json").write_text(
            json.dumps(qa, ensure_ascii=False, indent=2) + "\n", "utf-8"
        )
        print("REPLAY_PASS=" + json.dumps(qa, ensure_ascii=False), flush=True)
    except Exception:
        # In case of partial construction, do not leave mislabelled output artifacts.
        shutil.rmtree(a.out_dir)
        raise


if __name__ == "__main__":
    main()
