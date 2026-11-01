import unittest,struct
from package_reviewed_mods import patch_plugin,sha,plain,tokens,storage
def field(k,b):return struct.pack('<4sI',k,len(b))+b
def record(k,b):return struct.pack('<4sIII',k,len(b),0,0)+b
class ReviewedModTests(unittest.TestCase):
 def test_target_preserved_with_hidden_alias_and_reused_info_id(self):
  text='자네@가 제국#의 첩자라더군.';after='자네가 @제국\x7f#의 첩자라더군.'
  raw=record(b'DIAL',field(b'NAME',b'one\0'))+record(b'INFO',field(b'INAM',b'same\0')+field(b'NAME',text.encode()+b'\0')+field(b'BNAM',b'script\0'))
  tail=record(b'DIAL',field(b'NAME',b'two\0'))+record(b'INFO',field(b'INAM',b'same\0')+field(b'NAME',text.encode()+b'\0'))
  case=dict(kind='INFO',identity='same',parent='one',position=1,field='NAME',before_sha256=sha(text.encode()+b'\0'),after=after)
  old={'가 제국':'임페리얼','제국':'제국'};new={**old,'제국*':'임페리얼'}
  result=patch_plugin(raw+tail,[case],old,new)
  self.assertTrue(result.endswith(tail));self.assertEqual(plain(text),plain(after))
  with self.assertRaises(ValueError):patch_plugin(raw+tail,[case],old,{**new,'제국*':'제국'})
  case['before_sha256']='bad'
  with self.assertRaises(ValueError):patch_plugin(raw+tail,[case],old,new)
 def test_storage_matches_utf8_bom_crlf_first_wins(self):
  self.assertEqual(storage(b'\xef\xbb\xbfkey\tfirst\r\nkey\tsecond\r\n'),{'key':'first'})
if __name__=='__main__':unittest.main()
