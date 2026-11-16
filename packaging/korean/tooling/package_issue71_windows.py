"""Promote the verified 0019 Windows runtime plus two reviewed core voice scripts."""
import argparse
import codecs
import json
from pathlib import Path
from zipfile import ZipFile

from build_issue71_followup import REVIEW, sha, rewrite_plugin, verify_logic, write_zip

ASSET = 'Morrowind-Korean-OpenMW-0.51.0-KR13.2-Full.zip'
ENGINE_SHA = '67ff422ae07dca20ca43e23254b2888e0e7f2d0ff536abaa964bf83264032b78'
CORE_SHA = '9f94b1c96b10a491cec00d4931123ef1e0f52f52c6095da6b9b380eb9a617b1c'
ESP = 'payload/mods/Morrowind_Korean_ReTranslation/Morrowind_Korean_ReTranslation.esp'


def build(source, folder):
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / ASSET
    if target.exists():
        raise FileExistsError(target)
    review = json.loads((REVIEW / 'review.json').read_text(encoding='utf-8'))
    with ZipFile(source) as z:
        if z.testzip() is not None or len(z.namelist()) != 67:
            raise ValueError('Expected verified 67-member KR13.1 stage')
        files = {name: z.read(name) for name in z.namelist()}
    if sha(files['payload/openmw.exe']) != ENGINE_SHA or sha(files[ESP]) != CORE_SHA:
        raise ValueError('Unverified Windows engine/core source')
    updated, changes, _ = rewrite_plugin(files[ESP], 'core', review)
    if changes != {'SCPT.SCTX': 2, 'display_operands': 11}:
        raise ValueError('Unexpected core scope: ' + str(changes))
    count = verify_logic(files[ESP], updated, 'core', review)
    files[ESP] = updated
    for name in ('README-KOREAN.txt', 'KR13.1-RELEASE-NOTES-KO.txt', 'CORRESPONDING-SOURCE.txt', 'install-korean.ps1'):
        files[name] = files[name].replace(b'KR13.1', b'KR13.2').replace(b'kr13.1', b'kr13.2')
    notes = ('\r\nKR13.2 추가 보완\r\n'
             '- 본편 VampireMolag와 playScript의 Say 자막 11개를 한국어로 보완했습니다.\r\n'
             '- 검증된 0018~0019 엔진을 유지하며, NPC/아이템 ID와 퀘스트 조건·분기를 보존합니다.\r\n'
             '- 대응 지역 모드 ZIP은 토픽 표시명·인물명·선택지·알림을 함께 보강합니다.\r\n'
             '- 잠정 음역과 AI 검토를 포함하며, 모든 퀘스트의 완주·사람에 의한 전수 검수를 뜻하지 않습니다.\r\n').encode('utf-8')
    files['README-KOREAN.txt'] += notes
    files['KR13.2-RELEASE-NOTES-KO.txt'] = files.pop('KR13.1-RELEASE-NOTES-KO.txt') + notes
    provenance = json.loads(files['SOURCE-PROVENANCE.json'])
    provenance['translation_esp_sha256'] = sha(updated)
    provenance['issue71_core_display_repair'] = {'source_esp_sha256': CORE_SHA, 'scripts': ['VampireMolag', 'playScript'],
                                                'display_operands': 11, 'record_logic_verified': count,
                                                'review': 'translations/openmw-kr/issue71-20261116/review.json'}
    files['SOURCE-PROVENANCE.json'] = (json.dumps(provenance, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
    if len(files) != 67:
        raise ValueError('Unexpected Windows package membership')
    write_zip(target, files)
    digest = sha(target.read_bytes())
    (folder / (ASSET + '.sha256')).write_text(digest + '  ' + ASSET + '\n', encoding='ascii')
    report = {'asset': ASSET, 'version': '0.51.0-KR13.2', 'mod_id': 60496, 'uid': '429496790096', 'group': '8110335',
              'sha256': digest, 'bytes': target.stat().st_size, 'engine_sha256': ENGINE_SHA,
              'payload': {name: sha(data) for name, data in files.items()}, 'changes': changes,
              'source_esp_sha256': CORE_SHA, 'translated_esp_sha256': sha(updated), 'record_logic_verified': count}
    (folder / 'KR13.2-Windows-build-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.source, args.output)
    print(json.dumps({k: v for k, v in result.items() if k not in ('payload',)}, ensure_ascii=False, indent=2))
