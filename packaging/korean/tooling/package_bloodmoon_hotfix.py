#!/usr/bin/env python3
"""Build the Windows and PFP Bloodmoon release packages from verified inputs."""

import argparse
from copy import copy
import json
import struct
from pathlib import Path
from zipfile import ZipFile

from publish_pfp_kr12 import fields, records, sha


CORE = "payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.esp"
PFP = "Patch for Purists.esm"
GREETING = b"3276191812384925826"
UDYRFRYKTE = b"13458304612612714556"
MOON = b"bloodmoonscript"
WIN_VERSION = "KR13.2.2"
PFP_VERSION = "5.0.7-kr1.4"


def verified(path, digest):
    data = path.read_bytes()
    if sha(data) != digest:
        raise ValueError(f"Unexpected input SHA256 for {path}")
    return data


def record(header, subrecords):
    body = b"".join(struct.pack("<4sI", tag, len(value)) + value for tag, value in subrecords)
    return header[:4] + struct.pack("<I", len(body)) + header[8:] + body


def is_moon_script(subrecords):
    return dict(subrecords)[b"SCHD"][:32].rstrip(b"\0").lower() == MOON


def moon_script(header, subrecords):
    result = []
    for tag, value in subrecords:
        if tag == b"SCHD":
            value = value[:44] + b"\0" * 4 + value[48:]
        elif tag == b"SCDT":
            value = b""
        elif tag == b"SCTX":
            end = b"End bloodmoonScript"
            if value.count(end) != 1 or value.count(b"\t\tTurnMoonRed\r\n") != 2:
                raise ValueError("Unexpected bloodmoonScript source")
            # OpenMW recompiles the source and resets the renderer on load.
            value = value.replace(b"\t\tTurnMoonRed\r\n", b"").replace(
                end, b"if ( doOnce == 1 )\r\n\tTurnMoonRed\r\nendif\r\n\r\n" + end
            )
        result.append((tag, value))
    return record(header, result)


def patch_plugin(data, *, vanilla_moon=None):
    is_core = vanilla_moon is not None
    replacements = {
        UDYRFRYKTE: (
            "그 괴물을 @막아야# 하네." if is_core else "그 괴물을 막아야 하네.",
            "@그 짐승을 막아야 한다#.",
        ),
    }
    if not is_core:
        replacements[GREETING] = ("우디르프릭테였다고", "@우디르프릭테#였다고")

    edited = set()
    output = bytearray()
    for tag, header, body in records(data, 16):
        if tag == b"INFO":
            subrecords = fields(body)
            identity = subrecords[0][1].rstrip(b"\0")
            edit = replacements.get(identity)
            if edit:
                old, new = (text.encode("utf-8") for text in edit)
                response = dict(subrecords)[b"NAME"]
                if identity in edited or response.count(old) != 1:
                    raise ValueError(f"Unexpected dialogue response {identity!r}")
                output.extend(record(header, [
                    (key, value.replace(old, new) if key == b"NAME" else value)
                    for key, value in subrecords
                ]))
                edited.add(identity)
                continue
        elif tag == b"SCPT" and is_moon_script(subrecords := fields(body)):
            if is_core or MOON in edited:
                raise ValueError("Unexpected bloodmoonScript override")
            output.extend(moon_script(header, subrecords))
            edited.add(MOON)
            continue
        elif tag == b"TES3" and is_core:
            subrecords = fields(body)
            header_data = dict(subrecords)[b"HEDR"]
            count = struct.unpack_from("<I", header_data, 296)[0]
            output.extend(record(header, [
                (key, value[:296] + struct.pack("<I", count + 1) if key == b"HEDR" else value)
                for key, value in subrecords
            ]))
            continue
        output.extend(header + body)

    expected = set(replacements)
    if is_core:
        output.extend(vanilla_moon)
    else:
        expected.add(MOON)
    if edited != expected:
        raise ValueError(f"Missing expected records: {expected - edited}")
    return bytes(output)


