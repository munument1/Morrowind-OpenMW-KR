"""Repack approved KR13.2 bytes with the earlier Windows ZIP metadata convention."""
import hashlib,json,sys,time
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
from publish_issue71_nexus import target,readback,write,READY_SCAN_STATUSES,PENDING_SCAN_STATUSES
from verify_issue71_followup import PINS

def build(source,folder):
    assert hashlib.sha256(source.read_bytes()).hexdigest()=='805fd9dc6ffdb61639378893690d6c8eeda2b48e6b0f331c23828f3e21929115'
    approved=next(r for r in json.loads(PINS.read_text(encoding='utf-8'))['files'] if r['mod_id']==60496)
    with ZipFile(source) as z:
        assert z.testzip() is None
        files={n:z.read(n) for n in z.namelist()}
    assert len(files)==67 and {n:hashlib.sha256(b).hexdigest() for n,b in files.items()}==approved['payload']
    assert not any(n.lower().endswith(('.zip','.7z','.rar','.gz')) for n in files)
    folder.mkdir(exist_ok=True)
    path=folder/'Morrowind-Korean-OpenMW-0.51.0-KR13.2.1-Full.zip'
    with path.open('xb') as f,ZipFile(f,'w') as z:
        for name,data in sorted(files.items()):
            info=ZipInfo(name,(2026,11,16,12,0,0));info.create_system=0;info.external_attr=0x20
            z.writestr(info,data,compress_type=ZIP_DEFLATED,compresslevel=6)
    with ZipFile(path) as z:
        assert z.testzip() is None and all(i.create_system==0 for i in z.infolist())
        assert {n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}==approved['payload']
    row={'asset':path.name,'version':'0.51.0-KR13.2.1','mod_id':60496,'uid':'429496790096','group':'8110335','bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'payload_unchanged':True,'members':67,'zip_creator_system':0}
    write(folder/'REPACK-VERIFICATION.json',row)
    (folder/(path.name+'.sha256')).write_text(row['sha256']+'  '+path.name+'\n',encoding='ascii')
    return row

if __name__=='__main__':
    folder=Path('retry-dist')
    if sys.argv[1]=='build':
        row=build(Path(sys.argv[2]),folder)
        matches=target(row)
        if matches:raise ValueError('Retry version already exists; do not duplicate')
        print('PASS: 67 unchanged payloads, Windows ZIP metadata, exact owned Windows group')
    elif sys.argv[1]=='readback':
        row=json.loads((folder/'REPACK-VERIFICATION.json').read_text())
        for attempt in range(24):
            record=readback(row,require_ready=False)
            write(folder/'NEXUS-RETRY-RESULT.json',record)
            status=record['security_scan_status'];print('SECURITY_STATUS',status,flush=True)
            if status in READY_SCAN_STATUSES:break
            if status not in PENDING_SCAN_STATUSES:raise ValueError('Repack is still blocked: '+status)
            time.sleep(5)
        else:raise ValueError('Scan still pending; not approved for download')
