"""Restore TES3 BOOK Daedric-script passages and add readable Korean below.

The Korean ESP often replaces original A-Z text *inside* <FONT FACE="Daedric">
with Hangul. Daedric fonts lack Hangul glyphs, so the opened page appears blank.
This tool takes the original lettering from the master BOOK/TEXT field and leaves
the existing Korean translation in an unstyled line immediately after the tag.

Other BOOK fields, non-Daedric text, and unrelated TES3 records are unmodified.
This standalone postprocessor can run on any current translation ESP without
rebuilding or overwriting the team's journal/quest translation generator.
"""

import argparse
import json
import re
import struct
from pathlib import Path

from audit_scroll_text import decode, fields


DAEDRIC = re.compile(
    rb'(<font\b(?=[^>]*\bface\s*=\s*["\']Daedric["\'])[^>]*>)(.*?)(</font\s*>)',
    re.IGNORECASE | re.DOTALL,
)
HANGUL = re.compile("[\uac00-\ud7a3]")


def record_list(raw):
    pos = 0
    while pos < len(raw):
        if pos + 16 > len(raw):
            raise ValueError("Truncated TES3 record header")
        tag, length, unknown, flags = struct.unpack_from("<4sIII", raw, pos)
        end = pos + 16 + length
        if end > len(raw):
            raise ValueError("Truncated TES3 record body")
        yield tag, raw[pos + 16:end], unknown, flags
        pos = end


def subrecord_list(body):
    pos = 0
    while pos < len(body):
        if pos + 8 > len(body):
            raise ValueError("Truncated TES3 subrecord header")
        tag, length = struct.unpack_from("<4sI", body, pos)
        end = pos + 8 + length
        if end > len(body):
            raise ValueError("Truncated TES3 subrecord body")
        yield tag, body[pos + 8:end]
        pos = end


def pack_fields(values):
    return b"".join(struct.pack("<4sI", tag, len(value)) + value for tag, value in values)


def pack_record(tag, body, unknown, flags):
    return struct.pack("<4sIII", tag, len(body), unknown, flags) + body


def master_books(paths):
    result = {}
    for path in paths:
        for tag, body, _, flags in record_list(path.read_bytes()):
            if tag != b"BOOK" or flags & 0x20:
                continue
            fs = fields(body)
            if b"NAME" in fs:
                key = decode(fs[b"NAME"]).lower()
                result[key] = fs.get(b"TEXT", b"")
    return result


def restore(original, translated):
    english = list(DAEDRIC.finditer(original))
    current = list(DAEDRIC.finditer(translated))
    if not current:
        return translated, 0, None
    if len(english) != len(current):
        if any(HANGUL.search(decode(m.group(2))) for m in current):
            return translated, 0, f"Daedric span count mismatch ({len(english)} original, {len(current)} Korean)"
        return translated, 0, None
    replacements = []
    for source, target in zip(english, current):
        source_inner, korean_inner = source.group(2), target.group(2)
        if not HANGUL.search(decode(korean_inner)):
            continue
        if HANGUL.search(decode(source_inner)):
            return translated, 0, "Original Daedric passage contains Hangul"
        if b"<font" in source_inner.lower() or b"<font" in korean_inner.lower():
            return translated, 0, "Nested FONT inside Daedric span"
        if not re.search(rb"[A-Za-z]", source_inner):
            return translated, 0, "No Latin letters in original Daedric passage"
        # The paired original Latin letters render with the Daedric alphabet.
        # The Korean gloss after </FONT> uses the normal Korean-compatible font.
        replacement = target.group(1) + source_inner + target.group(3) + b"<BR>" + korean_inner
        replacements.append((target.start(), target.end(), replacement))
    if not replacements:
        return translated, 0, None
    patched = bytearray(translated)
    for start, end, replacement in reversed(replacements):
        patched[start:end] = replacement
    return bytes(patched), len(replacements), None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", required=True, type=Path, action="append")
    parser.add_argument("--translation", required=True, type=Path)
    parser.add_argument("--output", type=Path, help="New output ESP path; omit for read-only audit")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.output and args.output.exists():
        raise ValueError("Output path must not already exist")
    canonical = master_books(args.master)
    old = args.translation.read_bytes()
    changed = []
    errors = []
    out = []
    total_books = 0
    for tag, body, unknown, flags in record_list(old):
        if tag == b"BOOK" and not flags & 0x20:
            total_books += 1
            fs = fields(body)
            key = decode(fs.get(b"NAME", b"")).lower()
            original = canonical.get(key)
            text = fs.get(b"TEXT", b"")
            if original is None:
                if DAEDRIC.search(text) and HANGUL.search(decode(text)):
                    errors.append({"id": key, "error": "Missing original BOOK record"})
            else:
                new, count, error = restore(original, text)
                if error:
                    errors.append({"id": key, "error": error})
                if count:
                    if not any(k == b"TEXT" for k, _ in subrecord_list(body)):
                        raise ValueError("BOOK lacks TEXT despite detected Daedric span")
                    rebuilt = pack_fields(
                        [(k, new if k == b"TEXT" else v) for k, v in subrecord_list(body)]
                    )
                    if [(k, v) for k, v in subrecord_list(rebuilt) if k != b"TEXT"] != [
                        (k, v) for k, v in subrecord_list(body) if k != b"TEXT"
                    ]:
                        raise AssertionError("Changed unrelated BOOK field")
                    body = rebuilt
                    changed.append({"id": key, "restored_daedric_spans": count})
        out.append(pack_record(tag, body, unknown, flags))
    result = b"".join(out)
    report = {
        "master_books": len(canonical),
        "translation_books": total_books,
        "records_unchanged": sum(1 for _ in record_list(old)) == sum(1 for _ in record_list(result)),
        "updated_books": len(changed),
        "restored_daedric_spans": sum(x["restored_daedric_spans"] for x in changed),
        "errors": errors,
        "changes": changed,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
    if errors:
        raise ValueError(json.dumps(report, ensure_ascii=False))
    if args.output:
        if report["updated_books"] == 0:
            raise ValueError("No Korean Daedric passages were found to restore")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(result)
    print(json.dumps({k: v for k, v in report.items() if k != "changes"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
