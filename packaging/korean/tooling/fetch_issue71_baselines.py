"""Download two immutable owned Nexus baselines; never uploads or prints CDN links."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.request

SOURCES = (
    (60805, 1000073600, '7.2-kr1.2', 'Morrowind_Rebirth7.2-kr1.2.zip', 56495324,
     '6190df64064a40e69772f2c65917128ff3a8de9317ae72dd740ac611919fdd62'),
    (60826, 1000073523, '5.0.7-kr1.2', 'PFP_5.0.7-kr1.2_OpenMW-KR12.6.zip', 1756098,
     'fa8d7b168e3e1e745b64502e51423f4a9273b7fdc03a72ca7b6f07b5241159c1'),
)


def get(path):
    request = urllib.request.Request('https://api.nexusmods.com' + path,
        headers={'apikey': os.environ['NEXUS_KEY'], 'Accept': 'application/json', 'User-Agent': 'OpenMW-KR-Issue71-Baseline'})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def fetch(folder):
    folder.mkdir(parents=True, exist_ok=True)
    actor = str(get('/v1/users/validate.json')['user_id'])
    for mod, file_id, version, name, size, digest in SOURCES:
        owned = get(f'/v1/games/morrowind/mods/{mod}.json')
        if str(owned['user']['member_id']) != actor or str(owned['uid']) != str((100 << 32) + mod):
            raise ValueError('Wrong baseline owner/UID')
        files = get(f'/v1/games/morrowind/mods/{mod}/files.json')['files']
        selected = [r for r in files if int(r['file_id']) == file_id and r['version'] == version]
        if len(selected) != 1 or int(selected[0]['size_in_bytes']) != size:
            raise ValueError('Baseline identity/size changed')
        path = folder / name
        if path.exists():
            raise FileExistsError(path)
        links = get(f'/v1/games/morrowind/mods/{mod}/files/{file_id}/download_link.json')
        if not links or not links[0]['URI'].startswith('https://'):
            raise ValueError('No secure baseline download')
        request = urllib.request.Request(links[0]['URI'], headers={'User-Agent': 'OpenMW-KR-Issue71-Baseline'})
        total, computed = 0, hashlib.sha256()
        with urllib.request.urlopen(request, timeout=150) as response, path.open('xb') as target:
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > size:
                    raise ValueError('Baseline exceeds pinned size')
                target.write(block)
                computed.update(block)
        if total != size or computed.hexdigest() != digest:
            raise ValueError('Baseline SHA/size mismatch')
        print('PASS: owned immutable baseline', mod, file_id, version, digest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    fetch(parser.parse_args().output)
