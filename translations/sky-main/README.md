# Skyrim: Home of the Nords 26.09a 한국어 테스트 번역

OpenMW-KR에서 사용하는 **별도 선택 모드 번역**입니다. 원본 Skyrim: Home of the Nords 26.09a와 해당 버전의 필수 모드가 필요합니다.

- [Excel 한영 대조표](26.09a/Sky_Main.en_ko.xlsx): 종류, 레코드 ID, 토픽 ID, 영어·한국어, 검수 상태, 원문 위치 키로 확인합니다.
- [원문 보존 JSONL](26.09a/Sky_Main.en_ko.jsonl.gz): 태그·개행·변수·원문 해시를 보존하는 재빌드 입력입니다.
- [버전과 해시](26.09a/manifest.json), [독립 ESM 검증](26.09a/independent_binary_validation.json), [이번 표본 점검의 수정 내역](26.09a/spotcheck_corrections.json).
- [테스트 ZIP 릴리스](https://github.com/munument1/Morrowind-OpenMW-KR/releases/tag/sky-main-26.09a-kr-test-20261102).

8,279개 대조 행 가운데 실제 번역 적용은 8,202개입니다.

| 상태 | 행 수 | 의미 |
| --- | ---: | --- |
| `AI_SOURCE_REVIEWED` | 1,498 | 기존 AI 원문 대조 검수와 보완 반영 |
| `AI_SPOT_REVIEWED` | 6 | 이번 점검에서 기존 번역의 조사·저널 의미를 대조·수정 |
| `EXISTING_TRANSLATION_UNREVIEWED` | 6,698 | 기존 번역 재사용, 구조·원문 앵커 확인 |
| `HOLD` | 4 | 별명·룬 문자·암호·원문 비문 문제로 원문 유지 |
| `INTERNAL_SOURCE_PRESERVED` | 73 | 개발용 위치 마커 원문 유지, 번역 적용에서 제외 |

대조표에 포함됐다고 모두 새로 전수 감수한 것은 아닙니다. 이번에는 표시 필드 전체의 구조를 검사하고 대사·저널·책·표시명 40개 표본 및 NPC 이름 뒤의 조사를 점검해 오류 7곳을 수정했습니다. 책 표본은 발췌 점검입니다. AI 검수와 실제 게임 검증은 구분합니다.

Excel은 열람용입니다. 수정 사항을 빌드에 반영하려면 JSONL의 해당 `ko`와 manifest 해시·검증된 출력 해시를 함께 갱신해야 합니다. `applied=false`인 보류·개발 마커는 영어 원본 바이트 그대로 남깁니다.

## 원본에서 재빌드

Python 표준 라이브러리만 사용하며 원본 모드 ESM은 저장소에 포함하지 않습니다.

```powershell
python translations/sky-main/build.py --check-only
python translations/sky-main/build.py --source "원본/Sky_Main.ESM" --output "별도출력/Data Files/Sky_Main.ESM"
```

원본 SHA-256, 레코드 위치, 하위 레코드 해시, 영어·한국어 태그·변수·링크·내부 ID와 출력 ESM 해시를 검증합니다. 원본 또는 이미 존재하는 출력 파일을 덮어쓰지 않습니다. 실제 설치에는 원본 모드의 전체 자산을 유지하고 같은 `Sky_Main.ESM`을 하나만 활성화해야 합니다.

## Nexus 배포 준비

`.github/workflows/nexus-sky-main.yml`은 테스트 ZIP을 확인하는 수동 워크플로입니다. `dry_run=true`는 Nexus 파일 ID 없이 실행할 수 있습니다.

실제 업로드에는 **Sky_Main 선택 파일 전용 v3 업로드 API File ID**와 저장소 secret `NEXUSMODS_API_KEY`가 필요합니다. 현재 방식은 이미 등록된 파일의 새 버전을 업로드하므로 첫 모드 페이지·파일 등록은 별도로 준비해야 합니다. 기본 엔진 통합판 파일 ID를 사용하지 마세요. `category=optional`, `update_mod_version=false`이며 기존 파일을 보관 처리하지 않습니다.

이 커밋은 Nexus에 업로드하거나 모드 페이지를 공개하지 않습니다. 원본 모드 제작진과 기존 한국어 번역 자료를 바탕으로 제작한 테스트 번역이며, **실제 게임의 토픽 클릭·저널 링크·서적 글꼴·세이브 로드는 아직 검증하지 않았습니다.**
