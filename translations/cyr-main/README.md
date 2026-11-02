# Project Cyrodiil 26.09a 한국어 테스트 번역

OpenMW-KR용 **독립 선택 모드 번역**입니다. 엔진 통합판에 자동 설치하지 않습니다.
원본 Project Cyrodiil 26.09a Hotfix 1과 그 필수 모드가 필요합니다.

## 한영 대조와 수정

- [Excel 한영 대조표](26.09a/Cyr_Main.en_ko.xlsx): 영어 원문과 한국어를 나란히 확인합니다. 종류, 레코드 ID, 토픽 ID, 검수 상태로 필터링할 수 있습니다.
- [원본 보존 대조 데이터](26.09a/Cyr_Main.en_ko.jsonl.gz): 태그·개행·변수와 원문 위치/해시를 그대로 보존한 빌드 입력입니다.
- [검증 및 원문 해시](26.09a/manifest.json).

15,046개 필드 중 `AI_SOURCE_REVIEWED`는 6,500개, `HOLD`는 8개,
`EXISTING_TRANSLATION_UNREVIEWED`는 기존 저장소 번역 8,538개입니다.
전체가 새로 검수되었다는 뜻이 아닙니다. AI 검수와 실제 플레이 검증도 구분합니다.
대조표는 열람용이며, 수정 사항을 빌드에 반영하려면 JSONL의 해당 `ko`와 검증 해시를 함께 갱신해야 합니다.

## 재현 가능한 로컬 빌드

Python 표준 라이브러리만 사용합니다. 원본 ESM은 이 저장소에 포함하지 않습니다.

```powershell
python translations/cyr-main/build.py --check-only
python translations/cyr-main/build.py --source "원본/Cyr_Main.ESM" --output "별도출력/Data Files/Cyr_Main.ESM"
```

원본 SHA-256, 모든 대상 필드, 변수·태그·개행·명시 링크·내부 ID를 확인하며,
출력은 검증된 테스트 ESM 해시와 정확히 일치해야 합니다. 원본 덮어쓰기는 거부합니다.
일반적인 번역 수정을 배포할 때는 변경된 입력과 새 테스트 결과에 맞춰 manifest를 갱신해야 합니다.

## GitHub 및 Nexus 배포

테스트 ZIP과 SHA-256은 `cyr-main-26.09a-kr-test-20261102` 사전 릴리스에 게시합니다.
Nexus 배포는 `.github/workflows/nexus-cyr-main.yml`의 수동 실행을 사용합니다.
기존 엔진 Full ZIP 배포와 별개이며 `category: optional`, `update_mod_version: false`입니다.

1. GitHub Release에 `Cyr_Main_26.09a_KR_TEST_20261102.zip`과 같은 이름의 `.sha256`을 업로드합니다.
2. 기존 저장소 secret `NEXUSMODS_API_KEY`를 사용합니다. 키를 파일에 기록하지 않습니다.
3. Nexus 관리 화면에서 **시로딜 선택 파일 전용** 업로드 API File ID를 확인합니다. 엔진 통합판 File ID를 넣지 않습니다.
4. 워크플로에 릴리스 태그와 전용 File ID를 입력하고 먼저 `dry_run=true`로 검증합니다.
5. 검증 후 `dry_run=false`로 업로드합니다. 현재 버전을 보관하며 엔진 통합판 버전은 변경하지 않습니다.

**실제 게임 실행·토픽 클릭·책 글꼴 검증은 아직 수행하지 않았습니다.**
8개 보류를 포함한 시험용 번역이며 Nexus에 정식 검증 완료본으로 표시하지 않습니다.
