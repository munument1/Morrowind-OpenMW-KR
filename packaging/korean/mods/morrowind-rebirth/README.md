# Morrowind Rebirth 7.2 — v56 최종본 통합 관리

이 경로의 유일한 이관 기준은 **`Morrowind_Rebirth_7.2_Korean_OpenMW_KR12_v56_Full_Layout.zip`**이다. v1~v55 중간 단계, 초기 `optional_ko_v1` 150필드 초안, 수백 개의 작업용 JSON/QA를 이 저장소로 복사하지 않는다.

## 기준 버전

- 원본: Morrowind Rebirth 7.2 (`Morrowind Rebirth 37795 7.2 2026-10-23T19-19Z nOlkOzNs`)
- v56 ZIP SHA-256: `8b07aec7d2400f22c60f9833d6339185a54acea687de9ed7f8a9c1030bf6d8f3`
- 번역/런타임 기존 기준: OpenMW **KR12**. **KR12.4 검증 완료라고 주장하지 않는다.**
- 예상 최종 파일 구성: 15개 플러그인 = 기본 메인 1 + 대체 메인 1 + 애드온 6 + 호환 패치 7
- 애드온: Birthsigns, Mercenaries, Races, Skills, Tools, Game Settings. Game Settings에는 번역 대상 표시 텍스트가 없으므로 원본 유지.
- 호환 패치 7개는 번역이 아닌 원본 보존. 대체 메인은 원본의 독자적인 게임 설정·모델을 유지.
- v56의 과거 Windows KR12 스모크·주요 대화 경로 검수 기록은 비공개 원본 저장소 `BGS_Translation_Originals`의 `morrowind/region-expansions-eet/KR12_REBIRTH_TRANSLATION_REFERENCE_20261029_KO.md`에 있다. 전체 게임 완주나 Android 테스트를 의미하지 않는다.

## 왜 단일 번역 코퍼스로 관리하나

**15개 ESP/ESM을 물리적으로 합치지 않는다.** 게임 플러그인 경로와 의존 관계는 그대로 유지하면서, 원본 플러그인 대비 바뀐 한국어 필드만 **하나의 정적 코퍼스**(`REBIRTH_72_KR12_V56_CONSOLIDATED_PRIVATE.jsonl.gz`)로 관리한다. SHA 고정 원본을 통해 15개 결과물을 각각 재현할 수 있도록 만든다.

GitHub에는 **검증용 파이썬 도구·합성 테스트·SHA 매니페스트**만 둔다. v56 실제 번역 코퍼스, 원본 Rebirth/베데스다 리소스 및 전체 ESP/ESM 바이너리는 원래 비공개 환경에서 보존한다. 대용량 최종 ZIP을 공개 리포지토리로 복사하지 않는다.

## 단일 v56 최종 코퍼스 생성 (로컬 전용)

v56 **실제 ZIP**과 Rebirth 7.2 **원본 전체를 압축 해제한 폴더**가 있는 환경에서만 실행한다. 원본 폴더에는 Data Files, Alternate Version, Compability Patches의 기존 파일·상대 구조가 들어 있어야 한다.

```powershell
python packaging/korean/mods/morrowind-rebirth/rebirth_v56_consolidate.py capture `
  --v56-zip "D:\Rebirth\Morrowind_Rebirth_7.2_Korean_OpenMW_KR12_v56_Full_Layout.zip" `
  --source-root "D:\Rebirth\Original_7.2" `
  --out "D:\Rebirth\_NEW_PRIVATE_REBIRTH_V56_CORPUS"
```

도구는 v56 ZIP의 **전체 SHA 일치**와 **15개 파일의 유형별 수량**을 검사하고, 각 ESP/ESM의 TES3 레코드/서브레코드 및 원본 비문자열 바이트를 비교한다. 원본 데이터의 레코드/필드 개수, 순서, 플래그와 비텍스트 필드가 달라지면 자동 병합하지 않고 실패한다. 변경 허용 필드 외 수정도 실패로 남긴다.

성공하면 새 출력 폴더에 파일 두 개만 생성한다.

- `REBIRTH_72_KR12_V56_CONSOLIDATED_PRIVATE.jsonl.gz`: 15개 플러그인의 **최종 v56 변경 필드 전부와 세 개의 .top 토픽 별칭 데이터**를 담은 단일 비공개 코퍼스. 원본 파일별 SHA 및 각 원문 서브레코드 오프셋/해시로 고정.
- `REBIRTH_72_KR12_V56_SOURCE_ANCHORED_MANIFEST.json`: 15개 원본 및 v56 결과 SHA, 변경 수량, 컴파일 검토 필요 SCTX 수량.

새 번역으로 재생성하지 않는다. 모든 변경을 **v56 출력물 자체에서 추출**한다.

## 나중에 동일한 v56 플러그인 15개와 TOP 3개를 재생성하려면

```powershell
python packaging/korean/mods/morrowind-rebirth/rebirth_v56_consolidate.py apply `
  --corpus "D:\Rebirth\_NEW_PRIVATE_REBIRTH_V56_CORPUS" `
  --source-root "D:\Rebirth\Original_7.2" `
  --out "D:\Rebirth\_NEW_REBIRTH_V56_REBUILT"
```

각 출력 ESP/ESM의 SHA가 최초 v56 패키지의 개별 결과 SHA와 **정확히 같아야** 성공한다. 원본 및 기존 설치 폴더는 덮어쓰지 않으며 출력 경로는 반드시 비어 있는 **새 디렉터리**여야 한다. 자산 파일은 별도 원본 Rebirth 설치 상태를 그대로 사용한다.

## 주의: v56 ≠ KR12.4 검증 완료

