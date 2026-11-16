"""Build SHA-pinned full-plugin display repairs without changing game logic."""
import argparse
from collections import Counter
import hashlib
import json
import re
import struct
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from audit_cross_mod_topic_gaps import record_chunks, subs, unpack

ROOT = Path(__file__).resolve().parents[3]
REVIEW = ROOT / 'translations/openmw-kr/issue71-20261116'
COMMAND = re.compile(r'^\s*(?:(?:"[^"\r\n]+"|[\w\x80-\uffff]+)\s*->\s*)?(Choice|MessageBox|Say)\b', re.I)
QUOTED = re.compile(r'"([^"\r\n]*)"')
FORMAT = re.compile(r'%(?:[-+ 0#]*\d*(?:\.\d+)?[a-zA-Z]|[A-Za-z_]+)')
DEBUG = re.compile('test|debug|console', re.I)
KO = re.compile('[가-힣]')
SPECS = (
    ('TR_Mainland-kr0.4.1.zip', 'TR_Mainland-kr0.5.zip', 60844, '8296179', '26.11.2-kr0.5'),
    ('Tamriel_Data-kr0.4.1.zip', 'Tamriel_Data-kr0.5.zip', 60845, '8296167', '26.08-kr0.5'),
    ('Cyr_Main-kr0.4.1.zip', 'Cyr_Main-kr0.5.zip', 60846, '8296161', '26.09a-kr0.5'),
    ('Sky_Main-kr0.3.1.zip', 'Sky_Main-kr0.4.zip', 60847, '8296155', '26.09a-kr0.4'),
    ('Rebirth7.2-Cyr_Sky_Compatibility-kr0.4.1.zip', 'Rebirth7.2-Cyr_Sky_Compatibility-kr0.5.zip', 60805, '8296377', '7.2-kr0.5'),
    ('Morrowind_Rebirth7.2-kr1.2.zip', 'Morrowind_Rebirth7.2-kr1.3.zip', 60805, '8257641', '7.2-kr1.3'),
    ('PFP_5.0.7-kr1.2_OpenMW-KR12.6.zip', 'PFP_5.0.7-kr1.3_OpenMW-KR13.2.zip', 60826, '8280147', '5.0.7-kr1.3'),
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def module_for(member):
    stem = Path(member).stem.casefold()
    if stem.startswith('morrowind rebirth'):
        return 'Rebirth'
    return {'tr_mainland': 'TR_Mainland', 'tr_factions': 'TR_Mainland', 'tamriel_data': 'Tamriel_Data',
            'cyr_main': 'Cyr_Main', 'sky_main': 'Sky_Main',
            'patch for purists': 'PFP',
            'project cyrodiil [for rebirth]': 'Cyr_Main',
            'skyrim home of the nords [for rebirth]': 'Sky_Main'}.get(stem)


def uncomment(line):
    quoted = False
    for i, char in enumerate(line):
        if char == '"':
            quoted = not quoted
        elif char == ';' and not quoted:
            return line[:i]
    return line


def display_spans(script):
    offset = 0
    for line in script.splitlines(keepends=True):
        code = uncomment(line)
        command = COMMAND.match(code)
        if command:
            matches = list(QUOTED.finditer(code, command.end()))
            if command[1].lower() == 'say':
                matches = matches[1:]
            for match in matches:
                yield offset + match.start(1), offset + match.end(1), match[1]
        offset += len(line)


def script_shape(script):
    for start, end, _ in reversed(list(display_spans(script))):
        script = script[:start] + '<DISPLAY>' + script[end:]
    return script


def translate_script(raw, translations):
    try:
        source = raw.decode('utf-8')
    except UnicodeDecodeError:
        if all(not uncomment(line).strip() for line in raw.decode('cp1252').splitlines()):
            return raw, 0
        raise
    target, count = source, 0
    for start, end, value in reversed(list(display_spans(source))):
        if value not in translations:
            continue
        translated = translations[value]
        if not KO.search(translated) or any(c in translated for c in '"\r\n\0'):
            raise ValueError('Invalid script display target: ' + value)
        if FORMAT.findall(value) != FORMAT.findall(translated):
            raise ValueError('Format operands changed: ' + value)
        target = target[:start] + translated + target[end:]
        count += 1
    if script_shape(source) != script_shape(target):
        raise ValueError('Script code or choice numbers changed')
    return target.encode('utf-8'), count


def rewrite_plugin(raw, module, review):
    output, position, changed, found_names = [], 0, Counter(), set()
    names = {r['id'].casefold(): r for r in review['npc_names'].get(module, [])}
    for tag, body in record_chunks(raw):
        header = raw[position:position + 16]
        position += 16 + len(body)
        if tag not in (b'INFO', b'SCPT', b'NPC_'):
            output.append(header + body)
            continue
        fields = subs(body)
        values = dict(fields)
        identity = unpack(values.get(b'NAME', b'')) if tag == b'NPC_' else unpack(values.get(b'SCHD', b'')[:32])
        replacements = {}
        if tag == b'NPC_' and identity.casefold() in names:
            patch = names[identity.casefold()]
            if sha(values[b'FNAM']) != patch['source_sha256']:
                raise ValueError('NPC source mismatch: ' + identity)
            suffix = values[b'FNAM'][len(values[b'FNAM'].rstrip(b'\0')):]
            replacements[b'FNAM'] = patch['after'].encode('utf-8') + suffix
            found_names.add(identity.casefold())
            changed['NPC_.FNAM'] += 1
        field = b'BNAM' if tag == b'INFO' else b'SCTX' if tag == b'SCPT' else None
        if field in values and not (tag == b'SCPT' and DEBUG.search(identity)):
            updated, count = translate_script(values[field], review['script_strings'])
            if updated != values[field]:
                replacements[field] = updated
                changed[tag.decode() + '.' + field.decode()] += 1
                changed['display_operands'] += count
        if replacements:
            new_body = b''.join(key + struct.pack('<I', len(replacements.get(key, value))) + replacements.get(key, value)
                                for key, value in fields)
            output.append(header[:4] + struct.pack('<I', len(new_body)) + header[8:] + new_body)
        else:
            output.append(header + body)
    return b''.join(output), dict(changed), found_names


def verify_logic(before, after, module, review):
    old, new = iter(record_chunks(before)), iter(record_chunks(after))
    count, old_position, new_position = 0, 0, 0
    while True:
        a, b = next(old, None), next(new, None)
        if a is None or b is None:
            if a != b:
                raise ValueError('Record count changed')
            break
        if a[0] != b[0]:
            raise ValueError('Record type/order changed')
        if before[old_position + 8:old_position + 16] != after[new_position + 8:new_position + 16]:
            raise ValueError('Record flags/unknown header bytes changed')
        old_position += 16 + len(a[1])
        new_position += 16 + len(b[1])
        if a == b:
            count += 1
            continue
        af, bf = subs(a[1]), subs(b[1])
        if len(af) != len(bf):
            raise ValueError('Subrecord count changed')
        for (at, av), (bt, bv) in zip(af, bf):
            if at != bt:
                raise ValueError('Subrecord type/order changed')
            if av == bv:
                continue
            if (a[0], at) in ((b'INFO', b'BNAM'), (b'SCPT', b'SCTX')):
                if script_shape(av.decode('utf-8')) != script_shape(bv.decode('utf-8')):
                    raise ValueError('Script logic changed')
            elif (a[0], at) == (b'NPC_', b'FNAM'):
                ident = unpack(dict(af)[b'NAME']).casefold()
                allowed = {r['id'].casefold(): r['after'] for r in review['npc_names'].get(module, [])}
                if allowed.get(ident) != unpack(bv):
                    raise ValueError('Unreviewed NPC name change')
            else:
                raise ValueError('Non-display field changed: ' + str((a[0], at)))
        count += 1
    return count


def write_zip(path, files):
    with ZipFile(path, 'w') as z:
        for name, data in sorted(files.items()):
            item = ZipInfo(name, (2026, 11, 16, 12, 0, 0))
            item.external_attr = 0o100644 << 16
            z.writestr(item, data, compress_type=ZIP_DEFLATED, compresslevel=6)
    with ZipFile(path) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP CRC failed')
        for name, data in files.items():
            if z.read(name) != data:
                raise ValueError('ZIP payload mismatch')


def build(source, output, review_dir=REVIEW):
    if output.exists():
        raise FileExistsError(output)
    review = json.loads((review_dir / 'review.json').read_text(encoding='utf-8'))
    for old, *_ in SPECS:
        if sha((source / old).read_bytes()) != review['baseline_archives'][old]:
            raise ValueError('Pinned baseline ZIP mismatch: ' + old)
    output.mkdir(parents=True)
    plan = {'schema': 1, 'android_excluded': True, 'format': 'overwrite-existing-esm-esp',
            'language_review': review['language_review'], 'human_reviewed': False, 'files': []}
    for old, new, mod, group, version in SPECS:
        files, changes, found = {}, {}, set()
        with ZipFile(source / old) as z:
            if z.testzip() is not None:
                raise ValueError('Baseline CRC failure')
            original_meta = json.loads(z.read('INSTALL-MANIFEST.json')) if 'INSTALL-MANIFEST.json' in z.namelist() else {'source_archive': old}
            for name in z.namelist():
                suffix = Path(name).suffix.lower()
                if old.startswith(('Morrowind_Rebirth', 'PFP_')) and suffix in ('.txt', '.md', '.pdf'):
                    notice = 'SOURCE-NOTICES/' + name if Path(name).name.lower().startswith('readme') else name
                    files[notice] = z.read(name)
                    continue
                if suffix not in ('.esm', '.esp', '.top', '.mrk', '.cel', '.jrn'):
                    continue
                raw = z.read(name)
                module = module_for(name)
                if suffix in ('.esm', '.esp'):
                    if not module:
                        raise ValueError('Unexpected plugin: ' + name)
                    updated, detail, seen = rewrite_plugin(raw, module, review)
                    records = verify_logic(raw, updated, module, review)
                    files[name] = updated
                    changes[name] = {'before': sha(raw), 'after': sha(updated), 'records_verified': records, **detail}
                    found.update((module, value) for value in seen)
                    # TR_Factions shares the required TR_Mainland display sidecar.
                    if Path(name).stem.casefold() != 'tr_factions' and (review_dir / (module + '.dsp')).exists():
                        files[str(Path(name).with_suffix('.dsp')).replace('\\', '/')] = (review_dir / (module + '.dsp')).read_bytes()
                else:
                    files[name] = raw
        if not old.startswith('Rebirth'):
            expected = {(module, r['id'].casefold()) for module, rows in review['npc_names'].items()
                        if module == module_for(next(n for n in files if Path(n).suffix.lower() in ('.esm', '.esp')))
                        for r in rows}
            if not expected <= found:
                raise ValueError('NPC repair not applied: ' + str(expected - found))
        hashes = {name: sha(data) for name, data in files.items()}
        files['INSTALL-MANIFEST.json'] = (json.dumps({**original_meta, 'format': 'overwrite-existing-esm-esp',
            'version': version, 'files': hashes, 'issue71_followup': True, 'human_reviewed': False}, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        optional = 'TR_Factions.esp는 팩션 통합 모드를 사용하는 경우에만 교체합니다.\n' if mod == 60844 else ''
        files['README_KO.md'] = f'''# OpenMW-KR 모드 한국어 {version}

같은 원본 버전의 모드와 필요한 메쉬·텍스처·BSA를 먼저 설치하십시오.
기존 플러그인과 사이드카를 백업한 뒤, 이 ZIP의 전체 ESM/ESP와 CEL/TOP/MRK/JRN/DSP를 같은 위치에 덮어씁니다.
{optional}일반 Cyr/Sky와 Rebirth 전용 [For Rebirth] ESM은 함께 활성화하지 마십시오.

이슈 #71: 토픽 목록·응답 제목·일지 주제 표시, 인물명 잔재, 선택지와 스크립트 알림을 보강했습니다.
DSP는 표시 전용입니다. 원본 DIAL/NPC/아이템 ID, 퀘스트 조건, 선택 번호와 저장 데이터 형식을 보존합니다.
Windows 본편 KR13.1 이상이 필요합니다. 기존 로드 순서와 원본 모드의 필수 의존성을 유지하십시오.
신규 고유명 음역은 잠정 표기이며 AI 검토입니다. 전체 퀘스트 완주·사람에 의한 전수 검수 완료를 뜻하지 않습니다.
코드·회귀 검증과 실제 실행 범위는 아래 저장소의 배포 보고서를 참고하십시오.

Bethesda Softworks/Bethesda Game Studios, Tamriel Rebuilt Team, Tamriel Data/Cross-Project Coordination,
Project Tamriel 각 팀, Morrowind Rebirth의 Trancemaster_1988와 기여자, Patch for Purists의 Half11와 기여자,
각 호환 파일 제작자의 크레딧과 이용 조건을 보존합니다. SOURCE-NOTICES가 있으면 기존 배포본의 고지도 참고하십시오.
원본 모드의 아트와 정품 Bethesda 마스터를 포함하지 않습니다. Android 패키지는 이번 갱신 대상이 아닙니다.
https://github.com/munument1/Morrowind-OpenMW-KR
'''.encode('utf-8')
        path = output / new
        write_zip(path, files)
        digest = sha(path.read_bytes())
        (output / (new + '.sha256')).write_text(digest + '  ' + new + '\n', encoding='ascii')
        plan['files'].append({'asset': new, 'mod_id': mod, 'uid': str((100 << 32) + mod), 'group': group,
                              'version': version, 'sha256': digest, 'bytes': path.stat().st_size,
                              'payload': hashes, 'changes': changes})
    (output / 'ISSUE71-PUBLICATION-PLAN.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return plan


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.source, args.output)
    print(json.dumps([{k: row[k] for k in ('asset', 'bytes', 'sha256')} for row in result['files']], indent=2))
