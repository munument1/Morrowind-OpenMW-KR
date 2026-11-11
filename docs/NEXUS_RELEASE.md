# Korean OpenMW 넥서스 자동 배포

대상: https://www.nexusmods.com/morrowind/mods/60496

## 지역 모드 배포 형식

사용자 확정 사항: **모드 번역은 전체 ESM/ESP를 같은 파일명으로 덮어쓰는 ZIP으로 배포한다.**
본편 Windows 통합 ZIP·설치기는 별도로 유지한다. 기존 델타 도구는 내부 진단용으로만 보관한다.
모드 정식 파일에 BSDIFF/xdelta, Python 적용기, 추가 번역 ESP 설치를 요구하지 않는다.

원본 모드와 필요한 아트 파일을 먼저 설치하고 플러그인·사이드카를 백업한 다음, ZIP의 전체 번역
ESM/ESP와 TOP/MRK/CEL/JRN을 원래 위치에 덮어쓴다. TR_Factions는 기존에 사용하는 경우에만
선택한다. Rebirth 전용 Cyr/Sky와 일반 Cyr/Sky ESM을 동시에 켜지 않는다.

KR13 포장 수정 파일은 다음 다섯 개다. 본편 KR13 ZIP의 SHA와 내용은 유지한다.

| 파일 | Nexus 모드/기존 그룹 | Nexus 버전 |
| --- | --- | --- |
| TR_Mainland-kr0.4.1.zip | 60844 / 8296179 | 26.11.2-kr0.4.1 |
| Tamriel_Data-kr0.4.1.zip | 60845 / 8296167 | 26.08-kr0.4.1 |
| Cyr_Main-kr0.4.1.zip | 60846 / 8296161 | 26.09a-kr0.4.1 |
| Sky_Main-kr0.3.1.zip | 60847 / 8296155 | 26.09a-kr0.3.1 |
| Rebirth7.2-Cyr_Sky_Compatibility-kr0.4.1.zip | 60805 / 8296377 (optional) | 7.2-kr0.4.1 |

`package_kr13_mod_overwrites.py`는 검증된 KR13 전체 ZIP에서 7개 플러그인과 24개 사이드카를
바이트 변경 없이 포장한다. `KR13-MOD-OVERWRITE-SOURCES.json`은 기존 델타가 만드는 결과와
직접 대조한 파일별 SHA다. 빌더와 업로드 preflight는 실제 TES3 파일, 정확한 멤버 목록,
파일 해시와 CRC를 검사하여 델타 전용 ZIP이 정식 파일로 올라가는 것을 막는다.

`publish-kr13-nexus.yml`은 위 다섯 그룹만 갱신한다. 먼저 `dry_run=true`로 검사하고,
성공 후 `dry_run=false`로 업로드한다. 업로드 후 Nexus API에서 버전·파일 ID·바이트 크기를
대조하고 영수증을 저장한다. 직전 델타 전용 파일은 새 버전 등록 시 보관 처리한다.
GitHub에서도 새 ZIP·SHA를 확인한 뒤 이전 델타 ZIP·SHA를 제거하여 잘못 설치하는 경로를 없앤다.

다음 본편 섹션의 버전 규칙은 통합판에 대한 것이다.

## 버전 규칙

태그 `openmw-0.51.0-kr4`에서 엔진 버전 `0.51.0`과 한글판 차수 `4`를 읽어
넥서스 버전을 `0.51.0-KR4`로 만듭니다. 버전 접두사나 차수를 워크플로에 고정하지 않습니다.
기존 넥서스의 `0.51-kr4`는 `0.51.0-KR4`와 같은 버전으로 인식하며 중복 업로드하지 않습니다.

다음 배포는 다음과 같이 준비합니다.

1. 엔진/한글판에 맞는 새 태그를 만듭니다. 예: `openmw-0.51.0-kr5`.
2. 대응하는 Full ZIP과 SHA256을 GitHub 릴리즈에 첨부합니다.
3. 테스트 후 draft와 prerelease 상태를 모두 해제하고 정식 릴리즈를 발행합니다.
4. Actions의 `Publish Korean OpenMW to Nexus Mods` 결과를 확인합니다.

지원하는 파일명은 두 가지입니다.

- compact 배포판: `Morrowind-Korean-OpenMW-0.51.0-KR5-Full.zip`
- upstream port 번들: `Morrowind-Korean-OpenMW-openmw-0.51.0-kr5-Full.zip`

체크섬 파일은 선택된 ZIP 이름 뒤에 `.sha256`을 붙입니다.
두 종류의 ZIP이 한 릴리즈에 동시에 있으면 임의 선택하지 않고 실패합니다.
일반 OpenMW 엔진 태그, 다른 플랫폼 자산, draft/prerelease는 자동 배포하지 않습니다.

## 연결 설정과 테스트

Repository secret `NEXUSMODS_API_KEY`에 모드 소유자의 Personal API Key를 등록합니다.
메인 파일 하나인 현재 구성에서는 업로드 API File ID를 자동 조회합니다.
활성 파일이 여러 개가 되면 Repository variable `NEXUSMODS_FILE_ID`에
Manage Files/Advanced의 업로드용 File ID를 지정합니다. 모드에 속하는지도 확인합니다.

Actions → `Publish Korean OpenMW to Nexus Mods` → Run workflow:

- `tag`: 검사/배포할 정식 한글판 태그. 비우면 최신 정식 릴리즈를 사용합니다.
- `dry_run=true`: GitHub 파일명, SHA256, ZIP만 검사합니다. 업로드하지 않습니다.
- `dry_run=false`: 인증과 중복 버전 확인 후 새 버전인 경우 업로드합니다.

기존 `Korean Windows upstream port` 빌드의 성공도 연결합니다.
그 실행 중 갱신된 최신 정식 릴리즈 파일만 대상으로 합니다.
이 빌드가 만드는 draft prerelease는 검토 후 사람이 정식으로 발행해야 합니다.
빌드나 게임 회귀 검증 절차는 기존 `KOREAN_WINDOWS_RELEASE.md`를 따릅니다.

업로드 전에는 SHA256과 ZIP 무결성을 확인합니다.
중복 버전은 생략하며, 같은 태그의 파일 교체를 다시 배포하려면 새 한글판 차수를 사용하세요.
이전 버전은 자동 보관하지 않습니다. 설치형 도구이므로 새 버전의 모드 매니저 다운로드는 끕니다.
파일 설명에는 GitHub 릴리즈 링크를 넣고 모드의 표시 버전을 새 파일 버전과 맞춥니다.
변경 내역 본문이나 기존 GitHub 빌드/패키징은 수정하지 않습니다.
