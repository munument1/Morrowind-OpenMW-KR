"""Verify approved payloads, display coverage and remaining script literals."""
import argparse
import json
import re
from pathlib import Path
from zipfile import ZipFile

from build_issue71_followup import ROOT, REVIEW, sha, record_chunks, subs, unpack, display_spans, uncomment, DEBUG, KO

PINS = ROOT / 'packaging/korean/releases/ISSUE71-20261116-PAYLOAD-PINS.json'


def check_archive(path, expected):
    with ZipFile(path) as z:
        if z.testzip() is not None or len(z.namelist()) != len(set(n.casefold() for n in z.namelist())):
            raise ValueError('ZIP CRC/duplicate members: ' + path.name)
        allowed = set(expected['payload'])
        if expected['mod_id'] != 60496:
            allowed |= {'README_KO.md', 'INSTALL-MANIFEST.json'}
            meta = json.loads(z.read('INSTALL-MANIFEST.json'))
            if meta['files'] != expected['payload'] or meta['version'] != expected['version']:
                raise ValueError('Installation manifest drift')
        if set(z.namelist()) != allowed:
            raise ValueError('Unexpected/missing package member')
        for name, digest in expected['payload'].items():
            if sha(z.read(name)) != digest:
                raise ValueError('Approved payload differs: ' + name)
            if Path(name).suffix.lower() in ('.esm', '.esp') and not z.read(name).startswith(b'TES3'):
                raise ValueError('Not a complete plugin')
    return {'asset': path.name, 'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size,
            **{key: expected[key] for key in ('mod_id', 'uid', 'group', 'version')}}


def verify(folder):
    pins = json.loads(PINS.read_text(encoding='utf-8'))
    review = json.loads((REVIEW / 'review.json').read_text(encoding='utf-8'))
    verified = [check_archive(folder / row['asset'], row) for row in pins['files']]
    leftovers, modules = [], {}
    for row in pins['files']:
        with ZipFile(folder / row['asset']) as z:
            for member in z.namelist():
                if Path(member).suffix.lower() not in ('.esm', '.esp'):
                    continue
                stem = Path(member).stem.casefold()
                sidecars = {}
                for ext in ('.mrk', '.dsp'):
                    name = next((n for n in z.namelist() if Path(n).stem.casefold() == stem and Path(n).suffix.lower() == ext), None)
                    sidecars[ext] = dict(line.split('\t', 1) for line in z.read(name).decode('utf-8-sig').splitlines() if '\t' in line) if name else {}
                topics = {}
                for tag, body in record_chunks(z.read(member)):
                    if tag not in (b'DIAL', b'INFO', b'SCPT'):
                        continue
                    values = dict(subs(body))
                    if tag == b'DIAL':
                        if values.get(b'DATA', b'\xff')[:1] == b'\0' and b'DELE' not in values:
                            ident = unpack(values.get(b'NAME', b''))
                            topics[ident.casefold()] = ident
                        continue
                    ident = unpack(values.get(b'SCHD', b'')[:32]) if tag == b'SCPT' else unpack(values.get(b'INAM', b''))
                    if tag == b'SCPT' and DEBUG.search(ident):
                        continue
                    raw = values.get(b'SCTX' if tag == b'SCPT' else b'BNAM', b'')
                    try:
                        script = raw.decode('utf-8')
                    except UnicodeDecodeError:
                        # The unchanged core contains a CP1252 comment "naive" with an accented i.
                        if all(not uncomment(line).strip() for line in raw.decode('cp1252').splitlines()):
                            continue
                        raise
                    for _, _, text in display_spans(script):
                        if not re.search('[A-Za-z]', text) or KO.search(text) or text in review['preserved_strings']:
                            continue
                        if re.fullmatch(r'(?:[-+0-9., :]|%[-+0-9.#]*[A-Za-z])+', text) or re.fullmatch('[A-Z]', text):
                            continue
                        leftovers.append({'plugin': member, 'id': ident, 'text': text})
                modules[stem] = (sidecars, topics)
    coverage = {}
    core = 'morrowind_korean_retranslation'
    for label, active in {'regular': [core, 'tamriel_data', 'tr_mainland', 'tr_factions', 'sky_main', 'cyr_main'],
                          'rebirth_compatibility': [core, 'tamriel_data', 'tr_mainland', 'tr_factions',
                              'skyrim home of the nords [for rebirth]', 'project cyrodiil [for rebirth]']}.items():
        maps, topics = {'.dsp': {}, '.mrk': {}}, {}
        for stem in active:
            sidecars, local = modules[stem]
            topics.update(local)
            for ext in maps:
                for key, value in sidecars[ext].items():
                    maps[ext].setdefault(key, value)
        missing = []
        for ident in topics.values():
            caption = maps['.dsp'].get(ident, maps['.mrk'].get(ident, ident))
            if re.search('[A-Za-z]', caption) and not KO.search(caption) and ident not in review['preserved_strings']:
                missing.append(ident)
        coverage[label] = {'normal_topics': len(topics), 'untranslated_captions': sorted(missing)}
    report = {'files': verified, 'topic_coverage': coverage, 'unreviewed_script_literals': leftovers,
              'preserved_language_examples': review['preserved_strings']}
    (folder / 'ISSUE71-DISPLAY-VERIFICATION.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if leftovers or any(row['untranslated_captions'] for row in coverage.values()):
        raise ValueError('Unreviewed display strings remain; see verification JSON')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    result = verify(args.folder)
    print(json.dumps(result['topic_coverage'], ensure_ascii=False))
    print('PASS: approved payloads and display coverage; zero unreviewed script literals')
