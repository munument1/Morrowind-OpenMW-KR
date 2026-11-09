"""Promote verified direct topic data into numbered, inspectable release archives."""
from pathlib import Path
import zipfile,json,hashlib,shutil

ROOT=Path.cwd();OUT=ROOT/'release-KR12.9';OUT.mkdir(exist_ok=True)
QA=ROOT/'direct-topic-fixes-20261109'
REPO='munument1/Morrowind-OpenMW-KR';TAG='openmw-0.51.0-kr12.9'
URL='https://github.com/'+REPO+'/releases/tag/'+TAG
ORDER='Morrowind.esm → Tribunal.esm → Bloodmoon.esm → Morrowind_Korean_ReTranslation.esp → Tamriel_Data.esm → 사용 지역 모드 → TR_Factions/Rebirth 및 기존 지역 모듈'
NOTE=f'''OpenMW 한국어 토픽 데이터 업데이트 — 2026-11-09

설치 순서: {ORDER}
본편 한글 패치는 공식 본편/확장팩 바로 다음에 둡니다. OpenMW 런처에서 순서를 확인하십시오.
원본 게임과 지역 모드 리소스는 별도로 설치해야 합니다. 새 플러그인은 추가하지 않습니다.

본편: KR12.9. 기존 가입 링크 4곳, 초대·탈로스 교단·애완동물 판매 3곳,
카이우스 일지와 쌍둥이 등불 소문 5곳 수정. 표시 문구와 퀘스트 조건 보존.
TR/Tamriel Data/Cyrodiil: kr0.3. AddTopic 이름 17곳 수정.
기존 Rebirth 지역 모듈: kr0.3. 같은 AddTopic 이름 2곳 수정.
Sky kr0.2 및 Rebirth 본체 7.2-kr1.2는 기존 파일을 그대로 사용합니다.

8개 구성 597,238 INFO 전후 대조, 비대상 대사 링크 변경·끊어진 명시 링크·별칭 충돌 0.
추가 단위 검사 6개와 공식 배포본 필드 보존 검사 통과.
엔진 실행 파일은 기존 KR12.8과 동일하며 데이터 수정 릴리스입니다.
실게임 NPC 조건별 퀘스트 진행/기존 세이브 검증은 아직 하지 않았습니다.
일부 지역만 설치할 때의 기존 선택 모드 참조 및 테스트 스크립트는 별도 기록했습니다.
이 파일들은 SCTX 원문에서 컴파일하는 OpenMW용입니다.

릴리스와 상세 검증: {URL}
'''
PLAN=[
 dict(source='Morrowind-KR12.8-topic-fixes-QA.zip',asset='Morrowind-Korean-OpenMW-0.51.0-KR12.9-Full.zip',version='0.51.0-KR12.9',mod_id=60496,uid='429496790096',group='8110335',category='main',primary=True,update_main=True,name='OpenMW Korean KR12.9 Windows'),
 dict(source='TR_Mainland-kr0.2-topic-fixes-QA.zip',asset='TR_Mainland-kr0.3.zip',version='26.11.2-kr0.3',mod_id=60844,uid='429496790444',group='8296179',category='main',primary=True,update_main=True,name='Tamriel Rebuilt 26.11.2 Korean kr0.3'),
 dict(source='Tamriel_Data-kr0.2-topic-fixes-QA.zip',asset='Tamriel_Data-kr0.3.zip',version='26.08-kr0.3',mod_id=60845,uid='429496790445',group='8296167',category='main',primary=True,update_main=True,name='Tamriel Data 26.08 Korean kr0.3'),
 dict(source='Cyr_Main-kr0.2-topic-fixes-QA.zip',asset='Cyr_Main-kr0.3.zip',version='26.09a-kr0.3',mod_id=60846,uid='429496790446',group='8296161',category='main',primary=True,update_main=True,name='Project Cyrodiil 26.09a Korean kr0.3'),
 dict(source='Rebirth7.2-Cyr_Sky_Compatibility-kr0.2-topic-fixes-QA.zip',asset='Rebirth7.2-Cyr_Sky_Compatibility-kr0.3.zip',version='7.2-kr0.3',mod_id=60805,uid='429496790405',group='8296377',category='optional',primary=False,update_main=False,name='Rebirth 7.2 Cyr-Sky Korean kr0.3')]
def sha(raw):return hashlib.sha256(raw).hexdigest()
reports=[]
for item in PLAN:
 source=QA/item['source'];target=OUT/item['asset'];changed=[]
 with zipfile.ZipFile(source) as src,zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as dst:
  for info in src.infolist():
   name=info.filename;raw=src.read(info);data=raw
   if name=='README-KOREAN.txt':data=NOTE.encode('utf-8-sig')
   elif name=='README_KO_kr0.2.txt':name='README_KO_kr0.3.txt';data=NOTE.encode('utf-8-sig')
   elif name=='install-korean.ps1':
    data=raw.replace(b'KR12.3.1',b'KR12.9')
   if data!=raw or name!=info.filename:changed.append(dict(before=info.filename,after=name))
   dst.writestr(name,data,compress_type=info.compress_type)
  dst.writestr('KR12.9-RELEASE-NOTES-KO.txt' if item['mod_id']==60496 else 'kr0.3-RELEASE-NOTES-KO.txt',NOTE.encode('utf-8-sig'))
 with zipfile.ZipFile(source) as a,zipfile.ZipFile(target) as b:
  assert b.testzip() is None and len(b.namelist())==len(set(b.namelist()))
  for name in a.namelist():
   if name not in {c['before'] for c in changed}:assert a.read(name)==b.read(name),name
   if name.lower().endswith(('.esp','.esm','.top','.mrk','.jrn','.cel','.exe','.dll')):
    assert a.read(name)==b.read(name),'Validated game payload changed: '+name
 digest=sha(target.read_bytes());(OUT/(target.name+'.sha256')).write_text(digest+'  '+target.name+'\n',encoding='ascii')
 item['sha256']=digest;item['bytes']=target.stat().st_size
 reports.append(dict(asset=item['asset'],verified_QA_source_sha256=sha(source.read_bytes()),metadata_only_changes=changed,all_validated_game_payloads_identical=True))
for name in ('Sky_Main-kr0.2.zip','Morrowind_Rebirth7.2-kr1.2.zip'):
 shutil.copy2(ROOT/name,OUT/name);digest=sha((OUT/name).read_bytes())
 (OUT/(name+'.sha256')).write_text(digest+'  '+name+'\n',encoding='ascii')
 reports.append(dict(asset=name,sha256=digest,unchanged_existing_release=True))
manifest=dict(tag=TAG,required_order=ORDER,archives=reports,gameplay_tested=False,
 native_info_comparisons=597238,additional_plugins=0)
(OUT/'PUBLICATION-MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'NEXUS-PUBLICATION-PLAN.json').write_text(json.dumps(dict(tag=TAG,files=PLAN),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'RELEASE-NOTES-KO.md').write_text(NOTE,encoding='utf-8')
for source,name in ((QA/'검증요약.json','native-verification.json'),(QA/'build-verification.json','direct-data-verification.json')):shutil.copy2(source,OUT/name)
print(json.dumps(dict(tag=TAG,changed_assets=len(PLAN),unchanged_assets=2,output=str(OUT)),ensure_ascii=False))
