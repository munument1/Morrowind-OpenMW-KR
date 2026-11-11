# 배포 형식 — 사용자 확정 지침

- 본편은 기존 Windows 통합 ZIP·설치기 배포 방식을 유지한다.
- **지역 모드 한글 패키지는 번역된 전체 ESM/ESP와 대응 TOP/MRK/CEL/JRN을 넣은 덮어쓰기 ZIP이다.** 사용자는 같은 버전 원본 모드와 아트 파일을 설치하고, 원래 플러그인을 백업한 뒤 같은 파일명으로 교체한다.
- TR_Mainland, Tamriel_Data, Cyr_Main, Sky_Main, Rebirth 전용 Cyr/Sky 호환 파일 모두 이 규칙을 따른다. TR_Factions.esp는 선택 파일로 구분한다.
- 모드의 정식 배포를 BSDIFF/xdelta 차이 파일, Python 적용기, 추가 번역 ESP 방식으로 임의 전환하지 않는다. 기존 델타 도구는 내부 진단용이며 공개 모드 설치 절차에 넣지 않는다. 형식 변경은 사용자 명시 요청이 있을 때만 한다.
- 원본 모드의 메쉬·텍스처·BSA와 정품 Morrowind/Tribunal/Bloodmoon ESM은 모드 번역 ZIP에 넣지 않는다. 원작자 표기와 기존 고지는 보존한다.
- ZIP 안에 실제 TES3 ESM/ESP가 있고, 검증한 번역본과 SHA256이 같으며, 대응 사이드카가 누락되지 않았는지 검사한다. 압축 CRC와 설치 안내도 확인한다.
- Rebirth 전용 ESM과 일반 Cyr/Sky ESM은 동시에 활성화하지 않는다. 사용자의 실제 설치·저장 파일 대신 격리 폴더에서 검증한다.
- 같은 버전 중복 확인 때문에 Nexus 갱신이 생략되지 않도록 포장 수정 버전도 구분한다. 기존의 정확한 Nexus mod UID/file group을 사용하며 Android 그룹은 수정하지 않는다. 업로드 뒤 API로 버전·파일 크기·대상을 재확인한다.
