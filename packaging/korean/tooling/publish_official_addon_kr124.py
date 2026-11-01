#!/usr/bin/env python3
"""Reissue the verified KR3 Official Add-ons Korean translation as a KR12.4 optional file.

Source-only translation archive; never bundles Bethesda original plugin assets.
No local/game files changed. Nexus publication is explicitly a separate command.
"""
import argparse
import base64
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

SOURCE_SHA = "404dfe169203bdec679ec67d456aa7516421298dbec89620331a6af931bbe79f"
MAIN_SHA = "71fbbd1ae5506df4444fe47f31b29101f010a96fa5d73bb4b8699977cd211497"
SOURCE_NAME = "Morrowind_OfficialAddon_KR.zip"
MAIN_NAME = "Morrowind-Korean-OpenMW-0.51.0-KR12.4-Full.zip"
EXPECTED_FILES = {
    "Morrowind_OfficialAddon_KR.esp",
    "Morrowind_OfficialAddon_KR.top",
    "Morrowind_OfficialAddon_KR.mrk",
    "Morrowind_OfficialAddon_KR.cel",
    "README.txt",
    "SHA256SUMS.txt",
}
MASTERS = {
    "Morrowind.esm", "AreaEffectArrows.esp", "LeFemmArmor.esp",
    "master_index.esp", "bcsounds.esp", "entertainers.esp",
    "adamantiumarmor.esp", "EBQ_Artifact.esp", "Siege at Firemoth.esp",
}
MOD_UID = "429496790096"
MOD_SCOPED_ID = "60496"
VERSION = "0.51.0-KR12.4"
GROUP_NAME = "Official Add-ons Korean Translation"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(source, main):
    assert sha(source) == SOURCE_SHA, "Archived KR3 source SHA changed"
    assert sha(main) == MAIN_SHA, "Published KR12.4 main SHA changed"
    with zipfile.ZipFile(source) as archive:
        assert archive.testzip() is None, "Corrupt optional ZIP"
        assert set(archive.namelist()) == EXPECTED_FILES, "Unexpected file inventory"
        assert not any("/" in name or "\\" in name for name in archive.namelist()), "Unsafe paths"
        esp = archive.read("Morrowind_OfficialAddon_KR.esp")
        assert esp[:4] == b"TES3", "Translation plugin is not TES3"
        found = set()
        pos = 0
        while True:
            pos = esp.find(b"MAST", pos)
            if pos == -1:
                break
            size = int.from_bytes(esp[pos+4:pos+8], "little")
            if 0 < size < 256:
                found.add(esp[pos+8:pos+8+size].rstrip(b"\0").decode("ascii"))
            pos += 4
        assert found == MASTERS, f"Unexpected ESP masters: {found}"
    with zipfile.ZipFile(main) as archive:
        assert archive.testzip() is None, "Corrupt KR12.4 main ZIP"
        assert not any("officialaddon" in name.lower() for name in archive.namelist()), "Main already bundles optional translation"
    print("PASS: pinned source SHA, TES3 dependencies, ZIP entries, KR12.4 main separation")


def request_api(method, path, key, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        "https://api.nexusmods.com/v3" + path,
        data=data, method=method,
        headers={"apikey": key, "Accept": "application/json", "User-Agent": "Morrowind-OfficialAddon-KR-Release",
                 **({"Content-Type": "application/json"} if body is not None else {})})
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = resp.read()
        return json.loads(payload) if payload else {}


def response_data(payload):
    return payload.get("data", payload)


