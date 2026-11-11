"""Copy unambiguous regional responses to existing Korean core topic IDs.

Original records remain byte-identical. Existing Korean responses always win.
The mapping is anchored by INFO IDs AND their complete actor/quest predicates.
"""
import argparse
import hashlib
import json
import struct
import zipfile
from collections import defaultdict
from pathlib import Path

from audit_cross_mod_topic_gaps import subs
from audit_explicit_topic_tags import identity
from repair_shared_default_topics import change, decode, physical_records


def topic_records(raw, encoding='utf-8'):
    parent, kind, active = '', -1, False
    for record in physical_records(raw):
        fields = dict(subs(record[16:]))
        if record[:4] == b'DIAL':
            parent = fields[b'NAME'].rstrip(b'\0').decode(encoding)
            kind = fields.get(b'DATA', b'\xff')[0]
            active = b'DELE' not in fields
        elif record[:4] == b'INFO':
            yield parent, kind, active, record, fields


def make_mapping(masters, core):
    originals, candidates = defaultdict(set), defaultdict(lambda: defaultdict(list))
    for raw in masters:
        for parent, kind, active, record, fields in topic_records(raw, 'cp1252'):
            if active and kind == 0 and b'DELE' not in fields:
                originals[identity(subs(record[16:]))].add(parent.casefold())
    for parent, kind, active, record, fields in topic_records(core):
        anchor = identity(subs(record[16:]))
        names = originals.get(anchor, set())
        if active and kind == 0 and b'DELE' not in fields and len(names) == 1:
            candidates[next(iter(names))][parent].append(anchor)
    unique = {en: next(iter(ko)) for en, ko in candidates.items() if len(ko) == 1}
    reverse = defaultdict(set)
    for en, ko in unique.items():
        reverse[ko.casefold()].add(en)
    return [{'english': en, 'korean': ko, 'identity_anchors': sorted(candidates[en][ko])}
            for en, ko in sorted(unique.items())
            if en != ko.casefold() and len(reverse[ko.casefold()]) == 1]


def info_keys(raw):
    # Deleted and non-normal entries also reserve their IDs: never resurrect or
    # overwrite an existing Korean override by copying an English response.
    return {(parent.casefold(), decode(fields.get(b'INAM', b'')))
            for parent, _, _, _, fields in topic_records(raw)}


def extend(raw, mapping, protected):
    records = list(physical_records(raw))
    if not records or records[0][:4] != b'TES3':
        raise ValueError('Missing TES3 header')
    header = dict(subs(records[0][16:]))[b'HEDR']
    if len(header) != 300 or struct.unpack_from('<I', header, 296)[0] != len(records) - 1:
        raise ValueError('Unexpected record count')
    names = {r['english'].casefold(): r['korean'] for r in mapping}
    if len(names) != len(mapping):
        raise ValueError('Ambiguous topic mapping')
    reserved = set(protected) | info_keys(raw)
    copied = {}
    blocks, current = [], None
    for record in records[1:]:
        fields = dict(subs(record[16:]))
        if record[:4] == b'DIAL':
            name = decode(fields[b'NAME'])
            current = None
            if name.casefold() in names and b'DELE' not in fields and fields.get(b'DATA') == b'\0':
                current = {'source': name, 'target': names[name.casefold()], 'dial': record, 'infos': [], 'protected': 0}
                blocks.append(current)
        elif record[:4] == b'INFO' and current is not None:
            key = (current['target'].casefold(), decode(fields[b'INAM']))
            if key in copied and record != copied[key]:
                raise ValueError('Conflicting regional INFOs across synonym topics: ' + str(key))
            if key in reserved:
                current['protected'] += 1
            elif b'DELE' not in fields:
                current['infos'].append(record)
                reserved.add(key)
                copied[key] = record
        else:
            current = None
    added, ledger = [], []
    for block in blocks:
        if not block['infos']:
            continue
        old = dict(subs(block['dial'][16:]))[b'NAME']
        name = block['target'].encode() + old[len(old.rstrip(b'\0')):]
        added.extend([change(block['dial'], b'NAME', name), *block['infos']])
        ledger.append({'source_topic': block['source'], 'korean_topic': block['target'],
                       'copied_infos': len(block['infos']), 'protected_existing_infos': block['protected'],
                       'copied_info_sha256': hashlib.sha256(b''.join(block['infos'])).hexdigest()})
    if not added:
        return raw, ledger
    output = b''.join([change(records[0], b'HEDR', header[:296] + struct.pack('<I', len(records) - 1 + len(added))),
                       *records[1:], *added])
    rebuilt = list(physical_records(output))
    assert rebuilt[1:len(records)] == records[1:], 'Original record changed'
    assert rebuilt[len(records):] == added, 'Appended copy changed'
    return output, ledger


