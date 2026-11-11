"""Independently check every changed regional subrecord and unchanged ZIP entry."""
import argparse
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path

from audit_cross_mod_topic_gaps import record_chunks, subs
from repair_reviewed_regional_display import MANIFEST, module_for, parent_key, row_key


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def check_plugin(before, after, patches):
    old, new = list(record_chunks(before)), list(record_chunks(after))
    assert len(old) == len(new), 'Record count changed'
    expected = {row_key(r): r for r in patches}
    changed, parent, applied = Counter(), '', Counter()
    old_pos, new_pos = 0, 0
    for index, ((ot, ob), (nt, nb)) in enumerate(zip(old, new)):
        assert ot == nt, ('Record type changed', index)
        # Record flags and unknown header bytes must remain identical.
        assert before[old_pos + 8:old_pos + 16] == after[new_pos + 8:new_pos + 16]
        old_pos += len(ob) + 16
        new_pos += len(nb) + 16
        of, nf = list(subs(ob)), list(subs(nb))
        assert [t for t, v in of] == [t for t, v in nf], ('Field order changed', index)
        values = dict(of)
        if ot == b'DIAL':
            parent = values[b'NAME'].split(b'\0', 1)[0].decode('utf-8')
        rid = values.get(b'INAM' if ot == b'INFO' else b'NAME', b'').split(b'\0', 1)[0].decode('utf-8', errors='replace')
        ordinal = Counter()
        for (field, ov), (_, nv) in zip(of, nf):
            key = ot.decode(), rid.casefold(), parent_key(parent) if ot == b'INFO' else '', field.decode(), ordinal[field]
            ordinal[field] += 1
            patch = expected.get(key)
            if ov == nv:
                assert not patch, ('Reviewed field was not applied', key)
                continue
            assert patch, ('Unreviewed field changed', index, key)
            assert sha(ov) == patch['source_raw_sha256'], ('Source drift', key)
            if ot == b'FACT':
                assert len(ov) == len(nv) == 32
                assert nv == (patch['target'].encode('utf-8') + b'\0').ljust(32, b'\0')
            else:
                suffix = ov[len(ov.rstrip(b'\0')):]
                assert nv == patch['target'].encode('utf-8') + suffix, ('Target differs', key)
            changed[ot.decode() + '.' + field.decode()] += 1
            applied[key] += 1
    return {'records_checked': len(old), 'changed_fields': dict(changed),
            'logical_fields': len(applied), 'physical_fields': sum(applied.values()),
            'other_fields_changed': 0, 'headers_or_order_changed': 0}, applied


def verify(baseline, candidate, manifest=MANIFEST):
    review = json.loads(manifest.read_text(encoding='utf-8'))
    reports, applied = {}, set()
    for path in sorted(baseline.glob('*.zip')):
        changed_plugins, entries = {}, 0
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(candidate / path.name) as dst:
            assert src.namelist() == dst.namelist(), 'ZIP member list/order changed'
            assert dst.testzip() is None, 'ZIP CRC failure'
            for name in src.namelist():
                before, after = src.read(name), dst.read(name)
                module = module_for(name) if Path(name).suffix.lower() in ('.esm', '.esp') else None
                entries += 1
                if not module:
                    aliases = review.get('topic_aliases', {}).get(module_for(name), {}) if Path(name).suffix.lower() == '.top' else {}
                    if aliases:
                        assert after.startswith(before), 'Existing TOP bytes changed'
                        assert after[len(before):] == ''.join(k + '\t' + v + '\r\n' for k, v in aliases.items()).encode('utf-8'), 'Unexpected TOP additions'
                    else:
                        assert before == after, ('Unrelated ZIP entry changed', path.name, name)
                    continue
                rows = [r for r in review['rows'] if r.get('target') and r['module'] == module]
                report, seen = check_plugin(before, after, rows)
                applied.update((module, *k) for k in seen)
                changed_plugins[name] = report
        reports[path.name] = {'zip_entries_checked': entries, 'plugins': changed_plugins,
                              'baseline_sha256': sha(path.read_bytes()),
                              'candidate_sha256': sha((candidate / path.name).read_bytes())}
    expected = {(r['module'], *row_key(r)) for r in review['rows'] if r.get('target')}
    assert expected == applied, ('Review coverage mismatch', expected - applied, applied - expected)
    result = {'reviewed_fields': len(expected), 'archives': reports,
              'scope': 'Full physical record and ZIP payload comparison. Does not replace semantic or gameplay review.'}
    (candidate / 'display-physical-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--candidate', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(verify(a.baseline, a.candidate), ensure_ascii=False, indent=2))
