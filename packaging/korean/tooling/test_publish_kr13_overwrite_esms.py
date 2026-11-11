"""Static, network-free tests for manual KR13 overwritten-ESM Nexus publishing."""
from pathlib import Path
import re
import unittest

try:
    import yaml
except ImportError:
    yaml=None

WORKFLOW=Path(__file__).resolve().parents[3]/'.github/workflows/publish-kr13-overwrite-esm-nexus.yml'
ACTION='Nexus-Mods/upload-action@c96019556046053aa26044b44396cd38929daf23'

@unittest.skipIf(yaml is None,"PyYAML optional test dependency is unavailable")
class OverwriteESMNexusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=WORKFLOW.read_text('utf8')
        cls.yml=yaml.safe_load(cls.raw)
        cls.trigger=cls.yml.get('on',cls.yml.get(True))
        cls.job=cls.yml['jobs']['publish-owned']
        cls.matrix=cls.job['strategy']['matrix']['include']
        cls.steps=cls.job['steps']
    def test_manual_dispatch_and_safe_defaults(self):
        self.assertEqual(set(self.trigger),{'workflow_dispatch'})
        controls=self.trigger['workflow_dispatch']['inputs']
        self.assertIs(controls['dry_run']['default'],True)
        self.assertIs(controls['publish_rights_confirmed']['default'],False)
        self.assertEqual(self.yml['permissions'],{'contents':'read'})
        self.assertFalse(self.yml['concurrency']['cancel-in-progress'])
        self.assertEqual(self.job['strategy']['max-parallel'],2)
        guard=next(s for s in self.steps if s['name']=='Block unattended publishing')
        self.assertIn('publish_rights_confirmed != true',guard['if'])
    def test_targets_exact_six_existing_owned_groups(self):
        self.assertEqual(len(self.matrix),6)
        actual=[(int(e['mod_id']),str(e['canonical']),str(e['group']),e['zip'],e['version']) for e in self.matrix]
        expected=[
            (60496,'429496790096','8110335','Morrowind-Korean-OpenMW-0.51.0-KR13-Full.zip','0.51.0-KR13'),
            (60844,'429496790444','8296179','TR_Mainland-kr0.4.zip','26.09.27-kr0.4'),
            (60845,'429496790445','8296167','Tamriel_Data-kr0.4.zip','26.08-kr0.4'),
            (60846,'429496790446','8296161','Cyr_Main-kr0.4.zip','26.09a-kr0.4'),
            (60847,'429496790447','8296155','Sky_Main-kr0.3.zip','26.09a-kr0.3'),
            (60805,'429496790405','8296377','Rebirth7.2-Cyr_Sky_Compatibility-kr0.4.zip','7.2-kr0.4'),
        ]
        self.assertEqual(actual,expected)
        self.assertEqual(len({e[0] for e in actual}),6)
        self.assertEqual(self.matrix[-1]['category'],'optional')
        self.assertFalse(self.matrix[-1]['update_main'])
    def test_release_source_hash_and_archive_preflight(self):
        download=next(s for s in self.steps if s['name']=='Download SHA-pinned public GitHub KR13 assets')
        raw=download['run']
        for needle in ('NEXUS-PUBLICATION-PLAN.json','sha256sum --check','unzip -tq','overwrite-existing-ESM-ESP','entry["sha256"]==digest','openmw-0.51.0-kr13'):
            self.assertIn(needle,raw)
        self.assertNotIn('PATCH-SHA256-MANIFEST.json',raw)
        self.assertNotIn('BSDIFF40',raw)
    def test_nexus_owner_group_duplicate_check_and_upload_guards(self):
        preflight=next(s for s in self.steps if s['name'].startswith('Preflight owner'))
        for v in ('/v1/users/validate.json','/v3/mods/','/v3/mod-files/','is_active','PREEXISTING_VERSION'):
            self.assertIn(v,preflight['run'])
        upload=[s for s in self.steps if s.get('uses','').startswith('Nexus-Mods/')]
        self.assertEqual(len(upload),1)
        self.assertEqual(upload[0]['uses'],ACTION)
        self.assertIn('inputs.dry_run == false',upload[0]['if'])
        self.assertIn('inputs.publish_rights_confirmed == true',upload[0]['if'])
        self.assertIn("steps.nexus.outputs.upload == 'true'",upload[0]['if'])
        self.assertEqual(upload[0]['with']['archive_existing_version'],True)
        self.assertEqual(str(upload[0]['with']['file_id']),chr(36)+'{{ matrix.group }}')
        readback=next(s for s in self.steps if s['name'].startswith('Read back'))
        self.assertIn('publish_rights_confirmed == true',readback['if'])
    def test_inline_python_compiles(self):
        count=0
        for step in self.steps:
            script=step.get('run','')
            for chunk in re.findall(r"python3 - <<'PY'\n(.*?)\nPY",script,re.S):
                compile(chunk,step['name'],'exec')
                count+=1
        self.assertEqual(count,3)

if __name__=='__main__':
    unittest.main()
