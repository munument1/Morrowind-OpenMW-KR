# OpenMW-KR 및 지역 모드 토픽 QA — 348건 수정 / RC1 실물 배포 후보

검증일: **2026-11-04**. **정식 Nexus/GitHub 릴리스는 아직 게시하지 않았음.** 이 문서는 릴리스 후보 파일과 테스트 한계를 기록한다. 기존 게임 설치·세이브·배포본은 변경하지 않았다.

## 검수·수정 범위

- 영어 원문 ↔ 한국어 **283개 고유 대사** 전부 직접 비교, **367개 물리 INFO**로 매핑.
- **313개 INFO**의 신규 토픽 연결/문장 수정 승인. 나머지 **54개**는 일반 호칭 등의 불필요한 추가 링크를 제외.
- 이전에 소스·구조를 검증했던 35개 수정도 유지하여 **총 348개 INFO 수정**. **20개 물리 INFO의 한국어 문장**에 교정 적용(기존 17개+보류 해결 3개).
- 앞서 보류했던 세 대사: Nelyn Fathis의 오두막이 Evos 동쪽에 위치한다는 TES3 원본 외부 출입구 좌표·NPC 배치 대조, Arvs-Shadan 퀘스트 저널의 Alvayah 위치를 *ledge*로 명시한 근거, Bal Foyen과 Almalexia 관계를 과도하게 추가한 번역 교정. Bal Foyen 대사 수정 시 알말렉시아의 토픽이 사라지던 회귀를 발견하고 **한국어 표시명 → 영문 내부 TOP 대상** 명시 매핑으로 복구.
- 최초 지역용 플러그인 8종 및 수정된 최종 TR_Mainland ESM은 독립 OpenMW `esmtool` 검사 통과. 사용자가 설치한 모드 파일, 퀘스트 스크립트·조건·INFO 식별자 및 비대상 필드는 변경하지 않음.

## 12개 모드 구성 전체 네이티브 링크 회귀검사

- C++ 기반 실제 OpenMW 토픽 파서로 **755,471회 INFO 검사** (동일 INFO의 로드 구성별 반복 검사 포함).
- 기존 토픽 링크 손실 **0**, 비대상 대사의 의도치 않은 신규 링크 **0**, 승인한 링크 인식 실패 **0**, 표시 대사 불일치 **0**.
- 적용 구성에 기본 게임, PFP, Tamriel_Data + TR_Mainland, Cyr_Main, Sky_Main, Morrowind Rebirth 메인/대체, Rebirth 지역 호환 패치 포함.
- 자료: 로컬 `FINAL_313_PLUS_35_FULL_12_LOADOUT_ALL_INFO_NO_REGRESSION_V3_NATIVE_ALIAS_20261104/summary.json`.

## 실제 OpenMW 0.51.0 KR 포크 실행 — 두 버전 직접 비교

Windows의 별도 임시 설정/사용자 데이터 디렉터리에서 동일한 로드 순서 `Morrowind.esm`, `Tribunal.esm`, `Bloodmoon.esm`, `Patch for Purists.esm`, `Tamriel_Data.esm`, `TR_Mainland.esm`, `Morrowind_Korean_ReTranslation.esp`로 시험했다.

| 항목 | 기존 공개판 | 348 INFO 수정판 |
|---|---:|---:|
| 실제 대화 스크립트 컴파일 | 40,626 / 40,628 | 40,626 / 40,628 |
| 새 게임 시작 | 성공 | 성공 |
| Imperial Prison Ship 첫 셀 로딩 | 성공 | 성공 |
| 로그 E/W 오류·경고 이벤트 | 1,027 | 1,027 |
| 수정판에서 새롭게 발생한 오류·경고 | — | **0** |

