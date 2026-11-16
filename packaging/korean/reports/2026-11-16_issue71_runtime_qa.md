# 이슈 #71 실행 검증 — 2026-11-16

상태: Windows 수정 브랜치의 CI 및 아래 실행 검증 완료. 정식 릴리스·원래 설치 변경·이슈 종료는 하지 않았다.

## 확인된 원인과 수정

DIAL 내부 ID가 영어로 유지되는 지역 모드에서 대화 목록과 기록 제목이 내부 ID를 그대로 출력했다. 0018 패치는 MRK/DSP 표시명을 사용하면서 클릭·검색·퀘스트·저장의 원래 ID를 유지한다. 2026-11-16 실행 검증에서 목록 외에 선택 후 기록 제목도 영어인 것을 찾아 `Response::write`까지 같은 표시명으로 수정했다 (`ec69b11`). 일지 목록·제목·한국어 초성 색인은 0019를 사용한다.

자동 음성 자막은 대화 하이퍼링크 렌더러를 거치지 않았다. `voiceSubtitle`의 두 표시 경로에서 기존 `visibleKoreanTopicText`를 사용한다. 테스트용 GMST로 표시 시간을 늘리고 `Say`에 `@제국` + DEL 110개 + `#`를 전달해 실제 HUD에 `제국`만 나오는 것을 확인했다. 원래 게임의 자막 시간이나 INFO는 변경하지 않았다.

## 대화가 비어 보이는 두 NPC

- 스크린샷 3: `TR_m3_q_Murenio Galtrix`. 최초에는 인사말만 표시된다. 격리 프로필에서 `TR_m3_Vh_Boots_a` 40 및 `garyx rubber` 주제로 대화하면 원래 한국어 대사가 열리고 가릭스 고무 1개 지급과 일지 50 갱신이 이어졌다. 임의의 기본 대사를 추가하지 않았다.
- 스크린샷 6의 이름은 **파쿨**이며 `TR_m3_S_Pakhul`이다. Farul Sarayn이 아니다. `TR_m3_AT_HI_SlaveKey` 없이 인사말만 나오고 열쇠를 소지하면 `go free` 주제와 해방 선택지가 나타나는 것을 각각 실행 확인했다. 조건을 제거하지 않았다.

## 번역 데이터

TR DSP는 기존 네 표시명과 실제 두 NPC 검증에서 확인한 `go free → 풀어 주다`, `garyx rubber → 가릭스 고무`를 포함한다. 후자는 원래 퀘스트 아이템의 한국어 이름과 맞춘 것이다. 기존 ESM/ESP와 TOP/MRK/CEL/JRN은 공식 kr0.4.1 ZIP과 바이트가 같다. 새 전체 플러그인 덮어쓰기 ZIP의 CRC와 고정 원본 해시 검사를 통과했다.

이슈의 스크린샷에 보이는 15개 영어 주제(carriage service, Haimtir, Jarl Jona the Ansei-Ender, Alju-Deekus, retribution, Archad, Imperial Geographical Society, Marina, Almas Thirr, Bloodstone Pilgrimage, Bloodstone Shrine, Indoril Ilvi, local area, Necrom, Roa Dyr)는 MRK/DSP 번역 표시명과 대응한다. 모든 지역 모드의 미번역 주제 0건을 뜻하지 않는다.

## 검증 환경과 제한

정품 기본 게임을 읽되 원래 Rebirth 설치와 사용자 설정·저장은 그대로 두고 별도 프로필을 사용했다. 공식 OpenMW 0.51.0에 패치 0001–0019를 순서대로 적용했으며, 네 개 패키지 계약 검사와 실제 번역 로더·숨김 태그 회귀 검사를 통과했다. 지역 모드 아트는 이 PC에 없어 일부 모델은 오류 마커로 보인다. 이번 검증은 대화 UI·퀘스트 응답·일지 경로이며 전체 지역 렌더링 검증이 아니다.

초기 0019 CI 실행 파일에서 한국어 초성 `ㄱ` 아래 `가릭스 고무` 목록·주제 페이지와 한국어 일지 내용을 확인했고, 격리된 `Issue71_isolated_QA.omwsave`를 생성했다. 추가 기록 제목 수정이 들어간 최종 Release 실행 파일로 에르빌라의 `피의 돌 순례` 목록 클릭과 기록 제목이 모두 한국어인 것을 확인했다. 기존 격리 저장을 새 실행 파일에서 불러와 일지 본문·`ㄱ` 목록·`가릭스 고무` 제목/응답이 유지되는 것도 확인했다. 원래 저장 파일 SHA256은 불러오기 전후 동일하다.

## 최종 Windows 산출물

- CI: https://github.com/munument1/Morrowind-OpenMW-KR/actions/runs/43784502555 (`ec69b1133c284cae65a1446174d869fafcd3251e`). Release 빌드의 일반 components/OpenMW/OpenMW-CS 테스트 단계는 skipped이며, PR #72의 별도 소스/런타임/데이터 검사 13개는 모두 성공했다.
- 실행 파일 SHA256: `67ff422ae07dca20ca43e23254b2888e0e7f2d0ff536abaa964bf83264032b78`. 전용 실행 파일 artifact와 같은 CI의 NSIS 설치기에서 추출한 파일이 바이트 단위로 같다.
- KR13.1 Full ZIP SHA256: `fdc5eeb648d47c02e19378253d86e1551fa3d28c678ea6b08ff8cadc3eaba0b7`. 67개 멤버, CRC PASS, 원래 KR13의 게임 데이터·폰트·패치 0001–0017 보존 및 새 0018–0019 대응 소스 동봉.
- TR 전체 덮어쓰기 QA ZIP SHA256: `679267649bb0866c0c7e807bead0fdf71b91cc4400d8d53e3a8cc0c56f2ddcc1`.
- 기존 격리 저장 SHA256: `bf4cfab7a98627e9148f09fa5e7d5e0adce4ee9144e73b0f003c82ed4cd08ea3`.

검증 중 Windows CLI의 한글 절대 저장 경로는 문자 변환 오류를 냈다. ASCII 상대 경로로 불러오면 정상 동작했다. 원래 설치 경로 `D:\OpenMW 0.51.0`이나 실제 사용자 저장을 수정한 것은 아니다. 이 CLI 경로 문제는 #71 표시 수정에 포함하지 않았다.
