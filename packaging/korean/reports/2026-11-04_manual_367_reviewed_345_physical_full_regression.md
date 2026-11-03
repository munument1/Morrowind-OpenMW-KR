# 모로윈드 토픽: 367 INFO 수동 원문 검수 → 승인본 345 INFO 실물 QA

**기준일 2026-11-04 · 테스트 패키지 로컬 보존 · 정식 공개 릴리스 미게시**

## 범위 및 구분

이 문서는 먼저 작성된 [367건 원문 토픽 의미 검수](2026-11-04_367_INFO_full_manual_source_semantic_review.md)를 보완하는 **후속 문장 교정·선택적 링크 반영·실물 ESP/ESM 빌드·전체 회귀검사** 기록이다. 앞서 전부 링크를 연결한 367 INFO 시험판과 다르다. `367개 모두 영한 토픽 개념이 일치한다`와 `367개 모두 신규 클릭 링크를 만들어야 한다`는 별개이다.

- **283개 고유 영문 전문 ↔ 한국어 전문**을 별도 직접 읽고 367개 물리 INFO의 대응을 원본 바이너리/INFO.INAM/record_index로 재검증.
- 283개 고유 판정: **225개 링크 의미상 승인**, **14개 번역 문장 교정 후 승인**, **41개 일반 호칭·수식어 등 강제 링크 생략**, **3개 실제 위치·장면 해석 보류**.
- 367개 물리 INFO 판정: **310개 신규 토픽 링크 승인**, **54개 불필요한 추가 링크 미적용**, **3개 보류**.
- **14개 고유 문장에 대해 한국어 문맥·오역·용어 교정안**을 작성했고, 호환 플러그인/복제 레코드 포함 **17 INFO의 한국어 문장**을 실제 시험 바이너리에서 교정. 예: `%Name.입니다` 잘못된 문장 부호, 인물 소개 관계, `the other day` 기간 표현, `인도로일` 오탈자, `이전에르고니아` 붙여쓰기, `변태 과정`→`변이 과정`, `안아티린` 지명 오류 등. 이전 보고서의 **11개 TR 번역 품질 개선 권고**와는 조사 범위·기준이 달라 숫자를 동일 집합으로 오해하지 않는다.
- **3개 보류**: Evos 위치의 동서 관계가 실제 지형과 맞는지, `On the ledge!`가 실제 어떤 지형을 가리키는지, `So this is Bal Foyen, and Almalexia?`의 실제 발화 장면. 원문 근거만으로 단정하지 않아 원래 한국어/링크 상태를 보존.

## 원본 무결성·현행 플러그인 빌드

기존 [35개 소스 고정 수정](../../translations/openmw-kr/verified_topic_fixes_2026-11-04.json)을 먼저 replay하고, 그 위에 **신규 승인 310 INFO**만 적용하였다.

- 시험 ESP/ESM **8개** 생성, 신규 추가 TOP 별칭 **168개**, 실제 독립 OpenMW 0.51 `esmtool -q -C dump` **8/8 통과**.
- 기존 35개가 있는 Tamriel Data는 기존 검증판 플러그인·TOP을 그대로 재사용.
- 모든 타 레코드·플러그인 헤더·스크립트·선택 조건·ID는 변경하지 않았고, 기존 명시 링크도 보존. 원본 공개판 ZIP·설치 게임·세이브는 미수정.
- 실제 생성된 plugin binary를 **다시 읽고** 345 INFO(35 기존 + 310 신규)와 교정 문장 17개, DIAL/TOP·MRK를 C++ 네이티브 GUI 키워드 검사기에 전달. **12개 로드 구성 × 2,003 INFO 검사 모두 PASS**, 기존 링크 손실 0, 새 링크 미검출 0, 표시 문장 불일치 0.
- **더 중요한 전체 미변경 대사 간접 회귀검사:** 12개 구성에서 원본+수정본 **755,471회 INFO 검사 전부 PASS**. 기존 클릭 링크 손실 0, 신규 TOP 별칭 때문에 **미변경 대사에서 의도치 않게 새로 생성된 링크 0**, 승인 새 링크 누락 0, 문장 렌더링 불일치 0. 합산 로드 구성에 따라 동일 INFO가 여러 번 검사된 것으로, 고유 INFO 755,471개라는 뜻은 아니다.

## PC의 주요 QA 산출물

