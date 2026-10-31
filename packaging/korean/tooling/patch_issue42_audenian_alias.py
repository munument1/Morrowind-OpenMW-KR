#!/usr/bin/env python3
"""Prepare a data-only KR12.3.1 candidate fixing three source-confirmed wrong .top aliases.

The published ZIP and ESP are read-only. Generate a standalone candidate .top sidecar
and JSON evidence, never a release or replacement of an installed game asset.
"""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from audit_kr12_fighters_topic_candidates import dialogue

ESP_NAME = "Morrowind_Korean_ReTranslation.esp"
TOP_NAME = "Morrowind_Korean_ReTranslation.top"
ESP_SHA256 = "c0cb2f5702da067e11820e5a11ffb4b758ea28e101779fc43a721072783ed253"
DESTINATION = "아우데니안 발리우스"
EXACT_ALIASES = (
    "마법부여사 아우데니안",
    "마법부여사 아우데니안 발리우스",
    "텔바니 마법부여사 아우데니안 발리우스",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def patch_aliases(original: bytes, topics: set[str]) -> tuple[bytes, list[dict]]:
    if DESTINATION not in topics:
        raise ValueError("Audenian Valius DIAL missing: must not insert broken target")
    result = []
    seen = {}
    for line in original.splitlines(keepends=True):
        bom = b"\\xef\\xbb\\xbf" if line.startswith(b"\\xef\\xbb\\xbf") else b""
        actual = line[len(bom):]
        content = actual.rstrip(b"\\r\\n")
        ending = actual[len(content):]
        head, sep, target = content.partition(b"\\t")
        label = head.decode("utf-8") if sep else None
        if label in EXACT_ALIASES:
            if label in seen:
                raise ValueError("Duplicate .top alias: " + label)
            if target.decode("utf-8") != "마법부여":
                raise ValueError("Unexpected original alias target for " + label)
            replacement = DESTINATION.encode("utf-8")
            result.append(bom + head + sep + replacement + ending)
            seen[label] = {"alias": label, "previous": "마법부여", "next": DESTINATION}
        else:
            result.append(line)
    if set(seen) != set(EXACT_ALIASES):
        raise ValueError("Source alias list differs from verified KR12.3.1 data: "
                         + repr(set(EXACT_ALIASES) - set(seen)))
    patched = b"".join(result)
    if patched == original:
        raise ValueError("Candidate produced no changes")
    return patched, [seen[key] for key in EXACT_ALIASES]


def build(source_zip: Path) -> tuple[bytes, dict]:
    with zipfile.ZipFile(source_zip) as z:
        esp = [x for x in z.namelist() if x.endswith("/" + ESP_NAME) or x == ESP_NAME]
        sidecar = [x for x in z.namelist() if x.endswith("/" + TOP_NAME) or x == TOP_NAME]
        if len(esp) != 1 or len(sidecar) != 1:
            raise ValueError("Expected exactly one published translation ESP and .top")
        raw_esp, original = z.read(esp[0]), z.read(sidecar[0])
    if sha(raw_esp) != ESP_SHA256:
        raise ValueError("KR12.3.1 ESP hash mismatch; cannot safely patch newer data")
    topics, _ = dialogue(raw_esp)
    patched, changes = patch_aliases(original, topics)
    # Re-run the same exact source contract; never modify ESP/quest scripts.
    for c in changes:
        assert c["next"] in topics
    return patched, {
        "status": "DATA_ONLY_CANDIDATE_NOT_RELEASED",
        "source_esp_sha256": sha(raw_esp),
        "source_top_sha256": sha(original),
        "candidate_top_sha256": sha(patched),
        "source_sidecar_zip_path": sidecar[0],
        "record_count_unchanged": True,
        "other_bytes_untouched": True,
        "changes": changes,
        "requires_gameplay_qa": True,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-zip", type=Path, required=True)
    p.add_argument("--output-top", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    if args.output_top.exists() or args.report.exists():
        raise ValueError("Candidate outputs must be new")
    patched, report = build(args.source_zip)
    args.output_top.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output_top.write_bytes(patched)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
