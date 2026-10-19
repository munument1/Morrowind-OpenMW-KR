"""Verify that the Daedric-script patch changes only 22 spoken subtitles."""

import argparse
from pathlib import Path

from patch_daedric_shrine_dialogue import (
    SCRIPT_NAMES,
    SCRIPT_SAY,
    SUBTITLES,
    extract_master_english,
    fields,
    records,
    script_name,
)


def check(master: Path, original: Path, output: Path):
    expected = extract_master_english(master)
    before = list(records(original.read_bytes()))
    after = list(records(output.read_bytes()))
    if len(before) != len(after):
        raise AssertionError("Record count changed")

    changed_scripts = set()
    subtitles_checked = set()
    for index, (old, new) in enumerate(zip(before, after)):
        if old == new:
            continue
        if old[0] != new[0] or old[2:] != new[2:]:
            raise AssertionError(f"Unexpected record header change at index {index}")
        if old[0] != b"SCPT":
            raise AssertionError(f"Non-script record changed at index {index}")
        old_fields = list(fields(old[1]))
        new_fields = list(fields(new[1]))
        name = script_name(old_fields)
        if name not in SCRIPT_NAMES or script_name(new_fields) != name:
            raise AssertionError(f"Unexpected script changed: {name}")
        if [tag for tag, _ in old_fields] != [tag for tag, _ in new_fields]:
            raise AssertionError(f"Fields changed for {name}")
        for (old_tag, old_val), (_, new_val) in zip(old_fields, new_fields):
            if old_tag != b"SCTX":
                if old_val != new_val:
                    raise AssertionError(f"Non-source script data changed for {name}: {old_tag}")
                continue
            before_text = old_val.decode("utf-8")
            after_text = new_val.decode("utf-8")
            after_by_voice = {}
            for match in SCRIPT_SAY.finditer(after_text):
                voice = match[2].lower()
                if voice not in expected or expected[voice][0] != name:
                    raise AssertionError(f"Unexpected voice {voice} in {name}")
                translated = SUBTITLES[next(k for k in SUBTITLES if k.lower() == voice)]
                if match[3] != translated:
                    raise AssertionError(f"Voice has untranslated text: {voice}")
                after_by_voice[voice] = match[3]
                subtitles_checked.add(voice)

            def revert(match):
                return match[1] + expected[match[2].lower()][1] + match[4]

            if SCRIPT_SAY.sub(revert, after_text) != before_text:
                raise AssertionError(f"Changes outside the voiced subtitles in {name}")
            if not after_by_voice:
                raise AssertionError(f"No changed dialogue in {name}")
        changed_scripts.add(name)

    if changed_scripts != SCRIPT_NAMES:
        raise AssertionError(f"Missing scripts: {SCRIPT_NAMES - changed_scripts}")
    if subtitles_checked != set(expected):
        raise AssertionError(f"Missing voices: {set(expected) - subtitles_checked}")
    print(f"PASS: {len(before)} records preserved; {len(changed_scripts)} scripts / "
          f"{len(subtitles_checked)} subtitles translated; every other byte unchanged")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--master", required=True, type=Path)
    ap.add_argument("--source-esp", required=True, type=Path)
    ap.add_argument("--patched-esp", required=True, type=Path)
    a = ap.parse_args()
    check(a.master, a.source_esp, a.patched_esp)
