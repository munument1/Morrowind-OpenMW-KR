"""Compare reviewed regional fixes in twelve real-parser Windows loadouts."""
import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from audit_cross_mod_topic_gaps import subs
from repair_reviewed_regional_display import MANIFEST, ROOT, module_for, parent_key
from repair_shared_default_topics import SOURCES
from verify_shared_core_topics import loadouts
from verify_shared_default_topics import archive, merge, parse
from verify_kr5_links import inspect


def results(runner, state, discovery):
    topics, infos, maps = state
    keys = list(infos)
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        for ext, mapping in maps.items():
            (folder / ('Morrowind_Korean_ReTranslation.' + ext)).write_text(
                '\n'.join(k + '\t' + v for k, v in mapping.items()) + '\n', encoding='utf-8-sig')
        found = inspect(runner, folder, [(str(i), infos[k]['text']) for i, k in enumerate(keys)],
                        [t['name'] for t in topics.values() if t['active'] and t['kind'] == 0], False, discovery)
    return {key: found[str(i)] for i, key in enumerate(keys)}


def core_plugin(path):
    return parse(path.read_bytes(), path.name, sidecars={e: path.with_suffix('.' + e).read_bytes() for e in ('top', 'mrk', 'jrn')})


def verify(baseline, candidate, release, core, masters, before_runner, runner, pfp=None):
    mapping = json.loads((ROOT / 'translations/openmw-kr/shared_core_topic_mapping_20261111.json').read_text(encoding='utf-8'))
    for name, expected in mapping['master_sha256'].items():
        assert hashlib.sha256((masters / name).read_bytes()).hexdigest() == expected, 'Master SHA mismatch'
    canonical = {r['english']: r['korean'].casefold() for r in mapping['topics']}
    reverse = {}
    for en, ko in canonical.items():
        reverse.setdefault(ko, []).append(en)
    review = json.loads(MANIFEST.read_text(encoding='utf-8'))
    edited = {(r['module'], r['parent'].casefold(), r['record_id']): r for r in review['rows'] if r.get('target') and r['record_tag'] == 'INFO'}
    exceptions = json.loads((ROOT / 'translations/openmw-kr/issue63_reviewed_link_exceptions_20261111.json').read_text(encoding='utf-8'))
    allowed = {}
    for row in exceptions['rows']:
        key = row['module'], row['parent'].casefold(), row['record_id']
        assert edited[key]['source_raw_sha256'] == row['source_raw_sha256'], 'Exception source changed'
        allowed[key] = set(row['allowed_removed'])
    official = [parse((masters / name).read_bytes(), name, 'cp1252') for name in ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')]
    before = {n: archive(baseline / n) for n in SOURCES}
    after = {n: archive(candidate / n) for n in SOURCES}
    oldcore, newcore = core_plugin(core), core_plugin(candidate / 'core' / core.name)
    configs, purists = loadouts(release, pfp)
    reports, errors = [], []
    for label, (selected, extras) in configs.items():
        prefix = [m for m in extras if m in purists]
        suffix = [m for m in extras if m not in purists]
        old = merge(official + [oldcore] + prefix + [m for n in selected for m in before[n]] + suffix)
        new = merge(official + [newcore] + prefix + [m for n in selected for m in after[n]] + suffix)
        assert old[0] == new[0] and old[1].keys() <= new[1].keys(), 'Topic or original INFO removed'
        references, edits, copies = {}, {}, 0
        for key, row in new[1].items():
            reference = key
            if key not in old[1]:
                sources = [(en, key[1]) for en in reverse[key[0]] if (en, key[1]) in new[1]]
                sources = [k for k in sources if new[1][k]['body'] == row['body'] and new[1][k]['plugin'] == row['plugin']]
                assert sources, ('New INFO is not an exact regional copy', label, key)
                reference = sources[0]
                copies += 1
            previous = old[1][reference]
            if previous['body'] != row['body']:
                lookup = module_for(row['plugin']), parent_key(reference[0]), reference[1]
                patch = edited[lookup]
                assert [(t, v) for t, v in subs(previous['body']) if t != b'NAME'] == [(t, v) for t, v in subs(row['body']) if t != b'NAME'], 'INFO predicates or script changed'
                assert hashlib.sha256(dict(subs(previous['body']))[b'NAME']).hexdigest() == patch['source_raw_sha256']
                assert row['text'] == patch['target'], 'Reviewed translation differs'
                edits[key] = lookup
            references[key] = reference
        discovered = {}
        for discovery in (True, False):
            old_results, new_results = results(before_runner, old, discovery), results(runner, new, discovery)
            reviewed_removals, gains, unreviewed, overlaps = 0, 0, 0, 0
            if discovery:
                discovered = {k: {canonical.get(t, t) for t in v['targets']} for k, v in new_results.items()}
            for key, reference in references.items():
                prior, current = old_results[reference], new_results[key]
                old_targets = {canonical.get(t, t) for t in prior['targets']}
                new_targets = {canonical.get(t, t) for t in current['targets']}
                lost = old_targets - new_targets
                if not discovery:
                    # With every topic known, a restored longer alias can cover
                    # a shorter link. It remains discoverable by the same parser;
                    # actual dialogue display also filters NPC-available topics.
                    overlaps += len(lost & discovered[key])
                    lost -= discovered[key]
                permitted = allowed.get(edits.get(key), set())
                if lost - permitted:
                    errors.append({'configuration': label, 'mode': 'discovery' if discovery else 'display',
                                   'key': key, 'reference': reference, 'plugin': old[1][reference]['plugin'],
                                   'source_body_sha256': hashlib.sha256(old[1][reference]['body']).hexdigest(),
                                   'lost': sorted(lost - permitted), 'gained': sorted(new_targets - old_targets)})
                    unreviewed += len(lost - permitted)
                if key not in edits:
                    assert prior['text'] == current['text'], 'Unreviewed visible text changed'
                reviewed_removals += len(lost & permitted)
                gains += len(new_targets - old_targets)
            report = {'configuration': label, 'mode': 'discovery' if discovery else 'display', 'INFO_checked': len(new[1]),
                      'additional_copies': copies, 'reviewed_translated_INFO': len(edits), 'unreviewed_link_losses': unreviewed,
                      'reviewed_subject_or_prefix_removals': reviewed_removals, 'gained_destinations': gains}
            report['display_overlaps_still_discoverable'] = overlaps
            reports.append(report)
            print(json.dumps(report), flush=True)
    result = {'configurations': reports, 'unreviewed_losses': errors, 'pfp_included': bool(pfp),
              'runner_sha256': hashlib.sha256(runner.read_bytes()).hexdigest(),
              'before_runner_sha256': hashlib.sha256(before_runner.read_bytes()).hexdigest(),
              'scope': 'All configured INFOs, native discovery/display and pinned translation exceptions. NPC SCVR progression is unchanged but still needs gameplay checks.'}
    (candidate / 'reviewed-regional-runtime-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if errors:
        raise ValueError('Unreviewed native link losses; inspect reviewed-regional-runtime-verification.json')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline', 'candidate', 'release', 'core', 'masters', 'before-runner', 'runner'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--pfp', type=Path)
    a = p.parse_args()
    verify(a.baseline, a.candidate, a.release, a.core, a.masters, a.before_runner.resolve(), a.runner.resolve(), a.pfp)
