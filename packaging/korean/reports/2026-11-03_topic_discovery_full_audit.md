# 모로윈드 한국어 토픽 인식 전수 재검사 — 2026-11-03

**상태: READ-ONLY / 퀘스트 완료 여부 미검증 / 본편·모드 배포본 수정 없음.**

- [성공한 GitHub Actions 재검사](https://github.com/munument1/Morrowind-OpenMW-KR/actions/runs/41641911018)
- Actions **Morrowind-KR126-Topic-Preflight-QA** 아티팩트: `core_kr126_legacy_scan.json`, `cross_mod_kr126_topic_risk_audit.json`, `cross_mod_kr126_native_verification.json`, `native_npc_topic_evidence.json`, `bilingual_native_topic_diff.json`, `bilingual_npc_priority.json`, `mod_schemas.json`.
- 검사 스크립트: `audit_cross_mod_topic_gaps.py`, `verify_native_topic_gap_report.py`, `audit_native_bilingual_topic_differential.py`.
- 모든 입력은 GitHub KR12.6 공식 ZIP 및 저장소의 출처·해시로 추적되는 번역 자료. 테스트용으로 다운로드한 Rebirth kr1.1 및 Patch for Purists kr1.1 패키지는 **변경하지 않음**.

## 왜 지난 검수를 통과했나?

기존 검수는 DIAL 존재/명시 `@...#` 연결/TOP 키/허용 어미 목록 및 ESP 구조에 집중했다. 실제 엔진의 키워드 검색에서 **한국어로 자연스럽게 재표현된 문장이 원래의 토픽 검색어와 맞지 않는지**, 그리고 해당 토픽이 NPC의 가입·의뢰 진행에 필수적인지까지 연속 경로로 검사하지 않았다.

사례 1: `평신도 회원` `INFO 1341756011233729353`의 `제국 교단에 가입하시겠습니까?` 는 `제국 교단에 가입` 토픽을 인식하지 못한다. `@제국 교단에 가입#하시겠습니까?` 는 동일 한국어 표시 내용으로 엔진 파서 인식 성공. 실제 랄라티아/플레이어 조건 실증은 별도.

사례 2: 지역 모드에서는 `join the Fighters Guild` 토픽의 MRK 검색어가 `전사 길드 가입`인데, 실제 한국어 대사가 `전사 길드에 가입하고 싶은가?` 로 자연스럽게 번역된 경우 문자열 일치가 성립하지 않는다.

## 1차 본편 및 모드 원문 전수검사

| 검사 | 결과 |
|---|---:|
| 본편 KR12.6 DIAL | 2,060 |
| 본편 KR12.6 INFO (저널 등 전체) | 31,716 |
| 기존 KR12 게임 전체 어휘 검수기의 추가 후보 | 5,741 |
| 별도 범용 스캔(본편+지역+Rebirth/PFP), 일부 중복 16범위 | 136,455 INFO.NAME 행 |
| 범용 스캔 자동 인식 위험 문자열 후보 | 9,531 |
| HIGH/MEDIUM 후보를 **실제 OpenMW KR12.6 C++ 파서**로 검증 | 121 |
| 실제 파서가 기대 토픽을 발견 못한 건수 | 84 |
| 실제 파서가 인식해 초기 후보에서 제외 가능한 건수 | 37 |

**84건은 '파서 미인식 후보'이며 게임 진행 장애 확정 건수가 아니다.** 검사 시 토픽을 모두 알려진 것으로 시드했지만 현재 NPC가 해당 대답을 보유하는지, 저장 게임의 저널 상태, 퀘스트 결과 스크립트, 다른 플러그인 로드 순서는 평가하지 않았다.

### 가입·승급 관련 본편 우선 확인할 INFO

- `1341756011233729353` : 제국 교단 / 랄라티아 경로(동일 교단용 INFO 15건 및 가입 스크립트 확인)
- `1403130214698924047` : 도둑 길드 가입 / 승진 대화, 같은 파벌 INFO 16건, `PCJoinFaction` 존재
- `22990247762784528944` : 텔바니 가문 가입 / 승진 대화, 같은 파벌 INFO 16건, `PCJoinFaction` 존재
- `41295659805015760` : 마법사 길드 가입 / 임무 대화, 같은 파벌 INFO 7건, `PCJoinFaction` 존재
- `571631012022329261` : 레도란 가문 가입 / Neminda, 동일 NPC INFO 11건, `PCJoinFaction` 존재
- `13288348632198840`, `2435795662798020478` : 전사 길드 / Hrundi 및 Eydis의 가입 안내. 동일 NPC 가입 INFO의 존재는 이 테스트에서 확인하지 못함.

위 항목 중 일부는 가입을 이미 습득했거나 다른 경로로 전달받아 게임 진행에 영향이 없을 수 있다. `가입` 토픽 안에 동일한 말이 다시 등장하는 것은 자기 자신에게 재링크할 필요가 없는 문맥일 수도 있다.

## 원본 영어/번역 한국어 **동일 INFO** 네이티브 파서 비교

각 지역 모드의 **MRK로 명시적으로 매핑된 DIAL만** 대상으로, 영어 원문의 DIAL 키워드와 한국어 번역+MRK/TOP을 각각 같은 OpenMW 파서로 인식시켜 대조했다. 원작과 번역을 실제 게임에서 동시에 플레이해 비교한 것은 아니다.

| 번역 자료 | 영어에서는 인식되지만 한국어에서는 미인식 |
|---|---:|
| Project Cyrodiil 26.09a | 5,076 |
| Skyrim: Home of the Nords 26.09a | 2,411 |
| Tamriel Data 26.08 | 1,071 |
| TR_Mainland 26.11.2 | 10,069 |
| **지역 모드 4종 합계** | **18,627** |
| Rebirth Cyrodiil 호환판 | 5,077 (상당 부분 중복) |
| Rebirth Skyrim 호환판 | 2,411 (상당 부분 중복) |
| **6자료 단순 합계** | **26,115 (중복 포함)** |

이들은 **회귀 검토 후보**다. 영어에서 지명·일반 명사가 토픽으로 걸리고 한국어에서는 더 자연스럽게 번역돼 인식하지 않는 *의도된 차이*도 포함한다. 또한 **저널 INFO**도 포함하므로 모든 차이를 NPC 대화 오류나 진행 불가로 해석해서는 안 된다.

간단한 우선순위 휴리스틱으로 높은 등급을 받은 것은 Cyrodiil 57, Skyrim 20, Tamriel Data 51, Rebirth 호환판 68(중복 가능) = 196건. 이 중 기록 ID 규칙을 참고해 명백한 저널 형태를 제외한 `HIGH_REVIEW` 검토 예시는 각각 47, 18, 50건(호환판 중복 제외). 이는 원본 ESM의 실제 DIAL.DATA를 검증한 정식 NPC 분류가 아니며, 담당 NPC/상태 진단이 필요하다. TR_Mainland에서 HIGH 0은 **문제가 없다는 뜻이 아니라, 이번 가입·임무 키워드 휴리스틱이 높은 점수를 준 사례가 없다는 뜻**이다.

### 실제 비교된 우선 검토 대상

| 지역 자료 | 행 / 부모 DIAL | 영어에서 인식된 토픽 | 번역문 및 문제 |
|---|---|---|---|
| Cyr_Main | `Cyr_Main.ESM@45291051` / `Fighters Guild` | `join the Fighters Guild` | “전사 길드에 가입하고 싶은가?” vs MRK “전사 길드 가입” |
| Cyr_Main | `Cyr_Main.ESM@45516511` / `Kingdom of Anvil` | `join the Kingdom of Anvil` | “앤빌 왕국에 가입하려고 하십니까?” vs MRK “앤빌 왕국 가입” |
| Cyr_Main | `Cyr_Main.ESM@46099084` / `Thieves Guild` | `join the Thieves Guild` | “도둑 길드에 들어가고 싶은 거야?” vs MRK “도둑 길드 가입” |
| Sky_Main | `Sky_Main.ESM@29500154` / `Advancement` | `join the Fighters Guild` | “전사 길드에 가입할래?” vs MRK “전사 길드 가입” |
| Sky_Main | `Sky_Main.ESM@29755203` / `Fighters Guild` | `join the Fighters Guild` | “전사 길드에 가입하고 싶나?” vs MRK “전사 길드 가입” |
| Sky_Main | `Sky_Main.ESM@30463186` / `fix your mistake` | `join the Thieves Guild` | “그래도 도둑 길드에 가입하고 싶나?” vs MRK “도둑 길드 가입” |
| Tamriel_Data | `Tamriel_Data.esm@15117505` / `Advancement` | `join House Indoril` | “인도릴 가문에 가입해야 해.” vs MRK “인도릴 가문 가입” |
| Tamriel_Data | `Tamriel_Data.esm@15120535` / `Advancement` | `join the Ordinators` | “오디네이터에 입단하겠다는 것입니까?” vs MRK “오디네이터 가입” |

## 품질 보증 보완 요구

1. 영어 DIAL ID → 한국어 MRK/TOP → **실제 INFO 영어/한국어 파서 링크 결과**를 일대일 비교하고, 특히 `Greeting`, `Advancement`, `Orders`, `join...`, `duties`, `quest` 관련 소실을 우선 정렬.
2. 원본 ESM의 DIAL.DATA로 **NPC 대사와 저널을 분리**하고, 동일 NPC와 파벌 조건/SCVR/저널 진행 상태를 대조해 필수 연결인지 확인.
3. 본편과 지역 모드를 **함께 로드했을 때 TOP/MRK 중복·우선순위**가 어떤 링크에 영향을 주는지 조사. 이번 독립 플러그인 검사는 통합 로드 순서까지 증명하지 못함.
4. 실제 진행을 막는 것으로 확인된 항목만 원본 문구 보존형 명시 링크와 충돌 없는 TOP 별칭으로 교정. 일괄 `@...#` 삽입, 전체 어미 무제한 허용, 원본 ID 변경 금지.
5. 수정 뒤 원문·번역 동일 INFO의 C++ 파서 비교를 CI 게이트로 사용하고, 최소 1개의 가입/승진/퀘스트 실게임 테스트를 수행.

이번 검사는 **진단 워크플로·보고서 생성만 수행**. 번역 ESM/ESP, 원본 모드, 설치기, 현재 Nexus 릴리스, 게임 저장 데이터는 변경하지 않았다.
