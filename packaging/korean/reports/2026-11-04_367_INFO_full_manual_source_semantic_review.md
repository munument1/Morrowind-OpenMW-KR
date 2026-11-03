# 지역 모드 포함 367개 INFO — 원본 대조 수동 토픽 의미 검수

**2026-11-04 · 결과: 검수 대상 367/367개 INFO · 원문/토픽 지시 대상 일치 · 문장 품질 개선 11건 · 릴리스 미게시**

## 1. 검수 대상과 절차

이 보고서는 최근의 자동 C++ 네이티브 파서 QA에서 **추가 클릭 링크가 필요할 수 있고, 기존 링크를 가리지 않는 것으로 추린 367개 INFO**의 *토픽 의미*를 독립 검토한 결과이다. 토픽을 기계적으로 대량 삽입한 결과 자체를 ‘수동 검수’라고 부르지 않았다.

1. 영어 원본 `.esm/.esp`와 실제 공개된 한국어판 `.esm/.esp`를 다시 읽어 INFO.INAM·물리 레코드 번호·전체 영문/한국어 텍스트를 정확히 일치시켰다.
2. **367개 물리 INFO → 283개 서로 다른 전체 영한 대사·토픽 조합**으로 중복을 통합했다. **283개의 원문과 번역 전문을 각각 직접 읽고**, 해당 구절의 토픽/지명/인명/개념이 원문과 같은 대상을 가리키는지 판정했다.
3. 호환 패치와 복제 INFO의 결과를 다시 원래 **367개 물리 레코드 전체**에 배정했다. 모든 INFO에 단독 판정·고유 원문/번역 SHA-256·모드명·INFO ID·리뷰 번호를 기록했다.
4. 검토된 실제 시험본 **8개 ESP/ESM 파일에서 367개 INFO.NAME을 재추출**해 판정표와 대조. 새 클릭 링크는 모두 같은 TOP 별칭 대상으로 해석되고 기존에 표시되는 한국어는 동일했다.
5. 별도 **OpenMW C++ KeywordSearch 12개 가상 로드 구성 2,660회 회귀 검사 통과**, 기존 링크 소실 0건. 이전 OpenMW 0.51 `esmtool` 바이너리 구조 검증도 8/8 통과.

## 2. INFO 전체 검수 결과

| 모드 파일 | 물리 INFO |
|---|---:|
| OpenMW KR12.7 본편 | 160 |
| TR_Mainland 26.11.2 | 107 |
| Project Cyrodiil | 37 |
| Rebirth–Cyrodiil 호환 ESM | 37 |
| Skyrim: Home of the Nords | 9 |
| Rebirth–Skyrim 호환 ESM | 9 |
| Rebirth 7.2 메인 | 4 |
| Rebirth 7.2 메인 대체판 | 4 |
| **총계** | **367** |

**수동 토픽 지시 대상 판정**: 283개 고유 영문-한국어 조합에서 모두 원문의 같은 개념/고유명사를 가리킴. 복제 포함 **367/367 물리 INFO** 토픽 의미 대응 확인. 이는 클릭 가능한 토픽 지시 대상을 뜻하며 번역 문장 전체에 오류가 전혀 없다는 뜻은 아니다.

**기존 한국어 문장에서 별도로 발견한 11건**: 맞춤법/띄어쓰기 3, 표현 선택 1, 의미·번역 검토 2, 문체 2, 용어 표현 2, 지명 통일 1. 전부 TR_Mainland로, 링크 수정과 별도 수정 후보이며 **이번 시험본에서는 원래 문장을 변경하지 않았다.**

예:
- `이전에르고니아` → `이전에 아르고니아`
- `일이엇지` → `일이었지`
- `인도로일 가문` → `인도릴 가문`
- 영문 `all the different shacks`와 대조하면 `오락가락하는 판잣집`은 의미가 어색함
- `Council Seat`의 `의회 의석이 있는`은 `평의회 소재지` 계열로 조정 검토
- `Vhul`이 대사마다 `부훌`/ `불`로 달라 용어집 확인 필요
- `Bal Foyen, and Almalexia? She seems strong.`의 아말렉시아 부분에서 불필요한 `도시`라는 의미가 추가됐는지 검토 필요

