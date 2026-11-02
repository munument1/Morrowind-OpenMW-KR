> 최신 누적 Windows 통합판: [KR12.5](https://github.com/munument1/Morrowind-OpenMW-KR/releases/tag/openmw-0.51.0-kr12.5). 29개 대사의 잘못된 명시 링크 31개를 정리했으며 KR12.4 엔진을 유지합니다. [변경 내역](packaging/korean/KR12.5.md). 아래 KR12.4 상세 내역은 기반 릴리스의 기록입니다.

# OpenMW 한국어판

[OpenMW](https://openmw.org/) 0.51.0에서 《The Elder Scrolls III: Morrowind》를 한국어로 실행하기 위한 **Windows x64용 한국어 엔진·번역 통합판**입니다. Bethesda의 Morrowind 원본 데이터는 포함하지 않으며 정품 게임이 필요합니다.

## 최신 정식 배포판 — KR12.4 (2026-10-31)

- [**KR12.4 릴리스 및 Windows 통합 ZIP 다운로드**](https://github.com/munument1/Morrowind-OpenMW-KR/releases/tag/openmw-0.51.0-kr12.4)
- 파일명: `Morrowind-Korean-OpenMW-0.51.0-KR12.4-Full.zip`
- 기준: 공식 `OpenMW/openmw` **0.51.0**, 커밋 `f4bec41444214a7903bebd178389ca22ca13f646` + 한국어 런타임 패치 0001~0016
- 이 저장소의 개발용 master가 OpenMW 0.52 계열 코드를 포함하더라도 **KR12.4 Windows 실행 파일은 0.51.0 기반**입니다.
- **별도 이슈 #42 패치를 설치할 필요가 없습니다.** 기존 KR12.3.1의 누적 업데이트입니다.

### KR12.4 변경 사항

1. 한국어 조사·서술격·호격·동사 어미에 걸친 토픽 자동 탐색 경계 개선 (`0016-korean-predicative-topic-boundaries.patch`).
2. 잘못된 명시 대사 링크 **79건** 정리 (설원곰·설원늑대 74건 포함).
3. 동일 INFO ID의 영어 원본과 비교한 퀘스트 대사 **12건**에 명시 토픽 링크 추가.
4. 아우데니안 발리우스 관련 `.top` 별칭 **3개**의 잘못된 연결 대상 수정.
5. 나머지 번역 문자열·퀘스트 조건·스크립트·모드 자산은 KR12.3.1을 유지합니다.

[이슈 #42](https://github.com/munument1/Morrowind-OpenMW-KR/issues/42)에서 검사 방법과 알려진 한계를 확인할 수 있습니다. 원본 ESP/TOP SHA, TES3 구조·표시 문자열 보존, 91개 INFO.NAME 및 별칭 3개만 변경한 사실, ZIP 무결성, 네이티브 토픽 회귀 시험 및 Windows 컴파일·OpenMW 테스트를 검증했습니다. [빌드/배포 CI](https://github.com/munument1/Morrowind-OpenMW-KR/actions/runs/41183812834)의 검증 결과 JSON도 릴리스에 첨부되어 있습니다.

> **한계:** 실제 게임에서 모든 NPC와 퀘스트 단계의 토픽 클릭·습득을 플레이하여 검증한 것은 아닙니다. 제보된 219줄/51개 토픽이 모두 해결됐다고 주장하지 않습니다. 의심되는 대사와 퀘스트 단계는 이슈 #42에 제보해 주세요.

## 설치 및 업데이트 (Windows)

1. 공식 **OpenMW 0.51.0 Windows x64**와 정품 Morrowind(필요한 Tribunal/Bloodmoon 원본 데이터 포함)를 준비합니다.
2. 기존 OpenMW 설치 폴더, 사용자 설정 파일과 세이브를 백업합니다.
3. 위의 **KR12.4 Full ZIP**을 별도 폴더에 압축 해제합니다.
4. `Install-Korean.bat`을 실행하고 안내에 따라 OpenMW 설치 폴더를 지정합니다. **Morrowind의 `Data Files`가 아니라 `openmw.exe`가 있는 폴더**입니다.
5. 기존 KR12.3.1 사용자도 같은 설치기로 업데이트할 수 있습니다. 문제가 생기면 백업에서 복원하고 로그와 설치 버전을 제보해 주세요.

설치기는 한국어 엔진·폰트·번역 모드와 `openmw.cfg`의 한국어 관리 설정을 갱신하며, 기존 파일을 백업합니다. 전역 `encoding=utf8`을 무조건 강제할 필요는 없습니다.

### 베데스다 공식 애드온 8종 한국어화 (선택 설치)

베데스다 **Official Plugins** 8종에 대한 기존 한국어 번역은 본편 KR12.4 Full ZIP과 별도입니다. 해당 애드온을 사용하지 않는다면 설치할 필요가 없습니다.

- **GOG판:** Official Plugins가 기본 제공되므로 별도 다운로드는 필요하지 않습니다. 게임 `Data Files`에 애드온 ESP가 실제로 존재하는지, OpenMW에서 사용할 애드온이 활성화되었는지는 확인하세요.
- **Steam판:** Official Plugins가 포함되지 않습니다. [Bethesda Official Plugins (Nexus #3882)](https://www.nexusmods.com/morrowind/mods/3882?tab=files)에서 원본 애드온 8종을 내려받아 `Data Files`에 설치하고 사용할 플러그인을 활성화하세요. **8개 개별 플러그인과 합본(Official Mods Compilation)을 중복 활성화하지 마세요.**
- **한국어 번역:** [KR12.4 릴리스의 `Morrowind_OfficialAddon_KR.zip`](https://github.com/munument1/Morrowind-OpenMW-KR/releases/tag/openmw-0.51.0-kr12.4) 또는 [Nexus Mods #60496의 Optional Files](https://www.nexusmods.com/morrowind/mods/60496?tab=files)에서 별도로 다운로드합니다. KR3에서 제작한 ESP 및 OpenMW용 `.top`/`.mrk`/`.cel` 보조 파일을 그대로 재배포한 것입니다. 원본 애드온 8종이 모두 없으면 번역 ESP를 활성화하지 마세요.
- **로드 순서:** 공식 애드온과 `Morrowind_Korean_ReTranslation.esp` 다음에 `Morrowind_OfficialAddon_KR.esp`를 로드하세요. 보조 파일도 같은 OpenMW 번역 데이터 경로에 둡니다.

이 번역 패치는 원본 Bethesda 애드온 파일을 재배포하지 않습니다. **KR3 번역 ZIP의 무결성(SHA-256 `404dfe169203bdec679ec67d456aa7516421298dbec89620331a6af931bbe79f`)과 파일 구성은 확인했지만 KR12.4 전체 퀘스트/플러그인 조합을 실게임에서 재검증한 것은 아닙니다.**

### 포함 구성

- 한국어 대응 Windows `openmw.exe`
- `Morrowind_Korean_ReTranslation`의 `ESP / CEL / MRK / TOP / JRN / l10n`
- Galmuri11 기반 한국어 글꼴 및 라이선스
- Morrowind 본편 3개와 Bloodmoon 7개, 총 10개 UTF-8 SRT 영상 자막
- `Install-Korean.bat`, PowerShell 설치·환경설정 스크립트

## Project Cyrodiil 한국어 테스트 번역

엔진 통합판과 별도로 사용하는 [Project Cyrodiil 26.09a 한영 대조표·재현 빌드·Nexus 선택 파일 배포 안내](translations/cyr-main/README.md)를 제공합니다. 실제 게임 검증 전 테스트본이며 보류 8개와 기존 번역의 검수 상태를 공개합니다.

## Skyrim: Home of the Nords 한국어 테스트 번역

[Sky_Main 26.09a 한영 대조표·재현 빌드·Nexus 선택 파일 배포 안내](translations/sky-main/README.md)를 제공합니다. 8,279개 대조 행 중 8,202개 필드가 번역 적용되며, 보류 4개와 개발용 마커 73개는 원문을 유지합니다. 실제 게임 검증 전 테스트본입니다.

## Android

**KR12.4는 Windows x64 전용**입니다. Android APK나 Android용 엔진 실행 파일은 ZIP에 포함되지 않습니다. 수정한 ESP/TOP 데이터는 Android에도 공통으로 적용할 수 있는 후보이지만, `keywordsearch.cpp`의 네이티브 변경은 Android 엔진을 별도로 재빌드·검증해야 합니다. [GitHub Releases](https://github.com/munument1/Morrowind-OpenMW-KR/releases)에서 Android용 자산이 명시된 릴리스만 선택하세요.

## 개발자: 한국어 OpenMW 패치

`korean/patches`에는 공식 OpenMW 0.51.0 소스에 적용하는 누적 패치가 있습니다.

| 패치 | 기능 |
|---|---|
| 0001 | 한국어/CJK 대화 토픽 탐색 |
| 0002 | UTF-8 BOM 사이드카 파일 |
| 0003 | 혼합 원본 인코딩/UTF-8 레코드 읽기 |
| 0004 | 구형 한국어 저널 복구 |
| 0005 | 원본 영상 외부 SRT 자막 |
| 0006 | 저널 토픽 별칭 |
| 0007 | 한국어 저널 색인 |
| 0008–0011 | 한국어 단어 경계·조사·토픽 습득 개선 |
| 0012 | 음성 시간 동기화 자막 |
| 0013 | 마법 지속 시간 표시 |
| 0014–0015 | 인용형 조사 및 명사형 토픽 연결 |
| 0016 | 한국어 서술격·호격·동사 어미 경계 |

토픽 QA 도구는 `packaging/korean/tooling`에 있습니다. 영어 원본 파일을 로컬에서 대조하려면 [원본 대조 안내](packaging/korean/tooling/ISSUE42_ORIGINAL_MASTER_QA.md)를 참고하세요. **상용 `Morrowind.esm`, `Tribunal.esm`, `Bloodmoon.esm`을 저장소나 CI에 올리지 마세요.**

## 라이선스·상위 프로젝트

OpenMW의 라이선스는 GPLv3입니다. 글꼴과 서드파티 구성 요소는 각 라이선스 고지를 참고하세요.

- [OpenMW 공식 사이트](https://openmw.org/)
- [OpenMW 소스 저장소](https://github.com/OpenMW/openmw)
