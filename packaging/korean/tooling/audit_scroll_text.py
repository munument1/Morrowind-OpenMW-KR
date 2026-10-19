"""Audit the text shown when opening TES3 magic scrolls in OpenMW.

The opened page is BOOK/TEXT, not BOOK/FNAM or the linked ENCH record.
"""

import argparse
import json
import re
import struct
from pathlib import Path


def records(raw):
    pos = 0
    while pos < len(raw):
        if pos + 16 > len(raw):
            raise ValueError("Truncated TES3 record header")
        tag, size, _, flags = struct.unpack_from("<4sIII", raw, pos)
        end = pos + 16 + size
        if end > len(raw):
            raise ValueError("Truncated TES3 record")
        if tag == b"BOOK":
            yield raw[pos + 16:end], flags
        pos = end


def fields(body):
    result = {}
    pos = 0
    while pos < len(body):
        if pos + 8 > len(body):
            raise ValueError("Truncated subrecord header")
        tag, size = struct.unpack_from("<4sI", body, pos)
        end = pos + 8 + size
        if end > len(body):
            raise ValueError("Truncated subrecord")
        result[tag] = body[pos + 8:end]
        pos = end
    return result


def decode(value):
    value = value.rstrip(b"\x00")
    try:
        return value.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return value.decode("cp949")
        except UnicodeDecodeError:
            return value.decode("cp1252", "replace")


def text_excerpt(value):
    value = re.sub(r"<[^>]*>", " ", decode(value))
    return re.sub(r"\s+", " ", value).strip()[:220]


def extract_books(path):
    result = {}
    for body, flags in records(path.read_bytes()):
        if flags & 0x20:
            continue
        field = fields(body)
        if b"BKDT" not in field:
            continue
        if len(field[b"BKDT"]) < 12:
            raise ValueError(f"Invalid BKDT in {path}")
        record_id = decode(field[b"NAME"]).lower()
        result[record_id] = {
            "id": decode(field[b"NAME"]),
            "is_scroll": bool(struct.unpack_from("<I", field[b"BKDT"], 8)[0]),
            "name": decode(field.get(b"FNAM", b"")),
            "text": field.get(b"TEXT", b""),
            "enchantment": decode(field.get(b"ENAM", b"")),
            "source": path.name,
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", required=True, type=Path, action="append")
    parser.add_argument("--translation", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()

    original = {}
    for path in args.master:
        original.update(extract_books(path))
    translated = extract_books(args.translation)
    out = []
    for key, base in original.items():
        if not base["is_scroll"]:
            continue
        translated_book = translated.get(key)
        text = translated_book["text"] if translated_book else base["text"]
        name = translated_book["name"] if translated_book else base["name"]
        status = (
            "no_override" if translated_book is None
            else "identical_text" if text == base["text"]
            else "empty_text" if not text.strip(b"\x00")
            else "translated_or_modified"
        )
        out.append({
            "id": base["id"],
            "status": status,
            "name": name,
            "original_name": base["name"],
            "enchantment": base["enchantment"],
            "magic_scroll": bool(base["enchantment"]),
            "original_text": text_excerpt(base["text"]),
            "current_text": text_excerpt(text),
            "raw_original_text": decode(base["text"]),
            "raw_current_text": decode(text),
            "source": base["source"],
        })
    by_status = {name: sum(v["status"] == name for v in out) for name in
                 ("no_override", "identical_text", "empty_text", "translated_or_modified")}
    enchanted = [v for v in out if v["magic_scroll"]]
    report = {"master_books": len(original), "translation_books": len(translated),
              "scroll_count": len(out), "magic_scroll_count": len(enchanted),
              "status": by_status,
              "magic_scroll_status": {
                  name: sum(v["status"] == name for v in enchanted) for name in by_status},
              "scrolls": out}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"master_books": len(original), "translation_books": len(translated),
                      "scroll_count": len(out), "magic_scroll_count": len(enchanted),
                      "status": by_status, "magic_scroll_status": report["magic_scroll_status"]},
                     ensure_ascii=False))
    for item in enchanted[:args.limit]:
        print(json.dumps({k: v for k, v in item.items() if k not in
                          ("raw_original_text", "raw_current_text")},
                         ensure_ascii=False))


if __name__ == "__main__":
    main()
