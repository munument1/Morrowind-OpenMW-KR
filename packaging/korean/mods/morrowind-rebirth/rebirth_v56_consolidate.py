#!/usr/bin/env python3
"""Consolidate a verified Rebirth 7.2 v56 final layout into ONE private overlay.

No game files or translated output are shipped in this public repository.
Two modes:
  capture --v56-zip ZIP --source-root ORIGINAL_EXTRACTED --out NEW_DIR
  apply --corpus PRIVATE_DIR --source-root ORIGINAL_EXTRACTED --out NEW_DIR
"""
from __future__ import annotations

import argparse
import base64
import collections
import gzip
import hashlib
import json
import pathlib
import struct
import zipfile

FINAL_V56_SHA256 = "8b07aec7d2400f22c60f9833d6339185a54acea687de9ed7f8a9c1030bf6d8f3"
EXPECTED_COUNTS = {"main": 1, "alternate": 1, "addon": 6, "compatibility": 7}
CORPUS_FILENAME = "REBIRTH_72_KR12_V56_CONSOLIDATED_PRIVATE.jsonl.gz"
MANIFEST_FILENAME = "REBIRTH_72_KR12_V56_SOURCE_ANCHORED_MANIFEST.json"

# An unrecognized changed field must be reviewed, never silently incorporated.
TEXT_FIELDS = {
    "INFO": {"NAME", "BNAM"},
    "DIAL": {"NAME"}, "SCPT": {"SCTX"}, "BOOK": {"FNAM", "TEXT"},
    "NPC_": {"FNAM"}, "CREA": {"FNAM"}, "CLAS": {"FNAM", "DESC"},
    "RACE": {"FNAM", "DESC"}, "BSGN": {"FNAM", "DESC"},
    "SKIL": {"DESC"}, "MGEF": {"DESC"}, "FACT": {"FNAM", "RNAM"},
    "REGN": {"FNAM"}, "CELL": {"NAME"}, "GMST": {"STRV"},
    "WEAP": {"FNAM"}, "ARMO": {"FNAM"}, "CLOT": {"FNAM"},
    "APPA": {"FNAM"}, "ALCH": {"FNAM"}, "INGR": {"FNAM"},
    "MISC": {"FNAM"}, "ACTI": {"FNAM"}, "CONT": {"FNAM"},
    "DOOR": {"FNAM"}, "LIGH": {"FNAM"}, "SPEL": {"FNAM"},
    "ENCH": {"FNAM"}, "BODY": {"FNAM"}, "SOUN": {"FNAM"},
}
ADDONS = {"birthsigns", "mercenaries", "races", "skills", "tools", "game settings"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_path(name: str) -> str:
    """Strip ZIP wrapper folders; retain alternate/compatibility identities."""
    p = pathlib.PurePosixPath(name.replace("\\", "/"))
    parts = p.parts
    if not parts or any(x in (".", "..") or ":" in x for x in parts) or p.is_absolute():
        raise ValueError(f"Unsafe ZIP entry: {name!r}")
    lower = [x.casefold() for x in parts]
    for marker in ("alternate version", "compability patches", "compatibility patches"):
        if marker in lower:
            index = lower.index(marker)
            tail = [x for x in parts[index + 1:] if x.casefold() != "data files"]
            return "/".join((parts[index], *tail))
    if "data files" in lower:
        return "/".join(parts[lower.index("data files") + 1:])
    # Only top-level plugin paths are valid without a recognized mod folder.
    if len(parts) == 1:
        return parts[0]
    raise ValueError(f"Cannot determine plugin layout under archive wrapper: {name!r}")


def plugin_category(path: str) -> str:
    p = pathlib.PurePosixPath(path)
    parts = [x.casefold() for x in p.parts]
    filename = p.name.casefold()
    if parts[0] == "alternate version":
        return "alternate"
    if parts[0] in ("compability patches", "compatibility patches"):
        return "compatibility"
    if "[addon]" in filename:
        return "addon"
    return "main"


def validate_layout(plugins: dict[str, bytes]):
    counts = collections.Counter(plugin_category(p) for p in plugins)
    assert dict(counts) == EXPECTED_COUNTS, (counts, EXPECTED_COUNTS)
    addon_names = set()
    for p in plugins:
        if plugin_category(p) == "addon":
            for word in ADDONS:
                if word in pathlib.PurePosixPath(p).name.casefold():
                    addon_names.add(word)
    assert addon_names == ADDONS, ("Missing/additional optional add-ons", addon_names)


def scan_final_zip(path: pathlib.Path):
    assert digest(path.read_bytes()) == FINAL_V56_SHA256, "Not exact v56 final layout ZIP"
    result = {}
    with zipfile.ZipFile(path) as archive:
        for entry in archive.infolist():
            if entry.is_dir() or not entry.filename.casefold().endswith((".esm", ".esp")):
                continue
            key = canonical_path(entry.filename)
            folded = key.casefold()
            assert folded not in {x.casefold() for x in result}, ("Duplicate plugin key", key)
            result[key] = archive.read(entry)
    validate_layout(result)
    return result


def scan_original_root(root: pathlib.Path, expected: dict[str, bytes]):
    assert root.is_dir()
    found = {}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in (".esm", ".esp"):
            continue
        rel = path.relative_to(root).as_posix()
        try:
            name = canonical_path(rel)
        except ValueError:
            continue
        if name.casefold() not in {p.casefold() for p in expected}:
            continue
        assert name.casefold() not in found, ("Ambiguous source plugin", rel)
        found[name.casefold()] = (name, path.read_bytes())
    assert set(found) == {p.casefold() for p in expected}, (
        "Original 7.2 source plugins missing", sorted(set(p.casefold() for p in expected) - set(found))
    )
    return {key: found[key.casefold()][1] for key in expected}


def records(data: bytes):
    pos, ordinal = 0, 0
    while pos < len(data):
        assert pos + 16 <= len(data), "Truncated TES3 record header"
        header = data[pos:pos + 16]
        length = struct.unpack_from("<I", data, pos + 4)[0]
        end = pos + 16 + length
        assert end <= len(data), ("Corrupt TES3 record", ordinal)
        subs = []
        at = pos + 16
        while at < end:
            assert at + 8 <= end
            tag = data[at:at + 4]
            n = struct.unpack_from("<I", data, at + 4)[0]
            value_at = at + 8
            finish = value_at + n
            assert finish <= end, ("Corrupt TES3 subrecord", ordinal)
            subs.append((tag, value_at, data[value_at:finish]))
            at = finish
        assert at == end
        yield ordinal, header, subs
        pos = end
        ordinal += 1
    assert pos == len(data)


def collect(original: bytes, translated: bytes, plugin: str):
    src, dest = list(records(original)), list(records(translated))
    assert len(src) == len(dest), (plugin, "Record count differs")
    rows = []
    for left, right in zip(src, dest):
        index, head, old_subs = left
        i2, h2, new_subs = right
        assert i2 == index and head[:4] == h2[:4] and head[8:16] == h2[8:16], (
            plugin, index, "Record type/flags changed"
        )
        assert len(old_subs) == len(new_subs), (plugin, index, "Subrecord count differs")
        kind = head[:4].decode("ascii")
        for sub_index, (old, new) in enumerate(zip(old_subs, new_subs)):
            tag, source_off, before = old
            new_tag, _, after = new
            assert tag == new_tag, (plugin, index, sub_index, "Field order differs")
            if before == after:
                continue
            field = tag.decode("ascii")
            assert field in TEXT_FIELDS.get(kind, set()), (
                plugin, index, sub_index, "Unexpected edited non-text field", kind, field
            )
            rows.append({
                "plugin": plugin, "record_index": index, "subrecord_index": sub_index,
                "source_data_offset": source_off,
                "record_type": kind, "field_type": field,
                "source_field_sha256": digest(before), "source_field_size": len(before),
                "target_field_sha256": digest(after), "target_field_size": len(after),
                "target_base64": base64.b64encode(after).decode("ascii"),
                "review_flag": "source_only_script_requires_KR124_runtime_check"
                    if (kind, field) == ("SCPT", "SCTX") else None,
            })
    return rows, len(src)


def build_from_rows(source: bytes, rows: list[dict], plugin: str):
    patches = {}
    for row in rows:
        key = row["record_index"], row["subrecord_index"]
        assert key not in patches, (plugin, "duplicate source anchor", key)
        patches[key] = row
    blocks = []
    used = set()
    for index, header, subs in records(source):
        body = bytearray()
        kind = header[:4].decode("ascii")
        for n, (tag, off, raw) in enumerate(subs):
            match = patches.get((index, n))
            value = raw
            if match is not None:
                assert match["plugin"] == plugin
                assert match["source_data_offset"] == off
                assert match["record_type"] == kind
                assert match["field_type"] == tag.decode("ascii")
                assert match["source_field_sha256"] == digest(raw)
                assert match["source_field_size"] == len(raw)
                value = base64.b64decode(match["target_base64"], validate=True)
                assert match["target_field_sha256"] == digest(value)
                assert match["target_field_size"] == len(value)
                used.add((index, n))
            body += tag + struct.pack("<I", len(value)) + value
        blocks.append(header[:4] + struct.pack("<I", len(body)) + header[8:16] + body)
    assert used == set(patches), (plugin, "some source anchors not used", len(used), len(patches))
    return b"".join(blocks)


def save_gzip(path: pathlib.Path, entries: list[dict]):
    with path.open("xb") as out:
        with gzip.GzipFile(fileobj=out, mode="wb", filename="", mtime=0) as compressed:
            for item in entries:
                compressed.write((json.dumps(item, ensure_ascii=False, sort_keys=True,
                                              separators=(",", ":")) + "\n").encode("utf-8"))


def ensure_fresh_output(out: pathlib.Path, inputs: list[pathlib.Path]):
    target = out.resolve()
    assert not target.exists(), "Refusing to overwrite existing output directory"
    assert all(target != src and src not in target.parents for src in inputs), (
        "Output must be separate from its inputs"
    )
    return target


def capture(args):
    final_zip = pathlib.Path(args.v56_zip).resolve(strict=True)
    source_root = pathlib.Path(args.source_root).resolve(strict=True)
    out = ensure_fresh_output(pathlib.Path(args.out), [final_zip, source_root])
    finals = scan_final_zip(final_zip)
    originals = scan_original_root(source_root, finals)
    rows = []
    files = []
    stats = collections.Counter()
    for plugin in sorted(finals, key=str.casefold):
        src, dst = originals[plugin], finals[plugin]
        patches, count = collect(src, dst, plugin)
        assert build_from_rows(src, patches, plugin) == dst, ("Roundtrip mismatch", plugin)
        rows.extend(patches)
        stats[plugin_category(plugin)] += len(patches)
        files.append({
            "path": plugin, "category": plugin_category(plugin),
            "source_sha256": digest(src), "v56_sha256": digest(dst),
            "source_bytes": len(src), "v56_bytes": len(dst),
            "records": count, "changed_fields": len(patches),
            "source_only_script_fields": sum(r["review_flag"] is not None for r in patches),
        })
    manifest = {
        "schema": "rebirth_72_kr12_v56_consolidated_source_anchored_v1",
        "v56_archive_sha256": FINAL_V56_SHA256,
        "plugin_count": len(files), "changed_fields": len(rows),
        "by_category": dict(stats), "plugins": files,
        "historical_intermediate_versions_included": False,
        "complete_binary_roundtrip": True,
        "human_editorial_verified": False,
        "kr124_game_verified": False,
        "release_ready": False,
    }
    out.mkdir(parents=True, exist_ok=False)
    save_gzip(out / CORPUS_FILENAME, rows)
    (out / MANIFEST_FILENAME).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in manifest.items() if k != "plugins"},
                     ensure_ascii=False, indent=2))