def write_archive(source, output, changes):
    if set(changes) - set(source.namelist()):
        raise ValueError("Release ZIP is missing expected entries")
    with ZipFile(output, "x") as target:
        for entry in source.infolist():
            data = changes[entry.filename] if entry.filename in changes else source.read(entry)
            target.writestr(copy(entry), data)
    with ZipFile(output) as target:
        if target.testzip() or target.namelist() != source.namelist():
            raise ValueError(f"ZIP verification failed: {output}")
        for name in target.namelist():
            expected = changes[name] if name in changes else source.read(name)
            if target.read(name) != expected:
                raise ValueError(f"ZIP entry differs: {name}")
    print(f"{sha(output.read_bytes())}  {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("windows_zip", type=Path)
    parser.add_argument("pfp_zip", type=Path)
    parser.add_argument("bloodmoon_esm", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    verified(args.windows_zip, "ab07512ae7c78075f0c2fae473f7dedb83b1e8ee6ef05a108fc25f45616182c5")
    verified(args.pfp_zip, "22fc754fc3b6aa77394fefad10b96201ce9c92511dff65191b2a8c81db310f4d")
    master = verified(args.bloodmoon_esm, "bd27090d0e6ad4c1bf1abc83f1a2dac56fcc82cae7bfe8263c413fb301801357")
    moon, = [
        moon_script(header, subrecords)
        for kind, header, body in records(master, 16)
        if kind == b"SCPT" and is_moon_script(subrecords := fields(body))
    ]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.windows_zip) as source:
        original = source.read(CORE)
        plugin = patch_plugin(original, vanilla_moon=moon)
        provenance = json.loads(source.read("SOURCE-PROVENANCE.json"))
        if provenance["translation_esp_sha256"] != sha(original):
            raise ValueError("The input plugin does not match its provenance")
        provenance["translation_esp_sha256"] = sha(plugin)
        provenance["bloodmoon_data_hotfix"] = {
            "version": WIN_VERSION,
            "previous_translation_esp_sha256": sha(original),
            "source_bloodmoon_esm_sha256": sha(master),
        }
        notes = source.read("README-KOREAN.txt").replace(b"KR13.2", WIN_VERSION.encode(), 1)
        intro = (
            f"\r\n{WIN_VERSION} 변경 사항\r\n"
            "- 블러드문 우디르프릭테 후속 대화 링크와 세쿤다 색상 복원을 수정했습니다.\r\n"
            f"- Patch for Purists 사용 시 {PFP_VERSION} 한국어 패키지를 함께 적용하세요.\r\n"
        ).encode()
        heading, newline, rest = notes.partition(b"\n")
        installer = source.read("install-korean.ps1")
        installer = installer.replace(b"KR13.2", WIN_VERSION.encode()).replace(
            b"korean-kr13.2-backup-", b"korean-kr13.2.2-backup-"
        )
        write_archive(source, args.output_dir / f"Morrowind-Korean-OpenMW-0.51.0-{WIN_VERSION}-Full.zip", {
            CORE: plugin,
            "README-KOREAN.txt": heading + newline + intro + rest,
            "install-korean.ps1": installer,
            "SOURCE-PROVENANCE.json": (json.dumps(provenance, ensure_ascii=False, indent=2) + "\n").encode(),
        })
    with ZipFile(args.pfp_zip) as source:
        plugin = patch_plugin(source.read(PFP))
        manifest = json.loads(source.read("INSTALL-MANIFEST.json"))
        manifest["source_archive"] = args.pfp_zip.name
        manifest["version"] = PFP_VERSION
        manifest["files"][PFP] = sha(plugin)
        notes = source.read("README_KO.md").decode("utf-8")
        notes = notes.replace("5.0.7-kr1.3", PFP_VERSION, 1)
        notes = notes.replace("\n\n", (
            f"\n\n스벤야의 우디르프릭테 대화와 세쿤다 색상을 수정했습니다. "
            f"Windows 본편 {WIN_VERSION}과 함께 사용하세요.\n\n"
        ), 1)
        write_archive(source, args.output_dir / f"PFP_{PFP_VERSION}_OpenMW-{WIN_VERSION}.zip", {
            PFP: plugin,
            "INSTALL-MANIFEST.json": (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode(),
            "README_KO.md": notes.encode(),
        })


if __name__ == "__main__":
    main()
