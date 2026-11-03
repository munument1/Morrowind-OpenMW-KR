# 모로윈드 KR — 영어 원문 ↔ 한국어 토픽 명칭·본문 불일치 네이티브 전체 검사

**2026-11-04 KST · 읽기 전용 QA · 정식 수정판 릴리스 미실시**

## 핵심 결론

기존 가입/승진 14건만의 문제가 아니다. `DIAL`의 한국어 검색어와 NPC가 실제로 말하는 한국어 어절이 다르면 자동 토픽 인식이 빠질 수 있다. 현행 OpenMW-KR `keywordsearch.cpp`는 `.mrk`에서 토픽별 기본 검색어를 불러와 `KeywordSearch::seed`한다. `.top`은 `@...#` 명시 링크의 표기→토픽 이름 매핑이며, **모든 `.top` 별칭을 자동 토픽 검색어로 추가하는 것은 아니다.** 따라서 `.top`에 번역어가 존재한다고 평문에서 자동 인식되리라는 보장은 없다.

## 실제 검사 규모

사용자가 바탕화면에 준비한 원본 ESM/ESP 및 현재 공개 Korean zip(고정 해시)에서 **17개 플러그인 / INFO 160,932개**를 순회한 기존 정적 감사에 더하여, [KR0.51 실제 C++ 토픽 파서를 Windows용으로 컴파일](https://github.com/munument1/Morrowind-OpenMW-KR/actions/runs/41694814730)해서 Deck_Seung에서 영어 원문/한국어판을 직접 비교함.

- 실제 C++ 파서로 원문↔한국어 **1:1 대응 확인된 INFO 157,475개**
- 본편 원본의 중복 INFO ID/선택 필터 등으로 1:1 대상 확정 불가 **3,457개는 HOLD**
- 원문에서 인식된 링크 **248,279개**, 한국어 단독 플러그인 파서에서 같은 토픽 인식 불가 후보 **153,656회**, 누락 후보가 하나 이상 있는 INFO **75,915개**
- 동일 문제가 한 토픽에서 수백 번 반복되는 것을 통합하면 **모드×토픽별 6,249개 검토 묶음**(별도 Rebirth 호환/대체판 중복 포함)
- 번역 본문 안에서 해당 TOP 별칭이 그대로 발견되는 검토 묶음 **642개**. 기존 별칭이 있어도 평문 자동 검색에는 사용되지 않는 경우가 있어, INFO에 안전한 명시 태그를 넣을 여지가 있음.

**주의: 153,656회 / 75,915개 / 6,249개는 확정 오류 수가 아니다.** 영어의 일반 단어 work, good, guard, temple, outlander 등도 토픽 ID와 겹치기 때문에 원문 파서가 후보로 발견한다. 원문의 해당 NPC가 그 토픽을 실제로 알고 있는지, 접근 가능한 퀘스트 상태인지, 다른 모드에서 이미 인식되는지 등은 계산하지 않는다. 이 숫자를 자동 치환 건수나 퀘스트 진행 차단 건수로 쓰지 말 것.

### PFP 단독 검사 오탐 교정

PFP 5.0.7을 단독 번역 플러그인으로 검사했을 때 원문 대비 미인식이 **8,552회**였지만, **본편 KR12.7의 전체 TOP/MRK/DIAL과 함께 로드하는 조건을 네이티브 파서에서 합성하자**, PFP 자신의 원문 토픽 8,560회 중 **6,034회가 본편 또는 PFP 토픽으로 인식**, **2,526회가 여전히 미인식 후보**로 분리됨. 이로써 플러그인 단독 검사만으로 누락을 단정하면 크게 과장된다는 점도 실증됐다. 남은 2,526회도 실제 콘텐츠 로드 우선순위·NPC 조건 및 일지 진행은 미검증.

## 일반 퀘스트에서 확인한 5개 원문↔한국어 GUI 파서 차이

[Windows 네이티브 테스트](https://github.com/munument1/Morrowind-OpenMW-KR/actions/runs/41694814730)의 동일 실행 파일로 실제 최종 화면용 중첩 링크 우선순위(`parseHyperText` non-discovery mode)를 사용하여 재확인함.

| 모드 / INFO ID | 원문에서 인식된 DIAL | 한국어 화면 대사 (일부) | 한국어 자동 인식 |
|---|---|---|---|
| Sky_Main `16988138932555913235` | `components for a ritual` | 의식에 쓸 재료를 모았어? | 누락 |
| Cyr_Main `16990157761991814001` | `lucky amulet` | 내 행운의 부적을 되찾았어? | 누락 |
| Cyr_Main `2942812635768223789` | `varla stone` | 바를라 스톤을 가져가 버렸어 | 누락 |
| Cyr_Main `11763708293733692` | `explore Garlas Agea` | 가르라스 아게아를 더 깊이 탐험하는 것을 도와주시겠어요? | 누락 |
| Cyr_Main `130586384723121468` | `offering to Arkay` | 아케이께 제물을 바치는 걸 도울 준비가 됐나? | 누락 |

영어 대사에서는 해당 토픽이 **네이티브 OpenMW 토픽 파서에서 실제로 발견**됐고, 한국어에서는 발견되지 않았다. 이는 **토픽 자동 인식 회귀가 존재함을 재현한 것**이지, 해당 퀘스트에서 반드시 그 링크를 클릭해야 하는지/다른 `AddTopic` 경로가 있는지까지 증명한 것은 아니다.

## 누락 원인과 수정 방법

- `.mrk`의 하나의 기본 검색어만으로는 의역·동의어·표기 변형을 포괄하기 어려움. 예: `행운의 아뮬렛` ↔ `행운의 부적`.
- `.top`에 별칭을 넣는 것만으로는 **평문 자동 검색어로 추가되지 않음**. 단, `@표면형#`으로 명시 연결할 때 별칭을 안정적으로 매핑할 수 있음.
- 일괄 동의어 등록은 `일`, `말`, `작업` 같은 짧거나 중의적인 명사에 **오탐 링크를 새로 만드는 위험**이 있으므로 전역 자동 치환 금지.
- 검토가 필요한 실제 NPC/퀘스트 경로를 먼저 추린 후 (a) 특정 INFO에 표시 문장 불변 명시 링크 삽입 + TOP 별칭 추가, 또는 (b) 안전한 경우 정식 한국어 토픽 키워드 통일 중 선택.
- 변형이 대량·반복된다면 엔진에 별도의 **검증된 자동 검색 동의어 목록** 지원을 고려하되, 전체 TOP 별칭을 무조건 seed하는 방식은 금지.

## 보류 게이트와 로컬 산출물

사용자 PC `C:\Users\seung\OneDrive\Desktop\Morrowind\KR126_topic_fullaudit_20261103\`:

- `native_full_bilingual_topic_audit_v2.py`: 원문/현 공개 한국어 플러그인 전체 Native KeywordSearch INFO 비교
- `FULL_NATIVE_BILINGUAL_PARSER_AUDIT_V2/summary.json`, `all_native_INFO_diffs.jsonl.gz`: 17 플러그인 전체 원문↔한국어 파서 차이 근거
- `make_native_topic_repair_queue.py`, `FULL_NATIVE_TOPIC_REPAIR_TRIAGE/every_unique_mod_topic_candidate.jsonl.gz`: 6,249개 중복 통합 토픽별 검토 대기열
- `native_gui_prove_general_quest_topic_gaps.py`, `FULL_NATIVE_GENERAL_QUEST_UI_PROOF/five_general_quest_topic_issues.json`: 위 5건의 실제 GUI 파서 재현
- `native_pfp_with_core_loadout_audit.py`, `FULL_NATIVE_PFP_WITH_CORE_COMBINED/summary.json`: 본편+PFP 로드 조합 인식 확인

**미완료:** 다른 대표 로드 조합 전체 합성(코어+TR/TamData/Cyr/Sky/Rebirth), 원본 INFO의 실제 플레이어 토픽 습득·퀘스트 일지 상태·NPC 선택 필터·스크립트 `AddTopic` 도달성, 모든 고유 토픽 후보의 의미 판정 및 안전 수정 후 회귀 테스트. 본편 HOLD 3,457개를 별도 재매핑해야 전수 판정에 포함 가능.

**이번 검사에서 실제 원본/번역 ESP·ESM 및 기존 Nexus 릴리스 수정 없음.** 5건의 GUI 파서 불일치를 포함한 후보를 곧바로 대량 수정·공개하면 숨겨진 일반 토픽을 오히려 가릴 수 있으므로, 최종 검수판 릴리스는 보류한다.
