#!/usr/bin/env python3
"""Read-only English master cross-check for KR12.3.1 issue #42 candidates.

Run locally with legally installed Morrowind.esm/Tribunal.esm/Bloodmoon.esm.
This produces evidence, NOT a claim that a topic is playable or unlearnable.
Never rewrites masters, Korean data, sidecars or saves.
"""
import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from audit_kr12_fighters_topic_candidates import chunks, dialogue, package
from audit_issue42_reported_candidates import EXPECTED_ESP_SHA

ADDTOPIC = re.compile(r'\baddtopic\s+(?:"([^"]+)"|\'([^\']+)\'|([^\s;]+))', re.I)


def string(data):
    return data.rstrip(b'\0').decode('cp1252', errors='replace')


def parse_original_masters(paths):
    """Read English only; later masters override earlier INFO by INAM."""
    orig_infos = {}
    orig_topics = set()
    script_refs = defaultdict(list)
    file_hashes = {}
    for path in paths:
        data = path.read_bytes()
        file_hashes[path.name] = hashlib.sha256(data).hexdigest()
        parent = None
        kind = None
        for tag, blob in chunks(data, 16):
            if tag not in (b'DIAL', b'INFO', b'SCPT'):
                continue
            fld = dict(chunks(blob, 8))
            if tag == b'DIAL':
                parent = string(fld.get(b'NAME', b''))
                kind = fld.get(b'DATA', b'\xff')[0]
                if kind == 0 and b'DELE' not in fld:
                    orig_topics.add(parent.casefold())
            if tag == b'INFO':
                iid = string(fld.get(b'INAM', b''))
                if not iid:
                    continue
                if b'DELE' in fld:
                    orig_infos.pop(iid, None)
                    continue
                response = string(fld.get(b'NAME', b''))
                orig_infos[iid] = {
                    'INAM': iid, 'english_parent': parent,
                    'kind': kind, 'english_text': response,
                    'english_actor': string(fld.get(b'ONAM', b'')),
                    'source_file': path.name,
                    'SCVR_present': b'SCVR' in fld,
                }
                script = string(fld.get(b'BNAM', b''))
            elif tag == b'SCPT':
                script = string(fld.get(b'SCTX', b''))
            else:
                continue
            for m in ADDTOPIC.finditer(script):
                name = next(x for x in m.groups() if x is not None)
                script_refs[name.casefold()].append({
                    'source_file': path.name,
                    'record': 'SCPT' if tag == b'SCPT' else 'INFO.BNAM',
                    'INAM': iid if tag == b'INFO' else None,
                    'argument': name,
                })
    return orig_infos, orig_topics, script_refs, file_hashes


def topic_mapping(korean_infos, original_infos, min_support=1):
    """Safe vote by identical INFO ID, no positional or name heuristics."""
    votes = defaultdict(Counter)
    for row in korean_infos:
        english = original_infos.get(row['info'])
        if english is None or row['kind'] != english['kind'] or english['kind'] != 0:
            continue
        if row['parent'] and english['english_parent']:
            votes[row['parent']][english['english_parent']] += 1
    answer = {}
    for ko, count in votes.items():
        ranking = count.most_common()
        answer[ko] = {
            'english_topic': ranking[0][0] if len(ranking) == 1 and ranking[0][1] >= min_support else None,
            'matched_INFO_count': sum(count.values()),
            'candidates': dict(count),
            'mapping_ambiguous': len(count) != 1,
        }
    return answer


def literal_english(text, topic):
    # Match actual words, not a substring of another Latin word.
    if not text or not topic:
        return False
    visible = re.sub(r'@([^@#]+)#', lambda m: m.group(1), text)
    return bool(re.search(r'(?<![A-Za-z0-9])' + re.escape(topic) + r'(?![A-Za-z0-9])',
                          visible, flags=re.I))


