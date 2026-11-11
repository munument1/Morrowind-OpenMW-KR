"""Static, local-only safety tests for the KR13 manual Nexus workflow.

Run with: python -B packaging/korean/tooling/test_publish_kr13_nexus_workflow.py -v
No network, GitHub or Nexus credentials are required.
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest
from package_kr13_mod_overwrites import SPECS

try:
    import yaml
except ImportError:
    yaml = None


PATH = Path(__file__).resolve().parents[3] / '.github/workflows/publish-kr13-nexus.yml'
ACTION = 'Nexus-Mods/upload-action@c96019556046053aa26044b44396cd38929daf23'


def inline_python(text: str) -> str:
    found = re.findall(r"(?ms)^python3 - <<'PY'\n(.*?)^PY$", text)
    if len(found) != 1:
        raise AssertionError(f'Expected exactly one embedded Python program, got {len(found)}')
    compile(found[0], '<workflow inline Python>', 'exec')
    return found[0]


@unittest.skipIf(yaml is None, 'PyYAML not installed for optional static validation')
class NexusKR13WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = PATH.read_text(encoding='utf-8')
        cls.yml = yaml.safe_load(cls.source)
        cls.events = cls.yml.get('on', cls.yml.get(True))
        cls.preflight = cls.yml['jobs']['preflight']
        cls.upload = cls.yml['jobs']['upload-owned']

    def test_manual_only_and_safe_defaults(self):
        self.assertEqual(set(self.events), {'workflow_dispatch'})
        inputs = self.events['workflow_dispatch']['inputs']
        self.assertIs(inputs['dry_run']['default'], True)
        self.assertIs(inputs['publish_changelog']['default'], False)
        self.assertEqual(self.yml['permissions'], {'contents': 'read'})
        self.assertEqual(self.yml['concurrency']['group'], 'nexus-publish')
        self.assertIs(self.yml['concurrency']['cancel-in-progress'], False)
        self.assertEqual(self.upload['if'], '${{ inputs.dry_run == false }}')
        self.assertEqual(self.upload['needs'], 'preflight')

    def test_exact_five_owned_groups_excluding_core_and_android(self):
        matrix = self.upload['strategy']['matrix']['include']
        observed = [(x['mod_id'], x['canonical'], x['group'], x['zip'], x['version'])
                    for x in matrix]
        expected = [
            (60844, '429496790444', '8296179', 'TR_Mainland-kr0.4.1.zip', '26.11.2-kr0.4.1'),
            (60845, '429496790445', '8296167', 'Tamriel_Data-kr0.4.1.zip', '26.08-kr0.4.1'),
            (60846, '429496790446', '8296161', 'Cyr_Main-kr0.4.1.zip', '26.09a-kr0.4.1'),
            (60847, '429496790447', '8296155', 'Sky_Main-kr0.3.1.zip', '26.09a-kr0.3.1'),
            (60805, '429496790405', '8296377', 'Rebirth7.2-Cyr_Sky_Compatibility-kr0.4.1.zip', '7.2-kr0.4.1'),
        ]
        self.assertEqual(observed, expected)
        self.assertEqual(self.upload['strategy']['max-parallel'], 2)
        self.assertEqual(len(matrix), 5)
        self.assertNotIn(60496, {x['mod_id'] for x in matrix})
        self.assertEqual(matrix[-1]['category'], 'optional')
        self.assertIs(matrix[-1]['primary'], False)
        self.assertIs(matrix[-1]['update_main'], False)

    def test_preflight_specs_match_upload_matrix(self):
        program = inline_python(next(s['run'] for s in self.preflight['steps'] if 'run' in s))
        self.assertIn('from package_kr13_mod_overwrites import SPECS,verify_folder,PLAN', program)
        specs = [(name, mod, str((100 << 32) + mod), group, version)
                 for _, name, mod, group, version, _ in SPECS]
        matrix = self.upload['strategy']['matrix']['include']
        self.assertEqual(len(specs), len(matrix))
        for item, row in zip(specs, matrix):
            self.assertEqual(item, (row['zip'], row['mod_id'], row['canonical'], row['group'], row['version']))

    def test_inline_python_and_pinned_upload_action(self):
        for job in (self.preflight, self.upload):
            for step in job['steps']:
                if "python3 - <<'PY'" in step.get('run', ''):
                    inline_python(step['run'])
        matches = [x for x in self.upload['steps']
                   if x.get('uses', '').startswith('Nexus-Mods/')]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['uses'], ACTION)
        self.assertEqual(matches[0]['if'], "steps.nexus.outputs.upload == 'true'")
        self.assertEqual(matches[0]['with']['file_id'], '${{ matrix.group }}')

    def test_full_plugin_preflight_and_owner_checks(self):
        program = inline_python(next(s['run'] for s in self.preflight['steps'] if 'run' in s))
        for phrase in (
            'verify_folder(ROOT)', "'.sha256'", 'asset_shas=',
            'GitHub digest mismatch', 'asset_sizes=',
            '/v1/users/validate.json', '/v3/games/morrowind/mods/',
            '/v3/mod-files/', 'member_id', 'is_active',
        ):
            self.assertIn(phrase, program)
        self.assertIn('fromJSON(needs.preflight.outputs.asset_shas)[matrix.zip]', self.source)
        self.assertIn('sha256sum --check --status', self.source)
        self.assertIn('unzip -tq', self.source)
        self.assertIn('NEXUS_KR13_READBACK_PASS', self.source)
        self.assertIn("actual[0]['size_in_bytes']", self.source)

    def test_no_automatic_publish_and_opt_in_changelog(self):
        changelog = next(x for x in self.upload['steps']
                         if x.get('name') == 'Optionally create a missing Nexus version changelog')
        self.assertEqual(changelog['if'], '${{ inputs.publish_changelog == true }}')
        self.assertNotIn('push:\n', self.source)
        self.assertNotIn('schedule:\n', self.source)
        self.assertNotIn('release:\n', self.source)
        self.assertNotIn("'8257539'", str(self.upload['strategy']['matrix']['include']))


if __name__ == '__main__':
    unittest.main()
