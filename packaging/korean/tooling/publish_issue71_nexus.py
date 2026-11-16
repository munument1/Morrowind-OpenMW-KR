"""Read-only Nexus preflight/readback; upload is the pinned official action."""
import argparse
import json
import os
from pathlib import Path
import time
import urllib.request

from build_issue71_followup import ROOT, sha
from verify_issue71_followup import PINS, check_archive, verify

QA = ROOT / 'packaging/korean/releases/ISSUE71-20261116-QA.json'
TARGETS = {(60496, '8110335'), (60844, '8296179'), (60845, '8296167'),
           (60846, '8296161'), (60847, '8296155'), (60805, '8296377'),
           (60805, '8257641'), (60826, '8280147')}
ANDROID_GROUP = '8257539'
READY_SCAN_STATUSES = {'VERIFIED', 'INTERNALLY_VERIFIED', 'MANUALLY_VERIFIED'}
PENDING_SCAN_STATUSES = {'NOT_SCANNED', 'QUEUED', 'WAITING_REPORT'}


def get(path):
    key = os.environ['NEXUS_KEY']
    request = urllib.request.Request('https://api.nexusmods.com' + path,
        headers={'apikey': key, 'Accept': 'application/json', 'User-Agent': 'OpenMW-KR-Issue71-Owner-Release'})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def target(row):
    mod, uid, group = row['mod_id'], row['uid'], row['group']
    if (mod, group) not in TARGETS or group == ANDROID_GROUP or uid != str((100 << 32) + mod):
        raise ValueError('Wrong Nexus target / Android forbidden')
    actor = str(get('/v1/users/validate.json')['user_id'])
    owned = get(f'/v1/games/morrowind/mods/{mod}.json')
    if str(owned['user']['member_id']) != actor or str(owned['uid']) != uid:
        raise ValueError('Nexus ownership/UID mismatch')
    if str(get(f'/v3/games/morrowind/mods/{mod}')['data']['id']) != uid:
        raise ValueError('Nexus canonical UID drift')
    groups = get(f'/v3/mods/{uid}/files')['data']['mod_files']
    if len([r for r in groups if str(r['id']) == group and r['is_active']]) != 1:
        raise ValueError('Inactive or wrong Nexus file group')
    versions = get(f'/v3/mod-files/{group}/versions')['data']['versions']
    matches = [v for v in versions if str(v.get('version', '')).casefold() == row['version'].casefold()]
    if len(matches) > 1 or (matches and str(matches[0].get('category', '')).lower() == 'removed'):
        raise ValueError('Duplicate/removed Nexus version')
    return matches


def scan_status(row, file_id):
    # The public GraphQL scan enum distinguishes an uploaded file from an approved file.
    query = '''query ReleaseScan($mod: ID!, $game: ID!) {
      modFiles(modId: $mod, gameId: $game) {
        fileId modId modUid version sizeInBytes scannedV2
      }
    }'''
    request = urllib.request.Request('https://api.nexusmods.com/v2/graphql',
        data=json.dumps({'query': query, 'variables': {'mod': str(row['mod_id']), 'game': '100'}}).encode(),
        headers={'Content-Type': 'application/json', 'User-Agent': 'OpenMW-KR-Release-Scan-Status'})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = json.load(response)
    if data.get('errors'):
        raise ValueError('Nexus scan status query failed')
    files = [f for f in data.get('data', {}).get('modFiles', []) if str(f.get('fileId')) == str(file_id)]
    if len(files) != 1:
        raise ValueError('Scan status missing or ambiguous')
    file = files[0]
    if (str(file.get('modId')) != str(row['mod_id']) or str(file.get('modUid')) != row['uid']
            or file.get('version') != row['version'] or int(file.get('sizeInBytes', -1)) != row['bytes']):
        raise ValueError('Scan record identity/size mismatch')
    return file.get('scannedV2', 'UNKNOWN')