def apply(args):
    corpus = pathlib.Path(args.corpus).resolve(strict=True)
    root = pathlib.Path(args.source_root).resolve(strict=True)
    out = ensure_fresh_output(pathlib.Path(args.out), [corpus, root])
    manifest = json.loads((corpus / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert manifest["v56_archive_sha256"] == FINAL_V56_SHA256
    assert manifest["plugin_count"] == 15 and not manifest["release_ready"]
    plugins = {x["path"]: b"" for x in manifest["plugins"]}
    validate_layout(plugins)
    originals = scan_original_root(root, plugins)
    grouped = collections.defaultdict(list)
    with gzip.open(corpus / CORPUS_FILENAME, "rt", encoding="utf-8") as raw:
        for line in raw:
            if not line.strip():
                continue
            row = json.loads(line)
            assert row["plugin"] in plugins
            grouped[row["plugin"]].append(row)
    results = {}
    total = 0
    for file in manifest["plugins"]:
        name = file["path"]
        source = originals[name]
        assert digest(source) == file["source_sha256"], ("Source archive changed", name)
        rows = grouped[name]
        assert len(rows) == file["changed_fields"]
        rebuilt = build_from_rows(source, rows, name)
        assert digest(rebuilt) == file["v56_sha256"], ("Final v56 SHA differs", name)
        results[name] = rebuilt
        total += len(rows)
    assert total == manifest["changed_fields"]
    out.mkdir(parents=True, exist_ok=False)
    for name, data in results.items():
        dest = out.joinpath(*pathlib.PurePosixPath(name).parts)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    (out / "RECONSTRUCTION_QA.json").write_text(
        json.dumps({"status": "PASS_EXACT_V56_PLUGIN_RECONSTRUCTION",
                    "plugin_count": len(results), "changed_fields": total,
                    "source_only_script_runtime_verified": False,
                    "kr124_game_verified": False, "release_ready": False},
                   indent=2) + "\n", encoding="utf-8"
    )
    print(f"Reconstructed {len(results)} original-layout plugins in new folder: {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sp = ap.add_subparsers(dest="action", required=True)
    a = sp.add_parser("capture", help="Compare original plugins with exact v56 ZIP; output one PRIVATE overlay")
    a.add_argument("--v56-zip", required=True)
    a.add_argument("--source-root", required=True)
    a.add_argument("--out", required=True)
    a.set_defaults(func=capture)
    b = sp.add_parser("apply", help="Reconstruct all 15 v56 plugins locally from the ONE private overlay")
    b.add_argument("--corpus", required=True)
    b.add_argument("--source-root", required=True)
    b.add_argument("--out", required=True)
    b.set_defaults(func=apply)
    options = ap.parse_args()
    options.func(options)


if __name__ == "__main__":
    main()
