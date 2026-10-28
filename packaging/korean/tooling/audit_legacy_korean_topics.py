"""Read-only save/content audit using the actual C++ legacy topic decoder.

This checks ID/INFO resolution, not NPC dialogue conditions or rendered UI.
No save, content, or configuration file is written.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from build_kr5_data import records, fields


def key(text):
    # OpenMW's topic ID comparison folds ASCII, not Unicode legacy glyphs.
    return text.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))


def content_text(raw):
    raw = raw.split(b'\0', 1)[0]
    try:
        text = raw.decode('utf-8')
        if any(0xac00 <= ord(c) <= 0xd7a3 or 0x1100 <= ord(c) <= 0x11ff
               or 0x3130 <= ord(c) <= 0x318f for c in text):
            return text
    except UnicodeDecodeError:
        pass
    return raw.decode('cp1252', errors='replace')


def ref(raw, version):
    if version <= 23:
        return raw.rstrip(b'\0').decode('utf-8')
    if not raw or raw[0] == 0:
        return None
    if raw[0] == 2:
        return raw[1:].decode('utf-8')
    if raw[0] == 1:
        size, = struct.unpack_from('<I', raw, 1)
        if len(raw) != 5 + size:
            raise ValueError('Invalid sized string RefId')
        return raw[5:].decode('utf-8')
    return None  # Non-string IDs must never be decoded as legacy text.


def audit(save, content, decoder):
    paths = [save, *content]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    topics = {}
    current = None
    for path in content:
        for tag, body, _, _ in records(path.read_bytes()):
            data = dict(fields(body))
            if tag == b'DIAL':
                current = key(content_text(data[b'NAME']))
                if b'DELE' in data:
                    topics.pop(current, None)
                    current = None
                    continue
                topic = topics.setdefault(current, {'infos': set()})
                topic['type'] = data.get(b'DATA', b'\xff')[0]
            elif tag == b'INFO' and current is not None:
                info = key(content_text(data[b'INAM']))
                if b'DELE' in data:
                    topics[current]['infos'].discard(info)
                else:
                    topics[current]['infos'].add(info)

    known, responses = [], []
    version = 0
    for tag, body, _, _ in records(save.read_bytes()):
        pairs = list(fields(body))
        data = dict(pairs)
        if tag == b'TES3':
            version, = struct.unpack('<I', data.get(b'FORM', b'\0' * 4))
        elif tag == b'DIAS':
            known.extend(ref(raw, version) for name, raw in pairs if name == b'TOPI')
        elif tag == b'JOUR' and data.get(b'JETY') == b'\1\0\0\0':
            responses.append((ref(data[b'YETO'], version), ref(data[b'YEIN'], version)))

    values = sorted({x for x in [*known, *(t for t, _ in responses)] if x is not None})
    if any('\n' in x or '\r' in x for x in values):
        raise ValueError('Line separators in topic IDs are unsupported by audit adapter')
    result = subprocess.run([str(decoder)], input=('\n'.join(values) + ('\n' if values else '')).encode('utf-8'),
                            stdout=subprocess.PIPE, check=True)
    decoded = result.stdout.decode('utf-8').splitlines()
    if len(values) != len(decoded):
        raise ValueError('Decoder result count mismatch')
    mapping = dict(zip(values, decoded))

    def resolve(original, info=None):
        if original is None:
            return 'non_string'
        existing = topics.get(key(original))
        if existing and (info is None or key(info) in existing['infos']):
            return 'existing'
        candidate = mapping[original]
        if not candidate:
            return 'unsupported'
        target = topics.get(key(candidate))
        if not target or target['type'] != 0:
            return 'target_missing'
        if info is not None and key(info) not in target['infos']:
            return 'info_missing'
        return 'recoverable'

    report = {'save': save.name, 'format': version,
              'known_topics': dict(Counter(resolve(x) for x in known)),
              'journal_topic_responses': dict(Counter(resolve(t, i) for t, i in responses)),
              'input_sha256': hashes}
    if any(hashlib.sha256(p.read_bytes()).hexdigest() != hashes[str(p)] for p in paths):
        raise ValueError('Input changed during read-only audit')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--save', type=Path, required=True)
    parser.add_argument('--content', type=Path, nargs='+', required=True, help='Files in load order')
    parser.add_argument('--decoder', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.save, args.content, args.decoder.resolve()), ensure_ascii=False, indent=2))
