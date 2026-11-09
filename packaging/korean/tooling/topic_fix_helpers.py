"""Build guarded direct OpenMW topic data repairs."""
from pathlib import Path
import struct,zipfile,json,hashlib,re,collections,sys,os
tooling=Path(__file__).resolve().parent
if not (tooling/'repair_kr128_deleted_join_targets.py').is_file():
 tooling=Path('Morrowind-OpenMW-KR/packaging/korean/tooling').resolve()
sys.path.insert(0,str(tooling))
from types import SimpleNamespace
from audit_cross_mod_topic_gaps import subs

def decode_value(raw, encoding='utf-8'):
    try:return raw.rstrip(b'\0').decode(encoding)
    except UnicodeDecodeError:return raw.rstrip(b'\0').decode('cp1252')
def side_rows(raw):
    for line in raw.decode('utf-8-sig').splitlines():
        if '\t' in line:yield tuple(line.split('\t',1))
audit=SimpleNamespace(subs=subs,dec=decode_value,side_rows=side_rows,
    ADD=re.compile(r'\baddtopic\s+(?:"([^"]+)"|([^\s;]+))',re.I))
from repair_kr128_deleted_join_targets import patch as repair_join, STEM
from build_kr12_7_guild_join_release import display

ROOT=Path.cwd();OUT=ROOT/'topic-fix-20261109';OUT.mkdir(exist_ok=True)
MASTER=Path(os.environ.get('MORROWIND_MASTER_DIR','C:/Games/Steam/steamapps/common/Morrowind/Data Files'))
def sha(raw):return hashlib.sha256(raw).hexdigest()
def sub(t,v):return t+struct.pack('<I',len(v))+v
def rec(t,body,header=None):return t+struct.pack('<I',len(body))+(header[8:16] if header else b'\0'*8)+body
def chunks(raw):
 pos=0
 while pos<len(raw):
  if pos+16>len(raw):raise ValueError('Truncated record')
  n=struct.unpack_from('<I',raw,pos+4)[0];end=pos+16+n
  if end>len(raw):raise ValueError('Record outside file')
  yield raw[pos:end];pos=end
def fs(raw):return audit.subs(raw[16:])
def change(raw,updates):
 items=fs(raw);seen=collections.Counter(t for t,v in items)
 if any(seen[t]!=1 for t in updates):raise ValueError('Missing/duplicate changed field')
 return rec(raw[:4],b''.join(sub(t,updates.get(t,v)) for t,v in items),raw)
def readzip(file,member):
 with zipfile.ZipFile(file) as z:return z.read(member)
def check_inputs():
 manifest_file=Path(__file__).with_name('direct_topic_fixes_inputs.json')
 if not manifest_file.exists():manifest_file=ROOT/'topic-audit-20261109/input-sha256.json'
 manifest=json.loads(manifest_file.read_text())
 for name,expected in manifest.items():
  path=MASTER/name if name.endswith('.esm') else ROOT/name
  if sha(path.read_bytes())!=expected:raise ValueError('Input hash mismatch: '+name)

CORE_SPECS={
 '16638405123153970':('초대장','@초대#장'),
 '2861216450312110117':('탈로스 교단원','@탈로스 교단#원'),
 '2693718122219617829':('판매할','@판매\x7f#할'),
 '19032803425526617':('@카이우스 코사데스#','@카이우스 코사데스\x7f#'),
 **{iid:('@쌍둥이 등불#','@쌍둥이 등불\x7f#') for iid in
 ('390813500242161843','18405186102623220646','31548130972094426071','30491192722836529980')}}
ALIASES={'판매*':'판매','카이우스 코사데스*':'카이우스 코사데스','쌍둥이 등불*':'쌍둥이 등불'}
def core_fix():
 file='Morrowind-Korean-OpenMW-0.51.0-KR12.8-Full.zip'
 with zipfile.ZipFile(file) as z:
  raw,prior=repair_join(z.read(STEM+'.esp'));top=z.read(STEM+'.top')
  existing=dict(audit.side_rows(top))
  if set(ALIASES)&existing.keys():raise ValueError('Reserved TOP alias collision')
  seen=set();out=[];edits=[]
  for record in chunks(raw):
   f=dict(fs(record)) if record[:4]==b'INFO' else {}
   iid=audit.dec(f.get(b'INAM',b''))
   if iid in CORE_SPECS:
    if iid in seen:raise ValueError('Ambiguous core INFO identity')
    before=audit.dec(f[b'NAME']);old,new=CORE_SPECS[iid]
    if before.count(old)!=1:raise ValueError('Core source text changed: '+iid)
    after=before.replace(old,new,1)
    if display(before)!=display(after):raise ValueError('Visible text changed')
    end=f[b'NAME'][len(f[b'NAME'].rstrip(b'\0')):]
    record=change(record,{b'NAME':after.encode()+end});seen.add(iid)
    edits.append(dict(info=iid,before_sha256=sha(f[b'NAME']),after_sha256=sha(after.encode()+end)))
   out.append(record)
  if seen!=CORE_SPECS.keys():raise ValueError('Missing core INFO')
  core=b''.join(out)
  top+= ('\r\n'+''.join(k+'\t'+v+'\r\n' for k,v in ALIASES.items())).encode()
  target=OUT/'Morrowind-KR12.8-topic-fixes-QA.zip'
  with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as dst:
   for item in z.infolist():
    dst.writestr(item,core if item.filename==STEM+'.esp' else top if item.filename==STEM+'.top' else z.read(item))
  return core,top,dict(prior_join_changes=prior,new_info_name_changes=edits,new_top_aliases=ALIASES)

ADDTOPIC_MAP={'agrippina herrenia':'아그리피나 헤레니아','alit hide':'알릿 가죽',
 'caldera ebony mines':'칼데라 에보니 광산','guar hide':'구아 가죽','hound meat':'하운드 고기',
 'kagouti hide':'카구티 가죽','kwama cuttle':'크와마 큐틀',"maurrie's glove":'마우리에의 장갑',
 'nevena ules':'네베나 울레스','rat meat':'쥐고기','scales':'비늘','scrib jelly':'스크립 젤리',
 'scuttle':'스커틀','shalk resin':'샬크 수지','velanda omani':'벨란다 오마니',
 'yngling half-troll':'반트롤 잉링','kingdom o the reach':'Kingdom of the Reach'}
def fix_script(raw,live):
 field=b'BNAM' if raw[:4]==b'INFO' else b'SCTX';f=dict(fs(raw))
 if field not in f:return raw,[]
 source=f[field];edits=[]
 operand=re.compile(rb'\baddtopic\s+(?:"([^"]+)"|([^\s;]+))',re.I)
 def repl(m):
  original=m[1] or m[2]
  try:old=original.decode('ascii')
  except UnicodeDecodeError:return m[0]
  key=old.lower()
  if key in live or key not in ADDTOPIC_MAP:return m[0]
  new=ADDTOPIC_MAP[key]
  if new.lower() not in live:raise ValueError('Reviewed AddTopic target missing: '+new)
  edits.append(dict(before=old,after=new));return m[0].replace(original,new.encode('utf-8'),1)
 lines=[]
 for line in source.splitlines(keepends=True):
  code,sep,comment=line.partition(b';');lines.append(operand.sub(repl,code)+sep+comment)
 target=b''.join(lines)
 if not edits:return raw,[]
 return change(raw,{field:target}),edits
