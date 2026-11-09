"""Repair four core links redirected to DIAL records deleted by the core ESP.

Keep the starred regional TOP aliases: regional plugins use English DIAL IDs.
Only core INFO.NAME markup changes; visible text and other fields stay exact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path

from build_kr12_7_guild_join_release import decode, display, fields, records

ZIP_SHA = '3542bfdfe0bbadff3827f1d36fcb83955193d366d4567b018d8f434a04eadeb6'
STEM = 'payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation'
SPECS = {
    ('전사 길드', '13288348632198840'): ('전사 길드에 가입', 'join the Fighters Guild'),
    ('전사 길드', '2435795662798020478'): ('전사 길드에 가입', 'join the Fighters Guild'),
    ('승진', '22990247762784528944'): ('텔바니 가문에 가입', 'join House Telvanni'),
    ('평신도 회원', '1341756011233729353'): ('제국 교단에 가입', 'join the Imperial Cult'),
}


def patch(raw):
    parent = ''
    states = {}
    for tag, body in records(raw):
        fs = dict(fields(body))
        if tag == b'DIAL':
            states[decode(fs[b'NAME']).casefold()] = b'DELE' not in fs
    for target, deleted in SPECS.values():
        if states.get(target.casefold()) is not True or states.get(deleted.casefold()) is not False:
            raise ValueError('Expected live Korean / deleted English DIAL pair missing')
    result, changes = [], []
    pos = 0
    for tag, body in records(raw):
        original = raw[pos:pos + 16 + len(body)]
        pos += len(original)
        fs = fields(body)
        data = dict(fs)
        if tag == b'DIAL':
            parent = decode(data[b'NAME'])
        key = (parent, decode(data.get(b'INAM', b'')))
        if tag == b'INFO' and key in SPECS:
            target, deleted = SPECS[key]
            before = data[b'NAME']
            old = ('@' + target + '\x7f#').encode()
            new = ('@' + target + '#').encode()
            if before.count(old) != 1:
                raise ValueError('Pinned core link markup changed: ' + repr(key))
            after = before.replace(old, new, 1)
            if display(decode(before)) != display(decode(after)):
                raise ValueError('Visible text changed')
            payload = b''.join(t + struct.pack('<I', len(v)) + v
                               for t, v in ((t, after if t == b'NAME' else v) for t, v in fs))
            original = original[:4] + struct.pack('<I', len(payload)) + original[8:16] + payload
            changes.append(dict(topic=parent, info=key[1], target=target,
                                deleted_target=deleted))
        result.append(original)
    if len(changes) != len(SPECS):
        raise ValueError('Missing or duplicate core INFO')
    output = b''.join(result)
    # Independent field-level comparison, including record headers and ordering.
    before_records, after_records = list(records(raw)), list(records(output))
    if len(before_records) != len(after_records):
        raise ValueError('Record count changed')
    changed = 0
    for (a, before), (b, after) in zip(before_records, after_records):
        if a != b:
            raise ValueError('Record order changed')
        if before == after:
            continue
        if a != b'INFO' or len(fields(before)) != len(fields(after)):
            raise ValueError('Unexpected record edit')
        edits = [(ta, va, vb) for (ta, va), (tb, vb) in zip(fields(before), fields(after))
                 if ta != tb or va != vb]
        if len(edits) != 1 or edits[0][0] != b'NAME' or edits[0][1].replace(b'\x7f', b'') != edits[0][2]:
            raise ValueError('Unexpected field edit')
        changed += 1
    if changed != 4:
        raise ValueError('Expected four INFO.NAME edits')
    return output, changes


def build(source, output):
    if hashlib.sha256(source.read_bytes()).hexdigest() != ZIP_SHA:
        raise ValueError('Official KR12.8 ZIP SHA mismatch')
    if output.exists():
        raise FileExistsError(output)
    with zipfile.ZipFile(source) as src:
        target, changes = patch(src.read(STEM + '.esp'))
        with zipfile.ZipFile(output, 'x') as dst:
            for info in src.infolist():
                dst.writestr(info, target if info.filename == STEM + '.esp' else src.read(info))
    with zipfile.ZipFile(source) as src, zipfile.ZipFile(output) as dst:
        if dst.testzip() or src.namelist() != dst.namelist():
            raise ValueError('Output ZIP differs structurally')
        if [n for n in src.namelist() if src.read(n) != dst.read(n)] != [STEM + '.esp']:
            raise ValueError('Unrelated ZIP entry changed')
    report = dict(source_zip_sha256=ZIP_SHA, changes=changes,
                  candidate_zip_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                  changed_info_names=4, other_zip_members_unchanged=True,
                  visible_text_unchanged=True, gameplay_tested=False, published=False)
    output.with_suffix('.verification.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(build(a.source, a.output), ensure_ascii=False, indent=2))