루트 폴더:
`C:\Users\seung\OneDrive\Desktop\Morrowind\KR126_topic_fullaudit_20261103\`

- `MANUAL_367_FULL_SOURCE_REVIEW_VERDICTS_20261104/summary.json` — 283 원문별 개별 수동 판정/영한 전문/교정안/367 INFO 결론
- `MANUAL_VERIFIED_KOREAN_310_INFO_BINARY_TEST_ONLY_20261104/summary.json` — 실제 8개 수정 플러그인, SHA256·INFO 이름 무결성·esmtool 결과
- `FINAL_MANUAL_REVIEW_345_PHYSICAL_INFO_NATIVE_12_LOADOUT_20261104/summary.json` — 2,003/2,003 실제 빌드 바이너리 C++ 파서 검사
- `FINAL_310_PLUS_35_FULL_12_LOADOUT_ALL_INFO_NO_REGRESSION_20261104/summary.json` — 755,471회 전수 INFO 간접 회귀, 링크 유실 0
- `MANUAL_REVIEW_345_INFO_TEST_ONLY_PACKAGES_20261104/qa_manifest.json` — 별도 시험용 7 ZIP 패키지 멤버·CRC·SHA

[367개 물리 INFO별 판정·교정 텍스트·소스 해시 기록](../../translations/openmw-kr/manual_topic_review_367_2026-11-04.json) (영어 원문 전문은 GitHub에 다시 복제하지 않음).

## 시험용 ZIP 7개 — 공식 배포용 아님

`MANUAL_REVIEW_345_INFO_TEST_ONLY_PACKAGES_20261104/` 내 파일:

| 구분 | 시험 ZIP | SHA-256 |
|---|---|---|
| Tamriel Rebuilt | `QA_ONLY_TR_Mainland_TopicReview_20261104.zip` | `d4a5890b63f4425570d4412293d81acb430e75ce0232b63015ee77acfdeef904` |
| Tamriel Data | `QA_ONLY_Tamriel_Data_TopicReview_20261104.zip` | `f56e8f7839b01b12081595e62e862cd8d82a5efc82b2786598da80d37c26f8d9` |
| Project Cyrodiil | `QA_ONLY_Cyr_Main_TopicReview_20261104.zip` | `7f8b91d5e714d44e33f15ec86f80e8d3985103efcaf4f13fe73a16fe5c359a36` |
| Skyrim: Home of the Nords | `QA_ONLY_Sky_Main_TopicReview_20261104.zip` | `a236af268ac987b6d0e191f48849e94b014bad7d0bb39eca9f1a0508b97503a4` |
| Morrowind Rebirth 7.2 | `QA_ONLY_Rebirth7.2_TopicReview_20261104.zip` | `a4c9a33560c4967e3803590681c8fde451c7bad8ee8e272dc6a9849df315ddc6` |
| OpenMW KR12.7 | `QA_ONLY_OpenMW_KR12.7_TopicReview_20261104.zip` | `7262d3cc1f80f70c72b6483f729368fd8b81bbe79640ed4e534e2787865f8a13` |
| Rebirth–Cyr/Sky 호환 패치 | `QA_ONLY_Rebirth7.2_RegionalCompatibility_TopicReview_20261104.zip` | `8ed2353c49e24fab017b4d1f9ac63c2a8b9bea1b4852c5e769e9d589c54285af` |

패키지는 **현재 공개판 원본 ZIP에서 승인한 ESM/ESP 및 TOP 파일만 교체**. MRK·JRN·CEL·기타 모드·OpenMW EXE·리소스 등 나머지 ZIP 멤버는 현재 공개판과 동일한 원본 바이트를 보존했다. 새 `QA_TEST_ONLY_NOT_RELEASED.txt` 주의문만 추가했다. 파일은 사용자 PC에만 생성하였으며 Nexus/GitHub releases에는 업로드하지 않았다.

## 완료되지 않은 별도 검증

- **3개 대사 보류**의 실제 게임 발화 위치/장면 검사.
- **NPC별 선행 퀘스트 단계, SCVR/조건, 퀘스트 일지/저장 데이터의 실제 도달성, 성공/실패 분기** 실게임 검증.
- 이번 367개 바깥 **6,249개 모드×토픽 검토 묶음**의 모든 의미 판정 및 실게임 동작 확인.

따라서 **367개 영한 토픽 의미 수동 검토와 승인 345 INFO의 전체 로드아웃 파서 회귀 검사는 끝났지만, 전체 모드·전체 퀘스트의 최종 플레이테스트/릴리스 완료는 아니다**. 이 보수적인 구분을 유지해야 한다.
