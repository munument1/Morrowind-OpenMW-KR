# Tamriel Rebuilt 26.11.2 한국어 번역 데이터 — kr0.1

OpenMW-KR용 **초기 테스트 번역**입니다. 원본·번역 ESM/ESP, 엔진, 게임 자산 및 설치 ZIP은 이 폴더에 포함하지 않습니다. 모드 설치 파일은 Nexus Mods 배포 대상으로 분리합니다.

- [Mainland 영한 대조 데이터](26.11.2-kr0.1/TR_Mainland.en_ko.jsonl.gz): 후보 90,106행 중 88,521개 적용, 1,585개 원문 보존.
- [Factions 영한 대조 데이터](26.11.2-kr0.1/TR_Factions.en_ko.jsonl.gz): 318행 중 표시 필드 315개 적용, 내부 제어 액티베이터 3개 원문 보존. 적용 필드에는 계급명 109개가 포함됩니다.
- [Factions 스크립트 표시 문구](26.11.2-kr0.1/TR_Factions.script_display.jsonl.gz): 선택지·알림 19회. OpenMW가 컴파일하는 SCTX/BNAM 문자열만 번역하며 원본 SCDT는 보존합니다.
- [지역 표시명 CEL](26.11.2-kr0.1/TR_Mainland.cel), [TOP](26.11.2-kr0.1/TR_Mainland.top), [MRK](26.11.2-kr0.1/TR_Mainland.mrk), [JRN](26.11.2-kr0.1/TR_Mainland.jrn): UTF-8 BOM. CEL 3,887개, 나머지 각각 755개 연결입니다.
- [버전·원본/출력 해시·검수 상태](26.11.2-kr0.1/manifest.json), [Mainland 바이너리 QA](26.11.2-kr0.1/TR_Mainland_binary_QA.json), [Factions QA](26.11.2-kr0.1/TR_Factions_QA.json), [보조 파일 QA](26.11.2-kr0.1/OpenMW_sidecar_QA.json).

Mainland 적용 번역 88,521개 중 87,013개는 기존 번역 재사용(`EXISTING_TRANSLATION_UNREVIEWED`), 1,508개는 기존 AI 원문 대조/구조 교정·후속 검수 자료에 해당합니다. 새로 전수 의미 감수를 끝냈다는 뜻이 아닙니다. 실게임 검증 완료로 표시하지 않습니다.

대사 문맥 변경 26,805개 중 26,737개는 결과 스크립트 BNAM 끝 NUL 차이뿐임을 원본끼리 비교했습니다. 이 판정은 번역문 전체의 의미 검수가 아닙니다. [근거 데이터](26.11.2-kr0.1/dialogue_context_equivalence.jsonl.gz)에 나머지 실제 변경 68개의 보류 판정도 포함합니다.

Mainland의 남은 보류는 숫자 의미 888개, 실제 문맥 변경 68개, Daedric 본문 57개, 내부 마커·빈 번역 등입니다. 같은 필드에 사유가 겹칠 수 있어 단순 합산하지 않습니다. 데이터에서 `applied=false`, `ko=null`, `hold_reasons`로 구분합니다. 고유 보류 필드는 1,585개입니다.

일반 셀/지역·문 목적지 이름은 정적 수집 범위에서 번역을 채웠으나, 새 고유명사 음역은 잠정 표기입니다. 내부·미공개 셀 120개는 [보류 데이터](26.11.2-kr0.1/cell_translation_holds.jsonl.gz)에 남겼습니다. 본편/Tamriel Data가 정의한 문 기본 이름은 각 번역이 담당하며 별도 문 이름 ESP는 만들지 않습니다. TOP/MRK/JRN은 토픽 연결을 보완하고 토픽 목록 전체 표시명을 번역하는 형식은 아닙니다.

## 원본에서 재빌드

Python 표준 라이브러리만 사용합니다. 원본 버전·필드 해시, 태그·변수·링크·개행, 레코드 순서 및 비대상 바이트와 최종 출력 해시를 확인합니다. 이미 존재하는 출력 폴더는 거부합니다.

```sh
python translations/tamriel-rebuilt/build.py --check-only
python translations/tamriel-rebuilt/build.py --mainland-source "원본/TR_Mainland.esm" --factions-source "원본/TR_Factions.esp" --output-dir "새출력/Data Files"
```

원본 Tamriel Rebuilt 26.11.2, Tamriel Data 26.08, Morrowind/Tribunal/Bloodmoon 및 모드 자산은 사용자가 준비해야 합니다. 번역문 수정 시 데이터/manifest 해시와 검증된 출력 해시도 함께 갱신해야 합니다.

한국어 혼합 UTF-8 ESM/ESP 및 UTF-8 BOM 보조 파일을 지원하는 OpenMW-KR 대상입니다. 바닐라 Morrowind의 컴파일 SCDT는 현지화하지 않았습니다. 원본 CELL 이름·엔진 ID·대화 조건은 유지하고, Factions의 TR_Mainland 마스터 크기 참고값은 번역 ESM에 맞춥니다.

**실게임 QA는 사용자 담당이며 kr0.1에서 아직 완료되지 않았습니다.** 실제 퀘스트 수행, 호타토르 선택지·보상·계급, 토픽/저널 링크, 서적/데이드릭 폰트, 저장·불러오기 검증이 남아 있습니다. 소스 구조 QA를 플레이 검증으로 간주하지 않습니다.
