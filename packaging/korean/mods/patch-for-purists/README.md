## 2026-11-02 후속 검수 및 kr1.1

Nexus 60826: 5.0.7-kr1.1. 실제 공개 kr1.0 패키지를 기준으로 책/간판 3필드, INFO 링크 범위 12필드와 TOP 별칭 3개 교정. 아래 v19 초안 빌더와는 별개의 공개 배포본 유지보수 작업이다.

원본 SHA 고정, 표시 대사·토픽 대상 보존 및 비대상 필드 전수 대조를 수행한다. 실게임 검증은 수행하지 않았다. Nexus 게시 완료 여부와 다운로드 해시는 `publish-reviewed-mod-translations.yml`의 최종 검증 기록을 참조한다. 아래 내용은 기존 작업 기록이다.

---

# Patch for Purists 5.0.7 / OpenMW KR12.4 작업 워크플로

이 경로는 **OpenMW 0.51.0 / 한국어판 KR12.4 전용 PFP 번역 도구**다. 엔진 소스 패치가 아닌 ESM 데이터 번역으로, 게임에서 PFP 원본 플러그인을 **`Patch for Purists.esm` 한 파일로 덮어쓰는 방식**을 유지한다. 별도 ESP, 런타임 훅, 사용자용 설치기 또는 자동 덮어쓰기는 만들지 않는다.

## 데이터의 위치와 현재 상태

- 비공개 원본/번역 저장소: `munument1/BGS_Translation_Originals`, 브랜치 `feature/mw-kr124-python-pfp507-20261031`.
- 현 단계의 보존된 *v19 초안*: 원문 기준 필드 8,823개 중 한국어 초안 8,815개, 보류 8개(책 6, 내부 액티베이터 2). **사람의 최종 교정이나 게임 실행 테스트가 끝난 릴리스가 아니다.**
- 작업 브랜치의 `morrowind/pfp507_kr124_private_upgrade/PFP507_KR124_EFFECTIVE_8815_PRIVATE_DRAFT.jsonl.gz`와 `PFP_KR124_MIGRATION_REPORT.json`을 별도로 가져와야 빌드할 수 있다. **이 자료를 공개 저장소에 올리지 않는다.**
- 이전 작업에는 9,494개 서브레코드 변경 시험본과 스크립트 검수 후보도 존재하지만, 그 후속 산출물은 이 v19 빌더와 동일하지 않다. 검증된 신규 매니페스트로 이관하기 전에는 8,815개 초안을 최종본이라고 주장하지 않는다.
- PFP 5.0.7 정본 원본 ESM SHA-256: `8593e1446e2e569a356f0d9a4b69582d1e113ffcdcc25ba953bee3524d286818`.
- KR12.4 공식 한국어 ESP SHA-256: `2276384ad93fd3e56bc0d401aacc45418ba38993ee798e0e1a7e09564a375d3a`.

기존 비공개 저장소의 병합 과정과 인접 검수 보고서는 **계속 원래 위치에 보존**한다. 공개 레포는 빌더·테스트·가이드만 보유한다. 원본 PFP, Bethesda ESM/BSA, 비공개 번역문, 기계 생성 시험 ZIP, 개인 게임 데이터는 포함하지 않는다.

## 로컬 제작 (정적 시험본만)

먼저 공식 PFP 5.0.7의 `Patch for Purists.esm`과 위의 비공개 JSONL.GZ/JSON 두 개를 준비한다. PowerShell의 경로를 실제 로컬 파일로 바꿔 실행한다.

```powershell
python packaging/korean/mods/patch-for-purists/pfp507_build_overwrite_kr124.py `
  --source "D:\Morrowind\Data Files\Patch for Purists.esm" `
  --draft "D:\Private\PFP507_KR124_EFFECTIVE_8815_PRIVATE_DRAFT.jsonl.gz" `
  --report "D:\Private\PFP_KR124_MIGRATION_REPORT.json" `
  --out-dir "D:\PFP507_KR124_NEW_PRIVATE_QA"
```

- **이미 존재하는 출력 디렉터리, 원본과 다른 SHA, 원문 바이트/레코드 앵커 불일치, 중복 오프셋, 검수 미완료 상태의 변경은 즉시 중단**한다.
- 출력물에는 `Patch for Purists.esm`, **정적 시험용** `PFP507_KR124_OVERWRITE_PRIVATE_TEST.zip`(내부 멤버는 ESM 하나), `PFP507_KR124_OVERWRITE_QA.json`이 들어간다.
- ESM의 번역 대상 이외 모든 서브레코드 원문 바이트를 다시 비교한다. `INFO.BNAM`과 `SCPT.SCTX/SCDT`는 이 v19 빌더에서 원본 보존한다.
- 데이드릭 글꼴·이미지 책·해독 전 문서 등 보류 8필드는 **원본 상태로 유지**한다. 기존 교정 및 용어집의 `타이버 셉팀` 표기도 유지한다.
- 실제 OpenMW 한국어 화면, 로드 순서, NPC 토픽, 퀘스트, 스크롤 및 모드 충돌을 시험하지 않았으므로 이 ZIP을 **정식 배포하거나 KR12.4 릴리스에 자동 포함하지 않는다.**

## 공개 저장소 CI

`pfp-translation-qa.yml`은 PFP 원본이나 비공개 초안을 내려받지 않는다. 안전한 **합성 TES3 레코드**로 서브레코드 구조·원문 SHA 앵커·바이트 비변경 검사를 수행한다. CI PASS는 **실제 PFP 번역 검증 완료가 아니라 코드 구조 검증**을 뜻한다.

추후 9,494개 변경 후속 시험본을 합치려면 기존 초안과 충돌하는 필드별 SHA 대조, 승인된 오버레이 순서 및 실제 게임 검증 근거를 따로 보관한 뒤, 별도 PR로 빌더를 확장한다. 엔진/한국어 번역 정식 릴리스와 PFP 전용 릴리스는 항상 분리한다.
