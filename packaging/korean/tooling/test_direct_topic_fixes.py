import unittest,struct
import topic_fix_helpers as h

def script(text):
 return h.rec(b'SCPT',h.sub(b'SCHD',b'Example'+b'\0'*45)+h.sub(b'SCDT',b'untouched bytecode')+h.sub(b'SCTX',text))
class DirectFixTests(unittest.TestCase):
 def test_only_reviewed_operand_bytes_change(self):
  source=b'; comment \x96 remains\r\nAddTopic "Velanda Omani" ; note\r\nSet value to 7\r\n'
  raw=script(source);out,edits=h.fix_script(raw,{'벨란다 오마니'})
  fields=dict(h.fs(out))
  self.assertEqual(fields[b'SCTX'],source.replace(b'Velanda Omani','벨란다 오마니'.encode()))
  self.assertEqual(fields[b'SCDT'],b'untouched bytecode')
  self.assertEqual(len(edits),1)
 def test_live_regional_target_keeps_its_own_responses(self):
  raw=script(b'AddTopic "Velanda Omani"')
  self.assertEqual(h.fix_script(raw,{'velanda omani','벨란다 오마니'}),(raw,[]))
 def test_missing_reviewed_destination_fails_closed(self):
  with self.assertRaises(ValueError):h.fix_script(script(b'AddTopic "Velanda Omani"'),set())
 def test_comments_and_unrelated_commands_preserved(self):
  raw=script(b'; AddTopic "Velanda Omani"\r\nMessageBox "Velanda Omani"\r\n')
  self.assertEqual(h.fix_script(raw,{'벨란다 오마니'}),(raw,[]))
 def test_existing_korean_operand_untouched(self):
  raw=script('AddTopic "벨란다 오마니"'.encode())
  self.assertEqual(h.fix_script(raw,{'벨란다 오마니'}),(raw,[]))
 def test_record_parser_rejects_truncation(self):
  with self.assertRaises(ValueError):list(h.chunks(b'INFO'+struct.pack('<I',100)+b'\0'*8))
if __name__=='__main__':unittest.main()
