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
        elif tag == b'INFO' and kind in (0, 2, 3, 4) and b'NAME' in data:
            # Voice (1) belongs to spoken sound subtitles; the same clickable
            # Topic/Journal hyperlink display is not used for voice playback.
            section = {0: 'topic_dialogue', 2: 'greeting', 3: 'persuasion', 4: 'journal'}[kind]
            entries.append({'info': decode(data.get(b'INAM', b'')),
                            'section': section,
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
    dialogue_phrases, journal_phrases = defaultdict(set), defaultdict(set)
    for topic in topics:
        # The NPC dialogue panel seeds only .mrk (or the canonical name as
        # fallback). The journal additionally seeds the canonical name.
        display = keywords.get(topic, topic)
        if HANGUL.search(display):
            dialogue_phrases[display].add(topic)
            journal_phrases[display].add(topic)
        if HANGUL.search(topic):
            journal_phrases[topic].add(topic)
    for phrase, topic in (journal_aliases or {}).items():
        if topic in topics and HANGUL.search(phrase):
            journal_phrases[phrase].add(topic)

    stats, by_section, examples = Counter(), Counter(), defaultdict(list)
    for entry in entries:
        text = entry['text']
        section = entry['section']
        phrases = journal_phrases if section == 'journal' else dialogue_phrases
        explicit = [(m.start(), m.end()) for m in EXPLICIT.finditer(text)]
        for phrase, targets in phrases.items():
            pos = text.find(phrase)
            while pos >= 0:
                end = pos + len(phrase)
                if not any(pos < stop and end > start for start, stop in explicit):
                    category = classify(text, pos, end)
                    if category:
                        stats[(section, phrase, category)] += 1
                        by_section[section] += 1
                        if len(examples[(section, phrase, category)]) < max_samples:
                            examples[(section, phrase, category)].append({
                                'info': entry['info'], 'section': section,
                                'snippet': text[max(0, pos - 30):min(len(text), end + 30)],
                                'targets': sorted(targets)})
                pos = text.find(phrase, pos + 1)
    kinds = Counter(entry['section'] for entry in entries)
    return {
        'topics_loaded': len(topics), 'infos_scanned': len(entries),
        'infos_by_section': dict(kinds),
        'candidate_occurrences': sum(stats.values()),
        'candidate_occurrences_by_section': dict(by_section),
        'counts_by_category': dict(Counter({
            category: sum(n for (_, _, kind), n in stats.items() if kind == category)
            for _, _, category in stats})),
        'candidates': [
            {'section': section, 'keyword': phrase, 'category': category,
             'occurrences': count, 'samples': examples[(section, phrase, category)]}
            for (section, phrase, category), count in stats.most_common()],
        'notes': ('Review candidates, not confirmed links: actual visible topics '
                  'depend on NPC response context or topics recorded in the journal. '
                  'Books and Voice subtitles do not use this automatic link display.')
    }

def selftest():
    topics = {'은', '일', '에이', '마법사 길드', '빛'}
    sample = '싫은 것일 수도 있고 하지-에이의 행방을 물었다. 빛나는 밤. 마법사 길드에서만 물었다. @은#.'
    entries = [{'info': str(i), 'section': section, 'text': sample}
               for i, section in enumerate(('greeting', 'topic_dialogue', 'persuasion', 'journal'))]
    result = collect(topics, entries, {})
    found = {(c['keyword'], c['category']) for c in result['candidates']}
    for expected in [
        ('은', 'inside_hangul_word'), ('일', 'inside_hangul_word'),
        ('에이', 'after_hyphenated_name'),
        ('빛', 'suffix_or_continuation_review'),
        ('마법사 길드', 'suffix_or_continuation_review')
    ]:
        assert expected in found, expected
    assert result['infos_scanned'] == 4
    assert set(result['infos_by_section']) == {'greeting', 'topic_dialogue', 'persuasion', 'journal'}

    # MRK replacements must be respected in NPC responses. The original
    # topic form remains searchable only in journal entries.
    overridden = collect({'마법사 길드'}, entries, {'마법사 길드': '길드'})
    assert all(c['section'] == 'journal' for c in overridden['candidates']
               if c['keyword'] == '마법사 길드')

    # Exercise binary DIAL type dispatch: greeting and persuasion were previously
    # omitted, and Voice must remain outside hyperlink audits.
    import tempfile
    def field(tag, value):
        return struct.pack('<4sI', tag, len(value)) + value
    def record(tag, body):
        return struct.pack('<4sIII', tag, len(body), 0, 0) + body
    binary = b''
    for dial_type in range(5):
        binary += record(b'DIAL', field(b'NAME', b'topic\\0') + field(b'DATA', bytes([dial_type])))
        binary += record(b'INFO', field(b'INAM', str(dial_type).encode())
                         + field(b'NAME', '싫은 것일'.encode('utf-8') + b'\\0'))
    with tempfile.TemporaryDirectory() as tmp:
        esp = Path(tmp) / 'fixture.esp'
        esp.write_bytes(binary)
        _, parsed = load_esp(esp)
    assert {entry['section'] for entry in parsed} == {
        'topic_dialogue', 'greeting', 'persuasion', 'journal'}
    assert 'voice' not in (entry['section'] for entry in parsed)
    print('PASS: Korean collision scanner covers greeting, topic, persuasion and journal')

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
