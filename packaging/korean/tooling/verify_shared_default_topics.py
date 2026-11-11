"""Check shared-topic copies through the actual OpenMW parser in 12 loadouts."""
from __future__ import annotations
import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

from audit_cross_mod_topic_gaps import record_chunks, subs
from repair_shared_default_topics import CORE, CORE_SHA, SOURCES, TOPICS, plugin
from verify_kr5_links import inspect


def decode(raw, encoding='utf-8'):
    try:
        return raw.rstrip(b'\0').decode(encoding)
    except UnicodeDecodeError:
        return raw.rstrip(b'\0').decode('cp1252', errors='replace')


def parse(raw, name, encoding='utf-8', sidecars=None):
    topics, infos = {}, {}
    parent, kind = '', -1
    for tag, body in record_chunks(raw):
        if tag not in (b'DIAL', b'INFO'):
            continue
        fields = dict(subs(body))
        if tag == b'DIAL':
            title = decode(fields[b'NAME'], encoding)
            parent = title.casefold()
            kind = fields.get(b'DATA', b'\xff')[0]
            topics[parent] = {'name': title, 'kind': kind, 'active': b'DELE' not in fields}
        else:
            info = decode(fields.get(b'INAM', b''), encoding)
            infos[parent, info] = {'parent': parent, 'info': info, 'kind': kind,
                                  'active': b'DELE' not in fields, 'body': body, 'plugin': name,
                                  'text': decode(fields.get(b'NAME', b''), encoding)}
    return {'name': name, 'topics': topics, 'infos': infos, 'sidecars': sidecars or {}}


def archive(path):
    result = []
    with zipfile.ZipFile(path) as src:
        for member in src.namelist():
            if Path(member).suffix.lower() not in ('.esp', '.esm'):
                continue
            stem = member.rsplit('.', 1)[0]
            sidecars = {}
            for extension in ('top', 'mrk', 'jrn'):
                found = next((n for n in src.namelist() if n.casefold() == (stem + '.' + extension).casefold()), None)
                if found:
                    sidecars[extension] = src.read(found)
            result.append(parse(src.read(member), member, sidecars=sidecars))
    return result


def merge(plugins):
    topics, infos = {}, {}
    maps = {extension: {} for extension in ('top', 'mrk', 'jrn')}
    for mod in plugins:
        deleted = {key for key, value in mod['topics'].items() if not value['active']}
        infos = {key: value for key, value in infos.items() if key[0] not in deleted}
        for key, value in mod['topics'].items():
            current = dict(value)
            if current['active'] and topics.get(key, {}).get('active'):
                current['name'] = topics[key]['name']
            topics[key] = current
        infos.update(mod['infos'])
        for extension, raw in mod['sidecars'].items():
            encoding = 'utf-8-sig' if raw.startswith(b'\xef\xbb\xbf') else 'cp1252'
            for line in raw.decode(encoding).splitlines():
                if '\t' in line:
                    key, value = line.split('\t', 1)
                    if key and value:
                        maps[extension].setdefault(key, value)
    infos = {key: value for key, value in infos.items()
             if value['active'] and topics.get(key[0], {}).get('active') and value['kind'] in (0, 2, 3, 4)}
    return topics, infos, maps


def native(runner, state):
    topics, infos, maps = state
    keys = list(infos)
    with tempfile.TemporaryDirectory(prefix='shared-topics-') as temp:
        folder = Path(temp)
        for extension, mapping in maps.items():
            (folder / ('Morrowind_Korean_ReTranslation.' + extension)).write_text(
                '\n'.join(key + '\t' + value for key, value in mapping.items()) + '\n', encoding='utf-8-sig')
        found = inspect(runner, folder, [(str(index), infos[key]['text']) for index, key in enumerate(keys)],
                        [value['name'] for value in topics.values() if value['active'] and value['kind'] == 0],
                        False, discovery=True)
    return {key: found[str(index)] for index, key in enumerate(keys)}


