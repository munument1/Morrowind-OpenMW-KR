"""KR12.5: remove source-anchored accidental explicit links; preserve visible text."""
import argparse,hashlib,json,re,struct,zipfile
from pathlib import Path
from patch_kr12_quest_entry_topics import chunks,fields,decoded,pack
ESP_SHA='2276384ad93fd3e56bc0d401aacc45418ba38993ee798e0e1a7e09564a375d3a'
MANIFEST=Path(__file__).with_name('reviewed_semantics_manifest.json')
def sha(b):return hashlib.sha256(b).hexdigest()
def plain(s):return re.sub(r'@([^@#]*)#',r'\1',s)
def rewrite(raw):
 if sha(raw)!=ESP_SHA:raise ValueError('Unknown baseline ESP')
 cases=json.loads(MANIFEST.read_text(encoding='utf8'))
 targets={(a['parent'],a['id'],a['actor']):a for a in cases}
 if len(targets)!=29:raise ValueError('Manifest identity drift')
 out=[];seen=set();parent=None;report=[]
 for tag,h,b in chunks(raw,16):
  fs=fields(b);f=dict(fs)
  if tag==b'DIAL':parent=decoded(f.get(b'NAME',b''))
  key=(parent,decoded(f.get(b'INAM',b'')),decoded(f.get(b'ONAM',b'')))
  if tag!=b'INFO' or key not in targets:out.append(h+b);continue
  a=targets[key];text=decoded(f[b'NAME']);new=a['after']
  if key in seen or sha(text.encode())!=a['before_sha256']:raise ValueError('INFO source drift')
  if plain(text)!=plain(new):raise ValueError('Visible text changed')
  seen.add(key);data=new.encode()+f[b'NAME'][len(f[b'NAME'].rstrip(b'\0')):]
  nb=b''.join(struct.pack('<4sI',k,len(data if k==b'NAME' else v))+(data if k==b'NAME' else v) for k,v in fs)
  assert [(k,v) for k,v in fields(nb) if k!=b'NAME']==[(k,v) for k,v in fs if k!=b'NAME']
  out.append(pack(tag,h,nb));report.append({'DIAL':parent,'INFO':key[1],'actor':key[2],'removed_tags':text.count('@')-new.count('@')})
 if seen!=targets.keys():raise ValueError('Missing targeted INFO')
 result=b''.join(out)
 # Independently compare all record/subrecord positions, including unselected INFO.
 for (t,h,b),(nt,nh,nb) in zip(chunks(raw,16),chunks(result,16),strict=True):
  assert t==nt and h[8:]==nh[8:]
  if b!=nb:
   assert t==b'INFO'
   for (k,v),(nk,nv) in zip(fields(b),fields(nb),strict=True):
    assert k==nk
    if v!=nv:assert k==b'NAME' and plain(decoded(v))==plain(decoded(nv))
 return result,report
def package(source,output,baseline_sha):
 if sha(source.read_bytes())!=baseline_sha:raise ValueError('ZIP source hash mismatch')
 with zipfile.ZipFile(source) as z:
  assert z.testzip() is None
  names=z.namelist();ep=next(n for n in names if n.endswith('Morrowind_Korean_ReTranslation.esp'))
  esp,report=rewrite(z.read(ep));modified={ep:esp}
  for n in names:
   if Path(n).name in ('README-KOREAN.txt','install-korean.ps1'):
    b=z.read(n);modified[n]=b.replace(b'KR12.4',b'KR12.5')
  output.parent.mkdir(parents=True,exist_ok=True)
  with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as dest:
   for n in names:dest.writestr(n,modified.get(n,z.read(n)))
   dest.writestr('KR12.5-CHANGES.txt','KR12.5: 29 INFO.NAME, 31 accidental topic tags removed; visible Korean and other ESP fields unchanged. KR12.4 engine reused unchanged. No in-game QA.\n')
  with zipfile.ZipFile(output) as new:
   assert new.testzip() is None
   for n in names:assert new.read(n)==modified.get(n,z.read(n))
  qa={'baseline_zip_sha256':baseline_sha,'output_zip_sha256':sha(output.read_bytes()),'esp_before':ESP_SHA,'esp_after':sha(esp),'changed_info':len(report),'removed_tags':sum(a['removed_tags'] for a in report),'cases':report,'all_other_esp_fields_unchanged':True,'visible_text_unchanged':True,'unchanged_zip_entries':[n for n in names if n not in modified],'changed_zip_entries':list(modified),'gameplay_tested':False}
 output.with_suffix('.zip.sha256').write_text(qa['output_zip_sha256']+'  '+output.name+'\n',encoding='ascii')
 output.with_suffix('.verification.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf8')
 return qa
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--source-sha',required=True);a=p.parse_args()
 q=package(a.source,a.output,a.source_sha);print(json.dumps({k:q[k] for k in ('changed_info','removed_tags','esp_after','output_zip_sha256')},indent=2))
