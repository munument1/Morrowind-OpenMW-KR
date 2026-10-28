"""Build a reproducible, fail-closed Windows KR9 compact ZIP from released KR8.

Only payload\\openmw.exe may differ. The rest of KR8 (including corrected CEL,
translation ESP, fonts, sidecars, installer, and subtitles) stays byte-identical.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

WIN_EXECUTABLE = 'payload/openmw.exe'


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(source: Path, executable: Path, output: Path, expected_source_sha256: str,
          release_tag: str = 'openmw-0.51.0-kr9') -> dict:
    if output.exists() or output.resolve() in (source.resolve(), executable.resolve()):
        raise ValueError('KR9 output must be a new file distinct from inputs')
    source_bytes = source.read_bytes()
    if sha256(source_bytes) != expected_source_sha256.lower():
        raise ValueError('KR8 source ZIP checksum mismatch')
    binary = executable.read_bytes()
    if len(binary) < 1024 * 1024 or not binary.startswith(b'MZ'):
        raise ValueError('Expected a substantial Windows PE executable beginning with MZ')
    with ZipFile(source) as zin:
        entries = zin.infolist()
        names = [entry.filename for entry in entries]
        matches = [name for name in names if name.replace('\\', '/').lower() == WIN_EXECUTABLE]
        if len(matches) != 1 or len(set(names)) != len(names):
            raise ValueError('Missing/duplicate KR8 Windows runtime archive entry')
        if zin.testzip() is not None:
            raise ValueError('Corrupt source ZIP')
        target = matches[0]
        old_binary = zin.read(target)
        if old_binary == binary:
            raise ValueError('No executable changes: refusing KR9 relabeling')
        if not old_binary.startswith(b'MZ'):
            raise ValueError('Unexpected KR8 runtime format')
        with ZipFile(output, 'w') as zout:
            zout.comment = zin.comment
            for entry in entries:
                payload = binary if entry.filename == target else zin.read(entry)
                zout.writestr(entry, payload)
    with ZipFile(source) as zin, ZipFile(output) as zout:
        if zout.testzip() is not None or zin.namelist() != zout.namelist():
            raise ValueError('KR9 archive CRC or member list changed')
        differences = [name for name in zin.namelist()
                       if zin.read(name) != zout.read(name)]
        if differences != [target]:
            raise ValueError(f'Unexpected changed KR9 entries: {differences!r}')
        if zout.read(target) != binary:
            raise ValueError('KR9 runtime binary parity mismatch')

    output_digest = sha256(output.read_bytes())
    output.with_name(output.name + '.sha256').write_text(
        f'{output_digest}  {output.name}\n', encoding='ascii')
    return {
        'base_release': 'openmw-0.51.0-kr8',
        'base_sha256': expected_source_sha256.lower(),
        'new_release': release_tag,
        'runtime_entry': target,
        'old_runtime_sha256': sha256(old_binary),
        'new_runtime_sha256': sha256(binary),
        'output_sha256': output_digest,
        'changed_entries': differences,
        'unchanged_member_count': len(names) - 1,
        'archive_members': len(names),
        'status': 'PASS',
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--executable', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--expected-source-sha256', required=True)
    p.add_argument('--release-tag', default='openmw-0.51.0-kr9')
    a = p.parse_args()
    report = build(a.source, a.executable, a.output, a.expected_source_sha256, a.release_tag)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