두 컴파일 실패는 **원본 PFP**의 `Greeting 1` — `Goobye` 비정상 명령 (`INFO 6709168181081812211`) 및 **원본 TR_Mainland**의 `letter to Kha'Raji` — `PC_m1_KhaRaji` 참조 (`INFO 8370303521136630756`). 원본과 공개 한국어판 **INFO.BNAM 바이트 해시가 각각 동일**하며, 348건 토픽 수정에서 두 스크립트는 편집하지 않았다.

격리 실행 환경에서는 **양쪽 버전에 동일한 Lua UI/카메라 및 영상 누락 오류**가 존재한다. 새 게임 시작과 대화 스크립트 컴파일은 실제 수행했지만, **전체 NPC 클릭·퀘스트 진행/선택지 분기·저장/불러오기**를 실플레이로 전수 검증한 것은 아니다. 이 제한 때문에 **공식 정식 릴리스 대신 RC1**으로 보존한다.

실행 로그와 소스 비교 근거(로컬):
- `OPENMW_REAL_REGIONAL_TR_TD_PFP_348_BASELINE_VS_QA_20261104/official_stable_EW_only_baseline_candidate_comparison.json`
- `OPENMW_REAL_REGIONAL_TR_TD_PFP_348_BASELINE_VS_QA_20261104/two_baseline_dialogue_compile_failures_source_comparison.json`
- `TR_MAINLAND_3_HOLD_WORLD_SOURCE_RESOLVED_V3_NATIVE_ALMALEXIA_20261104_TEST_ONLY/summary.json`
- `RELEASE_CANDIDATE_7_KR02_KR127_LINKFIX_20261104/UPLOAD_CHECKSUMS_AND_RC_STATUS.json`

## 사용자 PC에 마련한 7개 RC1 ZIP

로컬 폴더 `KR126_topic_fullaudit_20261103/RELEASE_CANDIDATE_7_KR02_KR127_LINKFIX_20261104/`. 모든 ZIP **CRC PASS**; 기존 QA 확정 패키지의 ESM/ESP/TOP 및 기타 모드 자료 **바이트 동일**, 새 한국어 RC 주의문만 교체했다. 공개 업로드 전 상태다.

| 파일명 | SHA-256 |
|---|---|
| `TR_Mainland-KR0.2-20261104-RC1.zip` | `1335a4ec9b76db9c79d0d48f7cfd6e02818a3f9e83ae9d00f1e9bf4414a9a848` |
| `Tamriel_Data-KR0.2-20261104-RC1.zip` | `43ad6f1d3b4bbeece5e0b0b2307a411a5184081da756941fc2c08181b4431c76` |
| `Cyr_Main-KR0.2-20261104-RC1.zip` | `d02e5f252a745ad3dfc44283633e4f5bb0f6bb2d43b3d20c36595e5966e0d096` |
| `Sky_Main-KR0.2-20261104-RC1.zip` | `3ec39211611c1247cd29112a5c50af73e183d25d16856fa6bb7fc42cb170c69a` |
| `Morrowind_Rebirth7.2-KR0.2-20261104-RC1.zip` | `00e10166c0af46083de7497d263c345a7617a187b763b96d514f81c42c264159` |
| `OpenMW-KR12.7-TopicFix-20261104-RC1.zip` | `e121d6eeb0e18d623b2f1fa1e52e3242afb20dea28e487dd391f4439d828513c` |
| `Rebirth7.2-Cyr_Sky_Compatibility-KR0.2-20261104-RC1.zip` | `bb3809b44a14a78a696cdeff9e42d81a90ab332ff22933add52586273d799c04` |

관련 고유 대사 검수 기록: [367건 수동 검수 명세](../../translations/openmw-kr/manual_topic_review_367_2026-11-04.json), [직전 345건 검수 단계](2026-11-04_manual_367_reviewed_345_physical_full_regression.md).

**판정:** 348건 수정본은 **전체 토픽 파서 회귀검사와 기본·지역 모드 엔진 스크립트 컴파일 비교에서 신규 회귀가 관찰되지 않은 RC1**이며, NPC별 퀘스트 실게임 전수 시험과 공식 릴리스 게시가 별도로 남아 있다.