11건은 [원본 해시 포함 개별 교정 권고 목록](../../../translations/openmw-kr/manual-review-2026-11-04/11-existing-text-issues-review.jsonl) 참조.

## 3. 실물 검사에서 발견한 세부 사항

367개 INFO는 실제 시험 바이너리와 정상 대응. **2개 레코드의 명시 링크 내부에 들어간 `\x7f` 별칭 구분문자 개수만 1개씩 달랐음**: `Sky_Main.ESM@17887278092337132596`과 `Skyrim Home of the Nords [For Rebirth].esm@17887278092337132596`. 두 레코드 모두 **TOP 대상·화면 텍스트·네이티브 클릭 결과가 동일**하므로 실제 기능 차이는 없음. 바이너리가 완전히 같은 문자열이라고 주장하지 않고 차이를 기록했다.

## 4. 영구 보존된 검수 파일

GitHub에 [367개 INFO별 수동 토픽 판정표](../../../translations/openmw-kr/manual-review-2026-11-04/367-info-topic-semantic-verdicts.jsonl)를 저장했다. **각 INFO의 DIAL 표적, 원본/번역 SHA-256, 검수 결과, 문장 품질 별도 권고, 실제 게임 테스트 여부**를 포함한다. 원본 저작권 텍스트 전문은 공개 GitHub에 다시 복제하지 않았다.

실제 원문·번역 전문과 검수 증거는 사용자 PC의 아래 폴더에서 검증할 수 있다.

`C:\Users\seung\OneDrive\Desktop\Morrowind\KR126_topic_fullaudit_20261103\`

- `MANUAL_SEMANTIC_DOSSIER_ALL_367_20261104/readable_part_01.md` ~ `readable_part_05.md`: 283개 고유 대사 원문·한국어 전문·검수 대상 토픽
- `MANUAL_REVIEW_ALL_367_INFO_20261104/ALL_283_UNIQUE_FULL_SOURCE_EN_KO_MANUAL_REVIEWS.jsonl.gz`: 각 영한 대사 전문을 포함한 실제 검수 결과
- `MANUAL_REVIEW_ALL_367_INFO_20261104/ALL_367_PHYSICAL_INFO_MANUAL_VERDICTS.jsonl`: 367개 INFO별 결과
- `MANUAL_REVIEW_ALL_367_INFO_20261104/all_existing_translation_issues.jsonl`: 11개 개선 권고 원문/한국어 맥락
- `MANUAL_REVIEW_ALL_367_INFO_20261104/actual_staged_binary_crosscheck_v2.json`: 367개 실물 바이트/별칭/표시 문장 검사
- `FINAL_PHYSICAL_402_INFO_NATIVE_12_LOADOUT_QA_20261104/summary.json`: 기존 검증 35개와 추가 367개를 합친 실물 토픽 회귀 검사
- `SOURCE_PINNED_367_PRIORITY_LINK_BINARY_QA_UNRELEASED/`: 별도 8개 바이너리 시험본

## 5. 남은 배포 위험과 결론

**367건의 수동 토픽 의미 검수는 완료했으나, 실제 플레이에서 모든 NPC가 해당 토픽을 제공하는지, 퀘스트 진행 상태마다 토픽이 알려졌는지, 모드 로드 순서에 따라 결과가 달라지는지까지 검증되지는 않았다.**

또한 앞선 전체 전수검사에서 남은 수천 개의 의역/동사·합성어·NPC 조건 후보는 이번 **367개 한정 의미 검수 범위에 포함되지 않는다**. 모로윈드 지역 확장 모드 전수 게임 플레이 완료라는 표현을 써서는 안 된다.

**새 정식 Nexus/GitHub 릴리스 없음.** 원본 플러그인·게임 설치·세이브·기존 공개판 변경 없음. 이 시험본과 11개 교정 권고는 추가 확인 전까지 사용자가 설치할 정식 모드가 아니다.
