#!/usr/bin/env python3
"""Read-only lexical audit of dialogue links in the pinned Korean release ZIP.

Candidates are not confirmed broken quests: runtime actor/quest conditions and
unmodified English masters are not included in the redistributed Korean ZIP.
"""
import argparse
import hashlib
import json
import re
import struct
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

STEM = "Morrowind_Korean_ReTranslation"
# Missing from the KR12.2 implicit Korean topic boundary allowlist.
QUOTATIVE_ENDINGS = ("이라는", "라는", "이란", "란")
FIGHTERS = (
    "persius mercius", "eydis fireeye", "eydis fire-eye", "hrundi",
    "lorbumol gro-aglakh", "lorbumol gro-uglakh", "sjoring hard-heart",
)
FIGHTERS_WORDS = ("전사 길드", "전사 조합", "울리네", "바스", "드로'사카르")


def chunks(data, header):
    offset = 0
    while offset < len(data):
        if offset + header > len(data):
            raise ValueError("truncated TES3 record")
        tag, size = struct.unpack_from("<4sI", data, offset)
        end = offset + header + size
        if end > len(data):
            raise ValueError("TES3 subrecord out of bounds")
        yield tag, data[offset + header:end]
        offset = end


def dec(value):
    return value.rstrip(b"\0").decode("utf-8", errors="replace")


def sidecar(data):
    return dict(line.split("\t", 1) for line in data.decode("utf-8-sig").splitlines() if "\t" in line)


def package(path):
    result = {}
    with zipfile.ZipFile(path) as archive:
        for suffix in ("esp", "top", "mrk"):
            names = [n for n in archive.namelist() if n.endswith(STEM + "." + suffix)]
            if len(names) != 1:
                raise ValueError("expected one Korean ." + suffix + " but found " + repr(names))
            result[suffix] = archive.read(names[0])
    return result


def dialogue(esp):
    topics = set()
    infos = []
    parent, kind = None, None
    for tag, blob in chunks(esp, 16):
        if tag not in (b"DIAL", b"INFO"):
            continue
        fields = dict(chunks(blob, 8))
        if tag == b"DIAL":
            parent = dec(fields.get(b"NAME", b""))
            kind = fields.get(b"DATA", b"\xff")[0]
            if kind == 0 and b"DELE" not in fields:
                topics.add(parent)
        elif b"NAME" in fields:
            infos.append({
                "parent": parent, "kind": kind,
                "info": dec(fields.get(b"INAM", b"")),
                "actor": dec(fields.get(b"ONAM", b"")),
                "faction": dec(fields.get(b"FNAM", b"")),
                "text": dec(fields[b"NAME"]),
            })
    return topics, infos


def hangul(char):
    return bool(char) and "\uac00" <= char <= "\ud7a3"


def scan(data):
    topics, infos = dialogue(data["esp"])
    mark = sidecar(data["mrk"])
    forms = sidecar(data["top"])
    by_tail = defaultdict(list)
    for topic in topics:
        keyword = mark.get(topic, topic)
        if keyword and len(keyword) > 1 and keyword != "일" and hangul(keyword[-1]):
            by_tail[keyword[-1]].append((topic, keyword))

    findings, orphan = [], []
    suffix_counts = Counter()
    for info in infos:
        text = info["text"]
        for suffix_match in re.finditer(r"(이라는|라는|이란|란)(?![가-힣])", text):
            suffix_start = suffix_match.start()
            if not suffix_start:
                continue
            preceding = text[suffix_start - 1]
            for topic, keyword in by_tail.get(preceding, []):
                start = suffix_start - len(keyword)
                if start < 0 or text[start:suffix_start] != keyword:
                    continue
                if start > 0 and hangul(text[start - 1]):
                    continue
                # An explicit @topic# covers this occurrence through a separate path.
                if "@" in text[:start].split("#")[-1]:
                    continue
                guild = ("fighters guild" in info["faction"].lower()
                         or any(a in info["actor"].lower() for a in FIGHTERS)
                         or any(word in text for word in FIGHTERS_WORDS))
                row = {key: info[key] for key in ("parent", "kind", "info", "actor", "faction")}
                row.update({
                    "topic": topic, "keyword": keyword,
                    "suffix": suffix_match.group(1),
                    "scope": "fighters_candidate" if guild else "other",
                    "context": text[max(0, start - 36):min(len(text), suffix_match.end() + 44)],
                })
                findings.append(row)
                suffix_counts[suffix_match.group(1)] += 1
        for tag in re.findall(r"@([^@#]+)#", text):
            tag = tag.rstrip("\x7f")
            target = forms.get(tag, tag)
            if target not in topics:
                orphan.append({"info": info["info"], "parent": info["parent"],
                               "tag": tag, "target": target})
    return {
        "status": "SOURCE_LEXICAL_CANDIDATES_NOT_GAMEPLAY_VERIFIED",
        "esp_sha256": hashlib.sha256(data["esp"]).hexdigest(),
        "topic_count": len(topics),
        "info_count": len(infos),
        "candidate_count": len(findings),
        "fighters_candidate_count": sum(x["scope"] == "fighters_candidate" for x in findings),
        "by_suffix": dict(suffix_counts),
        "orphan_tag_candidate_count": len(orphan),
        "orphan_tag_examples": orphan[:100],
        "findings": findings,
        "note": "Do not auto-apply INFO fixes: verify topic alias, source English, NPC conditions, and player-openable dialogue.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-esp-sha")
    a = parser.parse_args()
    data = package(a.zip)
    report = scan(data)
    if a.expected_esp_sha and report["esp_sha256"] != a.expected_esp_sha.lower():
        raise ValueError("unexpected released ESP hash; refusing to audit a different baseline")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("findings", "orphan_tag_examples")}, ensure_ascii=False, indent=2))
    print("FIGHTERS_GUILD_CANDIDATES:")
    for row in (r for r in report["findings"] if r["scope"] == "fighters_candidate"):
        print(json.dumps(row, ensure_ascii=False))
    print("OTHER_FIRST_CANDIDATES:")
    for row in report["findings"][:35]:
        print(json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()
