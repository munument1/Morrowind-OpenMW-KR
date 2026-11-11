"""Bind English source topic IDs to verified Korean core IDs before regional maps."""
import hashlib
import json
from pathlib import Path


def build(core, output, manifest):
    review = json.loads(manifest.read_text(encoding='utf-8'))
    if hashlib.sha256(core.read_bytes()).hexdigest() != review['core_sha256']:
        raise ValueError('Core plugin SHA mismatch')
    original = core.with_suffix('.top').read_bytes()
    if hashlib.sha256(original).hexdigest() != review['core_top_source_sha256']:
        raise ValueError('Core TOP source SHA mismatch')
    mapping = {r['english']: r['korean'] for r in review['topics']}
    bom = b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b''
    lines, seen, changes = [], set(), []
    for line in original[len(bom):].decode('utf-8').splitlines(keepends=True):
        content = line.rstrip('\r\n')
        if '\t' in content:
            key, value = content.split('\t', 1)
            if key in mapping:
                target = mapping[key]
                if value.casefold() not in (key, target.casefold()):
                    raise ValueError('Canonical English alias conflicts in core: ' + key)
                if value != target:
                    changes.append({'key': key, 'old': value, 'new': target})
                line = key + '\t' + target + line[len(content):]
                seen.add(key)
        lines.append(line)
    for key in sorted(mapping.keys() - seen):
        if lines and not lines[-1].endswith(('\r', '\n')):
            lines.append('\n')
        lines.append(key + '\t' + mapping[key] + '\n')
        changes.append({'key': key, 'new': mapping[key]})
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    for extension in ('.esp', '.cel', '.mrk', '.jrn'):
        path = core.with_suffix(extension)
        if path.exists():
            (output / path.name).write_bytes(path.read_bytes())
    updated = bom + ''.join(lines).encode('utf-8')
    (output / core.with_suffix('.top').name).write_bytes(updated)
    report = {'source_top_sha256': review['core_top_source_sha256'],
              'candidate_top_sha256': hashlib.sha256(updated).hexdigest(), 'changes': changes,
              'plugin_bytes_changed': 0, 'other_sidecars_changed': 0}
    (output / 'core-alias-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report
