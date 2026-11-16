import copy
import struct
import unittest
from unittest.mock import patch

import build_issue71_followup as fix
import publish_issue71_nexus as nexus


def sub(tag, value):
    return tag + struct.pack('<I', len(value)) + value


def record(tag, body):
    return tag + struct.pack('<I', len(body)) + b'\x01\x02\x03\x04\x05\x06\x07\x08' + body


class FollowupTests(unittest.TestCase):
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
