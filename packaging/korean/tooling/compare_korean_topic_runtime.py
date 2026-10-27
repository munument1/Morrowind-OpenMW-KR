"""Compare OpenMW implicit display hyperlinks on the real KR8 translation corpus.

Uses verify-journal-links.cpp compiled with the baseline and the proposed
keywordsearch.cpp. Seeds every Topic as a conservative upper bound; game NPCs
only display currently available topics and journals only recorded topics.
"""
from collections import Counter, defaultdict
import argparse
import json
from pathlib import Path

from audit_topic_collisions import load_esp
from verify_kr5_links import inspect


def compare(baseline, proposed, mod):
    topics, entries = load_esp(mod / 'Morrowind_Korean_ReTranslation.esp')
    names = sorted(topics)
    groups = {'npc': [], 'journal': []}
    context = {}
    for index, entry in enumerate(entries):
        group = 'journal' if entry['section'] == 'journal' else 'npc'
        key = f"{group}:{index}"
        groups[group].append((key, entry['text']))
        context[key] = entry

    totals = Counter()
    by_section = defaultdict(Counter)
    samples = {'removed': [], 'added': []}
    for group, texts in groups.items():
        before = inspect(baseline, mod, texts, names, group == 'journal')
        after = inspect(proposed, mod, texts, names, group == 'journal')
        for key, body in texts:
            old, new = before[key], after[key]
            assert old['text'] == new['text'], ('display text changed', key)
            oldlinks, newlinks = Counter(old['targets']), Counter(new['targets'])
            removed = list((oldlinks - newlinks).elements())
            added = list((newlinks - oldlinks).elements())
            section = context[key]['section']
            row = by_section[section]
            row['infos'] += 1
            row['baseline_links'] += sum(oldlinks.values())
            row['proposed_links'] += sum(newlinks.values())
            row['removed_links'] += len(removed)
            row['added_links'] += len(added)
            if removed or added:
                row['changed_infos'] += 1
            for kind, matches in [('removed', removed), ('added', added)]:
                if matches and len(samples[kind]) < 80:
                    samples[kind].append({
                        'section': section,
                        'info': context[key]['info'],
                        'topics': matches[:16],
                        'text_excerpt': body[:220],
                    })
    for row in by_section.values():
        for name, n in row.items():
            totals[name] += n
    report = {
        'all_topics_seeded': len(names),
        'scope': ('Worst-case display fixture: all KR8 translated DIAL topics seeded. '
                  'Actual NPC dialogue and journal knowledge gates reduce visible links. '
                  'This compares the real OpenMW parser and real release sidecars; '
                  'not an in-game save-state test.'),
        'totals': dict(totals),
        'by_section': {section: dict(stats) for section, stats in by_section.items()},
        'samples': samples,
    }
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline', type=Path, required=True)
    ap.add_argument('--proposed', type=Path, required=True)
    ap.add_argument('--mod', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    report = compare(args.baseline.resolve(), args.proposed.resolve(),
                     args.mod.resolve())
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf-8')
    print('RUNTIME_COMPARISON_TOTALS='
          + json.dumps(report['totals'], ensure_ascii=False))
    print('RUNTIME_COMPARISON_BY_SECTION='
          + json.dumps(report['by_section'], ensure_ascii=False))
    for kind in ('added', 'removed'):
        print('RUNTIME_COMPARISON_' + kind.upper() + '_SAMPLES='
              + json.dumps(report['samples'][kind][:15], ensure_ascii=False))


if __name__ == '__main__':
    main()
