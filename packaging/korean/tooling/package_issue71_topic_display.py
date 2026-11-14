"""Create an isolated TR overlay candidate with display-only topic titles.

The input is the official KR13 full-plugin TR archive. Every original plugin
and sidecar must match its pinned SHA256; only a new .dsp and installation
metadata are permitted in the candidate archive. Never modifies game files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from audit_cross_mod_topic_gaps import record_chunks, subs, unpack


ROOT = Path(__file__).resolve().parents[3]
PINNED = ROOT / "packaging/korean/releases/KR13-MOD-OVERWRITE-SOURCES.json"
DSP = ROOT / "translations/tamriel-rebuilt/26.11.2-kr0.1/TR_Mainland.dsp"
OLD_NAME = "TR_Mainland-kr0.4.1.zip"
NEW_NAME = "TR_Mainland-kr0.4.2-Issue71-QA.zip"
MEMBER = "Data Files/TR_Mainland.dsp"
PLUGIN = "Data Files/TR_Mainland.esm"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def display_names(data: bytes) -> dict[str, str]:
    if not data.startswith(b"\xef\xbb\xbf"):
        raise ValueError("Display map must have UTF-8 BOM")
    names: dict[str, str] = {}
    for line in data.decode("utf-8-sig").splitlines():
        if not line or line.count("\t") != 1:
            raise ValueError("Expected one non-empty tab-delimited mapping per line")
        name, caption = line.split("\t")
        if not name or not caption or name in names or any("\uac00" <= c <= "\ud7a3" for c in name):
            raise ValueError("Missing/duplicate/non-English topic identifier: " + name)
        if not any("\uac00" <= c <= "\ud7a3" for c in caption):
            raise ValueError("Display name must contain Korean text")
        names[name] = caption
    return names


def topic_names(plugin: bytes) -> set[str]:
    names: set[str] = set()
    for tag, body in record_chunks(plugin):
        if tag != b"DIAL":
            continue
        fields = dict(subs(body))
        if fields.get(b"DATA") == b"\0" and b"DELE" not in fields:
            names.add(unpack(fields[b"NAME"]))
    return names


def build(source: Path, output: Path, dsp: Path = DSP) -> dict:
    if source.resolve() == output.resolve() or output.exists():
        raise ValueError("Output must be a new file separate from the official release")
    pin = json.loads(PINNED.read_text(encoding="utf-8"))["TR_Mainland-kr0.4.zip"]["files"]
    labels = display_names(dsp.read_bytes())
    if not labels:
        raise ValueError("No display-only topic labels")
    with ZipFile(source) as src:
        if src.testzip() is not None:
            raise ValueError("Source ZIP CRC error")
        names = src.namelist()
        if set(names) != set(pin) | {"README_KO.md", "INSTALL-MANIFEST.json"}:
            raise ValueError("Unexpected KR13 full-plugin archive contents")
        for name, expected in pin.items():
            if sha(src.read(name)) != expected:
                raise ValueError("Source payload differs from pinned KR13: " + name)
        actual_topics = topic_names(src.read(PLUGIN))
        if not labels.keys() <= actual_topics:
            raise ValueError("Display map contains unknown DIAL IDs: " + str(sorted(labels.keys() - actual_topics)))
        mrk = {
            row.split("\t", 1)[0]
            for row in src.read("Data Files/TR_Mainland.mrk").decode("utf-8-sig").splitlines()
            if "\t" in row
        }
        if labels.keys() & mrk:
            raise ValueError("Do not override an existing MRK without reviewing the conflict")

        manifest = json.loads(src.read("INSTALL-MANIFEST.json"))
        if manifest.get("version") != "26.11.2-kr0.4.1" or manifest.get("files") != pin:
            raise ValueError("Unexpected source manifest/version")
        manifest["version"] = "26.11.2-kr0.4.2"
        manifest["files"][MEMBER] = sha(dsp.read_bytes())
        readme = src.read("README_KO.md").decode("utf-8")
        if "kr0.4.1" not in readme:
            raise ValueError("Source installation guide version missing")
        readme = readme.replace("kr0.4.1", "kr0.4.2")
        readme += (
            "\n## 이슈 #71 대화 주제 제목\n"
            "TR_Mainland.dsp는 표시 이름만 번역합니다. 같은 폴더에 ESM/MRK/TOP과 함께 설치하세요.\n"
            "**차기 OpenMW-KR 대화 목록 표시 패치가 적용된 실행 파일이 필요합니다. "
            "공식 KR13 실행 파일에서는 이 파일의 표시명 기능이 적용되지 않습니다.**\n"
        )

        output.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output, "x") as dst:
            for info in src.infolist():
                if info.filename == "INSTALL-MANIFEST.json":
                    data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
                elif info.filename == "README_KO.md":
                    data = readme.encode("utf-8")
                else:
                    data = src.read(info.filename)
                dst.writestr(info, data)
            extra = ZipInfo(MEMBER, date_time=(2026, 11, 15, 0, 0, 0))
            extra.compress_type = ZIP_DEFLATED
            extra.external_attr = 0o100644 << 16
            dst.writestr(extra, dsp.read_bytes())
    with ZipFile(source) as src, ZipFile(output) as dst:
        if dst.testzip() is not None or set(dst.namelist()) != set(src.namelist()) | {MEMBER}:
            raise ValueError("Candidate ZIP CRC or member check failed")
        for name in pin:
            if src.read(name) != dst.read(name):
                raise ValueError("Unrelated plugin/sidecar content changed: " + name)
        if dst.read(MEMBER) != dsp.read_bytes():
            raise ValueError("Display-only sidecar changed")
        copied = json.loads(dst.read("INSTALL-MANIFEST.json"))
        if copied["files"] != manifest["files"]:
            raise ValueError("New metadata does not cover payload")
    return {
        "status": "ISSUE71_QA_CANDIDATE_NOT_PUBLISHED",
        "source": source.name,
        "candidate": output.name,
        "candidate_sha256": sha(output.read_bytes()),
        "display_only_topics": labels,
        "original_plugin_and_sidecars_byte_identical": True,
        "candidate_zip_crc": "PASS",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output), ensure_ascii=False, indent=2))
