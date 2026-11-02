# Morrowind Rebirth 7.2 — 지역 모드 호환 ESM 한국어화 (kr0.1)

**범위:** Rebirth 7.2 원본에 포함된 **Project Cyrodiil [For Rebirth].esm** 및 **Skyrim Home of the Nords [For Rebirth].esm**. *Morrowind Rebirth [Main].ESP 자체나 설치된 게임은 변경하지 않았다.*

주의: 이 파일들은 **Tamriel Rebuilt 호환 패치가 아니다.** Rebirth 7.2 원본의 `Compability Patches` 폴더에는 Tamriel Rebuilt용 패치가 없고, Tamriel Rebuilt 26.11.2와 Rebirth 7.2의 지형·모델·밸런스 충돌은 해결하지 못했다. 별도의 호환성을 주장하거나 배포해서는 안 된다.

## Nexus Optional Files용 번역 덮어쓰기 ZIP

| 원본 호환 플러그인 | 덮어쓰기 ZIP | 옮긴 한국어 필드 | 결과 ESM SHA-256 |
|---|---|---:|---|
| Project Cyrodiil [For Rebirth].esm | `Project_Cyrodiil_For_Rebirth-kr0.1.zip` | 15,034 | `7794af1214b759a0c85d655b2b40eb8774beb396ee7775dd76e965e63dbbca1e` |
| Skyrim Home of the Nords [For Rebirth].esm | `Skyrim_Home_of_the_Nords_For_Rebirth-kr0.1.zip` | 8,202 | `fbfe6a982c69d5da86120043e3e13dd2104f1569d8c846302367d070165d54f6` |

같은 이름의 원본 **호환판 ESM을 덮어쓰는 대체 파일**이며, 정상 지역 모드의 `Cyr_Main.ESM`·`Sky_Main.ESM`과 **동시에 활성화해서는 안 된다.** 원본 지역 모드 자산·Rebirth 7.2 및 동일 계열의 Tamriel Data 26.08이 선행 설치되어야 한다. 원본 호환 ESM을 이미 모드 관리자가 별도로 관리한다면 그보다 한국어 패치를 나중에 적용한다. OpenMW 한국어판의 `.cel/.top/.mrk/.jrn` 파일도 같은 호환판 이름으로 동봉한다. 두 ZIP은 사용자 PC에서 생성했으며 **GitHub에 업로드하지 않는다**. 사용자 본인이 이미 만들어 둔 Nexus 페이지의 Optional Files에 수동 업로드한다.

## 한국어 데이터와 독립 검증

- **버전 고정:** Rebirth 7.2, Project Cyrodiil 26.09a, Skyrim: Home of the Nords 26.09a, Tamriel Data 26.08.
- 레코드 순서가 서로 다르므로 **고유 레코드 타입·ID** 및 원문 서브레코드 SHA-256이 일치할 때만 기존 번역을 이식했다. 임의의 내부 ID·퀘스트 조건·스크립트 컴파일 바이트를 수정하지 않았다.
- 영문 본문의 끝 NUL 패딩만 달랐던 필드 388건은 한국어 변환 후 호환판의 종결 패딩을 보존했다. Cyrodiil의 의도적으로 제거된 밀랍 봉인 이미지 태그 7건도 **다시 추가하지 않았다**. 호환판에서 실제로 변경된 대사 3건은 한국어로 직접 교정하고 `%PCClass`, `%Name`, `%Class` 변수 보존을 검증했다.
- Rebirth 호환 ESM 원본에 남아 있던 구버전 Tamriel_Data.esm 마스터 크기 안내 14,887,395바이트만 최신 번역판 **18,536,570바이트**로 조정했다. 플러그인 헤더의 다른 필드와 미대상 서브레코드는 바이트 동일성을 검증했다.
- TES3 모든 레코드와 비수정 서브레코드 확인, `esmtool` 구조 검사, ZIP CRC 검사, SHA-256 검증 **PASS**. 별도의 [재생성 스크립트](replay_pinned_esm.py)가 GitHub의 한국어 데이터만으로 두 ESM을 재생산하고 **최종 ESM SHA-256 일치**를 확인했다.
- **고유 ID·원문 해시로 안전하게 대응시킨 번역 후보**에서는 호환판 특유의 문자열 보류가 0건이다. 다만 ID가 없거나 중복된 일부 레코드는 안전을 위해 원본 그대로 보존했으며, 전체 번역의 전문적인 언어 전수 검수 및 실제 게임 실행·퀘스트·충돌 검증은 수행하지 않았다. 따라서 **kr0.1 초기 테스트판**으로 배포한다.

## 저장 파일과 재현 방법

| 파일 | 목적 |
|---|---|
| `cyr_compatch_translation_delta.jsonl.gz` | Cyrodiil 호환판에서 실제 번역한 15,034개 텍스트 필드, 원문·한국어·필드 SHA |
| `sky_compatch_translation_delta.jsonl.gz` | Skyrim 호환판에서 실제 번역한 8,202개 텍스트 필드 |
| `cyr_compatch_build_QA.json` / `sky_compatch_build_QA.json` | 입력·출력 해시, 레코드 수, 마스터 크기, 원본 보존 검증 |
| `replay_pinned_esm.py` | 원본 호환 ESM에서 source-anchored 한국어 데이터를 재현하고 최종 해시 검증 |

재생성 예시 (원본 호환 ESM은 사용자가 별도로 보유해야 한다):

```bash
python replay_pinned_esm.py --mod cyr --input "Project Cyrodiil [For Rebirth].esm" --out "PC_Rebirth_kr0.1.esm"
python replay_pinned_esm.py --mod sky --input "Skyrim Home of the Nords [For Rebirth].esm" --out "Sky_Rebirth_kr0.1.esm"
```

*재생성 예시의 출력명은 검증용이며, 실제 게임에 설치할 때는 ZIP에 담긴 기존 호환판 ESM 이름을 그대로 유지해야 한다.*

사용자 원본 게임 설치·OneDrive 폴더·Rebirth 배포본의 ESM/ESP는 변형하거나 업로드하지 않았다.
