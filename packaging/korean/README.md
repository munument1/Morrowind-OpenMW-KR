# KR8 Windows installer payload

이 디렉터리는 OpenMW 0.51.0 Korean Support KR8의 Windows 설치기 구성 파일을 관리합니다.

최신 배포 ZIP은 [Windows KR8 릴리스](https://github.com/munument1/Morrowind-OpenMW-KR/releases/tag/openmw-0.51.0-kr8)에서 받습니다. KR8은 KR7의 `.cel` 실내 위치명 보정판입니다.

## 설치 흐름

`Install-Korean.bat`이 사용자 진입점이며 `install-korean.ps1`을 실행합니다.

설치기는 다음 작업을 수행합니다.

1. 공식 OpenMW 0.51.0 설치 경로를 찾거나 사용자에게 입력을 요청합니다.
2. 기존 `openmw.exe`를 백업하고 한국어 패치가 적용된 `payload/openmw.exe`를 설치합니다.
3. 한국어 폰트 파일을 `resources/vfs/fonts`에 백업 후 설치합니다.
4. 기존 한국어 모드 폴더를 백업하고 `payload/mods/Morrowind_Korean_ReTranslation`을 설치합니다.
5. ESP/CEL/MRK/TOP/JRN, `l10n`, 영상 SRT 10개를 검증합니다.
6. `install-korean-config.ps1`로 사용자 `openmw.cfg`를 백업하고 갱신합니다.

KR8 compact 패키지는 공식 OpenMW 0.51.0에 이미 포함된 DLL/도구를 중복 배포하지 않습니다.

## openmw.cfg 관리

설치기는 다음 한국어 항목만 관리합니다.

- `data="<OpenMW>/mods/Morrowind_Korean_ReTranslation"`
- `content=Morrowind_Korean_ReTranslation.esp`
- `korean-fallbacks.cfg`의 한국어 fallback/font 값
- Morrowind 영상 fallback (`Movies_New_Game=mw_intro.bik` 등)

다른 사용자의 `data=`, `content=`, archive, 모드 상대 순서와 기존 `encoding=` 값은 보존합니다. 전역 `encoding=utf8`은 추가하지 않습니다.

이전 설치에서 한국어 관리 블록이 닫히지 않은 상태를 발견하면 먼저 `openmw.cfg`를 백업한 뒤 해당 관리 블록만 복구합니다.

## 영상 자막

`0005-video-subtitles.patch`는 재생 중인 BIK와 같은 VFS 경로/이름의 UTF-8 SRT를 자동 탐색합니다.

예:

```text
video/mw_intro.bik -> video/mw_intro.srt
```

배포판에는 다음 10개 자막이 포함됩니다.

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

원본 BIK 파일은 수정하거나 재배포하지 않습니다.

## 필수 배포 구조

```text
Install-Korean.bat
install-korean.ps1
install-korean-config.ps1
korean-fallbacks.cfg
payload/openmw.exe
payload/resources/vfs/fonts/...
payload/mods/Morrowind_Korean_ReTranslation/
  Morrowind_Korean_ReTranslation.esp
  Morrowind_Korean_ReTranslation.cel
  Morrowind_Korean_ReTranslation.mrk
  Morrowind_Korean_ReTranslation.top
  Morrowind_Korean_ReTranslation.jrn
  l10n/...
  video/*.srt
```

필수 번역 데이터나 자막이 누락된 패키지는 배포하지 않아야 합니다.
