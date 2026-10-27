# Nexus Mods #60496 — Windows KR9 업로드 완료

**공식 Nexus Mods API를 통한 Windows KR9 업로드 성공.**

- 넥서스 모드: https://www.nexusmods.com/morrowind/mods/60496
- 업로드된 버전: `0.51.0-KR9`
- 업로드 파일: `Morrowind-Korean-OpenMW-0.51.0-KR9-Full.zip`
- 사용된 기존 파일 ID: `8110335`
- [업로드 성공 GitHub Actions 실행 #40601269540](https://github.com/munument1/Morrowind-OpenMW-KR/actions/runs/40601269540)
- 검증된 SHA-256: `1b38dc267249d6caf2c59aa487565b7377369d2d4b57bd117030721fad9a1049`
- 기존 자동화: [Publish Korean OpenMW to Nexus Mods](https://github.com/munument1/Morrowind-OpenMW-KR/actions/workflows/nexus-publish.yml)
- 인증 설정: 기존 `NEXUSMODS_API_KEY` repository secret과 기존 `NEXUSMODS_FILE_ID` variable(혹은 자동 선택)을 **변경하지 않고 재사용**함.
- GitHub release: https://github.com/munument1/Morrowind-OpenMW-KR/releases/tag/openmw-0.51.0-kr9

이 자동화는 **기존 넥서스 파일에 새 버전을 추가**하고 모드 표시 버전을 갱신합니다. 사이트의 모드 소개 본문 전체를 갱신하는 동작은 수행하지 않습니다.

---

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

GitHub Actions 로그에서 `Mod file version created successfully` 및 `File uploaded successfully to NexusMods.`를 확인했습니다. 공개 넥서스 Files 탭에 반영되는지 별도로 확인할 수 있습니다. 소개 본문·스크린샷은 업로드 API에 의해 자동 변경되지 않습니다.
