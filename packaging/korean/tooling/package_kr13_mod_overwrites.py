"""Package the verified KR13 regional binaries as same-name plugin overwrites."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[3]
PINS = ROOT / 'packaging/korean/releases/KR13-MOD-OVERWRITE-SOURCES.json'
PLAN = 'NEXUS-PUBLICATION-PLAN.json'
TAG = 'openmw-0.51.0-kr13'
FORMAT = 'overwrite-existing-esm-esp'
SPECS = (
    ('TR_Mainland-kr0.4.zip', 'TR_Mainland-kr0.4.1.zip', 60844, '8296179', '26.11.2-kr0.4.1', 'Tamriel Rebuilt 26.11.2'),
    ('Tamriel_Data-kr0.4.zip', 'Tamriel_Data-kr0.4.1.zip', 60845, '8296167', '26.08-kr0.4.1', 'Tamriel Data 26.08'),
    ('Cyr_Main-kr0.4.zip', 'Cyr_Main-kr0.4.1.zip', 60846, '8296161', '26.09a-kr0.4.1', 'Project Cyrodiil 26.09a'),
    ('Sky_Main-kr0.3.zip', 'Sky_Main-kr0.3.1.zip', 60847, '8296155', '26.09a-kr0.3.1', 'Skyrim: Home of the Nords 26.09a'),
    ('Rebirth7.2-Cyr_Sky_Compatibility-kr0.4.zip', 'Rebirth7.2-Cyr_Sky_Compatibility-kr0.4.1.zip', 60805, '8296377', '7.2-kr0.4.1', 'Morrowind Rebirth 7.2 Cyr/Sky compatibility'),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_member(z, name, data):
    item = ZipInfo(name, date_time=(2026, 11, 11, 12, 0, 0))
    item.compress_type = ZIP_DEFLATED
    item.external_attr = 0o100644 << 16
    z.writestr(item, data, compress_type=ZIP_DEFLATED, compresslevel=6)


def verify_archive(path, expected_files):
    with ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(n.casefold() for n in names)) or z.testzip() is not None:
            raise ValueError('Duplicate ZIP members or CRC failure')
        if set(names) != set(expected_files) | {'README_KO.md', 'INSTALL-MANIFEST.json'}:
            raise ValueError('Missing full plugin/sidecar or unexpected ZIP member')
        for name, digest in expected_files.items():
            p = PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name:
                raise ValueError('Unsafe ZIP member')
            data = z.read(name)
            if sha(data) != digest:
                raise ValueError('Verified KR13 payload hash mismatch')
            if p.suffix.lower() in {'.esm', '.esp'} and data[:4] != b'TES3':
                raise ValueError('Expected a complete TES3 plugin')
        meta = json.loads(z.read('INSTALL-MANIFEST.json'))
        if meta.get('format') != FORMAT or meta.get('files') != expected_files:
            raise ValueError('Incorrect overwrite installation manifest')
        if not any(PurePosixPath(n).suffix.lower() in {'.esm', '.esp'} for n in names):
            raise ValueError('Full translated ESM/ESP is required')


def readme(spec):
    _, _, _, _, version, label = spec
    return f'''# {label} 한국어 {version}

## 설치
1. 위 버전의 원본 모드와 필요한 메쉬·텍스처·BSA를 먼저 설치합니다.
2. 기존 ESM/ESP와 TOP/MRK/CEL/JRN을 백업합니다.
3. 이 ZIP의 `Data Files` 또는 `Compability Patches` 안에 있는 번역된 전체 ESM/ESP와 대응 사이드카를 원래 파일과 같은 위치에 덮어씁니다. 폴더 이름이 아닌 실제 플러그인·사이드카의 위치를 맞추세요.
4. TR의 `Faction intergration/TR_Factions.esp`는 해당 팩션 통합 모드를 사용 중인 경우에만 원래 파일을 교체합니다.

Python 실행이나 델타 적용 단계는 없습니다. kr0.4.1/kr0.3.1은 배포 형식 수정이며 플러그인과 사이드카 내용은 검증된 KR13 번역본과 동일합니다.

본편 KR13 코어는 Morrowind.esm → Tribunal.esm → Bloodmoon.esm 바로 다음에 로드합니다. 지역 모드의 필수 선행 모드와 기존 로드 순서를 유지하세요. 일반 Cyr_Main/Sky_Main과 Rebirth 전용 [For Rebirth] ESM을 동시에 활성화하지 마세요.

## 범위
이 패키지는 전체 번역 플러그인과 EET 사이드카를 포함합니다. 원본 모드 아트 파일과 정품 본편 마스터는 포함하지 않습니다. 모든 퀘스트 완역·완주 검증을 뜻하지 않습니다. TR 번역본 기준은 26.11.2이며 이전 델타 배포의 26.09.27 표기를 이 패키지의 원본 기준으로 사용하지 마세요.

## 원작자
Morrowind: Bethesda Softworks/Bethesda Game Studios. Tamriel Rebuilt/TR_Factions: Tamriel Rebuilt Team. Tamriel Data: Tamriel Data/Cross-Project Coordination. Project Cyrodiil/Skyrim Home of the Nords: Project Tamriel의 각 제작팀. Morrowind Rebirth 및 호환 파일: 해당 제작자. 원본 모드의 크레딧과 이용 조건을 보존합니다.

https://github.com/munument1/Morrowind-OpenMW-KR/releases/tag/{TAG}
'''.encode('utf-8')


def verify_folder(folder):
    pins = json.loads(PINS.read_text(encoding='utf-8'))
    plan = json.loads((folder / PLAN).read_text(encoding='utf-8'))
    if plan.get('tag') != TAG or plan.get('regional_packaging') != FORMAT:
        raise ValueError('Wrong release or regional packaging policy')
    rows = {r['asset']: r for r in plan['files']}
    if len(rows) != 6 or len(plan['files']) != 6:
        raise ValueError('Expected unchanged core plus five regional packages')
    for old, name, mod, group, version, _ in SPECS:
        row = rows[name]
        if (row['mod_id'], row['uid'], row['group'], row['version']) != (mod, str((100 << 32) + mod), group, version):
            raise ValueError('Wrong Nexus target/version')
        path = folder / name
        if sha(path.read_bytes()) != row['sha256'] or path.stat().st_size != row['bytes']:
            raise ValueError('Package SHA/size mismatch')
        expected_line = row['sha256'] + '  ' + name + '\n'
        if (folder / (name + '.sha256')).read_text(encoding='ascii') != expected_line:
            raise ValueError('Incorrect SHA sidecar')
        verify_archive(path, pins[old]['files'])
    core = rows['Morrowind-Korean-OpenMW-0.51.0-KR13-Full.zip']
    if core['sha256'] != '40da1be66a346c86baa2a3024346b300284c68a73379c64c4e1647744158ac31' or core['mod_id'] != 60496:
        raise ValueError('Core package must remain unchanged')
    return plan


def build(source, output, prior_plan):
    if output.exists():
        raise FileExistsError(output)
    pins = json.loads(PINS.read_text(encoding='utf-8'))
    old_plan = json.loads(prior_plan.read_text(encoding='utf-8'))
    core = next(r for r in old_plan['files'] if r['mod_id'] == 60496)
    output.mkdir(parents=True)
    rows = [core]
    for spec in SPECS:
        old, name, mod, group, version, _ = spec
        source_zip = source / old
        pin = pins[old]
        if sha(source_zip.read_bytes()) != pin['source_zip_sha256']:
            raise ValueError('Unverified source archive')
        meta = {'format': FORMAT, 'version': version, 'files': pin['files']}
        with ZipFile(source_zip) as src, ZipFile(output / name, 'w') as dst:
            for member, expected in pin['files'].items():
                data = src.read(member)
                if sha(data) != expected:
                    raise ValueError('Source payload changed')
                write_member(dst, member, data)
            write_member(dst, 'README_KO.md', readme(spec))
            write_member(dst, 'INSTALL-MANIFEST.json', (json.dumps(meta, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
        path = output / name
        digest = sha(path.read_bytes())
        (output / (name + '.sha256')).write_text(digest + '  ' + name + '\n', encoding='ascii', newline='\n')
        rows.append({'asset': name, 'mod_id': mod, 'uid': str((100 << 32) + mod), 'group': group,
                     'version': version, 'sha256': digest, 'bytes': path.stat().st_size, 'packaging': FORMAT})
    plan = {'schema_version': 2, 'tag': TAG, 'regional_packaging': FORMAT, 'files': rows}
    (output / PLAN).write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    verify_folder(output)
    return plan


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--prior-plan', type=Path)
    p.add_argument('--verify-dir', type=Path)
    a = p.parse_args()
    if a.verify_dir:
        result = verify_folder(a.verify_dir)
    else:
        if not all((a.source, a.output, a.prior_plan)):
            p.error('--source, --output and --prior-plan are required')
        result = build(a.source, a.output, a.prior_plan)
    print('PASS: five full-plugin overwrite ZIPs; seven unchanged TES3 plugins and 24 sidecars')
