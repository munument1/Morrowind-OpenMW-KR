import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from package_kr13_mod_overwrites import FORMAT, verify_archive


class OverwriteContractTests(unittest.TestCase):
    def package(self, folder, payload, extras=None, manifest_format=FORMAT):
        path = Path(folder) / 'mod.zip'
        files = {name: hashlib.sha256(data).hexdigest() for name, data in payload.items()}
        with ZipFile(path, 'w') as z:
            for name, data in {**payload, **(extras or {})}.items():
                z.writestr(name, data)
            z.writestr('README_KO.md', 'Install the same-named plugin overwrite.')
            z.writestr('INSTALL-MANIFEST.json', json.dumps({'format': manifest_format, 'files': files}))
        return path, files

    def test_full_plugin_and_matching_sidecar(self):
        with tempfile.TemporaryDirectory() as folder:
            path, files = self.package(folder, {'Data Files/mod.esm': b'TES3-fixture', 'Data Files/mod.top': b'keyword\ttopic'})
            verify_archive(path, files)

    def test_delta_cannot_replace_full_plugin_even_with_matching_hash(self):
        with tempfile.TemporaryDirectory() as folder:
            path, files = self.package(folder, {'Data Files/mod.esm': b'BSDIFF40-fixture'})
            with self.assertRaisesRegex(ValueError, 'complete TES3'):
                verify_archive(path, files)

    def test_missing_plugin_or_sidecar_and_injected_installer_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path, files = self.package(folder, {'Data Files/mod.top': b'keyword\ttopic'})
            with self.assertRaisesRegex(ValueError, 'Full translated'):
                verify_archive(path, files)
            files['Data Files/mod.esm'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'Missing full'):
                verify_archive(path, files)
            path, files = self.package(folder, {'Data Files/mod.esm': b'TES3-fixture'}, {'apply_regional_deltas.py': b'extra'})
            with self.assertRaisesRegex(ValueError, 'unexpected ZIP member'):
                verify_archive(path, files)

    def test_payload_drift_and_old_manifest_format_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path, files = self.package(folder, {'Data Files/mod.esm': b'TES3-fixture'})
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                verify_archive(path, {**files, 'Data Files/mod.esm': '0' * 64})
            path, files = self.package(folder, {'Data Files/mod.esm': b'TES3-fixture'}, manifest_format='BSDIFF40')
            with self.assertRaisesRegex(ValueError, 'installation manifest'):
                verify_archive(path, files)


if __name__ == '__main__':
    unittest.main()
