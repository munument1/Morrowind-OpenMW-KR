"""Offline checks for the eight-package manual Nexus publication workflow."""
from pathlib import Path
import json
import re
import unittest
from unittest.mock import patch
import os
import tempfile

import publish_issue71_nexus as nexus

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parents[3]
ACTION = 'Nexus-Mods/upload-action@c96019556046053aa26044b44396cd38929daf23'


@unittest.skipIf(yaml is None, 'PyYAML required for workflow validation')
class NexusKR13WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / '.github/workflows/publish-kr13-nexus.yml').read_text(encoding='utf-8')
        cls.yml = yaml.safe_load(cls.source)
        cls.events = cls.yml.get('on', cls.yml.get(True))
        cls.preflight = cls.yml['jobs']['preflight']
        cls.upload = cls.yml['jobs']['upload-owned']
        cls.pins = json.loads(nexus.PINS.read_text(encoding='utf-8'))['files']

    def test_manual_only_and_read_only_permissions(self):
        self.assertEqual(set(self.events), {'workflow_dispatch'})
        self.assertIs(self.events['workflow_dispatch']['inputs']['dry_run']['default'], True)
        self.assertEqual(self.yml['permissions'], {'contents': 'read', 'actions': 'read'})
        self.assertEqual(self.yml['concurrency'], {'group': 'nexus-publish', 'cancel-in-progress': False})
        self.assertEqual(self.upload['if'], '${{ inputs.dry_run == false }}')
        self.assertEqual(self.upload['needs'], 'preflight')

    def test_exact_eight_groups_exclude_android(self):
        expected = {(60496, '8110335'), (60844, '8296179'), (60845, '8296167'),
                    (60846, '8296161'), (60847, '8296155'), (60805, '8296377'),
                    (60805, '8257641'), (60826, '8280147')}
        self.assertEqual(nexus.TARGETS, expected)
        self.assertEqual({(r['mod_id'], r['group']) for r in self.pins}, expected)
        self.assertEqual(len(self.pins), 8)
        self.assertNotIn(nexus.ANDROID_GROUP, {r['group'] for r in self.pins})
        self.assertTrue(all(r['uid'] == str((100 << 32) + r['mod_id']) for r in self.pins))

    def test_matrix_and_artifact_names_cover_exact_approved_assets(self):
        matrix = self.upload['strategy']['matrix']['include']
        self.assertEqual({(r['mod'], r['asset']) for r in matrix},
                         {(r['mod_id'], r['asset']) for r in self.pins})
        self.assertEqual(len(matrix), 8)
        self.assertEqual(len({str(r['key']) for r in matrix}), 8)
        artifacts = {r['with']['name']: r['with']['path'] for r in self.preflight['steps']
                     if r.get('uses', '').startswith('actions/upload-artifact')}
        for row in matrix:
            self.assertEqual(artifacts['issue71-' + str(row['key'])], 'dist/' + row['asset'])
        self.assertEqual(self.upload['strategy']['max-parallel'], 2)

    def test_verified_gate_is_the_only_upload_target_source(self):
        step = next(s for s in self.upload['steps'] if s.get('uses', '').startswith('Nexus-Mods/'))
        self.assertEqual(step['uses'], ACTION)
        self.assertEqual(step['if'], "steps.gate.outputs.upload == 'true'")
        for key, output in (('file_id', 'group'), ('version', 'version'), ('category', 'category'),
                            ('primary_mod_manager_download', 'primary'), ('update_mod_version', 'primary')):
            self.assertEqual(step['with'][key], '${{ steps.gate.outputs.' + output + ' }}')
        gate = next(s for s in self.upload['steps'] if s.get('id') == 'gate')
        self.assertIn('publish_issue71_nexus.py gate', gate['run'])
        self.assertTrue(any('publish_issue71_nexus.py readback' in s.get('run', '') for s in self.upload['steps']))

    def test_rebirth_main_and_optional_flags_are_independent(self):
        for group, category, primary in (('8257641', 'main', 'true'), ('8296377', 'optional', 'false')):
            row = next(r for r in self.pins if r['group'] == group)
            with tempfile.TemporaryDirectory() as folder:
                out = Path(folder) / 'outputs'
                with patch.object(nexus, 'check_archive', return_value=row), \
                     patch.object(nexus, 'target', return_value=[]), \
                     patch.dict(os.environ, {'GITHUB_OUTPUT': str(out)}):
                    nexus.run('gate', Path(folder), row['asset'])
                values = dict(line.split('=', 1) for line in out.read_text().splitlines())
                self.assertEqual(values['group'], group)
                self.assertEqual(values['category'], category)
                self.assertEqual(values['primary'], primary)

    def test_final_readback_requires_uploads_and_checks_android(self):
        final = self.yml['jobs']['final-readback']
        self.assertEqual(set(final['needs']), {'preflight', 'upload-owned'})
        self.assertEqual(final['if'], '${{ inputs.dry_run == false }}')
        self.assertTrue(any('publish_issue71_nexus.py final' in s.get('run', '') for s in final['steps']))
        self.assertIn('publish_issue71_nexus.py preflight --armed', self.source)

    def test_all_embedded_python_compiles(self):
        programs = []
        for job in self.yml['jobs'].values():
            for step in job.get('steps', []):
                programs += re.findall(r"(?ms)^python3 - <<'PY'\n(.*?)^PY$", step.get('run', ''))
        self.assertEqual(len(programs), 2)
        for program in programs:
            compile(program, '<workflow Python>', 'exec')


if __name__ == '__main__':
    unittest.main()
