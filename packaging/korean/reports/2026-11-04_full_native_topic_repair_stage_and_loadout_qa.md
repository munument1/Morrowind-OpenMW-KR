# 모로윈드 모드 토픽 전수 검사 — 소스 고정 교정 시험본과 통합 회귀검사

**2026-11-04 · 검증 및 수정 스테이징 완료 / 신규 Nexus·GitHub 릴리스 미게시 / 게임 내 퀘스트 동작 미검증**

## 사용자가 요구한 범위와 실제 검사

가입·승진에 한정하지 않고 **인사말, 일반 토픽, 지명·인명, 퀘스트 단서, 아이템, 스크립트 Choice/AddTopic/Journal, PFP·Rebirth·지역 모드 호환 대화**를 포함하여 검사했다.

- 본편 KR12.7, TR_Mainland 26.11.2, TR_Factions, Tamriel Data 26.08, Project Cyrodiil 26.09a, Skyrim 26.09a, PFP 5.0.7, Morrowind Rebirth 7.2 본편·부가 ESP 및 Rebirth–Cyr/Sky 호환 ESM 포함 **17개 플러그인 변형, INFO 160,932건 전수 순회**.
- 그중 영어 원본과 한국어 INFO를 확정 매칭한 **157,475건**을 실제 Windows용 OpenMW KR 0.51 C++ `KeywordSearch`+번역 저장소로 재검사. 본편 중복 INAM/조건으로 1:1 원본 확정 불가 **3,457건 HOLD**.
- 단독 플러그인 비교에서 원문 링크는 잡혔지만 한국어에서는 빠진 **153,656회**는 흔한 영어 명사/구문, 다른 모드의 DIAL/MRK 필요성, 동일 토픽 반복으로 인해 오류 수가 아님. **모드×토픽 중복 묶음 6,249개**로 검토 항목 통합(대체/호환판 중복 포함). 미검토 다수.
- 단일 플러그인의 TOP·MRK 판단에 의존하지 않고 **12개 대표 로드아웃**을 전용 네이티브 파서로 별도 확인. 특히 PFP는 코어 데이터와 합치면 단독 검사보다 실제 발견 가능한 토픽이 많음.
- 전체 `@...#` 명시 링크 17,120개는 검사 대상 집합의 대응 TOP/DIAL 존재 여부 점검. 스크립트 `Choice` 14,295개, `AddTopic` 12,032개, `Journal` 계열 ID 19,276개 원본/한국어 구조 대조. 확인된 분기 번호·Journal 퀘스트 ID 변경 없음.

## 실제 네이티브 검증을 통과한 변경 — **35개 물리 INFO**, 중복 호환판 제외하면 **24개 고유 대사**

| 후보 수정 대상 | INFO.NAME 변경 | 추가 TOP 별칭 | 변경 방식 |
|---|---:|---:|---|
| Project Cyrodiil `Cyr_Main.ESM` | 7 | 7 | 전사/도둑 길드, 앤빌 왕국, 행운의 부적, 바를라 스톤, 유적 탐사, 아케이 공물 |
| Skyrim `Sky_Main.ESM` | 4 | 4 | 전사/도둑 길드, 의식 재료 |
| Tamriel Data `Tamriel_Data.esm` | 3 | 3 | 인도릴/오디네이터/마법사 길드 가입 연결 |
| Tamriel Rebuilt 26.11.2 `TR_Mainland.esm` | 10 | 10 | 이름·장소가 한국어 조사/어미와 이어져 놓친 NPC 퀘스트 인사말 |
| Rebirth 7.2–Cyrodiil 호환 ESM | 7 | 7 | 동일 Cyrodiil 수정사항의 호환 플러그인 대응 |
| Rebirth 7.2–Skyrim 호환 ESM | 4 | 4 | 동일 Skyrim 수정사항의 호환 플러그인 대응 |
| **합계** | **35** | **35** | **24개 고유 원문 대사 + 11개 호환판 복제** |

