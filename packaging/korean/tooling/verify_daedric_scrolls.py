"""Verify that localized Morrowind books preserve original Daedric lettering.

The DemonicLetters font maps Latin A-Z/a-z to Daedric glyphs. Translating the
contents of a <font face="Daedric"> span to Hangul makes the text invisible.
This checks overridden BOOK records against the original game masters without
modifying either source.
"""

import argparse
from pathlib import Path
import re

from build_kr5_data import fields, records


FONT_ELEMENT = re.compile(rb"<font\b(?P<attrs>[^>]*)>(?P<text>.*?)</font\s*>", re.I | re.S)
DAEDRIC_FACE = re.compile(rb"\bface\s*=\s*(?:\"daedric\"|'daedric'|daedric\b)", re.I)


def daedric_text(book_text):
    return [match.group("text") for match in FONT_ELEMENT.finditer(book_text)
            if DAEDRIC_FACE.search(match.group("attrs"))]


def glyph_text(spans):
    # The translation may reflow blank lines in letters without changing glyphs.
    return [re.sub(rb"\s+", b"", span) for span in spans]


def book_records(path):
    for tag, body, _, _ in records(path.read_bytes()):
        if tag != b"BOOK":
            continue
        subrecords = dict(fields(body))
        if b"NAME" in subrecords and b"TEXT" in subrecords:
            book_id = subrecords[b"NAME"].rstrip(b"\0").lower()
            yield book_id, daedric_text(subrecords[b"TEXT"])


def show(raw):
    return raw.decode("utf-8", errors="replace").replace("\r", "\\r").replace("\n", "\\n")[:140]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master", type=Path, action="append", required=True,
                        help="Original Morrowind.esm (repeat for Tribunal/Bloodmoon in load order)")
    parser.add_argument("--plugin", type=Path, required=True,
                        help="Localized Morrowind_Korean_ReTranslation.esp")
    args = parser.parse_args()

    originals = {}
    for master in args.master:
        for book_id, spans in book_records(master):
            if spans:
                originals[book_id] = spans

    if not originals:
        parser.error("Original masters contain no Daedric book text; check input files")

    checked = 0
    failures = []
    for book_id, translated_spans in book_records(args.plugin):
        if book_id not in originals:
            continue
        checked += 1
        original_spans = originals[book_id]
        if glyph_text(translated_spans) != glyph_text(original_spans):
            failures.append((book_id, original_spans, translated_spans))

    print(f"Original Daedric books: {len(originals)}; localized overrides checked: {checked}; failures: {len(failures)}")
    for book_id, expected, actual in failures:
        print(f"FAIL {book_id.decode('ascii', errors='replace')}")
        print("  original : " + " | ".join(show(part) for part in expected))
        print("  localized: " + " | ".join(show(part) for part in actual))

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
