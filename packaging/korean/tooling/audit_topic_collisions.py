"""Audit possible Korean topic hyperlinks in translated ESP DIAL/INFO text.

Output includes candidate collisions, not confirmed runtime links (which depend on
topic knowledge, alias files, and gameplay). No ESP modifications are performed.
Usage: python audit_topic_collisions.py --esp /path/translation.esp --output audit.json
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import struct

EXPLICIT = re.compile(r"@[^@#]*#")
HANGUL = re.compile(r"[가-힣]")
JOIN = "-·‐‑–—"

def records(data):
    i = 0
    while i < len(data):
        if i + 16 > len(data):
            raise ValueError("truncated record header")
        tag, size, _, _ = struct.unpack_from('<4sIII', data, i)
        end = i + 16 + size
        if end > len(data):
            raise ValueError("truncated record")
        yield tag, data[i + 16:end]
        i = end

def fields(data):
    i = 0
    while i < len(data):
        if i + 8 > len(data):
            raise ValueError("truncated subrecord header")
        tag, size = struct.unpack_from('<4sI', data, i)
        end = i + 8 + size
        if end > len(data):
            raise ValueError("truncated subrecord")
        yield tag, data[i + 8:end]
        i = end

def decode(raw):
    return raw.rstrip(b'\0').decode('utf-8', errors='replace')

def load_esp(path):
    topics, entries = set(), []
    kind = None
    for tag, body in records(path.read_bytes()):
        data = dict(fields(body))
        if tag == b'DIAL':
            kind = data.get(b'DATA', b'\xff')[0]
            if kind == 0 and b'NAME' in data:
                topics.add(decode(data[b'NAME']))
        elif tag == b'INFO' and kind in (0, 4) and b'NAME' in data:
            entries.append({'info': decode(data.get(b'INAM', b'')),
                            'section': 'dialogue' if kind == 0 else 'journal',
                            'text': decode(data[b'NAME'])})
    return topics, entries

def sidecar(path):
    if not path.exists():
        return {}
    return dict(line.split('\t', 1) for line in path.read_text('utf-8-sig').splitlines()
                if '\t' in line)

def classify(text, start, end):
    before, after = text[:start], text[end:]
    if before and HANGUL.fullmatch(before[-1]):
        return 'inside_hangul_word'
    if len(before) >= 2 and before[-1] in JOIN and HANGUL.fullmatch(before[-2]):
        return 'after_hyphenated_name'
    if len(after) >= 2 and after[0] in JOIN and HANGUL.fullmatch(after[1]):
        return 'before_hyphenated_compound'
    if after and HANGUL.fullmatch(after[0]):
        return 'suffix_or_continuation_review'
    return None

def collect(topics, entries, keywords, journal_aliases=None, max_samples=4):
    aliases = defaultdict(set)
    for topic in topics:
        if HANGUL.search(topic):
            aliases[topic].add(topic)
        keyword = keywords.get(topic, topic)
        if HANGUL.search(keyword):
            aliases[keyword].add(topic)
    for phrase, topic in (journal_aliases or {}).items():
        if topic in topics and HANGUL.search(phrase):
            aliases[phrase].add(topic)

    stats, examples = Counter(), defaultdict(list)
    for entry in entries:
        text = entry['text']
        explicit = [(m.start(), m.end()) for m in EXPLICIT.finditer(text)]
        for phrase, targets in aliases.items():
            pos = text.find(phrase)
            while pos >= 0:
                end = pos + len(phrase)
                if not any(pos < stop and end > start for start, stop in explicit):
                    category = classify(text, pos, end)
                    if category:
                        stats[(phrase, category)] += 1
                        if len(examples[(phrase, category)]) < max_samples:
                            examples[(phrase, category)].append({
                                'info': entry['info'], 'section': entry['section'],
                                'snippet': text[max(0,pos-30):min(len(text),end+30)],
                                'targets': sorted(targets)})
                pos = text.find(phrase, pos + 1)
    return {
        'topics_loaded': len(topics), 'infos_scanned': len(entries),
        'candidate_occurrences': sum(stats.values()),
        'counts_by_category': dict(Counter({category:sum(n for (_, kind),n in stats.items()
                                                           if kind == category)
                                            for _, category in stats})),
        'candidates': [
            {'keyword': phrase, 'category': category,
             'occurrences': count, 'samples': examples[(phrase, category)]}
            for (phrase, category), count in stats.most_common()],
        'notes': 'Candidate collisions, not confirmed hyperlinks. Check actual known topics, synonyms and context.'
    }

def selftest():
    topics = {'은', '일', '에이', '마법사 길드', '빛'}
    entries = [{'info': 'fixture', 'section': 'journal',
                'text': '싫은 것일 수도 있고 하지-에이의 행방을 물었다. 빛나는 밤. 마법사 길드에서만 물었다. @은#.'}]
    result = collect(topics, entries, {})
    found = {(c['keyword'], c['category']) for c in result['candidates']}
    for expected in [
        ('은', 'inside_hangul_word'), ('일', 'inside_hangul_word'),
        ('에이', 'after_hyphenated_name'),
        ('빛', 'suffix_or_continuation_review'),
        ('마법사 길드', 'suffix_or_continuation_review')
    ]:
        assert expected in found, expected
    assert result['infos_scanned'] == 1
    print('PASS: Korean topic collision scanner')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--esp', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        selftest()
        return
    if args.esp is None or args.output is None:
        parser.error('--esp and --output are required unless --self-test is given')
    topics, entries = load_esp(args.esp)
    result = collect(topics, entries, sidecar(args.esp.with_suffix('.mrk')),
                     sidecar(args.esp.with_suffix('.jrn')))
    result['source_file'] = str(args.esp)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), 'utf-8')
    print('Topics:', result['topics_loaded'], 'INFO records:', result['infos_scanned'],
          'candidates:', result['candidate_occurrences'])

if __name__ == '__main__':
    main()