현 공개된 원본 패키지의 정확한 ESM/ESP·TOP SHA-256을 고정하고, INFO.INAM·물리 레코드 인덱스·원래 한국어 바이트 해시를 모두 검증한 경우에만 변경을 적용. **다른 레코드, DIAL ID, SCVR, NPC 조건, 스크립트와 표시 한국어는 수정하지 않았음.**

기존 **개별 플러그인만 검사했을 때는 통과했지만**, 본편·다른 지역 모드와 합친 전체 키워드 공간에서 일부 새 명시 링크가 기존 토픽을 가리는 위험이 발견되어 재수정함. 이전 시험본은 사용 금지. 현 최신 후보만 사용.

**최종 시험 결과**: 수정 대상이 포함된 **9개 로드 조합 × 총 123개의 네이티브 GUI 링크 회귀검사** 모두 통과(**123/123**), 기존 링크 손실 **0**, 새 TOP 충돌 **0**, 한국어 표시 변경 **0**. 비대상 TES3 필드·레코드 수 보존.

## 이 변경이 다음 버전에서 유실되지 않도록 고정

- [35건의 소스 해시와 수정 전후 텍스트·TOP 별칭을 고정한 JSON](../../translations/openmw-kr/verified_topic_fixes_2026-11-04.json)
- [원본을 덮어쓰지 않는 SHA 검증 재빌더](../tooling/apply_verified_topic_fixes_20261104.py)
- 사용자 PC에서 **6개 플러그인 모두 현 공개판 원본에서 독립적으로 재생성, 수정 후보 플러그인 및 TOP의 최종 SHA-256 정확히 일치**, 테스트 `ROOT/FULL_SOURCE_REPLAY_VERIFIED_35_V2/all_6_module_replay_summary.json`.

