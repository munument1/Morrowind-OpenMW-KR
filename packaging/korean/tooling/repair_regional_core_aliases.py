"""Keep regional sidecars from stealing Korean core topic keywords."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from verify_shared_default_topics import parse


def rewrite(raw, extension, mapping, normal_topics=()):
    bom = b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    text = raw[len(bom):].decode('utf-8')
    result, ledger = [], []
    for line in text.splitlines(keepends=True):
        content = line.rstrip('\r\n')
        eol = line[len(content):]
        if '\t' not in content:
            result.append(line)
            continue
        key, value = content.split('\t', 1)
        if extension in ('top', 'jrn') and value.casefold() in mapping:
            target = mapping[value.casefold()]
            result.append(key + '\t' + target + eol)
            ledger.append({'key': key, 'old_value': value, 'new_value': target, 'action': 'canonical_korean_target'})
        else:
            result.append(line)
    existing = {line.rstrip('\r\n').split('\t', 1)[0]: line.rstrip('\r\n').split('\t', 1)[1]
                for line in result if '\t' in line}
    if extension == 'top':
        for english in sorted(set(normal_topics) & mapping.keys()):
            target = mapping[english]
            if english in existing:
                if existing[english] != target:
                    raise ValueError('English canonical alias conflicts: ' + english)
                continue
            if result and not result[-1].endswith(('\r', '\n')):
                result.append('\n')
            result.append(english + '\t' + target + '\n')
            ledger.append({'key': english, 'new_value': target, 'action': 'canonical_english_id_alias'})
    return bom + ''.join(result).encode('utf-8'), ledger


def build(source, output, manifest):
    review = json.loads(manifest.read_text(encoding='utf-8'))
    mapping = {r['english'].casefold(): r['korean'] for r in review['topics']}
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    reports = {}
    for path in sorted(source.glob('*.zip')):
        changes = {}
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(output / path.name, 'x') as dst:
            plugin_topics = {n.rsplit('.', 1)[0].casefold(): {k for k, v in parse(src.read(n), n)['topics'].items() if v['active'] and v['kind'] == 0}
                             for n in src.namelist() if Path(n).suffix.lower() in ('.esm', '.esp')}
            for item in src.infolist():
                before = src.read(item)
                extension = Path(item.filename).suffix.lower().lstrip('.')
                normal = plugin_topics.get(item.filename.rsplit('.', 1)[0].casefold(), set())
                after, ledger = rewrite(before, extension, mapping, normal) if extension in ('top', 'jrn') else (before, [])
                dst.writestr(item, after)
                if ledger:
                    changes[item.filename] = ledger
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(output / path.name) as dst:
            assert src.namelist() == dst.namelist() and dst.testzip() is None
            for name in src.namelist():
                before = src.read(name)
                extension = Path(name).suffix.lower().lstrip('.')
                normal = plugin_topics.get(name.rsplit('.', 1)[0].casefold(), set())
                expected = rewrite(before, extension, mapping, normal)[0] if name in changes else before
                assert dst.read(name) == expected, 'Unreviewed sidecar or plugin byte changed'
        if not changes:
            (output / path.name).write_bytes(path.read_bytes())
        reports[path.name] = {'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                             'candidate_sha256': hashlib.sha256((output / path.name).read_bytes()).hexdigest(), 'changes': changes}
    report = {'archives': reports, 'plugin_bytes_changed': 0, 'cell_sidecars_changed': 0,
              'mapping_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest()}
    (output / 'regional-core-alias-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'output', 'manifest'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    report = build(a.source, a.output, a.manifest)
    print(json.dumps({n: sum(len(rows) for rows in r['changes'].values()) for n, r in report['archives'].items()}, indent=2))
