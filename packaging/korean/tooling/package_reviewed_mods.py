"""Build exact-source Rebirth/PFP kr1.1 packages from owned published Nexus baselines."""
import argparse,json,hashlib,re,struct,zipfile
from pathlib import Path
from patch_kr12_quest_entry_topics import chunks,fields,pack,decoded
PLAN=Path(__file__).with_name('reviewed_mod_plan.json')
MAIN_SHA='eec9cc81bcb8de14e621e8e27c63c728ca4b2393ca372d68c3fc1867bd5f7479'
OUTPUTS={'60805':'Morrowind_Rebirth_7.2-kr1.1_OpenMW-KR12.5.zip','60826':'PFP_5.0.7-kr1.1_OpenMW-KR12.5.zip'}
ALIASES={'제국*':'임페리얼','노예*':'노예들','사악한 데이드라':'악한 데이드라'}
def sha(b):return hashlib.sha256(b).hexdigest()
def storage(raw):
 result={}
 for index,line in enumerate(raw.split(b'\n')):
  if line.endswith(b'\r'):line=line[:-1]
  if index==0:line=line.removeprefix(b'\xef\xbb\xbf')
  if b'\t' in line:
   key,value=line.decode('utf8').split('\t',1)
   if key and value:result.setdefault(key,value)
 return result
def tokens(s,aliases):
 return [aliases.get(m[1].rstrip('\x7f')+'*'*(len(m[1])-len(m[1].rstrip('\x7f'))),m[1]) for m in re.finditer(r'@([^@#]*)#',s)]
def plain(s):return re.sub(r'@([^@#]*)#',lambda m:m[1].rstrip('\x7f'),s)
def patch_plugin(raw,cases,aliases,updated):
 out=[];parent='';seen=set()
 for kind,h,b in chunks(raw,16):
  fs=fields(b);f=dict(fs)
  if kind==b'DIAL':parent=decoded(f.get(b'NAME',b''))
  if kind.decode() not in {c['kind'] for c in cases}:
   out.append(h+b);continue
  identity=decoded(f.get(b'INAM',f.get(b'NAME',b'')))
  nb=b;changes={}
  for index,c in enumerate(cases):
   if (kind.decode(),identity,parent if kind==b'INFO' else '')!=(c['kind'],c['identity'],c['parent']):continue
   pos=c['position'];tag,value=fs[pos]
   if index in seen or tag.decode()!=c['field'] or sha(value)!=c['before_sha256']:raise ValueError('Target field source drift')
   if tag not in (b'FNAM',b'NAME') or (tag==b'NAME' and kind!=b'INFO'):raise ValueError('Non-display mutation')
   before=decoded(value);after=c['after']
   if kind==b'INFO':
    if plain(before)!=plain(after):raise ValueError('Visible dialogue changed')
    if tokens(before,aliases)!=tokens(after,updated):raise ValueError('Topic targets changed')
   changes[pos]=(tag,after.encode()+value[len(value.rstrip(b'\0')):]);seen.add(index)
  if changes:
   nb=b''.join(struct.pack('<4sI',tag,len(value))+value for pos,(tag,value) in enumerate(fs) for tag,value in [changes.get(pos,(tag,value))])
  out.append(pack(kind,h,nb) if changes else h+b)
 if len(seen)!=len(cases):raise ValueError('Missing target field')
 result=b''.join(out)
 # Independent positional comparison of every field, not merely a hash of the output.
 changed=0
 for (k,h,b),(nk,nh,nb) in zip(chunks(raw,16),chunks(result,16),strict=True):
  assert k==nk and h[8:]==nh[8:]
  for (f,v),(nf,w) in zip(fields(b),fields(nb),strict=True):
   assert f==nf
   if v!=w:
    assert f==b'FNAM' or (k==b'INFO' and f==b'NAME');changed+=1
 assert changed==len(cases)
 return result
