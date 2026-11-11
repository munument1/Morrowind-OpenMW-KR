#!/usr/bin/env python3
"""Build an INTERNAL, deterministic, originals-excluded KR13 regional patch package.

This builder never bundles any third-party source or translated ESM/ESP master.
It only includes SHA-pinned BSDIFF40 deltas and authored EET name-mapping
sidecars, an applicator, manifest and documentation. Output remains PRIVATE
pending rights review and public release approval.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED

STAMP=(2026,11,11,12,0,0)
NATIVE_EXT={'.esm','.esp'}
SIDECARS={'.top','.jrn','.cel','.mrk'}
EXPECTED_ARCHIVES={
 'TR_Mainland-kr0.4.zip':{'Data Files/TR_Mainland','Faction intergration/TR_Factions'},
 'Tamriel_Data-kr0.4.zip':{'Data Files/Tamriel_Data'},
 'Cyr_Main-kr0.4.zip':{'Data Files/Cyr_Main'},
 'Sky_Main-kr0.3.zip':{'Data Files/Sky_Main'},
 'Rebirth7.2-Cyr_Sky_Compatibility-kr0.4.zip':{
   'Compability Patches/Project Cyrodiil [For Rebirth]',
   'Compability Patches/Skyrim Home of the Nords [For Rebirth]'}
}
PREFIXES={
 'Data Files/TR_Mainland':'TR_Mainland',
 'Faction intergration/TR_Factions':'TR_Factions',
 'Data Files/Tamriel_Data':'Tamriel_Data',
 'Data Files/Cyr_Main':'Cyr_Main',
 'Data Files/Sky_Main':'Sky_Main',
 'Compability Patches/Project Cyrodiil [For Rebirth]':'RebirthCompat',
 'Compability Patches/Skyrim Home of the Nords [For Rebirth]':'RebirthCompat'
}
NAME='Morrowind-KR13-Regional-PatchOnly-kr0.4.zip'

def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def canonical(j):return (json.dumps(j,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf8')
def add(z:ZipFile,name:str,data:bytes):
 assert '\\' not in name and '..' not in Path(name).parts and not name.startswith('/')
 info=ZipInfo(name,date_time=STAMP)
 info.compress_type=ZIP_DEFLATED
 info.external_attr=(0o100644<<16)
 info.create_system=3
 z.writestr(info,data,compress_type=ZIP_DEFLATED,compresslevel=9)

def build(source:Path,patchroot:Path,applier:Path,out:Path):
 assert source.is_dir() and patchroot.is_dir() and applier.is_file()
 assert not out.exists(),f'output exists: {out}'
 raw=json.loads((patchroot/'manifest.json').read_text('utf8'))
 assert raw['schema_version']==1 and raw['format']=='BSDIFF40' and len(raw['entries'])==7
 assert {e['group'] for e in raw['entries']}=={'common','standard','rebirth'}
 patch_files={}
 for e in raw['entries']:
  p_rel=e['patch']['path']; assert p_rel.startswith('patches/') and p_rel.count('/')==1
  p=patchroot/p_rel
  assert p.is_file(); b=p.read_bytes(); assert b[:8]==b'BSDIFF40' and sha(b)==e['patch']['sha256']
  assert p_rel not in patch_files
  patch_files[p_rel]=b
 sidecars={};sources={}
 for archive,expected in EXPECTED_ARCHIVES.items():
  p=source/archive; assert p.is_file(),p
  sources[archive]=sha(p.read_bytes())
  with ZipFile(p) as z:
   assert z.testzip() is None
   found=set()
   for info in z.infolist():
    if info.is_dir():continue
    parts=Path(info.filename)
    if parts.suffix.lower() in NATIVE_EXT:
     continue # CRITICAL: never package any full ESM/ESP, even translated versions
    if parts.suffix.lower() not in SIDECARS:continue
    stem=str(parts.with_suffix('')).replace('\\','/')
    assert stem in expected and stem in PREFIXES,(archive,stem)
    found.add(stem)
    name='sidecars/'+PREFIXES[stem]+'/'+parts.name
    data=z.read(info)
    if name in sidecars:
     # Cyr/Sky standard and Rebirth alternatives share exact EET sidecars.
     assert sidecars[name]==data,name
    else:sidecars[name]=data
   assert found=={x for x in expected if x != "Faction intergration/TR_Factions"},(archive,found,expected)
 assert len(sidecars)==24,len(sidecars)
 app=applier.read_bytes()
 assert b'bsdiff4' not in app.split(b'\n',80)[0:2] # installer is Python standard library only
 readme='''# 모로윈드 OpenMW KR13 지역 확장 모드 패치 (비공개 QA 후보)

이 자료에는 Tamriel Rebuilt, Tamriel Data, Project Cyrodiil, Skyrim: Home of the Nords, Rebirth 호환 모드의 **원본 및 번역본 ESM/ESP 전체가 포함되지 않습니다.** 원본 모드는 각 제작자의 공식 배포처에서 사용자가 직접 받아야 합니다.

## 지원 원본 버전
- Tamriel Rebuilt 26.09.27 — TR_Mainland.esm / TR_Factions.esp
- Tamriel Data HD 26.08 — Tamriel_Data.esm
- Project Cyrodiil 26.09a — Cyr_Main.ESM
- Skyrim: Home of the Nords 26.09a — Sky_Main.ESM
- Morrowind Rebirth 7.2 — Project Cyrodiil [For Rebirth].esm / Skyrim Home of the Nords [For Rebirth].esm

SHA-256이 정확히 일치하는 공식 **영문 원본**만 지원합니다. 파일명이 같아도 다른 버전이면 적용하지 않습니다. 원본 지역 모드의 텍스처·메쉬·음원 등 아트 파일은 별도로 설치해야 합니다.

## 적용 (Python 3 표준 라이브러리만 사용)
1. 공식 영문 원본 ESM/ESP 파일을 별도 `originals` 폴더에 복사합니다(7개 중 사용하는 모드에 필요한 것만). 원본 파일에는 손대지 않습니다.
2. 이 ZIP을 폴더에 압축 해제합니다. 기존 사용자 `Data Files`에 전체 압축 파일을 덮어쓰지 마세요.
3. 새 빈 `output` 폴더를 만듭니다.
4. 명령을 실행합니다.

일반 Cyrodiil/Skyrim 구성:
`python apply_regional_deltas.py --manifest manifest.json --originals-dir originals --output-dir output --mode standard`

Rebirth 7.2의 전용 Cyr/Sky 대체 ESM 구성:
`python apply_regional_deltas.py --manifest manifest.json --originals-dir originals --output-dir output --mode rebirth`

전체를 동시에 **생성만** 할 때:
`python apply_regional_deltas.py --manifest manifest.json --originals-dir originals --output-dir output --mode all`

출력 디렉터리와 영문 원본 디렉터리는 반드시 분리합니다. 패치가 재구성한 ESM/ESP의 SHA-256이 manifest의 목표 SHA와 일치하지 않으면 결과를 적용하지 않습니다.

5. `sidecars/<모드명>/*.top/*.jrn/*.cel/*.mrk`는 대응하는 `output/<모드명>/`에 따로 복사합니다(필요한 모드만). OpenMW 구성의 `data=`는 수정된 각 ESM과 sidecar가 있는 폴더를 가리키도록 설정합니다.

## 로드 순서
일반 구성: Morrowind.esm, Tribunal.esm, Bloodmoon.esm, Morrowind_Korean_ReTranslation.esp (KR13), Tamriel_Data.esm, TR_Mainland.esm, Cyr_Main.ESM, Sky_Main.ESM, TR_Factions.esp (선택).

Rebirth 구성: 위 공통 6개 다음 `Project Cyrodiil [For Rebirth].esm`, `Skyrim Home of the Nords [For Rebirth].esm`, `TR_Factions.esp` (선택), 별도 Rebirth 7.2 메인 ESP와 필요한 Addon을 로드합니다. **일반 Cyr_Main.ESM/Sky_Main.ESM과 [For Rebirth] ESM을 동시에 활성화하면 안 됩니다.**

## 주의
- 이것은 KR13 정식 릴리즈가 아니라 내부 검증용 후보입니다. 게임 원본/기존 설치/개인 저장 파일을 수정하지 않았습니다.
- 원본 번역 패치 범위는 4,187개 후보 전수 분류 중 1,033개 원문 표시 필드의 번역과 별도 FACT.RNAM 778개를 포함한 1,811개 변경입니다. 모든 게임 대사 완역을 주장하지 않습니다.
- PFP 5.0.7과 Rebirth 7.2의 핵심 GUI/저장 검증 및 24개 네이티브 토픽 검사 통과. 전 퀘스트를 끝까지 확인한 것은 아닙니다.
- 개발용 신문 템플릿 72개는 기존 영문 Placeholder가 남아 있으나, 검사한 기본 지역 로드 구성에서 자연 생성 경로는 확인되지 않았습니다. 외부 모드가 이를 사용할 경우 영어가 노출될 수 있습니다.
- 델타 패치 파일 자체에도 원저작물의 파생물과 관련한 권리 문제가 발생할 수 있습니다. 외부 공개 전 각 원저작자의 허가/라이선스를 확인해야 합니다.
'''.encode('utf8')
 pre={'schema_version':1,'published':False,'distribution':'internal patch-only','original_master_bytes_included':False,'patch_format':'BSDIFF40','delta_count':7,'source_regional_zip_shas':sources,'sha256':{},'versions':{'TR':'kr0.4','TD':'kr0.4','Cyr':'kr0.4','Sky':'kr0.3','Rebirth_compat':'kr0.4'}}
 files={'manifest.json':canonical(raw),'apply_regional_deltas.py':app,'README_KO.md':readme,**patch_files,**sidecars}
 for k,v in files.items():pre['sha256'][k]=sha(v)
 files['KR13-REGIONAL-PATCHONLY-MANIFEST.json']=canonical(pre)
 out.parent.mkdir(parents=True,exist_ok=True)
 with ZipFile(out,'x') as z:
  for k in sorted(files):add(z,k,files[k])
 with ZipFile(out) as z:
  assert z.testzip() is None and sorted(z.namelist())==sorted(files)
  assert not any(Path(n).suffix.lower() in NATIVE_EXT for n in z.namelist())
  assert all(sha(z.read(k))==sha(v) for k,v in files.items())
 return {'zip':str(out),'zip_sha256':sha(out.read_bytes()),'zip_bytes':out.stat().st_size,'members':len(files),'patch_bytes':sum(map(len,patch_files.values())),'sidecars':len(sidecars),'excluded_esm_esp':True,'published':False}

def main():
 cli=argparse.ArgumentParser()
 cli.add_argument('--source-regional-zips',type=Path,required=True)
 cli.add_argument('--patch-root',type=Path,required=True)
 cli.add_argument('--applier',type=Path,required=True)
 cli.add_argument('--output',type=Path,required=True)
 a=cli.parse_args()
 print(json.dumps(build(a.source_regional_zips,a.patch_root,a.applier,a.output),ensure_ascii=False,sort_keys=True,indent=2))
if __name__=='__main__':main()
