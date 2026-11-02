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

## 배포 방침

GitHub에는 번역 대조 데이터·검수 상태·해시·재빌드 도구만 보관합니다. 모드 ESM/ESP 및 설치 ZIP은 GitHub Releases에 게시하지 않습니다. 앞서 게시한 테스트 릴리스는 로컬에 백업한 뒤 공개 목록에서 제거했습니다.

실제 모드 파일 배포는 Nexus Mods에서만 진행합니다. 로컬에서 해당 원본 모드로 재빌드·패키징한 테스트 ZIP을 Nexus에 올립니다. 기존 엔진 통합판의 파일과 혼동하지 않도록 별도의 모드 파일 항목을 사용합니다.

기존 이름의 `nexus-cyr-main.yml` 워크플로는 이제 번역 데이터 검사만 수행합니다. GitHub Release를 생성·다운로드하거나 Nexus에 파일을 업로드하지 않습니다.

실제 게임의 토픽·저널 링크·서적 글꼴·세이브 로드는 별도로 시험해야 합니다.
