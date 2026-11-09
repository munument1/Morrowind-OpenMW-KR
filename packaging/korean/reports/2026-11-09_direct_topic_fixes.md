# 추가 토픽 직접 수정 및 지역 모드 회귀 검사

본편 한글 패치를 공식 본편·확장팩 바로 다음, 지역 모드보다 앞에 두는 설치 순서를 기준으로
원본 한글 패치 데이터를 직접 수정했다. 새 호환 ESP/ESM은 만들지 않는다.

## 수정

- 기존 PR의 가입 링크 4건 유지.
- 초대·탈로스 교단·애완동물 판매 대사 3곳에 명시 링크 추가.
- 지역 TOP이 기본 한국어 이름을 가리던 카이우스 일지 1곳과 쌍둥이 등불 소문 4곳을
  고유 TOP 별칭으로 보호. 표시 문구 보존, TOP 별칭 3개 추가.
- Tamriel_Data, TR_Mainland/TR_Factions, Cyr_Main의 AddTopic 인수 17곳을 현재 존재하는
  목표로 수정. 원본 INFO 조건·다른 스크립트 명령·SCPT의 비소스 필드는 보존.
- 이미 존재하는 Rebirth 지역 번역 모듈의 Cyr 응답이 예전 AddTopic 2곳을 되돌리는 것도
  해당 기존 ESM 내부에서 수정. 추가 플러그인 없음.
- Sky_Main 자체의 데이터 변경은 없음.

`SCTX` 수정은 스크립트 원문에서 컴파일하는 OpenMW용이다. 원래 바이트코드 `SCDT`를
다른 게임 엔진에서 실행하도록 재빌드하지 않았다. 이 결과를 원본 Morrowind.exe용으로 사용하지 않는다.

## 설치 순서

1. Morrowind.esm
2. Tribunal.esm
3. Bloodmoon.esm
4. Morrowind_Korean_ReTranslation.esp
5. Tamriel_Data.esm
6. 사용하는 지역 모드: TR_Mainland / Cyr_Main / Sky_Main
7. 사용하는 TR_Factions 및 Rebirth 본체·부가/기존 지역 대응 모듈

지역 모드 자체의 master 의존성도 지킨다. 기존 원본 리소스는 계속 필요하다.
**지역 모드를 한글 본편 앞으로 이동하는 순서는 지원하지 않는다.** 본편이 해당 영문 DIAL을
삭제하기 때문에 데이터 순서를 임의로 바꾸어도 안전하다고 안내하지 않는다.

## 검증

공식 배포 ZIP 7개 및 설치된 원본 master 3개의 SHA 고정. 출력 ZIP의 레코드/서브레코드 대조로
허용된 INFO.NAME, TOP 추가, AddTopic 원문 인수 외의 조건·명령·필드 불변 확인.

실제 OpenMW 네이티브 파서의 대화 검색 모드(MRK만 사용)로 **8개 구성, 597,238 INFO 대조**:

- 본편 단독
- 본편 + Tamriel_Data
- 본편 + TD/TR
- 본편 + TD/Cyr
- 본편 + TD/Sky
- 본편 + 지역 전체
- 본편 + 지역 전체 + Rebirth 기본판 및 기존 지역 모듈
- 본편 + 지역 전체 + Rebirth 대체판 및 기존 지역 모듈

모든 구성에서 끊어진 명시 링크, TOP/MRK 충돌, 잘못된 @/# 구조 및 비대상 대사의 토픽 집합 변경 **0**.
본편 단독은 신규 토픽 3곳을 복구하며, 지역 모드가 함께 있을 때는 보호한 링크 5곳까지 복구한다.
탈로스 교단의 명시 링크가 짧은 ‘탈로스’ 암시 링크를 포함하는 것은 검토한 변경이다.

전체 지역/Rebirth 구성의 일반 AddTopic 잔여 후보는 기존 영문 Maurrie fallback 1곳뿐이다.
한국어 Maurrie 경로는 이미 정상 목표를 추가한다. `T_ScTest_*` 1,490회는 일반 플레이용과
분리해 보존했다. 일부 지역만 설치한 구성에서는 TD가 다른 선택 지역 모드에 대해 가진 기존
조건부 참조가 남는다. 새로 끊긴 호출 위치는 없지만, 이 조건부 스크립트들의 실제 실행 가능성을
전부 검증했다는 의미는 아니다.

도구: `build_direct_topic_fixes.py`, `topic_fix_helpers.py`.
입력: `direct_topic_fixes_inputs.json`. `MORROWIND_MASTER_DIR`로 원본 master 폴더를 지정할 수 있다.
다운로드한 원본 ZIP들이 있는 작업 폴더에서 빌더를 실행한다. 빌더는 별도 출력 폴더에만 쓴다.
검사 요약: `direct_topic_fixes_native_verification.json`; 바이트 보존/실패 차단 단위 검사 6개 통과.

**실게임 퀘스트 진행·기존 세이브·NPC 조건별 선택지 테스트 및 정식 배포는 아직 하지 않았다.**
이 검증은 위 로드 순서의 토픽 데이터와 네이티브 문자열 검색을 대상으로 하며, 세계/아이템/다른 모드
상호작용 전체가 무오류라는 보증이 아니다. PFP 및 개별 공식 애드온 조합은 포함하지 않았다.
