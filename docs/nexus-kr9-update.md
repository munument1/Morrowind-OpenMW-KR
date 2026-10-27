# Nexus Mods #60496 — KR9 API 자동 업로드

## 자동 업로드 준비 완료

- Nexus 대상: https://www.nexusmods.com/morrowind/mods/60496 (현재 공개 파일은 KR5로 확인됨; KR9 게시 여부는 공개 페이지에서 재확인)
- [GitHub Actions: Publish verified Windows KR9 on existing Nexus mod](https://github.com/munument1/Morrowind-OpenMW-KR/actions/workflows/publish-windows-kr9-nexus.yml)
- `Nexus-Mods/upload-action`의 **공식 Nexus Mods v3 Upload API**를 사용합니다. 실제 GitHub Windows KR9 ZIP을 다운로드하여 SHA-256과 ZIP 무결성을 확인한 다음, 기존 넥서스 파일의 새 버전으로 올립니다.
- 이 워크플로는 현재 **구성만 완료**된 상태이며, Nexus Mods에 업로드되었다고 주장하면 안 됩니다.

### 계정 소유자가 한 번만 설정

1. GitHub 저장소 `munument1/Morrowind-OpenMW-KR`의 **Settings → Secrets and variables → Actions → New repository secret**에 이름 `NEXUSMODS_API_KEY`로 넥서스 계정의 API 키를 보관합니다. **API 키를 README, PR, 채팅에 붙이지 않습니다.**
2. 넥서스 모드 `60496`의 **Files → 기존 메인 파일 → API Info**에서 **file ID**를 확인합니다. `60496`은 모드 페이지 ID이지 파일 ID가 아닙니다.
3. 위 Actions 워크플로의 **Run workflow (master)**를 선택하고 `nexus_file_id`에 정확한 기존 파일 ID를 입력합니다. 성공하면 파일 버전은 `0.51.0-KR9`가 됩니다.
4. 공개 넥서스 Files 탭에서 KR9 ZIP·새 버전이 보이는지 확인합니다. 전체 모드 소개 글은 별도로 수정이 필요할 수 있으며 아래 문안을 활용할 수 있습니다.

---



Nexus Mods 등록 페이지: https://www.nexusmods.com/morrowind/mods/60496

**현재 이 문서는 업로드/등록 준비 문안입니다. Nexus Mods 사이트에 실제로 수정·게시된 것은 아닙니다.** 기존 Nexus Mods 페이지는 검색 시 버전 `0.51-kr4`로 표시되었습니다.

## 새 파일 (Windows)

- 표시 이름: `OpenMW 0.51.0 Korean Support KR9 - Windows`
- 파일명: `Morrowind-Korean-OpenMW-0.51.0-KR9-Full.zip`
- 버전: `0.51.0-KR9`
- 원본 파일과 체크섬: https://github.com/munument1/Morrowind-OpenMW-KR/releases/tag/openmw-0.51.0-kr9
- 모드 페이지에 최신 Windows 파일로 등록하고, 이전 KR4 파일은 필요 시 Old files로 유지합니다. 자동 교체 전 사용자의 기존 설정 백업을 권장합니다.

## Nexus 모드 소개/변경 내역 (붙여넣기)

**OpenMW 0.51.0 Korean Support KR9**

모로윈드 본편, Tribunal, Bloodmoon의 한국어 번역과 OpenMW 0.51.0용 엔진 보정을 제공하는 비공식 한국어 지원판입니다.

KR9에서는 NPC 대화, 인사말, 설득 대사 및 저널에서 한국어 단어의 일부가 다른 토픽으로 잘못 인식되어 **원치 않는 파란 하이퍼링크가 생기는 문제**를 수정했습니다. 명시적 토픽 링크와 정상적인 조사·복합 토픽은 보존하도록 처리했습니다.

기존 KR8의 번역 ESP·CEL·TOP·MRK·폰트·영상 자막은 그대로 유지했습니다. KR8과 비교해 Windows 패키지에서 교체된 내용은 `payload/openmw.exe` 엔진 파일뿐입니다. 특히 KR8에 반영된 Aradraen CELL 이름 보정도 유지됩니다.

Windows/Ubuntu 컴파일·테스트, 실제 OpenMW 파서 검증, 번역 데이터 전체 감사 및 배포 ZIP 검사에 통과했습니다. 별도 인게임 실행 검증은 진행하지 않았습니다.

**Windows KR9 다운로드**
https://github.com/munument1/Morrowind-OpenMW-KR/releases/tag/openmw-0.51.0-kr9

**Android/ChromeOS**
기존 KR8 앱을 삭제하지 않고 나란히 설치 가능한 Android KR9 별도 앱이 제공됩니다.
https://github.com/munument1/Morrowind-OpenMW-Android-KR/releases/tag/android-korean-0.51.0-12-kr9-standalone

Android KR9는 기존 앱과 저장 공간을 공유하지 않습니다. 원본 앱을 삭제하지 말고 세이브를 먼저 백업하세요. 이 초기 별도 설치판은 일회성 Debug 서명으로 만들어져 동일 패키지에 대한 추후 덮어쓰기 업데이트를 보장하지 않습니다. **영구 서명용 후속 APK는 공개 검증 및 릴리스 완료 후 이 링크를 갱신해야 합니다.**

원본 Morrowind 게임 데이터와 Bethesda 저작권 자료는 포함하지 않습니다.

## Change log

- **KR9**: Korean dialogue and journal implicit hyperlink boundary fix; unchanged KR8 translation resources; verified Windows release archive.
- **KR8**: Official Area Effect Arrows / Aradraen interior CELL translation correction.
- **Older versions**: See GitHub Releases for details.

## Nexus 게시 확인

GitHub Actions가 성공하면 넥서스 Files 탭의 메인 파일이 KR9인지 확인하세요. 이 자동화는 **파일 업로드와 모드 버전 갱신**을 수행하며, 전체 소개 글 전체를 덮어쓴다고 보장하지 않습니다.

공개 사이트의 소개·스크린샷을 편집하는 별도 계정 권한/기능이 필요한 경우, 파일 갱신과 구분해 처리합니다.
