# OpenMW Korean Support

OpenMW 0.51.0에서 《The Elder Scrolls III: Morrowind》를 한국어로 플레이하기 위한 Windows용 런타임/번역 통합 지원 저장소입니다.

> Morrowind 원본 게임 데이터는 포함하지 않습니다. 정품 Morrowind가 필요합니다.

## 현재 배포판

**OpenMW 0.51.0 Korean Support KR11**

- 릴리즈: https://github.com/munument1/Morrowind-OpenMW-KR/releases/tag/openmw-0.51.0-kr11
- 설치 파일: `Morrowind-Korean-OpenMW-0.51.0-KR11-Full.zip`
- 공식 OpenMW 0.51.0 Windows 설치본 위에 적용하는 compact 패키지
- 전역 `encoding=utf8` 설정 불필요

KR11은 폰트 설정에서 빠진 U+2160–U+217F 로마 숫자 범위를 추가해 `Ⅰ`, `Ⅺ`, `Ⅻ` 등이 밑줄로 표시되는 문제를 수정합니다. KR10의 실행 파일·번역 데이터·토픽 복구 기능은 그대로 유지합니다. KR10 사용자에게 엔진 재빌드나 전역 인코딩 변경은 필요하지 않습니다. 패키지 검증 결과에는 변경 파일과 보존 파일이 기록됩니다.

KR10부터 구형 세이브의 저널 토픽 ID와 NPC의 알려진 토픽 ID를 현재 데이터와 대조해 복구합니다. 이미 세이브에서 삭제된 토픽 기록은 재생성하지 않습니다. Rebirth 모드의 대화/스크립트 한글화는 본편 KR11 업데이트와 별도이며 이 배포물에 포함되지 않습니다.

## KR11 구성

- 한국어 런타임 패치가 적용된 `openmw.exe`
- 한국어 번역 데이터 `ESP / CEL / MRK / TOP / JRN / l10n`
- Galmuri11 기반 한국어 폰트 구성
- Morrowind 본편 3개 + Bloodmoon 7개, 총 10개 UTF-8 SRT 영상 자막
- `Movies_New_Game=mw_intro.bik` 등 원본 Morrowind 영상 fallback 복구
- 기존 `openmw.cfg`와 한국어 모드/엔진 자동 백업
- 이전 설치에서 한국어 관리 블록이 중간에 끊긴 경우 자동 복구

## 설치

1. 공식 **OpenMW 0.51.0 Windows x64**를 설치합니다.
2. OpenMW를 한 번 실행해 사용자 설정 파일이 생성되게 합니다.
3. KR11 ZIP을 압축 해제합니다.
4. `Install-Korean.bat`을 실행합니다.
5. OpenMW 설치 폴더를 자동으로 찾지 못하면 `openmw.exe`가 있는 폴더를 직접 지정합니다.

설치기는 기존 `openmw.exe`, 관리 대상 폰트, 한국어 모드 폴더와 `%Documents%\My Games\OpenMW\openmw.cfg`를 백업합니다. 사용자의 다른 `data=`, `content=` 항목과 모드 상대 순서, 기존 `encoding=` 값은 유지합니다.

## 한국어 런타임 패치

`korean/patches`에는 OpenMW 0.51.0에 적용하는 한국어 지원 패치가 있습니다.

1. `0001-cjk-topic-discovery.patch` — 한국어/CJK 대화 토픽 탐색 보완
2. `0002-utf8-bom-sidecars.patch` — BOM 기반 UTF-8 CEL/TOP/MRK 지원
3. `0003-mixed-utf8-esm-reader.patch` — 기존 win1252 마스터와 UTF-8 한국어 문자열 혼용 지원
4. `0004-legacy-korean-journal-recovery.patch` — 이전 저장 파일의 한국어 저널 텍스트 복구
5. `0005-video-subtitles.patch` — BIK 영상과 같은 이름의 외부 UTF-8 SRT 자막 지원
6. `0006-journal-topic-keywords.patch` — 저널의 정식 주제명과 `.jrn` 별칭 검색 지원
7. `0007-korean-journal-index.patch` — 한국어 저널 초성 색인 지원
8. `0008-korean-implicit-topic-boundaries.patch` — 한국어 대화·저널 링크의 잘못된 단어 내부 일치 방지
9. `0009-korean-honorific-particle.patch` — 정상 조사 `께서는`의 토픽 링크 보완
10. `0010-legacy-korean-topic-recovery.patch` — 현재 데이터와 대조해 구형 저널/NPC 토픽 ID 복구

## 영상 자막

자막 파일은 `korean/subtitles/video`에 있으며, 영상과 같은 VFS 경로/이름을 사용합니다.

예:

```text
video/mw_intro.bik
video/mw_intro.srt
```

포함된 자막:

- `mw_intro.srt`
- `mw_cavern.srt`
- `mw_end.srt`
- `bm_bearhunt1.srt`
- `bm_bearhunt2.srt`
- `bm_ceremony1.srt`
- `bm_ceremony2.srt`
- `bm_endgame.srt`
- `bm_frostgiant1.srt`
- `bm_frostgiant2.srt`

원본 BIK 영상은 수정하거나 재배포하지 않습니다.

## 개발/패키징

- Windows 설치기: `packaging/korean`
- 한국어 패치셋: `korean/patches`
- 영상 자막: `korean/subtitles/video`
- Windows CI: `.github/workflows/windows.yml`
- 한국어 패치/패키지 검증: `.github/workflows/korean-*.yml`

KR10 compact 배포판은 공식 OpenMW 0.51.0에 이미 포함된 DLL과 도구를 중복 배포하지 않고, 한국어 지원에 필요한 파일만 설치합니다.

## 라이선스

OpenMW 본체는 GPLv3입니다. 자세한 내용은 저장소의 `LICENSE`와 upstream OpenMW 프로젝트를 확인하세요.

- OpenMW: https://openmw.org/
- Upstream repository: https://gitlab.com/OpenMW/openmw
