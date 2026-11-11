import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from repair_core_topic_aliases import build


class CoreTopicAliasesTest(unittest.TestCase):
    def test_pinned_core_and_existing_forms_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            core = root / 'core.esp'
            core.write_bytes(b'unchanged plugin')
            old = b'\xef\xbb\xbf' + '탈로스***\t탈로스\r\n'.encode()
            core.with_suffix('.top').write_bytes(old)
            manifest = root / 'review.json'
            data = {'core_sha256': hashlib.sha256(core.read_bytes()).hexdigest(),
                    'core_top_source_sha256': hashlib.sha256(old).hexdigest(),
                    'topics': [{'english': 'talos', 'korean': '탈로스'}]}
            manifest.write_text(json.dumps(data), encoding='utf-8')
            build(core, root / 'result', manifest)
            self.assertEqual((root / 'result/core.esp').read_bytes(), core.read_bytes())
            self.assertEqual((root / 'result/core.top').read_bytes(), old + 'talos\t탈로스\n'.encode())
            core.with_suffix('.top').write_bytes(b'drift')
            with self.assertRaisesRegex(ValueError, 'TOP source SHA'):
                build(core, root / 'refused', manifest)


if __name__ == '__main__':
    unittest.main()
