# OpenMW-KR 전용 ESM 교체형 번역

**원본과 같은 이름의 번역 ESM으로 교체하는 배포 구성**입니다. 별도 번역 ESP나 OMWADDON을 추가하지 않습니다. 원본 모드의 필수 자산은 유지하고, 교체 ESM 옆에 같은 stem의 CEL/TOP/MRK/JRN을 함께 둡니다.

| 모드 | 원문 버전 | 번역 필드 | CEL 표시명 | TOP/MRK/JRN 연결(각각) |
|---|---|---:|---:|---:|
| [Tamriel Data](tamriel-data/26.08/manifest.json) | 26.08 HD | 25,788 | 2 | 111 |
| [Project Cyrodiil](cyr-main/26.09a/manifest.json) | 26.09a Hotfix 1 | 15,035 | 552 | 606 |
| [Skyrim: Home of the Nords](sky-main/26.09a/manifest.json) | 26.09a | 8,202 | 431 | 355 |

GitHub에는 번역 데이터·보조 표·도구만 저장합니다. ESM과 설치 ZIP은 게시하지 않으며, 모드 릴리스는 Nexus Mods에서만 합니다.

## 설치 파일의 역할

`Tamriel_Data`의 예:

```text
Data Files/
  Tamriel_Data.esm
  Tamriel_Data.cel
  Tamriel_Data.top
  Tamriel_Data.mrk
  Tamriel_Data.jrn
```

- ESM: 대사·저널·책 본문과 NPC·아이템 등의 표시 이름.
- CEL: 영문 셀 이름 → 한국어 표시명. CELL.NAME, 배치 오브젝트 NAME, 문 목적지 DNAM과 지역 참조 RGNN은 원문 보존.
- TOP: 명시 링크의 표시 표현 → 실제 원문 토픽 ID.
- MRK: 실제 원문 토픽 ID → 한국어 본문 검색어.
- JRN: 저널 검색 표현 → 실제 원문 토픽 ID. 저널 본문 전체의 번역 파일이 아님.

보조 파일은 UTF-8 BOM을 붙인 탭 구분 텍스트입니다. 실제 일반 대화 DIAL을 대상으로 하는지, 중복·역방향 연결·본편 및 메인랜드와의 충돌을 검사합니다. 원래 DIAL.NAME, INFO.INAM/PNAM/NNAM, 조건, 스크립트, 마스터 목록, CELL과 문 목적지 ID를 바꾸지 않습니다.

기존 셀·이름 번역과 스카이림 우선 용어 자료를 재사용하고, [보류 지명·토픽의 번역 1,109종](term_translations_20261102.json)을 추가했습니다. 반복되는 지명 구성요소를 조합하여 실사용 셀 985개를 번역했으며, 내부용 셀 19개는 원문 보존합니다. 실사용 지명과 토픽 표현의 미번역은 0개입니다. 새 이름의 음역은 잠정 표기이고 `NOT_REVIEWED`를 유지합니다.

토픽 1,229개 중 1,072개는 TOP/MRK/JRN으로 연결하고, 157개는 번역은 있으나 자동 연결을 보류합니다. 짧아 오인하기 쉬운 검색어 119개, 본편·메인랜드의 기존 연결과 충돌하는 표현 38개입니다. 모드별 `sidecar_holds.json`에 번역과 사유를 보관하며, 이들에 임의의 토픽 ID를 연결하지 않습니다. **KR12.5의 MRK는 본문 검색용이므로 토픽 목록 제목까지 자동 번역하지 않습니다.** 이번 작업에서 엔진/UI는 변경하지 않았습니다.

### 이슈 #71: 지역 모드 대화 주제의 표시 이름 (차기 엔진 패치)

