# OpenMW Korean Support

OpenMW 0.51.0에서 《The Elder Scrolls III: Morrowind》를 한국어로 플레이하기 위한 Windows용 런타임/번역 통합 지원 저장소입니다.

> Morrowind 원본 게임 데이터는 포함하지 않습니다. 정품 Morrowind가 필요합니다.

## 현재 배포판

**OpenMW 0.51.0 Korean Support KR8**

- 릴리즈: https://github.com/munument1/Morrowind-OpenMW-KR/releases/tag/openmw-0.51.0-kr8
- 설치 파일: `Morrowind-Korean-OpenMW-0.51.0-KR8-Full.zip`
- 공식 OpenMW 0.51.0 Windows 설치본 위에 적용하는 compact 패키지
- 전역 `encoding=utf8` 설정 불필요

KR8은 KR7에서 공식 추가 콘텐츠 *Area Effect Arrows*의 실내 CELL 이름(`Vivec, Aradraen: Fletcher` → `비벡, 아라드라엔: 화살 제작자`)을 수정한 데이터 업데이트입니다. KR7 대비 `.cel` 외 파일은 변경되지 않았습니다.

## KR8 구성

- 한국어 런타임 패치가 적용된 `openmw.exe`
- 한국어 번역 데이터 `ESP / CEL / MRK / TOP / JRN / l10n`
- Gowun Batang 기반 한국어 폰트 구성
- Morrowind 본편 3개 + Bloodmoon 7개, 총 10개 UTF-8 SRT 영상 자막
- `Movies_New_Game=mw_intro.bik` 등 원본 Morrowind 영상 fallback 복구
- 기존 `openmw.cfg`와 한국어 모드/엔진 자동 백업
- 이전 설치에서 한국어 관리 블록이 중간에 끊긴 경우 자동 복구

## 설치

1. 공식 **OpenMW 0.51.0 Windows x64**를 설치합니다.
2. OpenMW를 한 번 실행해 사용자 설정 파일이 생성되게 합니다.
3. KR8 ZIP을 압축 해제합니다.
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

KR8 compact 배포판은 공식 OpenMW 0.51.0에 이미 포함된 DLL과 도구를 중복 배포하지 않고, 한국어 지원에 필요한 파일만 설치합니다.

## 라이선스

OpenMW 본체는 GPLv3입니다. 자세한 내용은 저장소의 `LICENSE`와 upstream OpenMW 프로젝트를 확인하세요.

- OpenMW: https://openmw.org/
- Upstream repository: https://gitlab.com/OpenMW/openmw
