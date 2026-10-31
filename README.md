# OpenMW 한국어 지원판 (OpenMW Korean Support)

《The Elder Scrolls III: Morrowind》를 OpenMW에서 한국어로 플레이하기 위한 **한국어 런타임·번역 데이터·설치 도구** 프로젝트입니다.

> 정품 Morrowind의 게임 데이터(ESM/BSA/영상)는 포함하지 않습니다. Windows와 Android는 **별도의 배포판**이며 서로의 실행 파일을 교체해 사용할 수 없습니다.

## 최신 배포판 (2026-10-31 기준)

| 플랫폼 | 최신 정식판 | 다운로드 | 설치 파일 |
| --- | --- | --- | --- |
| Windows x64 | **OpenMW 0.51.0 KR12.3.1** | [Windows KR12.3.1](https://github.com/munument1/Morrowind-OpenMW-KR/releases/tag/openmw-0.51.0-kr12.3.1) | `Morrowind-Korean-OpenMW-0.51.0-KR12.3.1-Full.zip` |
| Android ARM64 | **OpenMW Android 0.51.0-12 KR12.1** | [Android KR12.1](https://github.com/munument1/Morrowind-OpenMW-Android-KR/releases/tag/android-korean-0.51.0-12-kr12.1-permanent) | APK와 한국어 데이터 ZIP **모두 필요** |

**중요:** Windows KR12.3.1에 포함된 최신 퀘스트 토픽 수정은 Android KR12.1에 아직 이식·배포되지 않았습니다. Android APK/데이터를 Windows ZIP으로 덮어쓰면 안 됩니다.

## Windows KR12.3.1의 변경 사항

- KR12.3에서 추가한 한국어 대화 토픽의 인용 조사(`라는/이라는/란/이란`)와 명사형 연결 규칙을 유지하면서, ZIP 내부 `README-KOREAN.txt`와 릴리스 설명의 **한글 물음표(??) 인코딩 오류를 정정**했습니다.
- 전사 길드 페르시우스 메르시우스의 **바스** 퀘스트 링크 표시·클릭·수락·일지 갱신은 실제 게임에서 확인했습니다.
- 도둑 길드 이에니스, 블레이드 승진, 블러드문 결정 관련 대사 `INFO.NAME` 3건을 보완했습니다. 퀘스트 조건과 결과 스크립트는 유지했습니다.
- KR12 계열의 대화·저널 토픽 링크 개선, NPC 음성과 연동되는 자막 표시, 로마 숫자 폰트, 한국어 데이터 및 기존 호환성 수정을 계승합니다.
- **실게임 검증 범위:** 바스 퀘스트 경로는 확인했지만 나머지 세 퀘스트의 전체 진행 및 모든 모드 호환성은 검증되지 않았습니다.

KR12.3.1은 **KR12.3의 문서 인코딩만 바로잡은 정정판**으로, 두 버전의 엔진과 번역 ESP 자체는 같습니다. 구버전 KR12.3 대신 KR12.3.1을 사용하세요. 자세한 검증 이력은 [PR #41](https://github.com/munument1/Morrowind-OpenMW-KR/pull/41)을 참고하세요.

## Windows 설치

1. [공식 OpenMW **0.51.0 Windows x64**](https://openmw.org/)를 설치하고 한 번 실행합니다.
2. 기존 OpenMW 설치 폴더·사용자 설정·세이브를 백업합니다.
3. 위 Windows KR12.3.1 릴리스에서 `Morrowind-Korean-OpenMW-0.51.0-KR12.3.1-Full.zip`을 다운로드해 압축을 풉니다.
4. `Install-Korean.bat`을 실행하고, 자동 탐색에 실패하면 `openmw.exe`가 있는 **OpenMW 0.51.0** 폴더를 지정합니다.
5. 런처에서 한국어 번역 ESP 및 데이터 경로를 확인하고 게임을 실행합니다.

이 ZIP은 단독 실행판이 아니라 **기존 OpenMW 0.51.0에 덧씌우는 compact 패치 패키지**입니다. 설치기는 기존 `openmw.exe`, 관리 대상 글꼴과 한국어 모드 폴더, `%Documents%\My Games\OpenMW\openmw.cfg`를 백업하고, 한국어 관리 항목만 갱신하도록 설계되어 있습니다. 다른 모드의 `data=`/`content=` 순서와 기존 `encoding=`은 유지하며 전역 `encoding=utf8` 설정을 요구하지 않습니다.

Windows 패키지는 한국어 지원 엔진(`openmw.exe`), `ESP/CEL/MRK/TOP/JRN/l10n` 데이터, 갈무리11 기반 폰트 구성, 본편 3개·Bloodmoon 7개의 UTF-8 SRT 영상 자막을 제공합니다. 원본 BIK 영상은 배포하지 않습니다. Rebirth 모드 전용 번역도 포함되지 않습니다.

## Android 설치 및 Windows와의 차이

Android는 **[별도 저장소](https://github.com/munument1/Morrowind-OpenMW-Android-KR)**에서 배포합니다. 현재 정식판 KR12.1의 APK(`OpenMW-Android-0.51.0-12-Korean-KR12.1-Permanent-16K.apk`)와 데이터 ZIP(`OpenMW-Android-0.51.0-12-Korean-Data-KR12.1.zip`)을 **한 세트로** 받아야 합니다.

1. 이전 Android 앱을 삭제하기 전에 사용자 설정과 세이브를 백업합니다.
2. KR12.1 서명 APK를 설치하고 정품 Morrowind 게임 데이터를 설정합니다.
3. 한국어 데이터 ZIP의 `Morrowind_Korean_ReTranslation` 폴더를 데이터 경로에 추가하고, 한국어 ESP를 마스터 파일 뒤에 활성화합니다.

KR12.1은 이전 Android KR12 기능에 더해 마법 효과의 **빛·지속·적용** 표시, 드로'사카르 대화 연결, Siege at Firemoth 내부 지명 표기를 보완했습니다. 앱 식별자는 `com.ast.openmw.korean`, versionCode는 `5115`입니다. KR8/초기 KR9는 서로 다른 앱 식별자이므로 세이브는 자동 이전되지 않습니다. 네이티브 빌드·서명·16 KiB 정렬 검사 결과는 있지만 **Android 실기기 전체 플레이는 아직 미검증**입니다.

Windows에서 추가로 수정한 한국어 토픽 경계 판정(C++ 엔진)과 퀘스트 대사 교정(번역 ESP)은 Android에서 각각 **네이티브 APK 재빌드** 및 **데이터 ZIP 갱신** 대상입니다. Android용 후속 검증판이 공개되기 전까지 KR12.1을 최신 정식판으로 안내합니다.

## 개발·검증 자료

- 한국어 패치 소스: [`korean/patches`](korean/patches) (기본 브랜치에는 `0001`–`0013` 패치가 있으며, KR12.3.x의 추가 토픽 변경은 [PR #41](https://github.com/munument1/Morrowind-OpenMW-KR/pull/41) 및 해당 릴리스 소스에서 확인)
- Windows 설치기: [`packaging/korean`](packaging/korean)
- 영상 자막: [`korean/subtitles/video`](korean/subtitles/video)
- Windows 빌드·검증: [`.github/workflows`](.github/workflows)
- Windows KR12.3.1 엔진의 기준: **공식 OpenMW 0.51.0 소스** `OpenMW/openmw@f4bec41444214a7903bebd178389ca22ca13f646`. 저장소의 개발 브랜치가 추적하는 0.52.0 소스를 0.51.0 릴리스 빌드로 혼용하지 마세요.

문제를 발견하면 [이슈](https://github.com/munument1/Morrowind-OpenMW-KR/issues)에 사용한 플랫폼·배포판·모드 목록·재현 단계와 가능한 로그를 첨부해 주세요.

## 라이선스

OpenMW 본체는 GPLv3입니다. [LICENSE](LICENSE) 및 [OpenMW 원본](https://gitlab.com/OpenMW/openmw)을 참고하세요.