기존 KR13 이하 실행 파일은 오른쪽 대화 목록에 원문 DIAL 토픽 ID를 표시합니다. 이슈 #71 수정 후보에서는 목록에 MRK의 한국어 검색 표현을 표시하되, 내부 토픽 ID, NPC 조건, 저장 파일과 클릭 결과는 원래 ID를 유지합니다. MRK가 없거나 검색어와 표시명이 달라야 할 경우 선택적인 UTF-8 BOM 탭 구분 `.dsp` 파일(`원본 토픽 ID<TAB>한국어 표시명`)을 함께 배치할 수 있습니다. `.dsp` 값은 대화 텍스트의 자동 링크·토픽 습득·조건 판단에 참여하지 않습니다.

`translations/tamriel-rebuilt/26.11.2-kr0.1/TR_Mainland.dsp`에는 제보된 4개 토픽의 표시명 보완이 있습니다. `Alju-Deekus`는 기존 MRK에 표기가 있으므로 DSP 중복 등록을 피합니다. **이 변경은 소스 코드 후보이며 기존 KR13 배포본에는 포함되지 않습니다.** OpenMW 실행 파일을 새로 빌드하고 동일 버전 ESM 및 사이드카를 함께 검증한 다음 배포해야 합니다.

같은 이슈의 야외 자동 인사(HUD 자막)는 `@제국`과 숨김 문자 `0x7F`가 문자 그대로 출력되던 경로를 고칩니다. 자막을 전달하기 전에 기존 `visibleKoreanTopicText`를 적용해 표시 문구만 남깁니다. 실제 INFO 레코드와 퀘스트 조건은 변경하지 않습니다.

추가 점검에서 일지의 주제 색인 목록과 주제별 페이지 제목도 원래 영문 DIAL ID를 직접 사용함을 확인했습니다. 후속 `0019-korean-journal-topic-captions.patch`는 이 두 화면에 동일한 DSP/MRK 표시명을 적용하며, 한국어 초성 색인도 표시명을 기준으로 분류합니다. 일지의 원본 주제 ID, 클릭 대상, 퀘스트 기록 및 저장 데이터는 변경하지 않습니다. 이 부분 역시 새 엔진 빌드와 실제 일지 클릭 검증 전까지 배포 대상이 아닙니다.

`strings.jsonl.gz`의 검수 상태는 기존 그대로입니다. Tamriel Data의 남은 책 722개는 모두 미검수 상태이며, 기존 가상언어 보존과 순화판 재사용도 유지했습니다. 메인랜드의 별도 v3 작업 자료는 변경하지 않았습니다.

## 재빌드와 검사

```sh
python translations/openmw_kr_replacement.py --dataset translations/openmw-kr/tamriel-data/26.08 --check-only
python translations/openmw_kr_replacement.py --dataset translations/openmw-kr/tamriel-data/26.08 --source "원본/Tamriel_Data.esm" --output "새출력/Tamriel_Data_KR_TEST"
python -m unittest discover -s translations -p test_openmw_kr.py
```

다른 모드도 dataset 경로와 해당 원본을 바꿔 같은 도구로 만듭니다. 원본 버전·위치·하위 레코드 해시·태그·변수·연결과 출력 해시를 검사합니다. 새 ESM은 기존에 검증한 번역 테스트본과 바이트 단위로 같습니다. 원본이나 기존 출력 디렉터리를 덮어쓰지 않고, 실제 게임 폴더에 적용하지 않습니다.

배포 시 사용자는 원본 모드의 필수 자산을 설치하고 번역 ESM과 보조 파일로 덮어씁니다. 모드 관리자를 쓰면 번역 폴더가 같은 이름 ESM의 파일 우선순위를 갖도록 합니다. 같은 ESM은 한 번만 로드하며, 다른 버전 원본과 혼용하지 않습니다.

코드 검사·전체 레코드 파싱과 OpenMW esmtool 검사는 통과했습니다. 실게임 대화/저널 클릭·퀘스트·글꼴·저장/불러오기는 아직 검증하지 않았습니다. API 추가 호출, 검수 상태 승격, 게임 적용 및 Nexus 업로드는 하지 않았습니다.