사용자 PC 증거 경로:
`C:\Users\seung\OneDrive\Desktop\Morrowind\KR126_topic_fullaudit_20261103\`

- `FULL_STAGED_ALL_12_LOADOUT_NATIVE_UI_GATE_V3/report.json` (9개 적용 조합 123/123)
- `FULL_REGIONAL_14_NATIVE_GUI_GLOBAL_ZERO_LOSS/report.json` (14/14)
- `FULL_TR_MAINLAND_10_NATIVE_GLOBAL_NO_MASK/qa_report.json` (10/10)
- `FULL_REBIRTH_COMPAT_11_NATIVE_GLOBAL_ZERO_LOSS/report.json` (11/11)
- `FULL_SOURCE_REPLAY_VERIFIED_35_V2/` (6개 SHA 재현 검증 결과)
- `CANDIDATE_REGIONAL_KR02_ALL_14_GLOBAL_ZERO_LOSS_NOT_RELEASED/`
- `CANDIDATE_TR_MAINLAND_10_GLOBAL_NO_MASK_NOT_RELEASED/`
- `CANDIDATE_REBIRTH_COMPAT_14LINK_GLOBAL_ZERO_LOSS_NOT_RELEASED/`

위 세 스테이징 폴더는 **배포한 정식 모드가 아니며, 사용자 게임 설치·세이브를 수정하지 않음.**

## 추가로 발견된 미해결 문제

- **기존 MRK 중복 해석 주의**: `CORE_PFP_ALL_REGION` 조합의 번역 데이터에서 `join the Mages Guild`라는 동일 원문 토픽에 처음 `마법사 길드에 가입하다`가 설정되지만 Tamriel Data 및 Cyrodiil에서는 `메이지 길드 가입`으로 별도 지정. `Translation::Storage::emplace`는 먼저 읽힌 값 유지하므로 **충돌 1종의 원문 키가 2개 추가 플러그인에서 상충**. 효과와 실제 로드 순서 확인 전 일괄 .mrk 통일 금지.
- **본편 중복 INFO 3,457건** 원본 영어→한국어 연결 판단 보류.
- **6,249개 모드×토픽 후보** 중 고위험 정밀 판정, 다른 모드/기본 퀘스트 연쇄, NPC `SCVR`·일지 단계 및 플레이어 토픽 습득 상태는 전부 확정하지 못함.
- TR `monastery of st. felms` 인사말은 변경 후 파서에서 인식되지만 해당 화자와 동일한 actor/faction target INFO를 찾지 못함(타 NPC에게 묻는 토픽일 수도 있음). 플레이어 경로 확인 필요.
- 본편/Android 및 다른 지역 모드의 최종 릴리스/설치 전 게임 플레이 테스트 없음.

## 공개 릴리스 게이트

**2026-11-04 현재 신규 패키지는 어떤 Nexus/GitHub 릴리스에도 업로드하지 않았다.** 이미 공개된 Windows KR12.7은 이전의 본편 INFO 5건만 교정한 부분 핫픽스일 뿐이다. 이번 35건을 전체 전수 검수 완료판이라고 표시하거나 나머지 6,249개가 모두 해결된 것처럼 배포하지 않는다.

다음은 각 후보의 실제 NPC/퀘스트 도달 조건 판단, 한국어 검색어 모호성·기존 링크·중복 INFOnames·MRK 충돌 해결 및 실게임 일지 경로 회귀 테스트다. 그 후 다시 바이트 고정 검증을 수행하고 공식 릴리스 생성 가능.

## 2026-11-04 후속 검증: 본편 중복 INFO 원문 대응 2,642건 복구

기존 영어 `Morrowind.esm` / `Tribunal.esm` / `Bloodmoon.esm`의 INFO.INAM은 DLC 중복·서로 다른 DIAL에서 재사용된다. **3,457개의 보류 INFO를 임의로 첫 번째 원본에 연결하지 않고**, 독립적으로 확인된 영어 DIAL→한국어 DIAL 대응표와 실제 원문 대사/선택 조건을 다시 대조했다.

- **2,605건:** 여러 영어 마스터/INFO가 원문 DIAL+대사 내용까지 일치하는 중복으로, 원문 대사를 안전하게 확정.
- **37건:** 독립 DIAL 대응으로 유일한 원문 INFO를 확정.
- **4건:** 원문 DIAL은 같으나 대사 내용이 달라 보류.
- **811건:** 원문 DIAL 이름을 유일하게 대응할 증거가 없는 경우(다수 생귄 장비 토픽 등) 보류.

**추가 2,642건에 대해 실제 OpenMW 한국어 C++ 파서 재검사 완료.** 추가 원문 링크 6,457개 비교, 한국어 링크 미인식 후보 895회(그런 후보가 있는 INFO 697건), 번역 DIAL 매핑 불명 원문 링크 47건 보류.

현재 본편 **31,716 INFO 중 원문 대응·네이티브 파서 검증 30,901건, 원문 대응 최종 HOLD 815건**. 697건은 확정 퀘스트 장애가 아니라 네이티브 파서 차이 후보다.

사용자 PC 데이터: `FULL_CORE_3457_DUPLICATE_SOURCE_NATIVE_RECOVERY/summary.json`, `newly_covered_duplicate_INFO_native_audit.jsonl.gz`, `remaining_held_ambiguous_INFO.jsonl.gz`.

**이 작업도 기존 ESM/ESP와 릴리스는 변경하지 않았음.**

### 남은 815건의 유형 분해

실제 한국어 `DIAL.DATA` 종류에 따라 재검사한 결과:

- **저널(JOURNAL, type 04): 663건.** NPC 대화 선택지 자체가 아니라 퀘스트 일지 항목이므로 별도 `.jrn` 및 저널 레코드 검증 대상으로 유지.
- **일반 대화 토픽(TOPIC, type 00): 151건.** 원문 DIAL 후보가 여러 개이거나 유일한 매핑 근거 부족. 링크 누락 여부는 개별 검토.
- **음성/전투 대사(VOICE, type 01): 1건.** 대화창의 새 토픽 링크와 별도 성격.

따라서 미매핑 815건을 모두 NPC 토픽 누락 위험으로 집계하는 것은 잘못이다. 전체 31,716 INFO를 순회했고, 그중 30,901건은 네이티브 원문↔한국어 대응 확인, 나머지 815건의 타입별 HOLD 분류까지 완료했다. 이는 여전히 실제 플레이어 상태별 전수 게임 검증을 대신하지 않는다.

## 2026-11-04 추가 전수검수: 본편 원본 대응 31,716/31,716

이전 섹션의 **815건 HOLD는 아래 후속 검수로 원본 식별·구조 측면에서 해소**했다. 다만 실제 플레이어 토픽 습득/퀘스트 진행까지 보장하는 것은 아니다.

- 기존 정확 대응·중복 동등성 검증 **30,901건**.
- 중복된 INFO.INAM이 서로 다른 원문 대화에 사용된 **일반 TOPIC 151건**: 영어/한국어 고유명사·아이템명 DIAL을 직접 대응해 **149건의 원문 대사·스크립트를 유일하게 확인**. 나머지 **2건은 Tribunal/Bloodmoon에서 수정된 영어 문장**이 한국어에 반영된 경우로, 기존 Morrowind.esm과의 차이도 보존해 기록함.
- 별도 보류된 **JOURNAL 663건**은 퀘스트 ID·선택 조건·결과 스크립트 구조를 영어 원본 3종과 재대조해 **663/663 구조 검사 통과**(661건 동일 원문, 2건 영문 수정판 변형).
- **VOICE 1건**은 `Attack`의 `triffled`→`trifled` 영문 오탈자 수정으로, 조건/구조/한국어 의미 동등성을 확인.
- 합계 **30,901 + 149 + 2 + 663 + 1 = 31,716 INFO**, 본편 원본 식별 보류 **0건**.

검증 파일: `FULL_CORE_151_DUPLICATE_TOPIC_SOURCE_RECONCILIATION/summary.json`, `EXHAUSTIVE_663_JOURNAL_SOURCE_STRUCTURE_QA_20261104/summary.json`, `FULL_CORE_FINAL_3_INFO_SOURCE_VARIANTS_20261104/source_provenance_closure_report.json`.

**한계:** 저널 663건의 구조적 동등성은 한국어 번역 의미를 문장별 전수 교열했다는 뜻이 아니다. Morrowind-only 설치에서는 DLC 덮어쓰기 문구가 다를 수 있다.

## 새 검수기 오류 교정 및 6,249개 전수 위험 분류

기존 일부 임시 분석의 잘못된 한글 정규식 처리와, **.mrk 검색어를 원래 영문 DIAL 키로 조회한 오류**를 정정했다. 실제 엔진에서는 **한국어 DIAL명을 .mrk 기본 검색어 키로 사용**한다. 이전 1,739회 분류 대신 재현 가능한 새 분류표를 기준으로 삼는다.

- 네이티브 파서의 원문↔한국어 링크 차이 **153,656회**를 올바른 .mrk 키 기준으로 다시 **한 건도 빠짐없이 재분류**했다.
- 모드×토픽 **6,249개 검토 묶음** 중: 문자상 복원 후보 481, 의역·검색어 불일치 2,127, 매핑/문맥 보류 2,931, 저널 전용 710.
- 적용 모드 12개 로드 구성과 교차 검사했을 때 **5,704개는 파서 차이가 계속 재현, 544개는 재현되지 않음, 1개는 로드 구성에 따라 달라짐**. 재현은 진행 불가 확정이 아니다.
- **1,746회** 문자상 링크 누락 후보에서 INFO 1,663개에 실험적 클릭 태그를 적용해 전용 파서 검사. **1,378개 INFO 파서 무손실 통과**, 285개 INFO는 새 태그 때문에 기존 링크가 가려져 제외.
- **285/285개의 기존 링크 손실 원인을 역대조**하니 모두 현재 정상 클릭되는 긴 검색어와 새 짧은 태그가 겹치는 유형이었음(본편 171, TR 18, Cyr 17, Sky 31, Rebirth-Cyr 17, Rebirth-Sky 31). 이 285개는 수정 금지/기존 토픽 우선 보존.
- 네이티브 무손실 1,378개를 한국어 어절/조사·합성어 위험으로 재분류: **367개는 긴 명사+조사 기반 의미 검토 우선**, **662개는 짧거나 미분류 문법 위험**, **349개는 합성어·동사 어절 등 부적절할 가능성으로 HOLD**.

파일: `EXHAUSTIVE_UNICODE_KEYWORD_RECLASSIFICATION_V2_REAL_MRK_20261104/`, `FULL_285_NATIVE_MASKING_ROOTCAUSE_20261104/`, `FULL_1378_NATIVE_PASS_SEMANTIC_RISK_TRIAGE_20261104/`.

## 실제 바이너리·실제 네이티브 토픽 파서 이중 검증

기존 별도 검증 완료된 **35개 INFO**를 소스 SHA가 고정된 원본에 먼저 재적용하고, 이후 **언어적 위험이 비교적 낮은 의미 검토 후보 367개 INFO**를 추가한 실물 시험본을 새로 빌드했다.

- 이번에 새로 변경한 INFO **367개**, 새 TOP 별칭 **178개**, 실제 ESP/ESM **8개 파일**. 기존 35개 INFO + Tamriel Data의 별도 기검증 파일을 포함하면 수정 확인 대상은 **총 402개 INFO / 9개 실제 플러그인**.
- 각 파일의 **INFO.INAM·물리 레코드 인덱스·기존 한국어 문장**을 대조. **INFO.NAME 외 다른 TES3 레코드/스크립트/조건/헤더/레코드 수 변화 0건**, 화면에 보이는 한국어 문장 변화 0건.
- 설치된 OpenMW 0.51.0의 독립 `esmtool -q -C dump`에서 **영문 원본 16개 + 공개 한국어판 17개 + 기존 35건 시험판 6개 = 39/39 통과**. 신규 **367개 실물 수정본도 8/8 추가 통과**.
- 실제 **재빌드한 402개 INFO 파일**을 다시 읽어 C++ OpenMW-KR 토픽 파서에 투입. **12개 로드 구성에서 2,660회 검사 2,660회 통과**, 기존 클릭 가능 링크 소실 **0**, 새 TOP 별칭으로 인한 충돌 **0**. 이 결과는 계획된 문자열 조합만 검사한 것이 아니라 **재빌드된 실제 ESP/ESM 바이트를 독립 추출**하여 검사한 결과다.

주요 산출물:
- `SOURCE_PINNED_367_PRIORITY_LINK_BINARY_QA_UNRELEASED/summary.json` — 8개 실제 바이너리/새 TOP, SHA256, 독립 esmtool 검증
- `FINAL_PHYSICAL_402_INFO_NATIVE_12_LOADOUT_QA_20261104/summary.json` — 402개 물리 필드·12개 로드 구성·2660회 C++ 회귀
- `EXHAUSTIVE_367_SEMANTIC_PRIORITY_PLUS_35_COMBINED_NATIVE_QA/summary.json` — 35+367 통합 무손실 파서 재현
- `OPENMW_051_ESMTOOL_ALL_PLUGIN_INDEPENDENT_BINARY_QA/summary.json` — 39개 원본/현행/기검증판 전체 TES3/CELL 파싱

## 배포 판단과 남은 한계

**이번 367건은 파서와 바이너리 구조의 안전성에 대한 시험이지, 전체 의미 검수 승인이 아니다.** 별도 파일에만 보존했고 게임 설치·세이브·현재 공개 Nexus/GitHub 릴리스는 변경하지 않았다.

현재 Steam Morrowind 원본과 `C:\OpenMW 0.51.0`이 존재하며, 한국어 OpenMW 0.51 실행 파일을 시스템 DLL 검색 경로로 실행하여 `--version` 정상 동작까지 확인했다. 하지만 **실제 NPC별 퀘스트 진행/저장 데이터의 모든 가능한 조건을 실게임으로 재현하지는 않았다.** 엔진의 `--script-all-dialogue` 옵션도 발견했으나, 지금까지의 `esmtool` 파싱을 실제 퀘스트 플레이 테스트라고 과장해서는 안 된다.

따라서 **정식 전체 검수판 릴리스는 아직 보류**한다. 6,249개 자동 토픽 검토 묶음의 의미·NPC 도달 조건까지 완료하지 않은 이상 402건을 전체 오류 해결이라고 공지하지 말 것.
