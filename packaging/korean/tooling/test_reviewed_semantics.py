import unittest,tempfile,json,struct
from pathlib import Path
from unittest.mock import patch
import release_reviewed_semantics as mod
def field(k,s):
 b=s.encode()+b'\0';return struct.pack('<4sI',k,len(b))+b
def record(k,b):return struct.pack('<4sIII',k,len(b),0,0)+b
class ReviewedTests(unittest.TestCase):
 def test_duplicate_inam_different_parent_preserved(self):
  raw=b'';cases=[]
  for i in range(29):
   parent='topic'+str(i);before='황야@입#니다'
   raw+=record(b'DIAL',field(b'NAME',parent))
   raw+=record(b'INFO',field(b'INAM','same')+field(b'NAME',before)+field(b'BNAM','unchanged script'))
   cases.append(dict(parent=parent,id='same',actor='',before_sha256=mod.sha(before.encode()),after='황야입니다'))
  raw+=record(b'DIAL',field(b'NAME','unselected'))+record(b'INFO',field(b'INAM','same')+field(b'NAME','@입#을 다물어'))
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'manifest.json';p.write_text(json.dumps(cases),encoding='utf8')
   with patch.object(mod,'MANIFEST',p),patch.object(mod,'ESP_SHA',mod.sha(raw)):
    result,report=mod.rewrite(raw)
    self.assertEqual(len(report),29)
    self.assertTrue(result.endswith(record(b'INFO',field(b'INAM','same')+field(b'NAME','@입#을 다물어'))))
    cases[0]['after']='다른 문장';p.write_text(json.dumps(cases),encoding='utf8')
    with self.assertRaises(ValueError):mod.rewrite(raw)
 def test_wrong_release_refused(self):
  with self.assertRaises(ValueError):mod.rewrite(b'wrong baseline')
if __name__=='__main__':unittest.main()