def build(source, output, core, manifest):
    review = json.loads(manifest.read_text(encoding='utf-8'))
    raw_core = core.read_bytes()
    if hashlib.sha256(raw_core).hexdigest() != review['core_sha256']:
        raise ValueError('Korean core SHA mismatch')
    anchors = {identity(subs(record[16:])): parent
               for parent, kind, active, record, fields in topic_records(raw_core)
               if kind == 0 and active and b'DELE' not in fields}
    for row in review['topics']:
        if not row['identity_anchors'] or any(anchors.get(a) != row['korean'] for a in row['identity_anchors']):
            raise ValueError('Core topic identity anchor mismatch')
    if output.exists():
        raise FileExistsError(output)
    paths = sorted(source.glob('*.zip'))
    if not paths:
        raise ValueError('No regional ZIPs')
    protected = info_keys(raw_core)
    for path in paths:
        with zipfile.ZipFile(path) as src:
            for name in src.namelist():
                if Path(name).suffix.lower() in ('.esm', '.esp'):
                    protected.update(info_keys(src.read(name)))
    output.mkdir(parents=True)
    reports = {}
    for path in paths:
        changes = {}
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(output / path.name, 'x') as dst:
            for item in src.infolist():
                before = src.read(item)
                after, ledger = extend(before, review['topics'], protected) if Path(item.filename).suffix.lower() in ('.esm', '.esp') else (before, [])
                dst.writestr(item, after)
                if ledger:
                    changes[item.filename] = ledger
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(output / path.name) as dst:
            assert src.namelist() == dst.namelist() and dst.testzip() is None
            for name in src.namelist():
                before, after = src.read(name), dst.read(name)
                if name not in changes:
                    assert before == after, 'Unrelated ZIP member changed'
                else:
                    old, new = list(physical_records(before)), list(physical_records(after))
                    assert new[1:len(old)] == old[1:], 'Original records changed'
                    assert new[0][:4] == old[0][:4] and new[0][8:16] == old[0][8:16]
                    of, nf = list(subs(old[0][16:])), list(subs(new[0][16:]))
                    assert [t for t, _ in of] == [t for t, _ in nf]
                    for (tag, ov), (_, nv) in zip(of, nf):
                        assert (ov[:-4] == nv[:-4] if tag == b'HEDR' else ov == nv)
                    source_blocks, parent = {}, None
                    for r in old[1:]:
                        f = dict(subs(r[16:]))
                        if r[:4] == b'DIAL':
                            parent = decode(f[b'NAME']).casefold()
                            source_blocks[parent] = [r]
                        elif r[:4] == b'INFO' and parent:
                            source_blocks[parent].append(r)
                    added_blocks = iter(changes[name])
                    source_records = set()
                    for r in new[len(old):]:
                        f = dict(subs(r[16:]))
                        if r[:4] == b'DIAL':
                            ko = decode(f[b'NAME'])
                            block = next(added_blocks)
                            assert block['korean_topic'] == ko
                            source_topic = block['source_topic'].casefold()
                            source_records = set(source_blocks[source_topic][1:])
                            original_dial = source_blocks[source_topic][0]
                            assert [(t, v) for t, v in subs(original_dial[16:]) if t != b'NAME'] == [(t, v) for t, v in subs(r[16:]) if t != b'NAME']
                        else:
                            assert r[:4] == b'INFO' and r in source_records
                            assert (ko.casefold(), decode(f[b'INAM'])) not in protected
                    assert next(added_blocks, None) is None
        if not changes:
            (output / path.name).write_bytes(path.read_bytes())
        reports[path.name] = {'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                             'candidate_sha256': hashlib.sha256((output / path.name).read_bytes()).hexdigest(),
                             'changes': changes}
    report = {'archives': reports, 'original_records_preserved': True, 'existing_korean_infos_overwritten': 0,
              'sidecar_changes': 0, 'mapping_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest()}
    (output / 'shared-core-build-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--core', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    a = p.parse_args()
    result = build(a.source, a.output, a.core, a.manifest)
    print(json.dumps({n: sum(t['copied_infos'] for v in r['changes'].values() for t in v) for n, r in result['archives'].items()}, indent=2))
