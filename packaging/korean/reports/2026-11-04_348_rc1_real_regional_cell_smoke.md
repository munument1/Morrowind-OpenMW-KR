# KR12.7 / 지역 모드 RC1 — 실제 OpenMW 셀 로딩 추가 검사

**날짜 2026-11-04. 정식 릴리스 미게시.** 다음은 [348개 INFO 회귀 및 엔진 대조 보고](2026-11-04_manual_348_rc1_real_engine_qa.md)에 이어 수행한 독립 지역 셀 스모크 테스트이다.

## 환경·제약

- Windows OpenMW-KR **0.51.0** 포크 실행 파일, 기본 `Morrowind.esm`/`Tribunal.esm`/`Bloodmoon.esm`, `Patch for Purists.esm`, `Tamriel_Data.esm`, `TR_Mainland.esm`, `Morrowind_Korean_ReTranslation.esp` 함께 로딩.
- 검증 대상으로 고정한 **348건 수정 RC1**에서 읽어온 플러그인 바이너리와 별도의 사용자 데이터·설정·로그 디렉터리 사용. 사용자 원본 파일·설치 게임·세이브 미변경.
- `--start <cell>` 와 `--skip-menu=1`을 사용하되 `--new-game=1` 옵션을 **명시하지 않음**. 이 경우 목적지 진입 확인 가능. 반대로 `--new-game=1`을 함께 주면 도입부 `Imperial Prison Ship`에 진입하므로 해당 시험 결과는 **지역 셀 검증에서 제외**.
- **이 셀 스모크 시도에서는 전체 스크립트 재컴파일 기능을 끔.** 별도 [실제 지역 플러그인 스크립트 대조 시험](2026-11-04_manual_348_rc1_real_engine_qa.md)에서 확인한 40,626 / 40,628 컴파일 결과와 구분한다.

| 목표 셀 | 실제 OpenMW 로그의 셀 진입 결과 | 검사 시간 | 지역 리소스 누락 이벤트 |
|---|---|---:|---:|
| `Arvs-Shadan` | `Loading cell Arvs-Shadan` | 28초 | 68 |
| `Sailen` | `Loading cell Sailen (38,-16)`, `(37,-16)` 및 주변 7개 셀 | 18초 | 250 |
| `Bal Foyen` | `Loading cell Bal Foyen (1,-17)`, `(0,-17)`, 항구와 주변 6개 셀 | 18초 | 1,359 |
| `Evos` | `Loading cell Evos` (내부 셀) | 18초 | 0 |

**네 지점 모두 실제 셀 로딩까지 확인했다.** `Evos`는 마을 외부 지도 전체가 아니라 **Evos 내부 셀**이며, Nelyn 오두막의 동서 방향은 별도 TES3 좌표 분석으로 판정했다.

## 리소스 누락의 의미

추출한 한국어 지역 ZIP은 **원본 메쉬·텍스처 리소스 전체를 포함하는 모드 설치본이 아니다.** 격리 시험에서는 `meshes/tr/...`, `meshes/pc/...`, `meshes/sky/...`, `textures/tr/...` 등의 리소스가 없어 렌더 오류가 다수 기록됐다. **이 숫자를 번역 ESP가 새로 깨뜨린 오류로 해석하면 안 된다.** 완전한 Tamriel Data / Tamriel Rebuilt 원본 리소스가 연결된 테스트 환경에서 다시 확인해야 한다.

또한 테스트 환경의 UI Lua 오류는 공개판과 수정판 모두에서 재현됐다. 이 실험은 셀 탐색 및 로딩 성공을 확인한 것으로, NPC 대화 창 열기와 실제 퀘스트 진행의 성공은 증명하지 않는다.

## 정식 릴리스 판단과 남은 확인

- 확정: **367 INFO 전수 수동 검수**, 신규 승인 **313 INFO + 기존 35 INFO = 348 INFO**, 12개 구성 **755,471회 네이티브 토픽 회귀 0건 손실**, 실제 0.51 엔진에서 공개판/수정판 대화 스크립트 **40,626 / 40,628 동일**, 새 엔진 오류·경고 **0건**, 지역 **4곳 셀 로딩**.
- 원본부터 존재하는 2개 대화 스크립트 오류는 PFP `Greeting 1`의 `Goobye`, TR_Mainland `letter to Kha'Raji`의 NPC ID 참조이며, 양쪽 번역판의 `INFO.BNAM` 스크립트 바이트는 원본과 동일함.
- 정식 릴리스 전에는 **원본 Tamriel Data/지역 모드 리소스 완전 설치**와 다음 실제 플레이 경로 확인 권장:
  1. Sailen에서 Veradul Delvas의 Nelyn Fathis 안내를 받아 Evos 동쪽 길 안내/링크가 정상인지 확인.
  2. Arvs-Shadan에서 마법사를 처치한 후 Alvayah의 인사 및 이름 토픽 링크가 정상인지 확인.
  3. Bal Foyen에서 해당 Temple NPC의 **발 포옌** 및 **알말렉시아** 클릭 토픽이 둘 다 나타나고 정상적으로 연결되는지 확인.
  4. PFP 및 Morrowind Rebirth 메인/대체, Rebirth-Cyr/Sky 호환 구성을 실제 리소스와 함께 활성화하고 퀘스트 단계·UI·세이브 로딩 확인.
- 현재 공식 배포 작업은 **RC1 ZIP 7개 준비까지 완료**, Nexus·GitHub Release 공개 업로드 미실시.

RC1 ZIP 목록 및 해시: [348건 검증·RC1 보고](2026-11-04_manual_348_rc1_real_engine_qa.md). 로컬 산출물: `OPENMW_REAL_348_TARGETED_CELL_START_NO_NEWGAME_V2_20261104/` 및 `OPENMW_REAL_348_TARGETED_CELL_START_SAILEN_BALFOYEN_EVOS_V3_20261104/`. 대상 시험을 위해 실행한 OpenMW 프로세스만 종료, 기존 다른 프로그램에는 손대지 않음.
