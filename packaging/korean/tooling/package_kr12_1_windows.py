#!/usr/bin/env python3
"""Assemble KR12.1 Windows only after a fresh, verified runtime build."""
import argparse
import hashlib
import json
import pathlib
import zipfile

BASE_SHA = "4c1ab3d6163391e7592957552292f4fc5aff22ad0d14020130062ad2ae5c135c"
ESP_SHA = "0f04a21d69ecae16a1c2ae3bb0b739ac4e71cdb59054c809fc844128e2c12327"
EXE = "payload/openmw.exe"
ESP = "payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.esp"
CEL = "payload/mods/Morrowind_Korean_ReTranslation/Siege at Firemoth.cel"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    for key in ("baseline", "data", "exe", "output", "report"):
        parser.add_argument("--" + key, type=pathlib.Path, required=True)
    args = parser.parse_args()
    if sha(args.baseline.read_bytes()) != BASE_SHA:
        raise ValueError("Incorrect public KR12 baseline")
    binary = args.exe.read_bytes()
    if not binary.startswith(b"MZ") or len(binary) < 10_000_000:
        raise ValueError("Missing Windows PE runtime executable")
    with zipfile.ZipFile(args.baseline) as original, zipfile.ZipFile(args.data) as updated:
        old_names = original.namelist()
        new_names = updated.namelist()
        if new_names != old_names + [CEL] or len(set(new_names)) != len(new_names):
            raise ValueError("Unexpected KR12.1 translation archive member inventory")
        if sha(updated.read(ESP)) != ESP_SHA:
            raise ValueError("Incorrect shared KR12.1 translation ESP")
        if not updated.read(CEL).startswith(b"\xef\xbb\xbf"):
            raise ValueError("Official-plugin CEL sidecar must be UTF-8 BOM")
        if binary == original.read(EXE):
            raise ValueError("Unmodified KR12 engine cannot display '지속: N초'")
        for name in old_names:
            if name not in (EXE, ESP) and updated.read(name) != original.read(name):
                raise ValueError("Unexpected modified member " + name)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.output, "w") as target:
            for item in updated.infolist():
                value = binary if item.filename == EXE else updated.read(item.filename)
                target.writestr(item, value)
    with zipfile.ZipFile(args.output) as result:
        assert result.testzip() is None
        assert result.namelist() == new_names
        assert result.read(EXE) == binary
        assert sha(result.read(ESP)) == ESP_SHA
    report = {
        "version": "KR12.1",
        "baseline_zip_sha256": BASE_SHA,
        "exe_sha256": sha(binary),
        "new_exe": True,
        "esp_sha256": ESP_SHA,
        "output_zip_sha256": sha(args.output.read_bytes()),
        "files_unchanged_except_exe_translation_esp_and_new_firemoth_cel": True,
        "pillow_shipment_changed": False,
        "live_gameplay_verified": False,
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (args.output.parent / (args.output.name + ".sha256")).write_text(
        report["output_zip_sha256"] + "  " + args.output.name + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
