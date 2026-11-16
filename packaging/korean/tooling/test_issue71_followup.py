import copy
import struct
import unittest
import tempfile
import io
from pathlib import Path
from unittest.mock import patch

import build_issue71_followup as fix
import publish_issue71_nexus as nexus


def sub(tag, value):
    return tag + struct.pack('<I', len(value)) + value


def record(tag, body):
    return tag + struct.pack('<I', len(body)) + b'\x01\x02\x03\x04\x05\x06\x07\x08' + body


class FollowupTests(unittest.TestCase):
    def test_public_scan_record_must_match_exact_file_identity(self):
        row = {'mod_id': 60496, 'uid': '429496790096', 'version': '0.51.0-KR13.2', 'bytes': 14298825}
        file = {'fileId': 20, 'modId': row['mod_id'], 'modUid': row['uid'],
                'version': row['version'], 'sizeInBytes': row['bytes'], 'scannedV2': 'QUARANTINED'}
        for entry in (file, {**file, 'modUid': 'wrong'}, {**file, 'sizeInBytes': 1}, {**file, 'fileId': 21}):
            payload = nexus.json.dumps({'data': {'modFiles': [entry]}}).encode()
            with patch.object(nexus.urllib.request, 'urlopen') as request:
                request.return_value.__enter__.return_value = io.BytesIO(payload)
                if entry == file:
                    self.assertEqual(nexus.scan_status(row, 20), 'QUARANTINED')
                else:
                    with self.assertRaises(ValueError):
                        nexus.scan_status(row, 20)

    def test_final_receipt_records_quarantine_and_rejects_missing_packages(self):
        pins = nexus.json.loads(nexus.PINS.read_text(encoding='utf-8'))['files']
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'NEXUS-ANDROID-UNCHANGED-BEFORE.json').write_text('[]')
            nexus.write(root / 'NEXUS-ISSUE71-PREFLIGHT.json', pins)
            def status(row, require_ready):
                self.assertFalse(require_ready)
                return {**row, 'download_ready': row['mod_id'] != 60496,
                        'security_scan_status': 'QUARANTINED' if row['mod_id'] == 60496 else 'VERIFIED'}
            with patch.object(nexus, 'get', return_value={'data': {'versions': []}}), \
                 patch.object(nexus, 'readback', side_effect=status):
                with self.assertRaisesRegex(ValueError, 'awaiting security approval'):
                    nexus.run('final', root)
                receipt = nexus.json.loads((root / 'NEXUS-ISSUE71-FINAL.json').read_text(encoding='utf-8'))
                self.assertFalse(receipt['all_files_download_ready'])
                self.assertEqual(len(receipt['files']), 8)
                nexus.write(root / 'NEXUS-ISSUE71-PREFLIGHT.json', pins[1:])
                with self.assertRaisesRegex(ValueError, 'all eight'):
                    nexus.run('final', root)

    def test_matching_uploaded_metadata_is_not_enough_for_download_approval(self):
        row = {'mod_id': 60496, 'uid': '429496790096', 'group': '8110335',
               'version': '0.51.0-KR13.2', 'bytes': 14298825}
        def responses():
            return [{'data': {'versions': [{'id': 10, 'version': row['version'], 'category': 'main'}]}},
                    {'files': [{'file_id': 20, 'version': row['version'], 'size_in_bytes': row['bytes'], 'file_name': 'core.zip'}]}]
        for status in ('QUARANTINED', 'QUEUED', 'UNKNOWN', 'REPORT_ERROR'):
            with patch.object(nexus, 'get', side_effect=responses()), patch.object(nexus, 'scan_status', return_value=status):
                with self.assertRaisesRegex(ValueError, 'not approved for download'):
                    nexus.readback(row)
            with patch.object(nexus, 'get', side_effect=responses()), patch.object(nexus, 'scan_status', return_value=status):
                report = nexus.readback(row, require_ready=False)
                self.assertFalse(report['download_ready'])
                self.assertEqual(report['security_scan_status'], status)
        for status in ('VERIFIED', 'INTERNALLY_VERIFIED', 'MANUALLY_VERIFIED'):
            with patch.object(nexus, 'get', side_effect=responses()), patch.object(nexus, 'scan_status', return_value=status):
                self.assertTrue(nexus.readback(row)['download_ready'])

    def test_quarantined_readback_records_state_and_does_not_retry_or_reupload(self):
        pins = nexus.json.loads(nexus.PINS.read_text(encoding='utf-8'))['files']
        row = next(r for r in pins if r['mod_id'] == 60496)
        blocked = {**row, 'security_scan_status': 'QUARANTINED', 'download_ready': False}
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(nexus, 'check_archive', return_value=row), \
                 patch.object(nexus, 'readback', return_value=blocked) as readback, \
                 patch.object(nexus.time, 'sleep') as sleep:
                with self.assertRaisesRegex(ValueError, 'QUARANTINED'):
                    nexus.run('readback', Path(folder), row['asset'])
                readback.assert_called_once()
                sleep.assert_not_called()
            saved = nexus.json.loads((Path(folder) / 'NEXUS-60496-PUBLICATION.json').read_text(encoding='utf-8'))
            self.assertFalse(saved['download_ready'])

    def test_android_and_wrong_uids_rejected_before_network(self):
        for row in ({'mod_id': 60496, 'uid': '429496790096', 'group': '8257539'},
                    {'mod_id': 60496, 'uid': '60496', 'group': '8110335'}):
            with patch.object(nexus, 'get') as network:
                with self.assertRaises(ValueError):
                    nexus.target(row)
                network.assert_not_called()

    def test_wrong_owner_rejected_before_file_group_access(self):
        row = {'mod_id': 60496, 'uid': '429496790096', 'group': '8110335'}
        with patch.object(nexus, 'get', side_effect=[{'user_id': 1}, {'uid': row['uid'], 'user': {'member_id': 2}}]) as network:
            with self.assertRaises(ValueError):
                nexus.target(row)
            self.assertEqual(network.call_count, 2)

    def test_only_visible_quotes_change_and_choice_numbers_survive(self):
        source = b'Choice "Sure." 1 "No thanks." 2 ; "Leave me alone"\r\nAddItem "Sure." 1\r\n'
        result, count = fix.translate_script(source, {'Sure.': '좋습니다.', 'No thanks.': '괜찮습니다.', 'Leave me alone': '혼자 두세요'})
        self.assertEqual(count, 2)
        self.assertIn(b' 1 ', result)
        self.assertIn(b' 2 ; "Leave me alone"', result)
        self.assertIn(b'AddItem "Sure." 1', result)
        self.assertEqual(fix.script_shape(source.decode()), fix.script_shape(result.decode()))

    def test_quoted_actor_say_keeps_sound_id_and_semicolon_in_text(self):
        source = b'"Some NPC"->Say "voice.wav" "Hello; friend" ; comment\n'
        result, count = fix.translate_script(source, {'voice.wav': '소리', 'Hello; friend': '안녕; 친구'})
        self.assertEqual(count, 1)
        self.assertIn(b'"voice.wav"', result)
        self.assertTrue(result.endswith(b' ; comment\n'))

    def test_rejects_format_loss_and_quote_injection(self):
        self.assertEqual(fix.translate_script(b'; na\xefve healer', {}), (b'; na\xefve healer', 0))
        for target in ('잔액', '잔액 %G"\nJournal "quest" 100'):
            with self.assertRaises(ValueError):
                fix.translate_script(b'MessageBox "Balance %G" amount', {'Balance %G': target})

    def test_plugin_preserves_conditions_bytecode_and_record_flags(self):
        source_script = b'Choice "Yes" 7 "No" 9'
        body = sub(b'INAM', b'123\0') + sub(b'SCVR', b'condition') + sub(b'INTV', b'\x28\0\0\0') + sub(b'BNAM', source_script)
        raw = record(b'INFO', body) + record(b'SCPT', sub(b'SCHD', b'example'.ljust(52, b'\0')) + sub(b'SCDT', b'compiled') + sub(b'SCTX', b'MessageBox "Yes"'))
        review = {'npc_names': {}, 'script_strings': {'Yes': '네', 'No': '아니요'}}
        result, changes, _ = fix.rewrite_plugin(raw, 'Cyr_Main', review)
        self.assertEqual(result[8:16], raw[8:16])
        self.assertEqual(fix.verify_logic(raw, result, 'Cyr_Main', review), 2)
        self.assertIn(sub(b'INTV', b'\x28\0\0\0'), result)
        self.assertIn(sub(b'SCDT', b'compiled'), result)
        corrupted = result.replace(b'condition', b'bad_value')
        with self.assertRaises(ValueError):
            fix.verify_logic(raw, corrupted, 'Cyr_Main', review)
        with self.assertRaises(ValueError):
            fix.verify_logic(raw, result[:8] + b'\0' * 8 + result[16:], 'Cyr_Main', review)

    def test_npc_source_hash_guard_and_reject_unreviewed_name(self):
        raw = record(b'NPC_', sub(b'NAME', b'actor\0') + sub(b'FNAM', b'Name\0'))
        review = {'npc_names': {'Sky_Main': [{'id': 'actor', 'source_sha256': fix.sha(b'Name\0'), 'after': '이름'}]}, 'script_strings': {}}
        result, _, _ = fix.rewrite_plugin(raw, 'Sky_Main', review)
        self.assertEqual(fix.verify_logic(raw, result, 'Sky_Main', review), 1)
        bad = copy.deepcopy(review)
        bad['npc_names']['Sky_Main'][0]['source_sha256'] = 'bad'
        with self.assertRaises(ValueError):
            fix.rewrite_plugin(raw, 'Sky_Main', bad)
        with self.assertRaises(ValueError):
            fix.verify_logic(raw, result, 'Sky_Main', {'npc_names': {}})


if __name__ == '__main__':
    unittest.main()
