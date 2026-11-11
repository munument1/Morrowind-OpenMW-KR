"""Expose regional starter responses under the Korean core's shared topics.

Keep every original DIAL/INFO, script and sidecar byte. Add only eight reviewed
Korean DIAL blocks, copying their original INFO records verbatim, for OpenMW.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path
from audit_cross_mod_topic_gaps import record_chunks, subs

TOPICS = {
    'background': '배경',
    'latest rumors': '최근 소문',
    'little secret': '작은 비밀',
    'little advice': '작은 조언',
    'my trade': '내 직업',
    'services': '서비스',
    'someone in particular': '특정 인물',
    'specific place': '특정 장소',
}
SOURCES = {
    'Tamriel_Data-kr0.3.zip': 'db1069dc172333c7cfa45fe0ec654c12f022da5fef17d8252f40d68bfa11c608',
    'TR_Mainland-kr0.3.zip': '8221998908f06516c5f2c4f0600b2394d1820760d0f3af2e1ebc6256790083ee',
    'Cyr_Main-kr0.3.zip': 'efdf9d215d207cecc94b624db6d34d57941dd4bd6fa8be0c8f26e448fd865531',
    'Sky_Main-kr0.2.zip': '6c9c4b947295f3bb1c7b4df0433b202286ad9c9196c275f7d65c46515d157b77',
    'Rebirth7.2-Cyr_Sky_Compatibility-kr0.3.zip': 'e4de18d5de7f2aed2e6a436ec1c0aae0189e3ae6b697c0a4fd10d31033e19cba',
}
CORE = 'Morrowind-Korean-OpenMW-0.51.0-KR12.9-Full.zip'
CORE_SHA = 'f13574941ca699af479a2facbf87c06e5b9ae2cd4696d800c4b89e7ec4f88223'


def canonical(name):
    return TOPICS.get(name.casefold(), name)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def decode(raw):
    return raw.rstrip(b'\0').decode('utf-8')


def field(tag, value):
    return tag + struct.pack('<I', len(value)) + value


def change(record, key, value):
    fields = subs(record[16:])
    if sum(tag == key for tag, _ in fields) != 1:
        raise ValueError('Missing or duplicate changed subrecord')
    body = b''.join(field(tag, value if tag == key else raw) for tag, raw in fields)
    return record[:4] + struct.pack('<I', len(body)) + record[8:16] + body


def physical_records(raw):
    offset = 0
    for _, body in record_chunks(raw):
        end = offset + 16 + len(body)
        yield raw[offset:end]
        offset = end


def plugin(raw):
    records = list(physical_records(raw))
    if not records or records[0][:4] != b'TES3':
        raise ValueError('Missing TES3 header')
    header = dict(subs(records[0][16:]))[b'HEDR']
    if len(header) != 300 or struct.unpack_from('<I', header, 296)[0] != len(records) - 1:
        raise ValueError('Unexpected physical record count')
    names = set()
    blocks, current = [], None
    for record in records[1:]:
        tag = record[:4]
        if tag == b'DIAL':
            fields = dict(subs(record[16:]))
            name = decode(fields[b'NAME'])
            if name.casefold() in names:
                raise ValueError('Duplicate DIAL in source plugin')
            names.add(name.casefold())
            current = None
            if name.casefold() in TOPICS:
                if b'DELE' in fields or fields.get(b'DATA') != b'\0':
                    raise ValueError('Expected live shared topic')
                current = {'source': name, 'target': canonical(name), 'records': [record]}
                blocks.append(current)
        elif tag == b'INFO' and current is not None:
            current['records'].append(record)
        else:
            current = None
    if not blocks:
        return raw, []
    added, ledger = [], []
    for block in blocks:
        if block['target'].casefold() in names:
            raise ValueError('Korean topic already exists in source plugin')
        original = block['records'][0]
        old_name = dict(subs(original[16:]))[b'NAME']
        new_name = block['target'].encode('utf-8') + old_name[len(old_name.rstrip(b'\0')):]
        translated = change(original, b'NAME', new_name)
        added.extend([translated, *block['records'][1:]])
        ledger.append({'source_topic': block['source'], 'korean_topic': block['target'],
                       'copied_infos': len(block['records']) - 1,
                       'source_block_sha256': sha(b''.join(block['records']))})
    new_header = header[:296] + struct.pack('<I', len(records) - 1 + len(added))
    output = b''.join([change(records[0], b'HEDR', new_header), *records[1:], *added])
    # All existing records, including saved-topic IDs and every INFO, remain exact.
    result = list(physical_records(output))
    if result[1:len(records)] != records[1:]:
        raise ValueError('Existing record changed')
    for old, new in zip(subs(records[0][16:]), subs(result[0][16:])):
        if old[0] != new[0] or (old[0] != b'HEDR' and old != new):
            raise ValueError('Unrelated header field changed')
        if old[0] == b'HEDR' and old[1][:-4] != new[1][:-4]:
            raise ValueError('Unrelated HEDR byte changed')
    cursor = len(records)
    for block in blocks:
        fields = subs(result[cursor][16:])
        original_fields = subs(block['records'][0][16:])
        if [(t, v) for t, v in fields if t != b'NAME'] != [(t, v) for t, v in original_fields if t != b'NAME']:
            raise ValueError('Copied DIAL metadata changed')
        if decode(dict(fields)[b'NAME']) != block['target']:
            raise ValueError('Incorrect shared-topic target')
        cursor += 1
        for original_info in block['records'][1:]:
            if result[cursor] != original_info:
                raise ValueError('Copied INFO changed')
            cursor += 1
    if cursor != len(result):
        raise ValueError('Unexpected appended records')
    return output, ledger


def build(source, output):
    if output.exists():
        raise FileExistsError(output)
    for name, expected in {**SOURCES, CORE: CORE_SHA}.items():
        if sha((source / name).read_bytes()) != expected:
            raise ValueError('Release ZIP SHA mismatch: ' + name)
    with zipfile.ZipFile(source / CORE) as archive:
        raw = archive.read('payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.esp')
        live = {decode(f[b'NAME']) for tag, body in record_chunks(raw) if tag == b'DIAL'
                for f in [dict(subs(body))] if b'DELE' not in f and f.get(b'DATA') == b'\0'}
        if not set(TOPICS.values()) <= live:
            raise ValueError('Expected Korean core topics missing')
    output.mkdir(parents=True)
    report = {'shared_topics': TOPICS, 'archives': {}, 'published': False,
              'engine_changed': False, 'additional_plugins': 0,
              'original_records_preserved': True, 'sidecars_preserved': True}
    for name, expected in SOURCES.items():
        changes = {}
        with zipfile.ZipFile(source / name) as src, zipfile.ZipFile(output / name, 'x', zipfile.ZIP_DEFLATED) as dst:
            for item in src.infolist():
                before = src.read(item)
                after, ledger = plugin(before) if Path(item.filename).suffix.lower() in ('.esm', '.esp') else (before, [])
                if before != after:
                    changes[item.filename] = {'sha256_before': sha(before), 'sha256_after': sha(after), 'topics': ledger}
                dst.writestr(item, after)
        with zipfile.ZipFile(source / name) as src, zipfile.ZipFile(output / name) as dst:
            if dst.testzip() or src.namelist() != dst.namelist():
                raise ValueError('ZIP structure/CRC mismatch')
            if {n for n in src.namelist() if src.read(n) != dst.read(n)} != set(changes):
                raise ValueError('Unrelated ZIP entry changed')
        report['archives'][name] = {'source_sha256': expected, 'changes': changes,
                                    'candidate_sha256': sha((output / name).read_bytes())}
    (output / 'build-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = build(args.source, args.output)
    print(json.dumps({name: list(row['changes']) for name, row in report['archives'].items()}, ensure_ascii=False, indent=2))
