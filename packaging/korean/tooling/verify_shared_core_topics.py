"""Check additional topic copies with the Windows native parser in 12 loadouts."""
import argparse
import json
from pathlib import Path

from repair_shared_default_topics import SOURCES
from verify_shared_default_topics import archive, merge, native, parse


def verify(baseline, candidate, release, core, masters, runner, mapping, pfp=None):
    review = json.loads(mapping.read_text(encoding='utf-8'))
    reverse = {}
    for row in review['topics']:
        reverse.setdefault(row['korean'].casefold(), []).append(row['english'].casefold())
    official = [parse((masters / n).read_bytes(), n, 'cp1252') for n in ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')]
    coremod = parse(core.read_bytes(), core.name, sidecars={e: core.with_suffix('.' + e).read_bytes() for e in ('top', 'mrk', 'jrn')})
    before = {n: archive(baseline / n) for n in SOURCES}
    after = {n: archive(candidate / n) for n in SOURCES}
    td, tr, cyr, sky, compat = SOURCES
    rebirth = archive(release / 'Morrowind_Rebirth7.2-kr1.2.zip')
    main = [m for m in rebirth if m['name'].startswith('Data Files/')]
    alternate = [m for m in rebirth if m['name'].startswith('Alternate')]
    alternate += [m for m in main if '[Main]' not in m['name']]
    purists = []
    if pfp:
        path = pfp / 'Patch for Purists.esm'
        purists = [parse(path.read_bytes(), path.name, sidecars={e: path.with_suffix('.' + e).read_bytes() for e in ('top', 'mrk', 'jrn') if path.with_suffix('.' + e).exists()})]
    configs = {'core': ([], []), 'core-pfp': ([], purists), 'tamriel-data': ([td], []),
               'tr': ([td, tr], []), 'cyr': ([td, cyr], []), 'sky': ([td, sky], []),
               'all-regions': ([td, tr, cyr, sky], []), 'rebirth-main': ([], main),
               'rebirth-alternate': ([], alternate), 'all-rebirth-main': ([td, tr, compat], main),
               'all-rebirth-alternate': ([td, tr, compat], alternate),
               'all-pfp-rebirth': ([td, tr, compat], purists + main)}
    reports = []
    for label, (selected, extras) in configs.items():
        prefix = [m for m in extras if m in purists]
        suffix = [m for m in extras if m not in purists]
        common = official + [coremod] + prefix
        old = merge(common + [m for n in selected for m in before[n]] + suffix)
        new = merge(common + [m for n in selected for m in after[n]] + suffix)
        assert old[0] == new[0] and old[2] == new[2], 'Topic IDs or aliases changed'
        assert old[1].keys() <= new[1].keys(), 'Original response removed'
        old_results, new_results = native(runner, old), native(runner, new)
        copied = 0
        for key, row in new[1].items():
            if key in old[1]:
                assert row['body'] == old[1][key]['body'], ('Existing Korean response overwritten', label, key)
                reference = key
            else:
                references = [(source, key[1]) for source in reverse[key[0]] if (source, key[1]) in old[1]]
                references = [k for k in references if old[1][k]['body'] == row['body'] and old[1][k]['plugin'] == row['plugin']]
                assert references, ('Copy differs', label, key)
                reference = references[0]
                copied += 1
            assert old_results[reference] == new_results[key], ('Native parsing changed', label, key)
        report = {'configuration': label, 'INFO_checked': len(new[1]), 'copied_responses': copied,
                  'existing_responses_overwritten': 0, 'original_responses_removed': 0, 'native_link_losses': 0}
        reports.append(report)
        print(json.dumps(report), flush=True)
    result = {'configurations': reports, 'scope': 'Byte-identical additional regional responses and native keyword parsing. Full NPC quest progression requires gameplay review.'}
    (candidate / 'shared-core-native-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'release', 'core', 'masters', 'runner', 'mapping'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--pfp', type=Path)
    a = p.parse_args()
    verify(a.baseline, a.candidate, a.release, a.core, a.masters, a.runner.resolve(), a.mapping, a.pfp)
