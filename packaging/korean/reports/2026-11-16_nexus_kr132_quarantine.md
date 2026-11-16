# KR13.2 Nexus 격리 확인 및 배포 완료 판정 정정

2026-11-16 확인 시 Windows 본편 KR13.2(file ID `1000074196`)는 Nexus의 `QUARANTINED` 상태다. 다른 7개 지역/PFP/Rebirth 파일은 `VERIFIED`다. 이전 배포 실행은 업로드·UID·그룹·버전·크기 확인에 성공했지만, 안전 검사 승인까지 확인한 것이 아니었다. **본편 다운로드 승인 및 격리 해제는 아직 완료되지 않았다.**

## 확인 근거

- [실제 파일 페이지](https://www.nexusmods.com/morrowind/mods/60496?tab=files)에 자동 안전 검사 격리 안내가 표시된다.
- 공식 [GraphQL API](https://graphql.nexusmods.com/)의 `modFiles`에서 정확한 file ID·mod UID·버전·바이트 크기를 대조한 뒤 `scannedV2`를 읽었다. 본편은 `QUARANTINED`이고 나머지 7개는 `VERIFIED`다.
- Nexus에서 연결한 [기존 VirusTotal 보고서](https://www.virustotal.com/gui/file/805fd9dc6ffdb61639378893690d6c8eeda2b48e6b0f331c23828f3e21929115)는 0/66 탐지이며 마지막 분석은 2026-11-16 13:47:52 KST다. 재업로드나 재분석을 요청한 것이 아니다. 이 결과만으로 안전이나 오탐을 확정하지 않는다.
- 실제 업로드 ZIP의 SHA256은 `805fd9dc6ffdb61639378893690d6c8eeda2b48e6b0f331c23828f3e21929115`, 크기는 14,298,825바이트다. 67개 멤버와 CRC를 재검사했고 암호화·중첩 압축은 없다. EXE, BAT, PowerShell 설치 스크립트가 들어 있다. 공개 경고는 일반 사유만 나열하므로 정확한 내부 검사 원인을 단정할 수 없다.

공식 [격리 안내](https://help.nexusmods.com/article/117-file-scan-statuses)는 support@nexusmods.com 또는 운영진에게 수동 검토를 요청하고 기존 격리 파일을 가능한 한 삭제하지 말라고 설명한다. 파일·이름·버전을 바꿔 재업로드하지 않았으며, 검토 요청도 아직 발송하지 않았다.

전체 상태와 파일별 대조 결과는 [보안 상태 스냅샷](../releases/ISSUE71-20261116-SECURITY-STATUS.json)에 보관한다. 기존 Nexus 영수증은 당시 업로드 메타데이터 확인 기록으로 보존한다.

## 재발 방지

배포 readback은 앞으로 정확한 파일의 `scannedV2`까지 검사한다. `VERIFIED`, `INTERNALLY_VERIFIED`, `MANUALLY_VERIFIED`만 승인으로 판단하고, 대기·격리·미확인 상태를 완료로 기록하지 않는다. 격리는 상태를 기록하고 즉시 실패시키며 재업로드하지 않는다. 최종 영수증은 8개 파일을 모두 확인하고 `all_files_download_ready`를 명시한다. 격리 1개가 있어도 전체 성공이 되지 않는 회귀 검사를 추가했다.
