"""Rebuild reviewed regional fields, shared topics and matching Rebirth sidecars."""
import argparse
import json
import tempfile
from pathlib import Path

from repair_reviewed_regional_display import ROOT, build as display
from repair_shared_core_topics import build as shared
from repair_rebirth_sidecar_names import build as sidecars
from repair_regional_core_aliases import build as aliases
from repair_core_topic_aliases import build as core_aliases
from verify_reviewed_regional_display import verify as physical

MAPPING = ROOT / 'translations/openmw-kr/shared_core_topic_mapping_20261111.json'


def build(source, output, core):
    if output.exists():
        raise FileExistsError(output)
    with tempfile.TemporaryDirectory(prefix='regional-fixes-') as temp:
        folder = Path(temp)
        stages = [folder / n for n in ('display', 'shared', 'sidecars')]
        reports = {'display': display(source, stages[0])}
        # The display builder reconstructs the pinned eight-topic baseline.
        from repair_shared_default_topics import build as defaults
        baseline = folder / 'baseline'
        defaults(source, baseline)
        reports['display_physical'] = physical(baseline, stages[0])
        reports['shared'] = shared(stages[0], stages[1], core, MAPPING)
        reports['sidecars'] = sidecars(stages[1], stages[2])
        reports['aliases'] = aliases(stages[2], output, MAPPING)
        reports['core_aliases'] = core_aliases(core, output / 'core', MAPPING)
    (output / 'combined-build-verification.json').write_text(json.dumps(reports, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return reports


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'output', 'core'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    report = build(a.source, a.output, a.core)
    print('Reviewed display fields:', report['display']['reviewed_fields'])
