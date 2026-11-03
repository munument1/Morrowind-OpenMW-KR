# OpenMW KR12.6 — 설치된 영어 원본 3개 ESM 독립 QA (2026-11-03)

**상태: 정적 원본 데이터 대조 완료 / 실제 게임 진행·전체 지역 모드 QA 미완 / 정식 릴리스 변경 없음**

## 실제 입력

Remote Desktop Commander로 사용자의 허가된 온라인 Deck_Seung 컴퓨터에서 설치된 원본 `Morrowind.esm`, `Tribunal.esm`, `Bloodmoon.esm`을 읽기 전용으로 검사했다. KR12.6 공식 Windows 전체 ZIP을 내려받아 고정 SHA 검증했다.

| 대상 | SHA-256 |
|---|---|
| Morrowind.esm | `5c3c8c2cbd20e25901b59b3ece33d36b7ef0e3d60ad8d11828bcc61a5ead1647` |
| Tribunal.esm | `2ace511f23cc2a9ddd5f3aa59c7919789b9378cf4b17c8ae3375dd6b782f3f2b` |
| Bloodmoon.esm | `bd27090d0e6ad4c1bf1abc83f1a2dac56fcc82cae7bfe8263c413fb301801357` |
| KR12.6 ZIP | `2f4bb6b9cfd5916fd9574b6207628e4bb16f8bdc4f1c68fc1ef7581c970989e9` |
| KR12.6 ESP | `c52a5355752ef0be93fadeca9c95ca00d7cad808f713ce92a624a67d0cc277df` |

## 전수 검수 수치

- 영어 원본 세 ESM에 존재하는 INFO 레코드 합계: **36,954**, 한국어 ESP INFO: **31,716**.
- 한국어 고유 INFO ID: **31,498개**, 전부 영어 원본 ID와 일치. 원본에 존재하지 않는 KO INFO ID: **0개**.
- 중복 없는 영어·한국어 1:1 INFO **28,115개**에 대해 핵심 조건 필드(ONAM/FNAM/RNAM/CNAM/ANAM/DNAM/SCVR/INTV/FLTV/DATA/QSTI/QSTN/QSTF) 비교 시 불일치 **0개**.
- 다른 INFO의 대응 관계를 이용한 영어 DIAL ↔ 한국어 DIAL 매핑을 확장하면 **30,819/31,716건(97.172%)**에서 원본 DIAL에 속하는 INFO와 핵심 조건 바이트가 일치.
- 남은 **897건**도 동일 INFO ID를 가진 원본에서 핵심 조건이 일치함은 확인했으나, 영어 DIAL↔한국어 DIAL의 정확한 짝은 **확인되지 않아 보류**.
- 결과적으로 **31,716개 전부 ID 기반으로 원본과 조건이 동일한 항목이 존재**하지만 이것이 모든 NPC 접근성·토픽 진행을 증명하지는 않음. 별도 원본/번역 대사 파서 검수는 [기존 2026-11-03 보고서](2026-11-03_topic_discovery_full_audit.md) 참조.

## 실물 시험 후보 패키지 (사용자 PC 로컬, 정식 배포 금지)

이전 [네이티브 OpenMW C++ 파서 검수](https://github.com/munument1/Morrowind-OpenMW-KR/actions/runs/41644351838)에서 확인된 본편 가입 대사 5건(`1341756011233729353`, `13288348632198840`, `2435795662798020478`, `22990247762784528944`, `41295659805015760`)에 한국어 표시 내용 불변 `@...#` 명시 링크를 부착한 **UNRELEASED** ZIP을 제작.

- 한글 ESP의 **5개 INFO.NAME만** 변경. 나머지 ESP 서브레코드 및 ZIP 파일 멤버의 압축 해제 내용 전부 동일, 원본 48,146 TES3 레코드 수 유지.
- 시험 후보 ESP SHA-256 `b23701ec5ceb2e2b8bb777971dd1352b014fc118834dfea978bd065332f7e1ef`
- 시험 ZIP SHA-256 `3e9c3b2e3dcf88391c2e966553d86159638e098ca1e3e4165fd3a3b460961589`
- 해당 후보는 기존 일반 토픽을 일부 가릴 수 있음. **실제 NPC/퀘스트 조건과 겹침 영향을 실게임에서 검증하기 전 릴리스하지 않음**.

## 지역 모드 릴리스 차단 조건

해당 기기에는 원본 `Cyr_Main 26.09a`, `Sky_Main 26.09a`, `Tamriel Data 26.08` 자료가 있으나, 보관된 `Tamriel Rebuilt` 원본은 **26.09.27**로 최신 번역 기준 **26.11.2**와 일치하지 않는다. 주 작업 PC인 DESKTOP-5FSA3DE는 오프라인이었고 해당 기기의 최신 완성 한국어 ESM/ESP 및 호환 패치를 실물 검사하지 못함.

따라서 **지역 확장 모드 전부를 최신 원본 대비 완전 검수했다고 주장하거나, 이전 판본을 대신 써서 정식 릴리스를 생성하면 안 됨**. 최신 원본과 최종 실제 한글 ESM을 확보한 뒤 NPC 필터/대화 인식/저널/스크립트/로드 순서 검수 및 실게임 테스트를 완료해야 한다.

이번 원본 기반 QA는 사용자 기기 내 격리된 작업 폴더에만 검사 스크립트·JSON 결과·시험 ZIP을 작성했다. 설치된 게임·세이브·상용 원본 파일·기존 GitHub/Nexus 릴리스는 변경하지 않았다.