def readback(row, require_ready=True):
    versions = get(f"/v3/mod-files/{row['group']}/versions")['data']['versions']
    match = [r for r in versions if str(r.get('version', '')).casefold() == row['version'].casefold()
             and str(r.get('category', '')).lower() != 'removed']
    if len(match) != 1:
        raise ValueError('Expected exactly one version in the verified file group')
    public = get(f"/v1/games/morrowind/mods/{row['mod_id']}/files.json")['files']
    files = [r for r in public if str(r.get('version', '')).casefold() == row['version'].casefold()]
    if len(files) != 1 or int(files[0]['size_in_bytes']) != row['bytes']:
        raise ValueError('Nexus version/size readback mismatch')
    status = scan_status(row, files[0]['file_id'])
    if require_ready and status not in READY_SCAN_STATUSES:
        raise ValueError('Nexus file is not approved for download: ' + str(status))
    return {**row, 'file_version_id': str(match[0]['id']), 'server_file_id': files[0]['file_id'],
            'server_file_name': files[0]['file_name'], 'server_size_bytes': files[0]['size_in_bytes'],
            'security_scan_status': status, 'download_ready': status in READY_SCAN_STATUSES,
            'nexus_url': f"https://www.nexusmods.com/morrowind/mods/{row['mod_id']}?tab=files"}


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def run(mode, folder, asset=None, armed=False):
    pins = json.loads(PINS.read_text(encoding='utf-8'))['files']
    if {(r['mod_id'], r['group']) for r in pins} != TARGETS or len(pins) != 8:
        raise ValueError('Expected eight approved non-Android targets')
    if mode == 'preflight':
        if armed and not json.loads(QA.read_text(encoding='utf-8'))['ready_for_publication']:
            raise ValueError('Runtime/QA release gate incomplete')
        verified = verify(folder)['files']
        for row in verified:
            existing = target(row)
            if existing:
                readback(row)
        before = get(f'/v3/mod-files/{ANDROID_GROUP}/versions')['data']['versions']
        write(folder / 'NEXUS-ANDROID-UNCHANGED-BEFORE.json', before)
        write(folder / 'NEXUS-ISSUE71-PREFLIGHT.json', verified)
        print('PASS: eight owned groups; Android snapshot read only')
        return
    if mode == 'final':
        before = json.loads((folder / 'NEXUS-ANDROID-UNCHANGED-BEFORE.json').read_text(encoding='utf-8'))
        after = get(f'/v3/mod-files/{ANDROID_GROUP}/versions')['data']['versions']
        if before != after:
            raise ValueError('Android group versions changed during publication')
        stored = json.loads((folder / 'NEXUS-ISSUE71-PREFLIGHT.json').read_text(encoding='utf-8'))
        identity = lambda r: (r['mod_id'], r['group'], r['version'], r['asset'])
        if len(stored) != len(pins) or {identity(r) for r in stored} != {identity(r) for r in pins}:
            raise ValueError('Final readback must cover all eight approved packages')
        rows = [readback(r, require_ready=False) for r in stored]
        ready = all(row['download_ready'] for row in rows)
        write(folder / 'NEXUS-ISSUE71-FINAL.json', {'android_group_unchanged': True,
              'all_files_download_ready': ready, 'files': rows})
        if not ready:
            raise ValueError('Uploaded files are awaiting security approval; see final JSON')
        print('PASS: all eight versions, sizes, groups and security approvals; Android versions unchanged')
        return
    expected = next(r for r in pins if r['asset'] == asset)
    row = check_archive(folder / asset, expected)
    if mode == 'gate':
        if not json.loads(QA.read_text(encoding='utf-8'))['ready_for_publication']:
            raise ValueError('Publication QA gate incomplete')
        existing = target(row)
        if existing:
            readback(row)
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as out:
            out.write('upload=' + str(not existing).lower() + '\n')
            out.write('group=' + row['group'] + '\nversion=' + row['version'] + '\n')
            out.write('category=' + ('optional' if row['group'] == '8296377' else 'main') + '\n')
            out.write('primary=' + str(row['group'] != '8296377').lower() + '\n')
        print('READY' if not existing else 'ALREADY_VERIFIED', asset, row['group'], row['version'])
        return
    if mode == 'readback':
        for attempt in range(12):
            try:
                record = readback(row, require_ready=False)
            except ValueError:
                if attempt == 11:
                    raise
                time.sleep(5)
                continue
            write(folder / ('NEXUS-' + str(row['mod_id']) + '-PUBLICATION.json'), record)
            if record['download_ready']:
                print('PASS', row['mod_id'], row['group'], row['version'], row['bytes'], record['security_scan_status'])
                return
            status = record['security_scan_status']
            if status not in PENDING_SCAN_STATUSES or attempt == 11:
                raise ValueError('Nexus file is not approved for download: ' + str(status))
            time.sleep(5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('preflight', 'gate', 'readback', 'final'))
    parser.add_argument('--folder', type=Path, default=Path('dist'))
    parser.add_argument('--asset')
    parser.add_argument('--armed', action='store_true')
    args = parser.parse_args()
    run(args.mode, args.folder, args.asset, args.armed)
