"""Publish the verified Android KR12 release as an optional Nexus ZIP.

Runs only through the explicit manual Actions workflow. No local API key,
private signing files or Rebirth ESP are inputs.
"""
import base64,hashlib,json,os,time,zipfile,urllib.request,urllib.error
from pathlib import Path

TAG='android-korean-0.51.0-12-kr12-permanent'
REPO='munument1/Morrowind-OpenMW-Android-KR'
NAME='OpenMW Android Korean APK and Data'
VERSION='0.51.0-12-KR12'
APK='OpenMW-Android-0.51.0-12-Korean-KR12-Permanent-16K.apk'
DATA='OpenMW-Android-0.51.0-12-Korean-Data-KR12.zip'
CERT='ebf75015d1b61b14ffa2a3539d8981434c30272219eb6b0ae0c3de16bb2228f2'
OUT=Path('nexus-android-kr12');OUT.mkdir(exist_ok=True)

def request(url,method='GET',body=None,headers=None):
    req=urllib.request.Request(url,data=body,method=method,headers=headers or {})
    try:
        with urllib.request.urlopen(req,timeout=120) as response:return response.read()
    except urllib.error.HTTPError as error:
        # Do not print request headers or signed storage upload URLs.
        raise RuntimeError('HTTP '+str(error.code)+' during '+method+' request') from None

def nexus(path,method='GET',body=None,legacy=False):
    headers={'apikey':os.environ['NEXUS_API_KEY'],'User-Agent':'OpenMW-KR12-Android-release-sync','Content-Type':'application/json'}
    data=request('https://api.nexusmods.com'+path,method,None if body is None else json.dumps(body).encode(),headers)
    value=json.loads(data)
    return value if legacy else value['data']

def main():
    gh_headers={'Accept':'application/vnd.github+json','User-Agent':'OpenMW-KR12-release-sync'}
    if os.environ.get('GH_TOKEN'):gh_headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
    release=json.loads(request('https://api.github.com/repos/'+REPO+'/releases/tags/'+TAG,headers=gh_headers))
    assert not release['draft'] and not release['prerelease']
    assets={a['name']:a for a in release['assets']}
    files=[APK,APK+'.sha256',DATA,DATA+'.sha256','KR12-APK-independent-verification.json']
    for name in files:
        assert name in assets and assets[name]['state']=='uploaded',name
        (OUT/name).write_bytes(request(assets[name]['browser_download_url']))
    for name in (APK,DATA):
        digest=hashlib.sha256((OUT/name).read_bytes()).hexdigest()
        assert (OUT/(name+'.sha256')).read_text().split()[0]==digest
        if assets[name].get('digest'):assert assets[name]['digest']=='sha256:'+digest
    proof=json.loads((OUT/files[-1]).read_text())
    assert proof['status']=='PASS' and proof['application']['package']=='com.ast.openmw.korean'
    assert proof['application']['versionCode']==5114 and not proof['debuggable']
    assert proof['signer_certificate_sha256']==CERT
    assert proof['Daedric_slot']=='DemonicLetters'
    assert proof['APK_sha256']==hashlib.sha256((OUT/APK).read_bytes()).hexdigest()
    readme='''OpenMW Android Korean KR12 (0.51.0-12)

1. Install the signed ARM64 APK. Package: com.ast.openmw.korean, versionCode 5114.
2. Extract the Korean Data KR12 ZIP and add Morrowind_Korean_ReTranslation
   as a data directory in the new app. Enable its Korean ESP after the masters.
3. Original, legally owned Morrowind game data is required separately.

KR8 and early KR9 use different package IDs. This app coexists with them;
back up saves and transfer them manually. Do not delete an old app before backup.

KR12 ports Windows KR10 honorific and legacy topic/journal recovery fixes,
repairs false topic discovery and reviewed translation hyperlinks,
keeps Roman numeral font coverage, and preserves genuine Daedric lettering
with the original DemonicLetters font in slot 2.

The APK uses a permanent release certificate. Native/C++/Gradle/signature/16K
checks passed; full Android hardware gameplay has not been tested here.
Rebirth ESP, game master files and signing keys are not included.
'''
    (OUT/'README-ANDROID-KR12.txt').write_text(readme,encoding='utf8')
    bundle=OUT/'OpenMW-Android-0.51.0-12-Korean-KR12-Full.zip'
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name in files+['README-ANDROID-KR12.txt']:z.write(OUT/name,name)
    digest=hashlib.sha256(bundle.read_bytes()).hexdigest()
    (OUT/(bundle.name+'.sha256')).write_text(digest+'  '+bundle.name+'\n')
    user=nexus('/v1/users/validate.json',legacy=True)
    mod=nexus('/v1/games/morrowind/mods/60496.json',legacy=True)
    assert str(user['user_id'])==str(mod['user']['member_id'])
    uid=str(mod['uid'])
    candidates=[f for f in nexus('/v3/mods/'+uid+'/files')['mod_files'] if f['is_active'] and f['name']==NAME]
    assert len(candidates)<=1
    existing=candidates[0] if candidates else None
    if existing:
        versions=nexus('/v3/mod-files/'+str(existing['id'])+'/versions')['versions']
        if any(v['version']==VERSION for v in versions):
            print('Android KR12 already exists on Nexus; no duplicate upload.')
            return
    if os.environ.get('DRY_RUN','true')=='true':
        print('Android KR12 bundle and Nexus owner verified. Dry run; no writes.')
        return
    size=bundle.stat().st_size
    assert size<=100*1024*1024
    upload=nexus('/v3/uploads','POST',{'filename':bundle.name,'size_bytes':size})
    assert upload['presigned_url'].startswith('https://')
    payload=bundle.read_bytes()
    request(upload['presigned_url'],'PUT',payload,{'Content-Disposition':'attachment; filename="'+bundle.name+'"',
      'Content-Type':'application/octet-stream','Content-MD5':base64.b64encode(hashlib.md5(payload).digest()).decode()})
    upload_id=str(upload['id'])
    nexus('/v3/uploads/'+upload_id+'/finalise','POST')
    for _ in range(30):
        state=nexus('/v3/uploads/'+upload_id)['state']
        if state=='available':break
        assert state not in ('failed','rejected','expired'),state
        time.sleep(2)
    assert state=='available',state
    body={'upload_id':upload_id,'name':NAME,'version':VERSION,'file_category':'optional',
      'description':'ARM64 permanent signed KR12 APK plus Korean Data KR12. Install both. New package com.ast.openmw.korean; back up and manually transfer old saves. Native topic/journal fixes, Roman numerals and original Daedric font. Full Android device gameplay not tested. '+release['html_url'],
      'primary_mod_manager_download':False,'allow_mod_manager_download':False,'update_mod_version':False}
    if existing:
        body['archive_existing_file']=False
        response=nexus('/v3/mod-files/'+str(existing['id'])+'/versions','POST',body)
        file_id=str(existing['id'])
    else:
        body['mod_id']=uid
        response=nexus('/v3/mod-files','POST',body)
        file_id=str(response['id'])
    versions=nexus('/v3/mod-files/'+file_id+'/versions')['versions']
    assert any(v['version']==VERSION for v in versions)
    report={'status':'PUBLISHED_AND_READ_BACK','file_id':file_id,'version':VERSION,
      'bundle_sha256':digest,'GitHub_release':release['html_url'],'Nexus_mod':'https://www.nexusmods.com/morrowind/mods/60496'}
    (OUT/'Nexus-Android-KR12-result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
