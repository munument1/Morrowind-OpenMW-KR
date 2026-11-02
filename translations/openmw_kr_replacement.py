"""Build same-name OpenMW-KR translation ESMs and matching sidecars."""
import argparse, collections, gzip, hashlib, json, re, struct, zipfile
from pathlib import Path

H=struct.Struct('<4sIII'); S=struct.Struct('<4sI')
LAYOUT=r'<[^>]*>|@[^\r\n#]+#|\r\n|\r|\n'
VARS=r'%[A-Za-z_][A-Za-z0-9_]*'
IDS=r'(?<![A-Za-z0-9_])(?:Sky|sky|T|TR|Cyr)_[A-Za-z0-9_]+(?![A-Za-z0-9_])'
def sha(b):return hashlib.sha256(b).hexdigest()
def records(b):
 pos=0; ri=0
 while pos<len(b):
  assert pos+16<=len(b),'truncated record header'
  tag,n,u,f=H.unpack_from(b,pos);end=pos+16+n;assert end<=len(b)
  cur=pos+16; subs=[]
  while cur<end:
   assert cur+8<=end
   t,size=S.unpack_from(b,cur);a=cur+8;z=a+size;assert z<=end
   subs.append((t,a,z));cur=z
  assert cur==end
  yield ri,pos,end,tag,u,f,subs
  pos=end;ri+=1
 assert pos==len(b) and ri
def sub(tag,b):return S.pack(tag,len(b))+b
def record(tag,b,u=0,f=0):return H.pack(tag,len(b),u,f)+b
def sidecar_read(b):
 assert b.startswith(b'\xef\xbb\xbf'),'UTF-8 BOM required by OpenMW-KR'
 rows=[];keys=set()
 for line in b.decode('utf-8-sig').splitlines():
  assert line.count('\t')==1
  k,v=line.split('\t');assert k and v and not any(c in k+v for c in '\0\r\n@#')
  assert k.lower() not in keys;keys.add(k.lower());rows.append((k,v))
 return rows
def text_qa(en,ko,layout=None,variables=None,ids=None):
 assert not any(c in ko for c in '\0\ufffd\ufeff') and '__TR_' not in ko
 assert not any(ord(c)<32 and c not in '\r\n\t' for c in ko)
 assert re.findall(LAYOUT,ko)==(layout if en is None else re.findall(LAYOUT,en))
 assert dict(collections.Counter(re.findall(VARS,ko)))==(variables if en is None else dict(collections.Counter(re.findall(VARS,en))))
 assert dict(collections.Counter(re.findall(IDS,ko)))==(ids if en is None else dict(collections.Counter(re.findall(IDS,en))))
def load(folder):
 m=json.loads((folder/'manifest.json').read_text(encoding='utf8'))
 data=(folder/'strings.jsonl.gz').read_bytes();assert sha(data)==m['strings_sha256']
 rows=[json.loads(l) for l in gzip.decompress(data).decode('utf8').splitlines()]
 assert len(rows)==m['translated_fields']==len({(r['record_index'],r['subrecord_index']) for r in rows})
 for r in rows:
  assert r['field']=='FNAM' or (r['record_type'],r['field']) in [('INFO','NAME'),('BOOK','TEXT')]
  assert r['record_type'] not in ('CELL','DIAL','SCPT','LAND','PGRD','TES3')
  text_qa(r['en'],r['ko'],r.get('source_layout_tokens'),r.get('source_variable_counts'),r.get('source_engine_id_counts'))
 for ext in ('cel','top','mrk','jrn'):
  data=(folder/(m['plugin_stem']+'.'+ext)).read_bytes();assert sha(data)==m['sidecar_sha256'][ext];sidecar_read(data)
 top=dict(sidecar_read((folder/(m['plugin_stem']+'.top')).read_bytes()))
 mrk=dict(sidecar_read((folder/(m['plugin_stem']+'.mrk')).read_bytes()))
 jrn=dict(sidecar_read((folder/(m['plugin_stem']+'.jrn')).read_bytes()))
 assert all(top.get(ko)==en and jrn.get(ko)==en for en,ko in mrk.items())
 return m,rows

