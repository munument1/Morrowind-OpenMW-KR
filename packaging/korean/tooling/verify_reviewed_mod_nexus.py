"""Verify both owned Nexus releases and download their published bytes through API."""
import os,json,urllib.request,hashlib,time
from pathlib import Path
key=os.environ['NEXUS_KEY']
def call(path,body=None):
 req=urllib.request.Request('https://api.nexusmods.com'+path,headers={'apikey':key,'Accept':'application/json','Content-Type':'application/json','User-Agent':'KR125-Mod-Audit'},data=json.dumps(body,ensure_ascii=False).encode() if body else None,method='POST' if body else 'GET')
 with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
targets=[(60805,'429496790405','8257641','7.2-kr1.1','Morrowind_Rebirth_7.2-kr1.1_OpenMW-KR12.5.zip','기본/대체 메인 채집 식물 이름 4곳을 재료·퀘스트의 롤랜드의 눈물과 통일. 다른 플러그인 필드와 CEL 보존. KR12.5 기준 정적 검증 통과, 실게임 미검증.'),(60826,'429496790426','8280147','5.0.7-kr1.1','PFP_5.0.7-kr1.1_OpenMW-KR12.5.zip','책 제목과 마니크키 상점 간판 3곳 통일. 대사 12개의 명시 링크 표시 범위 교정 및 TOP 별칭 3개 추가. 표시 대사와 연결 대상·다른 ESM 필드 보존. KR12.5 기준 정적 검증 통과, 실게임 미검증.')]
reports=[]
for mid,uid,gid,version,filename,log in targets:
 mod=call(f'/v3/games/morrowind/mods/{mid}')['data'];assert str(mod['id'])==uid
 assert str(mod['version']).casefold()==version.casefold()
 versions=call(f'/v3/mod-files/{gid}/versions')['data']['versions']
 candidates=[v for v in versions if str(v.get('version','')).casefold()==version.casefold() and str(v.get('category','')).casefold()!='removed']
 assert len(candidates)==1
 v=candidates[0];fid=v['game_scoped_id'];links=call(f'/v1/games/morrowind/mods/{mid}/files/{fid}/download_link.json')
 with urllib.request.urlopen(links[0]['URI'],timeout=120) as r:download=r.read()
 expected=hashlib.sha256((Path('dist')/filename).read_bytes()).hexdigest()
 assert hashlib.sha256(download).hexdigest()==expected,'Published bytes mismatch'
 logs=call(f'/v1/games/morrowind/mods/{mid}/changelogs.json')
 assert isinstance(logs,dict)
 if not any(k.casefold()==version.casefold() for k in logs):call(f'/v3/mods/{uid}/changelogs',{'version':version,'changelog':log})
 reports.append(dict(modid=mid,uid=uid,file_group=gid,file_id=fid,version=version,sha256=expected,download_verified=True))
 print('NEXUS_PUBLISHED_BYTES_VERIFIED',mid,version,expected)
Path('dist/NEXUS_MODS_PUBLICATION_VERIFICATION.json').write_text(json.dumps(reports,indent=2),encoding='utf8')
