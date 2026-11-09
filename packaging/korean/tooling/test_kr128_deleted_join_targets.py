"""Exercise the actual release corpus and native parser, including deleted DIALs."""
import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

from build_kr12_7_guild_join_release import records, fields, decode, display
from repair_kr128_deleted_join_targets import STEM, SPECS, ZIP_SHA, patch
from verify_kr5_links import inspect


def corpus(raw):
    states, entries, parent = {}, {}, ''
    for tag, body in records(raw):
        fs = dict(fields(body))
        if tag == b'DIAL':
            parent = decode(fs[b'NAME'])
            states[parent.casefold()] = b'DELE' not in fs
        elif tag == b'INFO':
            key = (parent, decode(fs.get(b'INAM', b'')))
            if key in SPECS:
                if key in entries:
                    raise ValueError('Duplicate INFO')
                entries[key] = decode(fs[b'NAME'])
    return states, entries


def verify(source, runner, rebirth=None):
    assert hashlib.sha256(source.read_bytes()).hexdigest() == ZIP_SHA
    with zipfile.ZipFile(source) as z:
        raw = z.read(STEM + '.esp')
        fixed, changes = patch(raw)
        states, before = corpus(raw)
        _, after = corpus(fixed)
        # Supplying all live topics previously concealed redirects to deleted IDs.
        live = [key for key, active in states.items() if active]
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for ext in ('top', 'mrk', 'cel', 'jrn'):
                member = STEM + '.' + ext
                (folder / ('Morrowind_Korean_ReTranslation.' + ext)).write_bytes(
                    z.read(member) if member in z.namelist() else b'')
            b = inspect(runner, folder, [(str(i), before[k]) for i, k in enumerate(SPECS)], live, True, discovery=True)
            a = inspect(runner, folder, [(str(i), after[k]) for i, k in enumerate(SPECS)], live, True, discovery=True)
    cases = []
    for i, (key, (target, deleted)) in enumerate(SPECS.items()):
        old = b[str(i)]['targets']
        new = a[str(i)]['targets']
        assert deleted.casefold() not in live and target.casefold() in live
        assert target.casefold() not in {s.casefold() for s in old}
        assert target.casefold() in {s.casefold() for s in new}
        assert set(new) == set(old) | {target}
        assert display(a[str(i)]['text']) == display(b[str(i)]['text'])
        cases.append(dict(info=key[1], before_targets=old, after_targets=new))
    if rebirth:
        assert hashlib.sha256(rebirth.read_bytes()).hexdigest() == '6190df64064a40e69772f2c65917128ff3a8de9317ae72dd740ac611919fdd62'
        with zipfile.ZipFile(rebirth) as z:
            for member in ('Data Files/Morrowind Rebirth [Main].ESP',
                           'Alternate Version/Morrowind Rebirth [Main].ESP'):
                mod_states, mod_entries = corpus(z.read(member))
                # Both variants inherit the fixed Eydis INFO; neither deletes its target.
                assert ('전사 길드', '2435795662798020478') not in mod_entries
                assert mod_states.get('전사 길드에 가입', True)
    try:
        patch(fixed)
    except ValueError:
        pass
    else:
        raise AssertionError('Already-repaired input must fail closed')
    return dict(native_parser_passed=len(cases), cases=cases,
                rebirth_variants_checked=2 if rebirth else 0,
                visible_text_unchanged=True, gameplay_tested=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--runner', type=Path, required=True)
    p.add_argument('--rebirth', type=Path)
    p.add_argument('--report', type=Path, required=True)
    a = p.parse_args()
    report = verify(a.source, a.runner.resolve(), a.rebirth)
    a.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
