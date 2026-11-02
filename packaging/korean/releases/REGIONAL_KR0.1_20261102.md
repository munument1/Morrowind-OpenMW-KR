# 지역 확장 모드 kr0.1 — Nexus 수동 업로드용 덮어쓰기 ZIP

2026-11-02 현재 검증된 Windows/OpenMW 0.51 KR 배포 복사본에서 4개의 개별 덮어쓰기 압축 파일을 만들었다. 업로드·공개는 사용자가 이미 만들어 둔 Nexus 페이지에서 직접 수행한다. GitHub에는 ZIP/원본 ESM/ESP를 올리지 않고, 번역 변경 데이터·빌더·체크섬만 보존한다.

| 모드 | 원본 버전 | Nexus 업로드 파일명 | 구성 |
|---|---|---|---|
| Project Cyrodiil | 26.09a | Cyr_Main-kr0.1.zip | Data Files/Cyr_Main.ESM + cel/top/mrk/jrn |
| Skyrim: Home of the Nords | 26.09a | Sky_Main-kr0.1.zip | Data Files/Sky_Main.ESM + cel/top/mrk/jrn |
| Tamriel Data | 26.08 | Tamriel_Data-kr0.1.zip | Data Files/Tamriel_Data.esm + cel/top/mrk/jrn |
| Tamriel Rebuilt | 26.11.2 | TR_Mainland-kr0.1.zip | Data Files/TR_Mainland.esm + 선택적 TR_Factions.esp + cel/top/mrk/jrn |

각 압축의 README_KO_kr0.1.txt에는 설치 방법, 원본 모드 설치 필요성, 기능별 ESP 활성화 조건 및 주의사항이 들어 있다. 파일별 정확한 플러그인 SHA-256, ZIP SHA-256, TES3 레코드 수, 마스터 의존성 크기 및 esmtool 결과는 옆의 REGIONAL_KR0.1_20261102.json에 고정했다.

## 사용법

1. 대상 원본 모드와 필요한 리소스를 먼저 설치한다. Tamriel Data 26.08은 Project Cyrodiil / Skyrim: Home of the Nords / Tamriel Rebuilt와 버전을 맞춘다.
2. 사용자는 이미 준비한 각 Nexus 페이지에 해당 ZIP 하나씩 수동 업로드한다.
3. 게임 이용자는 MO2에서 한국어 ZIP을 원본보다 나중에 덮어쓰도록 배치한다. 원본 리소스는 유지하고 같은 이름의 ESM/ESP를 교체한다.
4. TR_Factions.esp는 Faction Integration 옵션을 사용하는 경우에만 활성화한다.
5. OpenMW-KR 관련 사이드카 .cel/.top/.mrk/.jrn도 반드시 한국어 ESM과 같은 버전으로 묶어 설치한다.

## QA 및 배포 한계

- 4개 플러그인 TES3 구조·고정 해시·esmtool 검사 통과, ZIP CRC 및 압축 내부 각 멤버의 SHA-256 확인.
- 현행 Tamriel_Data.esm 18,536,570바이트, TR_Mainland.esm 248,680,022바이트에 대한 관련 TES3 MAST/DATA 크기 일치 확인.
- TR_Mainland 마지막 4차 표시 문자열 검수 및 재패키징 검증 결과 반영: 본편 ESM SHA-256 1627359756ab5a429893044a8337a10b8688c5f5cdf1fa4ecdab628dbaa8a183, Factions 7906b753a801085e5984419575834692f5ac1c618cb5925a9a42b1d8c949e2fd.
- 이전 번역 데이터의 NOT_REVIEWED, 원문 보존 필드, 암묵적 토픽 연결 및 TR 숫자·구조 보류 3건을 임의로 해결된 것으로 표시하지 않는다. 실게임/퀘스트 스테이지 검증은 진행하지 않았다.
- kr0.1은 정적 테스트판이며 공식 원본 버전과 독립적인 한국어 덮어쓰기 패치다.

## GitHub 번역 원본 관리

현재까지 공개한 번역 변경 데이터: translations/openmw-kr/cyr-main, sky-main, tamriel-data, translations/tamriel-rebuilt/26.11.2-kr0.1. 최종 4차 TR 표현 수정은 remaining_display_changes_round4_20261102.jsonl.gz 등에 있다. 원본 전체 플러그인과 외부 모드 리소스는 저장소에 포함하지 않았다.

packaging/korean/tooling/package_regional_kr01.py는 Windows의 기존 검증된 배포 복사본에서 ZIP을 재생성한다. 원본 영어 ESM부터 번역을 전체 재적용하는 완전 독립 빌더는 아니며, 소스와 결과 해시가 변할 경우 재빌드를 중단한다.
