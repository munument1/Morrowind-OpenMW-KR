"""Give Rebirth replacement plugins matching translation sidecar filenames."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from audit_cross_mod_topic_gaps import record_chunks, subs
from verify_shared_default_topics import parse

ARCHIVE = 'Rebirth7.2-Cyr_Sky_Compatibility-kr0.3.zip'
REPLACEMENTS = {'Cyr_Main': ('Cyr_Main-kr0.3.zip', 'Project Cyrodiil [For Rebirth]'),
                'Sky_Main': ('Sky_Main-kr0.2.zip', 'Skyrim Home of the Nords [For Rebirth]')}


def cell_names(plugin):
    ids = set()
    for tag, body in record_chunks(plugin):
        if tag in (b'CELL', b'REGN'):
            items = list(subs(body))
            name = next((v for t, v in items if t == b'NAME'), None)
            if name is not None:
                ids.add(name.rstrip(b'\0').decode('utf-8').casefold())
            if tag == b'REGN':
                ids.update(v.rstrip(b'\0').decode('utf-8').casefold() for t, v in items if t == b'FNAM')
    return ids


def payloads(source):
    result, evidence = {}, []
    with zipfile.ZipFile(source / ARCHIVE) as compat:
        for original, (filename, replacement) in REPLACEMENTS.items():
            esm = 'Compability Patches/' + replacement + '.esm'
            plugin = compat.read(esm)
            topics = parse(plugin, esm)['topics']
            with zipfile.ZipFile(source / filename) as regular:
                normal_esm = next(n for n in regular.namelist() if Path(n).suffix.lower() == '.esm')
                normal_topics = parse(regular.read(normal_esm), normal_esm)['topics']
                assert normal_topics.keys() <= topics.keys(), 'Replacement topic IDs differ'
                for extension in ('top', 'mrk', 'cel', 'jrn'):
                    old = 'Compability Patches/' + original + '.' + extension
                    new = 'Compability Patches/' + replacement + '.' + extension
                    if new in compat.namelist():
                        raise ValueError('Replacement sidecar already exists: ' + new)
                    if old in compat.namelist():
                        raw, origin = compat.read(old), old
                    else:
                        origin = normal_esm.rsplit('.', 1)[0] + '.' + extension
                        raw = regular.read(origin)
                    # The regional CEL uses CELL/REGN engine names as its keys.
                    if extension == 'cel':
                        ids = cell_names(plugin)
                        normal_ids = cell_names(regular.read(normal_esm))
                        keys = {line.split('\t', 1)[0].casefold() for line in raw.decode('utf-8-sig').splitlines() if '\t' in line}
                        assert keys & normal_ids <= ids, ('CEL key removed in replacement', sorted((keys & normal_ids) - ids)[:10])
                    result[new] = raw
                    evidence.append({'source': origin, 'target': new, 'sha256': hashlib.sha256(raw).hexdigest(),
                                     'action': 'rename' if old in compat.namelist() else 'copy_matching_regional_sidecar'})
    return result, evidence


def build(source, output):
    additions, evidence = payloads(source)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    renamed = {r['source']: r['target'] for r in evidence if r['action'] == 'rename'}
    for path in sorted(source.glob('*.zip')):
        if path.name != ARCHIVE:
            (output / path.name).write_bytes(path.read_bytes())
            continue
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(output / path.name, 'x') as dst:
            for item in src.infolist():
                if item.filename in renamed:
                    old = item.filename
                    item.filename = renamed[old]
                    dst.writestr(item, additions[item.filename])
                else:
                    dst.writestr(item, src.read(item))
            for row in evidence:
                if row['action'] != 'rename':
                    dst.writestr(row['target'], additions[row['target']])
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(output / path.name) as dst:
            assert dst.testzip() is None
            assert set(dst.namelist()) == {renamed.get(n, n) for n in src.namelist()} | set(additions)
            for name in src.namelist():
                assert src.read(name) == dst.read(renamed.get(name, name)), 'Existing payload changed'
            for name, raw in additions.items():
                assert dst.read(name) == raw
    report = {'archive': ARCHIVE, 'operations': evidence, 'plugin_bytes_changed': 0,
              'unrelated_archives_changed': 0, 'missing_matching_sidecars_after': 0}
    (output / 'rebirth-sidecar-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(build(a.source, a.output), ensure_ascii=False, indent=2))