def build(inputdir,outdir,main_zip):
 assert sha(main_zip.read_bytes())==MAIN_SHA
 with zipfile.ZipFile(main_zip) as z:
  main=storage(z.read(next(n for n in z.namelist() if n.endswith('Morrowind_Korean_ReTranslation.top'))))
  esp=z.read(next(n for n in z.namelist() if n.endswith('Morrowind_Korean_ReTranslation.esp')))
  topics={decoded(dict(fields(b))[b'NAME']) for k,h,b in chunks(esp,16) if k==b'DIAL'}
 assert set(ALIASES.values())<=topics
 plan=json.loads(PLAN.read_text(encoding='utf8'));outdir.mkdir(parents=True,exist_ok=True);reports={}
 for mid,p in plan.items():
  source=inputdir/(mid+'-current.zip');assert sha(source.read_bytes())==p['baseline_zip_sha256']
  with zipfile.ZipFile(source) as z:
   assert z.testzip() is None
   aliases=dict(main);updates={};changes={}
   if mid=='60826':
    oldtop=z.read('Patch for Purists.top')
    for key,value in storage(oldtop).items():aliases.setdefault(key,value)
    assert not set(ALIASES)&aliases.keys()
    newtop=oldtop+b'\r\n'+''.join(k+'\t'+v+'\r\n' for k,v in ALIASES.items()).encode()
    changes['Patch for Purists.top']=newtop
    updates=dict(aliases)
    for key,value in storage(newtop).items():updates.setdefault(key,value)
    assert all(updates[k]==v for k,v in ALIASES.items())
   for name in {c['file'] for c in p['cases']}:
    cases=[c for c in p['cases'] if c['file']==name]
    changes[name]=patch_plugin(z.read(name),cases,aliases,updates)
   report={'source_zip_sha256':p['baseline_zip_sha256'],'modified_display_fields':len(p['cases']),'changed_INFO_NAME':sum(c['kind']=='INFO' for c in p['cases']),'all_other_plugin_fields_unchanged':True,'dialogue_visible_text_and_topic_targets_preserved':True,'gameplay_tested':False,'base_engine':'KR12.5','changed_members':{n:{'before':sha(z.read(n)),'after':sha(b)} for n,b in changes.items()},'new_top_aliases':ALIASES if mid=='60826' else {},'case_identities':[{k:v for k,v in c.items() if k!='after'} for c in p['cases']]}
   output=outdir/OUTPUTS[mid]
   with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as dest:
    for n in z.namelist():dest.writestr(n,changes.get(n,z.read(n)))
    dest.writestr('KR1.1-CHANGES.txt',('2026-11-02 kr1.1 / OpenMW KR12.5\n'+('Rebirth: 4 flora names now match the ingredient and quest name 롤랜드의 눈물. Both main variants corrected; CEL and addon plugins unchanged.\n' if mid=='60805' else 'PFP: 3 book/sign labels aligned with the established character/book names; 12 dialogue link spans corrected. Three collision-free TOP aliases preserve original topic targets. No ESP, installer or engine changes.\n')+'Other documents describe the preserved kr1.0 baseline. Static validation passed; no live gameplay QA.\n').encode())
    dest.writestr('KR1.1-verification.json',json.dumps(report,ensure_ascii=False,indent=2).encode())
   with zipfile.ZipFile(output) as new:
    assert new.testzip() is None
    for n in z.namelist():assert new.read(n)==changes.get(n,z.read(n))
   report['output_zip_sha256']=sha(output.read_bytes());reports[mid]=report
   output.with_suffix('.zip.sha256').write_text(report['output_zip_sha256']+'  '+output.name+'\n',encoding='ascii')
   output.with_suffix('.verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
   print(mid,output.name,len(p['cases']),report['output_zip_sha256'])
 return reports
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--base-zip',type=Path,required=True);a=p.parse_args();build(a.input,a.output,a.base_zip)