def build(folder,source,output):
 m,rows=load(folder);raw=source.read_bytes();assert source.name.lower()==m['source_plugin'].lower() and sha(raw)==m['source_sha256']
 assert not output.exists(),'Choose a fresh test output directory'
 assert not output.resolve().is_relative_to(source.parent.resolve()),'Never build into the original mod directory'
 wanted={(r['record_index'],r['subrecord_index']):r for r in rows};seen=set();parts=[];topics=set();original=list(records(raw))
 for ri,start,end,rt,u,flags,subs in original:
  if rt==b'DIAL':
   typ=next((raw[a:z][0] for t,a,z in subs if t==b'DATA'),None)
   if typ==0:topics.add(next(raw[a:z].rstrip(b'\0').decode('cp1252') for t,a,z in subs if t==b'NAME'))
  body=[]
  for si,(tag,a,z) in enumerate(subs):
   value=raw[a:z];r=wanted.get((ri,si))
   if r:
    assert rt.decode()==r['record_type'] and tag.decode()==r['field']
    assert a==r['source_offset'] and sha(value)==r['source_subrecord_sha256']
    if r['en'] is not None:assert value.rstrip(b'\0').decode('cp1252')==r['en']
    value=r['ko'].encode('utf8')+b'\0'*(len(value)-len(value.rstrip(b'\0')));seen.add((ri,si))
   body.append(sub(tag,value))
  parts.append(record(rt,b''.join(body),u,flags))
 built=b''.join(parts);assert seen==set(wanted) and sha(built)==m['translated_copy_sha256']
 untouched=0;checked=0
 for left,right in zip(original,records(built),strict=True):
  ri,_,_,rt,u,fl,subs=left;assert (ri,rt,u,fl)==(right[0],right[3],right[4],right[5]) and len(subs)==len(right[6])
  for si,((t,a,z),(nt,x,y)) in enumerate(zip(subs,right[6],strict=True)):
   assert t==nt;r=wanted.get((ri,si))
   expected=r['ko'].encode('utf8')+b'\0'*(z-a-len(raw[a:z].rstrip(b'\0'))) if r else raw[a:z]
   assert built[x:y]==expected
   untouched+=not bool(r);checked+=1
 for ext in ('top','mrk','jrn'):
  pairs=sidecar_read((folder/(m['plugin_stem']+'.'+ext)).read_bytes())
  assert all((k if ext=='mrk' else v) in topics for k,v in pairs)
 output.mkdir(parents=True);data_dir=output/'Data Files';data_dir.mkdir()
 (data_dir/m['source_plugin']).write_bytes(built)
 for ext in ('cel','top','mrk','jrn'):(data_dir/(m['plugin_stem']+'.'+ext)).write_bytes((folder/(m['plugin_stem']+'.'+ext)).read_bytes())
 report=dict(m,output_sha256=sha(built),output_bytes=len(built),records=len(original),validated_subrecords=checked,untouched_subrecords=untouched,structural_validation='PASS',source_unchanged=sha(source.read_bytes())==m['source_sha256'],game_applied=False,runtime_tested=False)
 (output/'build_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 readme=f'''OpenMW-KR 전용 한국어 교체형 TEST — {m['source_plugin']}

배포 형식: 원본과 같은 이름의 {m['source_plugin']} + .cel/.top/.mrk/.jrn.
원본 모드의 전체 필수 자산을 설치한 후 번역본 Data Files로 해당 ESM을 교체하는 구성입니다.
모드 관리자로 쓰는 경우 번역 폴더가 원본 ESM 파일을 덮어쓰도록 우선순위를 둡니다.
동일 ESM을 하나만 로드하며 별도 번역 addon을 추가 활성화하지 않습니다.
원본 ESM은 별도 보관합니다. 이 빌드 도구는 원본·실제 게임 폴더를 수정하지 않습니다.
마스터 의존성·CELL/DIAL/INFO 식별자·문 목적지·스크립트·조건은 원문 보존입니다.
본문과 표시 이름은 ESM, 셀 표시명은 CEL, 토픽 연결은 TOP/MRK/JRN으로 처리합니다.
TOP/JRN은 표시 표현→원래 토픽, MRK는 원래 토픽→본문 검색어입니다.
보조 파일은 원본 ESM과 같은 stem, UTF-8 BOM + 탭 구분으로 함께 설치합니다.
KR12.5의 MRK는 토픽 목록 제목을 바꾸지 않습니다. 엔진/UI 파일은 변경하지 않았습니다.
미확정 셀·토픽은 영어를 유지하고 보류 목록에 기록합니다. 미검수 표시도 유지합니다.
실게임 대화/저널 클릭·퀘스트·글꼴·세이브 검증은 하지 않았습니다.
GitHub에는 번역 데이터와 도구만 보관하고 모드 릴리스는 Nexus Mods에서만 합니다.

원본 SHA-256: {m['source_sha256']}
출력 SHA-256: {sha(built)}
번역 필드: {len(rows)}. CEL: {m['sidecar_counts']['cel']}. TOP/MRK/JRN 각각: {m['sidecar_counts']['mrk']}.
'''
 (output/'README_KR_TEST.txt').write_text(readme,encoding='utf-8-sig')
 z=output/(m['plugin_stem']+'_OpenMW_KR_ESM_TEST.zip')
 with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
  for p in sorted(data_dir.iterdir()):archive.write(p,p.relative_to(output).as_posix())
  for name in ('README_KR_TEST.txt','build_verification.json'):archive.write(output/name,name)
 with zipfile.ZipFile(z) as archive:assert archive.testzip() is None and not any(n.endswith('.omwaddon') for n in archive.namelist())
 z.with_suffix('.zip.sha256').write_text(sha(z.read_bytes())+'  '+z.name+'\n',encoding='ascii')
 return report
def main():
 p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--check-only',action='store_true');p.add_argument('--source',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 if a.check_only:
  m,rows=load(a.dataset);print(json.dumps({'dataset_qa':'PASS','plugin':m['source_plugin'],'rows':len(rows),'sidecar_counts':m['sidecar_counts']}));return
 if not a.source or not a.output:p.error('--source and --output required')
 r=build(a.dataset,a.source,a.output);print(json.dumps({k:r[k] for k in ('source_plugin','translated_fields','records','sidecar_counts','structural_validation','game_applied')}))
if __name__=='__main__':main()
