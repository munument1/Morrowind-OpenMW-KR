"""Build a reproducible, fail-closed Windows Korean OpenMW compact ZIP.

By default only payload/openmw.exe may differ, preserving already released KR9.1
packaging behavior. A future release may explicitly opt in to removing known
obsolete root-level documents and refreshing README-KOREAN.txt. Translation ESP,
fonts, licenses, installer, config, sidecars, and subtitles remain byte-identical.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZipFile

WIN_EXECUTABLE = 'payload/openmw.exe'
README = 'README-KOREAN.txt'

# Exact root-level historical release artifacts observed in the KR9.1 ZIP.
# Never delete a payload/ file, license, installer, or unknown documentation.
LEGACY_ROOT_DOCS = frozenset({
    'CI-ID.txt',
    'DAEDRIC-FIX-PREVIEW.txt',
    'FONT-ROLLBACK.txt',
    'KR4-SOURCE-CI-ID.txt',
    'KR5-CHANGES.txt',
    'KR5-data-verification.json',
    'KR5-journal-verification.json',
    'KR6-CHANGES.txt',
    'README-KR6-CHANGES.txt',
    'KR7-CHANGES.txt',
    'KR7-reference-audit.json',
    'SHA256SUMS.txt',  # Old embedded hashes do not describe the new executable.
})

ESSENTIAL_MEMBERS = frozenset({
    'Install-Korean.bat',
    'install-korean.ps1',
    'install-korean-config.ps1',
    'korean-fallbacks.cfg',
    'payload/openmw.exe',
    'payload/resources/vfs/fonts/Galmuri11-OFL-1.1.md',
    'payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.esp',
    'payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.cel',
    'payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.mrk',
    'payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.top',
    'payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.jrn',
})


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def current_readme(release_tag: str) -> bytes:
    match = re.fullmatch(r'openmw-(\d+\.\d+\.\d+)-kr\d+(?:\.\d+)?', release_tag)
    if match is None:
        raise ValueError('Expected a Korean OpenMW version tag for the new README')
    return (f"""OpenMW 한국어판 {release_tag}

Windows용 설치 안내
1. Morrowind 원본 게임 데이터와 공식 OpenMW {match.group(1)}을 준비합니다.
2. 이 ZIP을 새 폴더에 압축 해제합니다.
3. Install-Korean.bat를 실행하고 설치할 OpenMW 경로를 확인합니다.
4. 설치기는 기존 실행 파일, 폰트, 한국어 모드와 설정을 백업합니다.
5. OpenMW를 실행해 한글 메뉴, 대화 토픽과 저널을 확인합니다.

구성
- payload/openmw.exe: 한국어 기능을 적용한 OpenMW 실행 파일
- payload/mods/Morrowind_Korean_ReTranslation: ESP, CEL, TOP, MRK, JRN, l10n, 자막
- payload/resources/vfs/fonts: 한국어 폰트와 해당 라이선스
- Install-Korean.bat 및 PowerShell 설치/설정 스크립트

주의
- OpenMW {match.group(1)} Windows 설치본에 적용하는 패치이며 게임 원본 파일은 포함하지 않습니다.
- 기존 세이브 및 다른 모드를 삭제하지 않습니다. 설치 전에 중요한 데이터는 따로 백업하세요.
- Android용 빌드와는 별도입니다.
- 이전 버전의 변경 기록과 검증 결과는 GitHub 릴리스/저장소에서 확인하세요.

최신 배포 정보: https://github.com/munument1/Morrowind-OpenMW-KR/releases/tag/{release_tag}
ZIP 무결성 검증: 배포 ZIP 옆에 제공되는 .zip.sha256 파일을 사용하세요.
""").encode('utf-8')


def build(source: Path, executable: Path, output: Path, expected_source_sha256: str,
          release_tag: str = 'openmw-0.51.0-kr9',
          prune_legacy_docs: bool = False) -> dict:
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
        removed = sorted(LEGACY_ROOT_DOCS.intersection(names)) if prune_legacy_docs else []
        readme_bytes = current_readme(release_tag) if prune_legacy_docs else None
        if prune_legacy_docs:
            normalized = {name.replace('\\', '/') for name in names}
            if README not in names or not ESSENTIAL_MEMBERS.issubset(normalized):
                raise ValueError('Source ZIP lacks the README or an essential installation/payload file')
        target = matches[0]
        old_binary = zin.read(target)
        if old_binary == binary:
            raise ValueError('No executable changes: refusing KR9 relabeling')
        if not old_binary.startswith(b'MZ'):
            raise ValueError('Unexpected KR8 runtime format')
        with ZipFile(output, 'w') as zout:
            zout.comment = zin.comment
            for entry in entries:
                if entry.filename in removed:
                    continue
                payload = (binary if entry.filename == target else
                           readme_bytes if prune_legacy_docs and entry.filename == README else
                           zin.read(entry))
                zout.writestr(entry, payload)
    with ZipFile(source) as zin, ZipFile(output) as zout:
        expected_names = [name for name in names if name not in removed]
        if zout.testzip() is not None or zout.namelist() != expected_names:
            raise ValueError('KR9 archive CRC or member list changed')
        differences = [name for name in expected_names
                       if zin.read(name) != zout.read(name)]
        allowed_changes = {target} | ({README} if prune_legacy_docs else set())
        if set(differences) != allowed_changes:
            raise ValueError(f'Unexpected changed KR9 entries: {differences!r}')
        if zout.read(target) != binary:
            raise ValueError('KR9 runtime binary parity mismatch')
        if prune_legacy_docs and zout.read(README) != readme_bytes:
            raise ValueError('Current release README mismatch')

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
        'removed_legacy_docs': removed,
        'rewritten_docs': [README] if prune_legacy_docs else [],
        'unchanged_member_count': len(expected_names) - len(differences),
        'archive_members': len(expected_names),
        'status': 'PASS',
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--executable', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--expected-source-sha256', required=True)
    p.add_argument('--release-tag', default='openmw-0.51.0-kr9')
    p.add_argument('--prune-legacy-docs', action='store_true',
                   help='For a FUTURE release: drop known obsolete top-level docs and regenerate current README')
    a = p.parse_args()
    report = build(a.source, a.executable, a.output, a.expected_source_sha256,
                   a.release_tag, prune_legacy_docs=a.prune_legacy_docs)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
