"""Apply source-pinned INFO.NAME links without changing visible text or scripts."""
import argparse
import hashlib
import json
import re
import struct
import zipfile
from pathlib import Path

from audit_cross_mod_topic_gaps import subs

MANIFEST = Path(__file__).resolve().parents[3] / 'translations/openmw-kr/issue42_reviewed_links_20261111.json'
STEM = 'Morrowind_Korean_ReTranslation'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def visible(text):
    return re.sub(r'@([^@#]*)#', lambda m: m[1].replace('\x7f', ''), text)


def rewrite(raw, top, review):
    changes = {(c['parent'].casefold(), c['info']): c for c in review['changes']}
    if len(changes) != len(review['changes']):
        raise ValueError('Duplicate reviewed INFO key')
    aliases = {}
    for line in top.decode('utf-8-sig').splitlines():
        if '\t' in line:
            key, value = line.split('\t', 1)
            aliases.setdefault(key, value)
    for key, target in review['aliases'].items():
        if key in aliases:
            raise ValueError('New alias already exists: ' + key)
        aliases[key] = target
    result, applied, topics = [], set(), set()
    pos, parent = 0, ''
    while pos < len(raw):
        if pos + 16 > len(raw):
            raise ValueError('Truncated record header')
        tag, size = struct.unpack_from('<4sI', raw, pos)
        end = pos + 16 + size
        if end > len(raw):
            raise ValueError('Truncated record body')
        header, body = raw[pos:pos + 16], raw[pos + 16:end]
        if tag == b'DIAL':
            fields = dict(subs(body))
            parent = fields[b'NAME'].rstrip(b'\0').decode('utf-8').casefold()
            if fields.get(b'DATA', b'\xff')[:1] == b'\0' and b'DELE' not in fields:
                topics.add(parent)
        elif tag == b'INFO':
            fields = list(subs(body))
            values = dict(fields)
            key = parent, values.get(b'INAM', b'').rstrip(b'\0').decode('ascii')
            if key in changes:
                c = changes[key]
                if key in applied or sha(body) != c['source_body_sha256']:
                    raise ValueError('Reviewed INFO source mismatch: ' + str(key))
                old = values[b'NAME'].rstrip(b'\0').decode('utf-8')
                if old != c['before'] or visible(old) != visible(c['after']):
                    raise ValueError('Visible text or source mismatch: ' + str(key))
                suffix = values[b'NAME'][len(values[b'NAME'].rstrip(b'\0')):]
                updated = c['after'].encode('utf-8') + suffix
                body = b''.join(t + struct.pack('<I', len(updated if t == b'NAME' else v))
                                + (updated if t == b'NAME' else v) for t, v in fields)
                header = header[:4] + struct.pack('<I', len(body)) + header[8:]
                # Independently compare ordered fields; all conditions and scripts survive.
                assert [(t, v) for t, v in subs(body) if t != b'NAME'] == [(t, v) for t, v in fields if t != b'NAME']
                applied.add(key)
        result.append(header + body)
        pos = end
    if applied != changes.keys():
        raise ValueError('Reviewed INFO missing: ' + str(changes.keys() - applied))
    for c in review['changes']:
        if not set(t.casefold() for t in c['targets']) <= topics:
            raise ValueError('Reviewed target is absent')
        for phrase in re.findall(r'@([^@#]*)#', c['after']):
            shown = phrase.rstrip('\x7f')
            key = shown + '*' * (len(phrase) - len(shown))
            if aliases.get(key, key).casefold() not in topics:
                raise ValueError('Unresolved explicit topic: ' + key)
    additions = ''.join(k + '\t' + v + '\r\n' for k, v in review['aliases'].items()).encode('utf-8')
    updated_top = top + (b'' if top.endswith((b'\n', b'\r')) else b'\r\n') + additions
    return b''.join(result), updated_top


def build(source, output, manifest=MANIFEST):
    review = json.loads(manifest.read_text(encoding='utf-8'))
    if sha(source.read_bytes()) != review['baseline_zip_sha256']:
        raise ValueError('Published source ZIP SHA mismatch')
    if output.exists():
        raise ValueError('Output must be a new directory')
    with zipfile.ZipFile(source) as src:
        members = {Path(n).name: n for n in src.namelist() if Path(n).stem == STEM}
        esp, top = src.read(members[STEM + '.esp']), src.read(members[STEM + '.top'])
        updated, updated_top = rewrite(esp, top, review)
        output.mkdir(parents=True)
        for name, member in members.items():
            (output / name).write_bytes(updated if name.endswith('.esp') else updated_top if name.endswith('.top') else src.read(member))
    report = {'source_zip_sha256': sha(source.read_bytes()), 'before_esp_sha256': sha(esp),
              'after_esp_sha256': sha(updated), 'changed_INFO': len(review['changes']),
              'reported_pairs_fixed': len(review['reviewed_report_indices']),
              'new_aliases': len(review['aliases']), 'visible_text_unchanged': True,
              'other_fields_unchanged': True}
    (output / 'build-verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(build(args.source, args.output), indent=2))
