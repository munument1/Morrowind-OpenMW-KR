"""Compare reviewed core links in twelve valid Windows native-parser loadouts."""
import argparse
import json
import tempfile
from pathlib import Path

from repair_reviewed_issue42_links import MANIFEST, STEM, sha
from repair_shared_default_topics import CORE, SOURCES
from verify_shared_default_topics import archive, merge, native, parse
from verify_kr5_links import inspect


def display(runner, state):
    topics, infos, maps = state
    keys = list(infos)
    with tempfile.TemporaryDirectory(prefix='reviewed-display-') as temp:
        folder = Path(temp)
        for extension, mapping in maps.items():
            (folder / (STEM + '.' + extension)).write_text(
                '\n'.join(k + '\t' + v for k, v in mapping.items()) + '\n', encoding='utf-8-sig')
        found = inspect(runner, folder, [(str(i), infos[k]['text']) for i, k in enumerate(keys)],
                        [v['name'] for v in topics.values() if v['active'] and v['kind'] == 0], False)
    return {key: found[str(i)] for i, key in enumerate(keys)}


def verify(source, regional, candidate, masters, runner, pfp):
    review = json.loads(MANIFEST.read_text(encoding='utf-8'))
    changes = {(r['parent'], r['info']): r for r in review['changes']}
    core = archive(source / CORE)
    updated = parse((candidate / (STEM + '.esp')).read_bytes(), core[0]['name'], sidecars={
        e: (candidate / (STEM + '.' + e)).read_bytes() for e in ('top', 'mrk', 'jrn')})
    official = [parse((masters / n).read_bytes(), n, 'cp1252')
                for n in ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')]
    regions = {name: archive(regional / name) for name in SOURCES}
    td, tr, cyr, sky, compat = SOURCES
    rebirth = archive(source / 'Morrowind_Rebirth7.2-kr1.2.zip')
    main = [m for m in rebirth if m['name'].startswith('Data Files/')]
    alternate = [m for m in rebirth if m['name'].startswith('Alternate')]
    alternate += [m for m in main if '[Main]' not in m['name']]
    path = pfp / 'Patch for Purists.esm'
    purists = [parse(path.read_bytes(), path.name, sidecars={e: path.with_suffix('.' + e).read_bytes()
               for e in ('top', 'mrk', 'jrn') if path.with_suffix('.' + e).exists()})]
    configurations = {
        'core': ([], []), 'core-pfp': ([], purists), 'tamriel-data': ([td], []),
        'tr': ([td, tr], []), 'cyr': ([td, cyr], []), 'sky': ([td, sky], []),
        'all-regions': ([td, tr, cyr, sky], []), 'rebirth-main': ([], main),
        'rebirth-alternate': ([], alternate), 'all-rebirth-main': ([td, tr, compat], main),
        'all-rebirth-alternate': ([td, tr, compat], alternate),
        'all-pfp-rebirth': ([td, tr, compat], purists + main),
    }
    reports = []
    for label, (selected, extras) in configurations.items():
        assert not (compat in selected and (cyr in selected or sky in selected))
        prefix = [m for m in extras if m in purists]
        suffix = [m for name in selected for m in regions[name]] + [m for m in extras if m not in purists]
        suffix = prefix + suffix
        old_state = merge(official + core + suffix)
        new_state = merge(official + [updated] + suffix)
        before, after = native(runner, old_state), native(runner, new_state)
        old_ui, new_ui = display(runner, old_state), display(runner, new_state)
        assert before.keys() == after.keys()
        removed, added, checked = [], 0, 0
        for key in before:
            assert old_ui[key]['text'] == new_ui[key]['text'], ('Display changed', label, key)
            b, a = set(before[key]['targets']), set(after[key]['targets'])
            changed = key in changes and new_state[1][key]['plugin'] == updated['name']
            if changed:
                c = changes[key]
                assert set(t.casefold() for t in c['targets']) <= a, ('Target missing', label, key)
                assert not (b - a) - set(c.get('allowed_removed_targets', [])), ('Valid link lost', label, key, sorted(b-a), c.get('allowed_removed_targets', []))
                checked += 1
            else:
                assert before[key] == after[key], ('Unreviewed response changed', label, key)
            removed.extend({'parent': key[0], 'info': key[1], 'incorrect_target': t} for t in sorted(b - a))
            added += len(a - b)
        result = {'label': label, 'INFO_checked': len(before), 'reviewed_INFO_loaded': checked,
                  'new_targets': added, 'removed_incorrect_targets': removed,
                  'valid_links_lost': 0, 'display_changes': 0,
                  'plugins': [m['name'] for m in official + [updated] + suffix]}
        reports.append(result)
        print(json.dumps({k: v for k, v in result.items() if k not in ('removed_incorrect_targets', 'plugins')}), flush=True)
    report = {'configurations': reports,
              'source_zip_sha256': sha((source / CORE).read_bytes()),
              'candidate_esp_sha256': sha((candidate / (STEM + '.esp')).read_bytes()),
              'review_manifest_sha256': sha(MANIFEST.read_bytes()),
              'runner_sha256': sha(runner.read_bytes()),
              'master_sha256': {n: sha((masters / n).read_bytes()) for n in ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')},
              'scope': 'Actual native parser discovery and display; original masters and user saves read-only. Does not simulate quest conditions.'}
    (candidate / 'native-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'regional', 'candidate', 'masters', 'runner', 'pfp'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    verify(a.source, a.regional, a.candidate, a.masters, a.runner.resolve(), a.pfp)
