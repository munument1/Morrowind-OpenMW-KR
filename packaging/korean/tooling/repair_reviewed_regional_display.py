"""Replay reviewed display fields on pinned regional ZIPs after issue #66 repair."""
import argparse
import hashlib
import json
import struct
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

from audit_cross_mod_topic_gaps import subs
from repair_shared_default_topics import TOPICS, build as build_shared
from repair_reviewed_book_text import rewrite as rewrite_book

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / 'translations/openmw-kr/issue63_reviewed_display_20261111.json'
REVERSE_TOPICS = {v.casefold(): k for k, v in TOPICS.items()}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def parent_key(parent):
    return REVERSE_TOPICS.get(parent.casefold(), parent.casefold())


def row_key(row):
    return (row['record_tag'], row['record_id'].casefold(), parent_key(row.get('parent', '')),
            row['field'], row.get('field_ordinal', 0))


def rewrite(raw, patches):
    by_key = {row_key(r): r for r in patches}
    if len(by_key) != len(patches):
        raise ValueError('Duplicate display patch key')
    result, applied = [], Counter()
    pos, parent = 0, ''
    while pos < len(raw):
        if pos + 16 > len(raw):
            raise ValueError('Truncated record header')
        tag, size = struct.unpack_from('<4sI', raw, pos)
        end = pos + 16 + size
        if end > len(raw):
            raise ValueError('Truncated record body')
        header, body = raw[pos:pos + 16], raw[pos + 16:end]
        items = list(subs(body))
        values = dict(items)
        if tag == b'DIAL':
            parent = values[b'NAME'].rstrip(b'\0').decode('utf-8')
        id_tag = b'INAM' if tag == b'INFO' else b'NAME'
        record_id = values.get(id_tag, b'').rstrip(b'\0').decode('utf-8', errors='replace')
        ordinal, rewritten, changed = Counter(), [], False
        for field, value in items:
            key = (tag.decode(), record_id.casefold(), parent_key(parent) if tag == b'INFO' else '',
                   field.decode(), ordinal[field])
            ordinal[field] += 1
            if key in by_key:
                patch = by_key[key]
                if sha(value) != patch['source_raw_sha256']:
                    raise ValueError('Reviewed display source mismatch: ' + str(key))
                if (tag, field) not in ((b'INFO', b'NAME'), (b'BOOK', b'TEXT'), (b'FACT', b'RNAM')) and field != b'FNAM':
                    raise ValueError('Patch is not a supported display field: ' + str(key))
                if patch.get('book_patches'):
                    if (tag, field) != (b'BOOK', b'TEXT'):
                        raise ValueError('Book prose spans used outside BOOK.TEXT')
                    value = rewrite_book(value, patch['book_patches'])
                    applied[key] += 1
                    changed = True
                    rewritten.append(field + struct.pack('<I', len(value)) + value)
                    continue
                target = patch['target']
                if not target or '\0' in target:
                    raise ValueError('Invalid display target')
                if not any('\uac00' <= c <= '\ud7a3' for c in target):
                    raise ValueError('Translation has no Korean text')
                suffix = value[len(value.rstrip(b'\0')):]
                if tag == b'FACT':
                    updated = target.encode('utf-8') + b'\0'
                    if len(updated) > 32:
                        raise ValueError('Faction rank exceeds fixed 32-byte RNAM field: ' + str(key))
                    updated = updated.ljust(32, b'\0')
                else:
                    updated = target.encode('utf-8') + suffix
                value = updated
                applied[key] += 1
                changed = True
            rewritten.append(field + struct.pack('<I', len(value)) + value)
        if changed:
            body = b''.join(rewritten)
            header = header[:4] + struct.pack('<I', len(body)) + header[8:]
        result.append(header + body)
        pos = end
    return b''.join(result), applied


def module_for(member):
    name = Path(member).stem.casefold()
    return {'tamriel_data': 'Tamriel_Data', 'tr_mainland': 'TR_Mainland',
            'cyr_main': 'Cyr_Main', 'sky_main': 'Sky_Main',
            'project cyrodiil [for rebirth]': 'Cyr_Main',
            'skyrim home of the nords [for rebirth]': 'Sky_Main'}.get(name)


def append_aliases(raw, aliases):
    existing = {line.split('\t', 1)[0] for line in raw.decode('utf-8-sig').splitlines() if '\t' in line}
    if raw and not raw.endswith(b'\n'):
        raise ValueError('TOP does not end with a newline')
    for key, target in aliases.items():
        if key in existing or any(c in key + target for c in '\t\r\n\0'):
            raise ValueError('New reviewed alias conflicts or contains a control character: ' + key)
    return raw + ''.join(k + '\t' + v + '\r\n' for k, v in aliases.items()).encode('utf-8')


def build(source, output, manifest=MANIFEST):
    review = json.loads(manifest.read_text(encoding='utf-8'))
    if output.exists():
        raise ValueError('Output must be a new directory')
    reports, seen = {}, Counter()
    with tempfile.TemporaryDirectory(prefix='regional-display-') as temp:
        baseline = Path(temp) / 'shared'
        build_shared(source, baseline)
        output.mkdir(parents=True)
        for path in sorted(baseline.glob('*.zip')):
            changes = {}
            with zipfile.ZipFile(path) as src, zipfile.ZipFile(output / path.name, 'w') as dst:
                for info in src.infolist():
                    raw = src.read(info.filename)
                    module = module_for(info.filename) if Path(info.filename).suffix.lower() in ('.esm', '.esp') else None
                    if module:
                        patches = [r for r in review['rows'] if (r.get('target') or r.get('book_patches')) and r['module'] == module]
                        updated, applied = rewrite(raw, patches)
                        seen.update((module, *key) for key in applied)
                        if updated != raw:
                            changes[info.filename] = {'before_sha256': sha(raw), 'after_sha256': sha(updated),
                                                      'physical_fields_changed': sum(applied.values())}
                        raw = updated
                    elif Path(info.filename).suffix.lower() == '.top':
                        aliases = review.get('topic_aliases', {}).get(module_for(info.filename), {})
                        if aliases:
                            updated = append_aliases(raw, aliases)
                            changes[info.filename] = {'before_sha256': sha(raw), 'after_sha256': sha(updated), 'new_explicit_aliases': len(aliases)}
                            raw = updated
                    dst.writestr(info, raw)
            if not changes:
                (output / path.name).write_bytes(path.read_bytes())
            reports[path.name] = {'sha256': sha((output / path.name).read_bytes()), 'changes': changes}
    expected = {(r['module'], *row_key(r)) for r in review['rows'] if r.get('target') or r.get('book_patches')}
    if not expected <= seen.keys():
        raise ValueError('Reviewed source field not found: ' + str(expected - seen.keys()))
    report = {'manifest_sha256': sha(manifest.read_bytes()), 'reviewed_fields': len(expected), 'archives': reports}
    (output / 'display-build-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(build(a.source, a.output), ensure_ascii=False, indent=2))
