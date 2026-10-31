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

- `REBIRTH_72_KR12_V56_CONSOLIDATED_PRIVATE.jsonl.gz`: 15개 플러그인의 **최종 v56 변경 필드 전부**를 담은 단일 비공개 코퍼스. 원본 파일별 SHA 및 각 원문 서브레코드 오프셋/해시로 고정.
- `REBIRTH_72_KR12_V56_SOURCE_ANCHORED_MANIFEST.json`: 15개 원본 및 v56 결과 SHA, 변경 수량, 컴파일 검토 필요 SCTX 수량.

새 번역으로 재생성하지 않는다. 모든 변경을 **v56 출력물 자체에서 추출**한다.

## 나중에 동일한 v56 플러그인 15개를 재생성하려면

```powershell
python packaging/korean/mods/morrowind-rebirth/rebirth_v56_consolidate.py apply `
  --corpus "D:\Rebirth\_NEW_PRIVATE_REBIRTH_V56_CORPUS" `
  --source-root "D:\Rebirth\Original_7.2" `
  --out "D:\Rebirth\_NEW_REBIRTH_V56_REBUILT"
```

각 출력 ESP/ESM의 SHA가 최초 v56 패키지의 개별 결과 SHA와 **정확히 같아야** 성공한다. 원본 및 기존 설치 폴더는 덮어쓰지 않으며 출력 경로는 반드시 비어 있는 **새 디렉터리**여야 한다. 자산 파일은 별도 원본 Rebirth 설치 상태를 그대로 사용한다.

## 주의: v56 ≠ KR12.4 검증 완료

v56은 KR12 기준으로 빌드·검사된 과거 최종본이다. `DIAL.NAME`과 `AddTopic` 연결, `SCPT.SCTX`/컴파일된 `SCDT`, NPC 대사, 자막, 선택지, 저널, 지역 표시는 **KR12.4 변경 영향**을 별도로 확인해야 한다. 특히 대체 메인은 기본 메인의 번역 데이터를 통째로 덮어서는 안 된다.

**현재 이관 상태:** 저장소에는 v56 SHA·구성 및 재현 도구를 추가했지만, v56 ZIP 실물이 현재 연결된 소스에서 확인되지 않아 최종 코퍼스 생성/대상별 SHA QA는 아직 실행하지 못했다. 비공개 중간 자료·원본 게임 파일·Nexus 페이지·기존 OpenMW KR 정식 배포는 수정하지 않았다.
