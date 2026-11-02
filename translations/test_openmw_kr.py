"""Regression checks for replacement ESM identity and BOM sidecars."""
import collections,gzip,json,tempfile,unittest
from pathlib import Path
import openmw_kr_replacement as b

class TranslationReplacementTests(unittest.TestCase):
 def test_sidecar_requires_bom_and_unique_keys(self):
  self.assertEqual(b.sidecar_read('\ufeff시로딜\tCyrodiil\n'.encode()),[('시로딜','Cyrodiil')])
  for data in [b'a\tb\n','\ufeffa\tb\na\tc\n'.encode(),'\ufeffa\tb\tc\n'.encode()]:
   with self.assertRaises(AssertionError):b.sidecar_read(data)

 def test_rejects_truncated_record(self):
  for data in [b'TES3',b.H.pack(b'TES3',10,0,0),b.record(b'TES3',b.S.pack(b'HEDR',2)+b'x')]:
   with self.assertRaises(AssertionError):list(b.records(data))

 def test_info_ids_conditions_results_and_cells_survive(self):
  def chunk(t,*fields):return b.record(t,b''.join(b.sub(k,v) for k,v in fields))
  header=chunk(b'TES3',(b'HEDR',b'\0'*300),(b'MAST',b'Morrowind.esm\0'),(b'DATA',b'\0'*8))
  npc=chunk(b'NPC_',(b'NAME',b'original_npc_id\0'),(b'FNAM',b'Original Name\0'),(b'NPDT',b'\x01\x02'))
  dial=chunk(b'DIAL',(b'NAME',b'Original Topic\0'),(b'DATA',b'\0'))
  def info(i,prev,nxt,text):return chunk(b'INFO',(b'INAM',i),(b'PNAM',prev),(b'NNAM',nxt),(b'DATA',b'\0'*12),(b'SCVR',b'condition'),(b'NAME',text),(b'BNAM',b'Journal original_quest 10'))
  a=info(b'1\0',b'\0',b'2\0',b'Hello %PCName.\0');middle=info(b'2\0',b'1\0',b'3\0',b'Unchanged.\0');z=info(b'3\0',b'2\0',b'\0',b'Farewell.\0')
  cell=chunk(b'CELL',(b'NAME',b'Original Cell\0'),(b'DATA',b'\0'*12),(b'NAME',b'placed_object_id\0'),(b'DNAM',b'Other Cell\0'))
  original=header+npc+dial+a+middle+z+cell
  translations={(1,1):'원래 이름',(3,5):'%PCName, 안녕하세요.',(5,5):'안녕히 가세요.'}
  rows=[];translated=[]
  for ri,s,e,t,u,f,subs in b.records(original):
   fields=[]
   for si,(tag,x,y) in enumerate(subs):
    raw=original[x:y]
    if (ri,si) in translations:
     ko=translations[(ri,si)];rows.append({'record_index':ri,'subrecord_index':si,'record_type':t.decode(),'field':tag.decode(),'source_offset':x,'source_subrecord_sha256':b.sha(raw),'en':raw.rstrip(b'\0').decode(),'ko':ko})
     raw=ko.encode()+b'\0'
    fields.append(b.sub(tag,raw))
   translated.append(b.record(t,b''.join(fields),u,f))
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);folder=root/'dataset';folder.mkdir();source_dir=root/'original';source_dir.mkdir();source=source_dir/'Example.esm';source.write_bytes(original)
   data=gzip.compress(''.join(json.dumps(r)+'\n' for r in rows).encode(),mtime=0);(folder/'strings.jsonl.gz').write_bytes(data)
   hashes={};counts={}
   for ext,pairs in [('cel',[('Original Cell','원래 지역')]),('mrk',[('Original Topic','원래 토픽')]),('top',[('원래 토픽','Original Topic')]),('jrn',[('원래 토픽','Original Topic')])]:
    raw=('\ufeff'+''.join(k+'\t'+v+'\n' for k,v in pairs)).encode();(folder/('Example.'+ext)).write_bytes(raw);hashes[ext]=b.sha(raw);counts[ext]=len(pairs)
   m={'source_plugin':'Example.esm','source_sha256':b.sha(original),'translated_copy_sha256':b.sha(b''.join(translated)),'plugin_stem':'Example','translated_fields':len(rows),'strings_sha256':b.sha(data),'sidecar_sha256':hashes,'sidecar_counts':counts}
   (folder/'manifest.json').write_text(json.dumps(m))
   out=root/'output';r=b.build(folder,source,out);self.assertTrue(r['source_unchanged']);built=(out/'Data Files/Example.esm').read_bytes();rs=list(b.records(built))
   self.assertEqual([r[3] for r in rs],[b'TES3',b'NPC_',b'DIAL',b'INFO',b'INFO',b'INFO',b'CELL'])
   self.assertEqual(built,b''.join(translated));self.assertIn(b'Journal original_quest 10',built);self.assertIn(b'Original Topic',built);self.assertIn(b'placed_object_id',built)
   masters=[built[x:y] for tag,x,y in rs[0][6] if tag==b'MAST'];self.assertEqual(masters,[b'Morrowind.esm\0'])
   with self.assertRaises(AssertionError):b.build(folder,source,out)
   source.write_bytes(original+b'bad')
   with self.assertRaises(AssertionError):b.build(folder,source,root/'bad_output')
if __name__=='__main__':unittest.main()