v56은 KR12 기준으로 빌드·검사된 과거 최종본이다. `DIAL.NAME`과 `AddTopic` 연결, `SCPT.SCTX`/컴파일된 `SCDT`, NPC 대사, 자막, 선택지, 저널, 지역 표시는 **KR12.4 변경 영향**을 별도로 확인해야 한다. 특히 대체 메인은 기본 메인의 번역 데이터를 통째로 덮어서는 안 된다.

## 2026-11-01 실제 v56 파일 전수 대조 결과

사용자가 제공한 **v56 최종 ZIP(91,344,684 bytes)**과 **Rebirth 7.2 원본 RAR**의 ESP/ESM 15개를 직접 대조했다.

- v56 전체 ZIP SHA: `8b07aec7d2400f22c60f9833d6339185a54acea687de9ed7f8a9c1030bf6d8f3` (기존 기록과 일치)
- 원본 RAR SHA: `8f31db65c01e41744842c10151a3a5259e1e57668e6f89e444b10a73a2a20ee0`
- 실제 번역/문자열 변경: **27,016개 필드** — 일반 메인 13,268 / 대체 메인 13,268 / Birthsigns 40 / Mercenaries 330 / Races 51 / Skills 19 / Tools 40.
- Game Settings 애드온 및 호환 패치 7종은 원본 바이너리와 동일.
- **3개 TOP 토픽 별칭 파일**은 배포에 필수이므로 동일한 단일 코퍼스에 포함. 일반 메인·대체 메인·용병 애드온에 대응하며 상대 경로와 내용 SHA도 검증.
- 변경은 TES3의 허용된 표시 문자열 필드에 한정; `REPA.FNAM`, `LOCK.FNAM`, `PROB.FNAM` 역시 v56 실제 변경이 있어 검증 대상에 추가.
- `SCPT.SCTX` **39개는 소스만 바뀌었으므로** KR12.4에서 실제 스크립트 실행/컴파일 경로 별도 검증 필요.
- 전체 15개 플러그인과 3개 TOP 파일은 단일 코퍼스를 통한 바이트 단위 재구성 및 v56 원본 파일과의 SHA 대조 **PASS**.

생성된 비공개 코퍼스: `REBIRTH_72_KR12_V56_CONSOLIDATED_PRIVATE.jsonl.gz` (4,980,743 bytes), SHA-256 `63605e2f063247ec6ccc66e1fd8fdf1650237629a14779e3fddfe2cf59a47c43`.

**이 공개 GitHub 저장소에는 비공개 번역 코퍼스 실물을 넣지 않는다.** 추출 결과는 사용자의 이번 대화에서 생성한 별도 파일로 제공한다. 업로드/공개 여부가 확정되지 않은 원본 게임 모드 바이너리도 저장소에 넣지 않았다. 저장소에는 정확한 해시·검사 도구·합성 테스트·재구성 방법만 관리한다. KR12.4 실제 게임 플레이, Android 실행, Nexus 배포는 진행하지 않았다.

**현재 이관 상태:** 저장소에는 v56 SHA·구성 및 재현 도구를 추가했지만, v56 ZIP과 원본 RAR로 최종 코퍼스 생성·대상별 SHA 재구성 QA를 완료했다. 비공개 중간 자료·원본 게임 파일·Nexus 페이지·기존 OpenMW KR 정식 배포는 수정하지 않았다.


## KR12.4 업데이트 영향 검토 — 2026-11-01

**결론: 공식 KR12.4 변경사항 중 Rebirth v56 한국어 소유 필드에 바로 이식할 바이트 변경은 0건.** 기존 v56 최종본과 단일 코퍼스 그대로 보존한다. KR12.4용 Rebirth v57을 임의로 생성하지 않는다.

- 대상: 사용자 제공 KR12 v56 최종 ZIP 고정 SHA `8b07aec7d2400f22c60f9833d6339185a54acea687de9ed7f8a9c1030bf6d8f3`.
- KR12.4 [공식 릴리스](https://github.com/munument1/Morrowind-OpenMW-KR/releases/tag/openmw-0.51.0-kr12.4)의 91개 INFO.NAME(퀘스트 링크 12, 잘못된 명시 링크 79), 별칭 3개를 원문 INFO ID·문구 패턴·별칭 키 기준으로 점검.
- KR12.3.1의 4개 퀘스트 링크 INFO ID도 점검. **Rebirth 번역 메인/선택 애드온에 일치 항목 없음.**
- v56에서 원본 보존한 미번역 `Morrowind Patch Project v1.6.6 [For Rebirth].esm`에는 INFO ID 3개(12.4 관련 2, 12.3 관련 1)가 존재하나 영어 원문이며 **수정하지 않음**. 모드 로드 순서와 조건을 확인하지 않고 본편 번역으로 교체하지 않는다.
- Rebirth `.top` 3개에는 KR12.4의 아우데니안 별칭 수정 대상이 없음.
- KR12.1 효과·마법 범위 등의 UI 표기와 KR12.2/12.4 토픽 엔진 수정은 Rebirth ESP에 임의 복사하지 않고 **KR12.4 엔진 및 공식 본편 번역 데이터와 함께 사용**한다.

검사 도구: `audit_kr124_release_deltas.py`  
검사 기록: `KR124_V56_RELEASE_DELTA_IMPACT_QA_20261101.json`

**제한:** 이번 검사는 공식 릴리스 변경 소스 기반의 정적 영향 검토다. KR12.4 공식 ESP 바이너리 **전수 직접 비교**나 Rebirth 게임 내 토픽·퀘스트 경로 실행 검증은 아니므로 KR12.4 호환 전체 검증 완료/신규 릴리스 준비 완료로 표기하지 않는다.
