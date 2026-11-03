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