def publish_nexus(source):
    key = os.environ.get("NEXUSMODS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("No NEXUSMODS_API_KEY configured. GitHub asset remains available.")
    mod = response_data(request_api("GET", f"/games/morrowind/mods/{MOD_SCOPED_ID}", key))
    assert str(mod["id"]) == MOD_UID and str(mod["game_scoped_id"]) == MOD_SCOPED_ID, "Wrong Nexus mod"
    groups = response_data(request_api("GET", f"/mods/{MOD_UID}/files", key))["mod_files"]
    matching_groups = [g for g in groups if g.get("is_active") and g.get("name", "").casefold() == GROUP_NAME.casefold()]
    assert len(matching_groups) <= 1, "Ambiguous optional file group"
    for group in matching_groups:
        versions = response_data(request_api("GET", f"/mod-files/{group['id']}/versions", key))["versions"]
        for version in versions:
            if version.get("version", "").casefold() == VERSION.casefold() and version.get("category") == "optional":
                print("Already published as optional file; skipping duplicate Nexus upload.")
                return

    data = Path(source).read_bytes()
    digest = hashlib.md5(data).digest()
    created = response_data(request_api("POST", "/uploads", key, {
        "filename": SOURCE_NAME, "size_bytes": len(data)
    }))
    upload_id = created["id"]
    presigned = created["presigned_url"]
    import urllib.parse
    from xml.etree import ElementTree
    signed = urllib.parse.parse_qs(urllib.parse.urlsplit(presigned).query).get("X-Amz-SignedHeaders", [""])[0]
    print("Presigned URL expected headers:", signed, flush=True)
    req = urllib.request.Request(presigned, method="PUT", data=data, headers={
        "Content-Disposition": f'attachment; filename="{SOURCE_NAME}"',
        "Content-Type": "application/octet-stream"
    })
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            assert resp.status in (200, 201, 204), "Presigned PUT rejected"
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            root = ElementTree.fromstring(raw)
            code = root.findtext("Code", "?")
            message = root.findtext("Message", "?")
        except Exception:
            code, message = "unknown", "non-XML error response"
        raise RuntimeError(f"Presigned PUT HTTP {exc.code}: {code}: {message}") from None
    request_api("POST", f"/uploads/{upload_id}/finalise", key, {})
    for attempt in range(12):
        state = response_data(request_api("GET", f"/uploads/{upload_id}", key)).get("state")
        if state == "available":
            break
        if state in ("failed", "rejected", "cancelled"):
            raise RuntimeError(f"Nexus rejected upload state {state}")
        time.sleep(3)
    else:
        raise RuntimeError("Nexus upload not available; do not retry blindly")

    notes = ("베데스다 공식 애드온 8종 한국어화. GOG판은 원본 애드온 기본 포함(활성화 확인), "
             "Steam판은 https://www.nexusmods.com/morrowind/mods/3882 에서 8종 먼저 설치. "
             "한국어 ESP는 본편 한국어판 뒤에 로드. 원본 8종 모두 필요.")
    payload = {
        "upload_id": upload_id, "mod_id": MOD_UID,
        "name": GROUP_NAME,
        "version": VERSION,
        "description": notes,
        "file_category": "optional",
        "primary_mod_manager_download": False,
        "allow_mod_manager_download": True,
        "show_requirements_pop_up": True,
        "update_mod_version": False,
    }
    if matching_groups:
        result = request_api("POST", f"/mod-files/{matching_groups[0]['id']}/versions", key, {
            "upload_id": upload_id,
            "version": VERSION,
            "name": SOURCE_NAME,
            "description": notes,
            "category": "optional",
            "primary_mod_manager_download": False,
            "update_mod_version": False,
        })
    else:
        result = request_api("POST", "/mod-files", key, payload)
    print("Nexus create response:", json.dumps(response_data(result), ensure_ascii=False)[:900])
    groups = response_data(request_api("GET", f"/mods/{MOD_UID}/files", key))["mod_files"]
    if not any(g.get("name", "").casefold() == GROUP_NAME.casefold() and g.get("is_active") for g in groups):
        raise RuntimeError("Nexus create response returned but optional group was not found. Reconcile before retry.")
    print("PASS: Nexus optional file group created without changing Windows main or mod version")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["verify", "nexus"])
    p.add_argument("--source", default=SOURCE_NAME)
    p.add_argument("--main", default=MAIN_NAME)
    args = p.parse_args()
    verify(args.source, args.main)
    if args.mode == "nexus":
        publish_nexus(args.source)


if __name__ == "__main__":
    main()