def compare(released_esp, report, originals):
    source_sha = hashlib.sha256(released_esp).hexdigest()
    if source_sha != EXPECTED_ESP_SHA or report.get('source_esp_sha256') != source_sha:
        raise ValueError('KR12.3.1 source ESP and existing issue #42 report must match')
    en_infos, en_topics, addtopic_refs, provenance = parse_original_masters(originals)
    ko_topics, ko_infos = dialogue(released_esp)
    ko2en = topic_mapping(ko_infos, en_infos)
    matched = sum(1 for row in ko_infos if row['info'] in en_infos)
    checked_links = []
    for row in report['link_candidates']:
        mapping = ko2en.get(row['topic'])
        en_topic = mapping and mapping['english_topic']
        same = en_infos.get(row['INFO'])
        en_text = same['english_text'] if same else None
        found = literal_english(en_text, en_topic) if en_topic and same else None
        checked_links.append({
            'topic_ko': row['topic'], 'INFO': row['INFO'], 'reported_type': row['reported_type'],
            'english_INFO_found': same is not None,
            'english_parent_same_INFO': same['english_parent'] if same else None,
            'english_topic_mapping': mapping,
            'english_keyword_visible_in_same_INFO': found,
            'english_response': en_text,
            'SCVR_present_in_original_INFO': same['SCVR_present'] if same else None,
            'assessment': ('no_identical_original_INFO' if same is None
                           else 'ambiguous_topic_mapping' if not en_topic
                           else 'english_literal_present_not_gameplay_proof' if found
                           else 'english_literal_absent_needs_context_or_script'),
        })
    topic_cases = []
    for row in report['reported_unlearnable_topics']:
        mapping = ko2en.get(row['topic'])
        en_topic = mapping and mapping['english_topic']
        refs = addtopic_refs.get(en_topic.casefold(), []) if en_topic else []
        topic_cases.append({
            'topic_ko': row['topic'], 'reported_class': row['reported_class'],
            'english_topic_mapping': mapping,
            'english_DIAL_in_loaded_masters': en_topic.casefold() in en_topics if en_topic else None,
            'original_master_AddTopic_references': refs,
            'original_AddTopic_reference_count': len(refs),
            'assessment': ('mapping_not_proven' if not en_topic
                           else 'script_reference_not_reachability_proof' if refs
                           else 'no_matching_AddTopic_in_given_masters_not_unlearnable_proof'),
        })
    return {
        'status': 'READ_ONLY_ORIGINAL_ENGLISH_CROSSCHECK_NOT_GAMEPLAY_VERIFIED',
        'kr12_3_1_esp_sha256': source_sha,
        'provided_original_master_sha256': provenance,
        'english_original_INFO_count': len(en_infos),
        'english_original_DIAL_count': len(en_topics),
        'korean_INFO_count': len(ko_infos), 'korean_INFO_with_original_same_ID': matched,
        'korean_topic_crosswalk_count': len(ko2en),
        'unique_topic_crosswalk_count': sum(v['english_topic'] is not None for v in ko2en.values()),
        'reported_link_candidates': checked_links,
        'reported_51_plus_20_topics': topic_cases,
        'link_assessments': dict(Counter(x['assessment'] for x in checked_links)),
        'topic_assessments': dict(Counter(x['assessment'] for x in topic_cases)),
        'limitations': [
            'Crosswalk only from exact matching INFO IDs; non-overrides or generated IDs cannot be safely mapped.',
            'Unmatched, ambiguous or unmentioned English keywords do not by themselves prove a localization bug.',
            'Text presence is not identical to OpenMW KeywordSearch success or quest accessibility.',
            'SCVR/journal progression, actor availability, load order and runtime AddTopic execution not simulated.',
            'This tool does not read the reporter CSV directly; input is an existing source-anchored JSON report.',
        ],
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--zip', required=True, type=Path, help='Original published KR12.3.1 Full ZIP')
    p.add_argument('--report', required=True, type=Path, help='Output from audit_issue42_reported_candidates.py')
    p.add_argument('--original', required=True, type=Path, nargs='+', help='Legally installed English ESMs in Morrowind, Tribunal, Bloodmoon order')
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError('Output must be new; never overwrite reviewed evidence')
    if not all(x.is_file() for x in a.original):
        raise ValueError('Missing original ESM; never substitute copied or synthetic content for real comparison')
    ko_package = package(a.zip)
    report = json.loads(a.report.read_text(encoding='utf-8'))
    result = compare(ko_package['esp'], report, a.original)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ('reported_link_candidates', 'reported_51_plus_20_topics')},
                     ensure_ascii=False, indent=2))
    print('OUTPUT', a.output)


if __name__ == '__main__':
    main()
