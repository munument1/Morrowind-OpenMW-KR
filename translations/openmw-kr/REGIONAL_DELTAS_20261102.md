# 지역 확장 모드 2026-11-02 배포 ESM/ESP 수정분 보존

원본 플러그인과 게임 설치에는 접근하지 않고, `D:\Codex_Trans\Morrowind mod\work\regional_translation_review\outputs` 아래 배포용 ESM/ESP에 직접 적용한 **검증된 변경분을 데이터로 보존**했다.

## 저장 위치

- `cyr-main/26.09a/topic_link_overlay_20261102.jsonl.gz`: INFO.NAME 519필드
- `sky-main/26.09a/topic_link_overlay_20261102.jsonl.gz`: INFO.NAME 85필드
- `tamriel-data/26.08/topic_link_overlay_20261102.jsonl.gz`: INFO.NAME 453필드
- `../tamriel-rebuilt/26.11.2-kr0.1/topic_link_overlay_20261102.jsonl.gz`: INFO.NAME 3,590필드
- `../tamriel-rebuilt/26.11.2-kr0.1/script_display_overlay_20261102.jsonl.gz`: INFO.BNAM/SCPT.SCTX 6,784필드
- 각 폴더의 `post_handoff_overlay_20261102.json`: 실제 현행 배포 ESM SHA, 원본 백업 SHA, TOP 별칭 수, 미검수/테스트 미실시 표시

총 **4,647개 INFO 필드의 명시 링크**, **69개 새 TOP 구분 별칭**, TR_Mainland **6,784개 표시 문자열 필드**가 현재 배포 파일의 레코드·서브레코드 해시와 대조돼 있다. 중복 row_key, 소스 SHA, 표시 텍스트 변경 및 기존 TOP 매핑 덮어쓰기 검사를 통과했다.

## 복구·재빌드 경고

기존 `build.py`는 **초기 번역 베이스라인** 검증·재빌드 기능이다. 오늘 직접 반영된 링크/표시 문자열 오버레이를 별도로 재적용하지 않은 `build.py` 결과를 배포 파일에 덮어쓰면 수정이 사라진다. `--check-only` 검사는 저장 데이터 구조 검증이지, 새 배포용 ESM을 통째로 재생산했다는 뜻이 아니다.

오버레이의 `before_sha256`와 `after_sha256`/ `new_field_sha256`는 실제 TES3 서브레코드 바이트의 SHA-256이다. **정확히 대응하는 베이스라인**에만 적용한다. 현재 `.top`에서 반복 별표(`*`)는 본문 `0x7F` 숨김 구분 키의 일부라 삭제하면 안 된다. 초안의 `NOT_REVIEWED`, 구조 보류 45개, 스크립트 문맥 보류 474개는 그대로 유지한다.

TR 빌더의 `manifest.json`은 최신 `TR_Mainland.top`과 오버레이 해시도 검증한다. 이전 `mainland.output_sha256`는 초기 빌드 해시로 남겨두었고, 오늘 현행 배포 플러그인 해시는 `post_handoff_20261102.current_release_sha256`와 `post_handoff_overlay_20261102.json`을 따른다.

## 한계

원문·구조 기반 검수만 완료했고, 실제 OpenMW 실행, NPC별 필터와 퀘스트 단계, 모든 암묵적 키워드, 미검수 번역의 최종 언어 승인은 **실시하지 않았다**. Nexus에 이 지역 모드들의 신규 릴리스는 게시하지 않았다. Morrowind Rebirth는 이번 작업에서 수정하지 않았다.
