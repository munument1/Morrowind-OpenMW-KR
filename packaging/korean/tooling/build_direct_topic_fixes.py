"""Direct data corrections; core loads immediately after official masters."""
import topic_fix_helpers as base
from pathlib import Path
import zipfile,json

OUT=Path('direct-topic-fixes-20261109');OUT.mkdir(exist_ok=True)
def build():
 base.check_inputs();core,top,core_report=base.core_fix()
 src=base.OUT/'Morrowind-KR12.8-topic-fixes-QA.zip'
 import shutil
 shutil.copy2(src,OUT/src.name)
 inputs=[]
 for file in ('Tamriel_Data-kr0.2.zip','TR_Mainland-kr0.2.zip','Cyr_Main-kr0.2.zip','Sky_Main-kr0.2.zip',
              'Rebirth7.2-Cyr_Sky_Compatibility-kr0.2.zip'):
  with zipfile.ZipFile(file) as z:
   for n in z.namelist():
    if n.lower().endswith(('.esm','.esp')):inputs.append((file,n,z.read(n)))
 live=set()
 for raw in [*( (base.MASTER/n).read_bytes() for n in ('Morrowind.esm','Tribunal.esm','Bloodmoon.esm')),core,
             *(raw for _,_,raw in inputs)]:
  for record in base.chunks(raw):
   if record[:4]!=b'DIAL':continue
   f=dict(base.fs(record));name=base.audit.dec(f[b'NAME']).lower()
   if b'DELE' in f:live.discard(name)
   elif f.get(b'DATA')==b'\0':live.add(name)
 changes={};payloads={}
 for file,member,raw in inputs:
  output=[];ledger=[];parent=''
  for record in base.chunks(raw):
   if record[:4]==b'DIAL':parent=base.audit.dec(dict(base.fs(record))[b'NAME'])
   if record[:4] in (b'INFO',b'SCPT'):
    f=dict(base.fs(record));key=base.audit.dec(f.get(b'INAM',f.get(b'SCHD',b'')[:32]))
    if not key.lower().startswith('t_sctest_'):
     record,edits=base.fix_script(record,live)
     if edits:ledger.append(dict(record=key,parent=parent if record[:4]==b'INFO' else None,edits=edits))
   output.append(record)
  patched=b''.join(output)
  # Independently verify only script source fields changed, never conditions or commands.
  for before,after in zip(base.chunks(raw),base.chunks(patched)):
   if before==after:continue
   allowed=b'BNAM' if before[:4]==b'INFO' else b'SCTX'
   bf,af=base.fs(before),base.fs(after)
   if [(t,v) for t,v in bf if t!=allowed]!=[(t,v) for t,v in af if t!=allowed]:raise ValueError('Non-script change')
   b=dict(bf)[allowed];a=dict(af)[allowed]
   # Every source difference must be one of the reviewed AddTopic operands.
   if base.audit.ADD.sub('ADDTOPIC_OPERAND',base.audit.dec(b))!=base.audit.ADD.sub('ADDTOPIC_OPERAND',base.audit.dec(a)):
    raise ValueError('Script commands changed')
  payloads[file,member]=patched;changes[member]=ledger
 for file in sorted({x[0] for x in inputs}):
  with zipfile.ZipFile(file) as src,zipfile.ZipFile(OUT/file.replace('.zip','-topic-fixes-QA.zip'),'w',zipfile.ZIP_DEFLATED) as dst:
   for item in src.infolist():dst.writestr(item,payloads.get((file,item.filename),src.read(item)))
 report=dict(core=core_report,regional_changes=changes,compatibility_plugin=False,
             required_order='Morrowind.esm, Tribunal.esm, Bloodmoon.esm, Korean core, regional mods, Rebirth/compatibility mods',
             gameplay_tested=False)
 (OUT/'build-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Direct patch files:',len(list(OUT.glob('*.zip'))),'script operands:',sum(len(e['edits']) for rows in changes.values() for e in rows))
 return core,top,payloads,report
if __name__=='__main__':build()