def verify(source, candidate, masters, runner, pfp=None):
    for name, expected in {**SOURCES, CORE: CORE_SHA,
                           'Morrowind_Rebirth7.2-kr1.2.zip': '6190df64064a40e69772f2c65917128ff3a8de9317ae72dd740ac611919fdd62'}.items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Release ZIP SHA mismatch: ' + name)
    # Rebuild each plugin in memory so only the specified appended copies can pass.
    for filename in SOURCES:
        with zipfile.ZipFile(source / filename) as old, zipfile.ZipFile(candidate / filename) as new:
            if old.namelist() != new.namelist() or new.testzip():
                raise ValueError('Candidate ZIP structure changed')
            for member in old.namelist():
                before = old.read(member)
                expected = plugin(before)[0] if Path(member).suffix.lower() in ('.esm', '.esp') else before
                if new.read(member) != expected:
                    raise ValueError('Candidate payload differs from guarded build: ' + member)
    official = [parse((masters / name).read_bytes(), name, 'cp1252')
                for name in ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')]
    core = archive(source / CORE)
    before = {name: archive(source / name) for name in SOURCES}
    after = {name: archive(candidate / name) for name in SOURCES}
    td, tr, cyr, sky, compat = SOURCES
    rebirth = archive(source / 'Morrowind_Rebirth7.2-kr1.2.zip')
    main = [mod for mod in rebirth if mod['name'].startswith('Data Files/')]
    alternate = [mod for mod in rebirth if mod['name'].startswith('Alternate')]
    alternate += [mod for mod in main if '[Main]' not in mod['name']]
    purists = []
    if pfp:
        path = pfp / 'Patch for Purists.esm'
        sides = {ext: path.with_suffix('.' + ext).read_bytes() for ext in ('top', 'mrk', 'jrn') if path.with_suffix('.' + ext).exists()}
        purists = [parse(path.read_bytes(), path.name, sidecars=sides)]
    configurations = {
        'core': ([], []), 'core-pfp': ([], purists), 'tamriel-data': ([td], []),
        'tr': ([td, tr], []), 'cyr': ([td, cyr], []), 'sky': ([td, sky], []),
        'all-regions': ([td, tr, cyr, sky], []), 'rebirth-main': ([], main),
        'rebirth-alternate': ([], alternate),
        'all-rebirth-main': ([td, tr, cyr, sky, compat], main),
        'all-rebirth-alternate': ([td, tr, cyr, sky, compat], alternate),
        'all-pfp-rebirth': ([td, tr, cyr, sky, compat], purists + main),
    }
    english = {value: key for key, value in TOPICS.items()}
    reports = []
    for label, (selected, extras) in configurations.items():
        prefix = [mod for mod in extras if mod in purists]
        suffix = [mod for mod in extras if mod not in purists]
        old_state = merge(official + core + prefix + [mod for name in selected for mod in before[name]] + suffix)
        new_state = merge(official + core + prefix + [mod for name in selected for mod in after[name]] + suffix)
        if old_state[0].keys() != new_state[0].keys() or old_state[2] != new_state[2]:
            raise ValueError('Existing topic IDs or sidecar resolution changed')
        old_results, new_results = native(runner, old_state), native(runner, new_state)
        old_rows, new_rows = old_state[1], new_state[1]
        copies, overrides = 0, 0
        for key, row in new_rows.items():
            previous = old_rows.get(key)
            reference = key
            if previous is None or previous['body'] != row['body']:
                if key[0] not in english:
                    raise ValueError('Unrelated INFO changed: ' + str(key))
                reference = (english[key[0]], key[1])
                original = old_rows.get(reference)
                if not original or original['body'] != row['body'] or original['plugin'] != row['plugin']:
                    raise ValueError('Copy is not the original regional response: ' + str(key))
                copies += 1
                overrides += previous is not None
            if old_results[reference] != new_results[key]:
                raise ValueError('Native link/display regression: ' + str(key))
        if not old_rows.keys() <= new_rows.keys():
            raise ValueError('Saved-topic response removed')
        report = {'label': label, 'before_infos': len(old_rows), 'after_infos': len(new_rows),
                  'copied_responses_checked': copies, 'restored_regional_overrides': overrides,
                  'native_link_losses': 0, 'sidecar_changes': 0, 'original_topic_ids_removed': 0}
        reports.append(report)
        print(json.dumps(report), flush=True)
    return {'configurations': reports, 'pfp_included': bool(purists),
            'master_sha256': {name: hashlib.sha256((masters / name).read_bytes()).hexdigest()
                              for name in ('Morrowind.esm', 'Tribunal.esm', 'Bloodmoon.esm')},
            'scope': 'Physical preservation and native keyword parsing; NPC eligibility and gameplay require the separate game test.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--masters', type=Path, required=True)
    parser.add_argument('--runner', type=Path, required=True)
    parser.add_argument('--pfp', type=Path)
    args = parser.parse_args()
    report = verify(args.source, args.candidate, args.masters, args.runner.resolve(), args.pfp)
    (args.candidate / 'native-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
