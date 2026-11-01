"""Read owned Nexus release metadata; fetch current public translation packages for audit."""
import os,json,urllib.request,urllib.error,hashlib
from pathlib import Path
key=os.environ['NEXUS_KEY'];root=Path('audit-input');root.mkdir(exist_ok=True)
def get(path):
 req=urllib.request.Request('https://api.nexusmods.com'+path,headers={'apikey':key,'Accept':'application/json','User-Agent':'KR125-Mod-Translation-Audit'})
 with urllib.request.urlopen(req,timeout=40) as r:return json.load(r)
account=str(get('/v1/users/validate.json')['user_id'])
for modid in (60805,60826)+((45096,) if os.environ.get('FETCH_ORIGINAL_REFERENCE')=='1' else ()):
 mod=get(f'/v1/games/morrowind/mods/{modid}.json')
 if modid!=45096:assert str(mod['user']['member_id'])==account,'Not owned'
 uid=str(mod['uid']);groups=get(f'/v3/mods/{uid}/files')['data']['mod_files']
 files=get(f'/v1/games/morrowind/mods/{modid}/files.json')['files']
 meta={'modid':modid,'uid':uid,'version':mod['version'],'groups':groups,'files':files}
 (root/f'{modid}-metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
 print('REFERENCE' if modid==45096 else 'OWNED',modid,uid,mod['version'])
 for f in files:
  if str(f.get('category_name','')).upper()!='MAIN':continue
  fid=f['file_id'];print('CURRENT',modid,fid,f.get('version'),f.get('file_name'))
  try:links=get(f'/v1/games/morrowind/mods/{modid}/files/{fid}/download_link.json')
  except urllib.error.HTTPError as e:
   print('DOWNLOAD_UNAVAILABLE_HTTP',e.code)
   # Inspect the current v3 version shape without exposing private CDN links.
   for g in groups:
    vs=get(f"/v3/mod-files/{g['id']}/versions")['data']['versions']
    for v in vs:
     if str(v.get('game_scoped_id'))==str(fid):
      detail=get(f"/v3/mod-file-versions/{v['id']}")['data']
      print('DETAIL_FIELDS',sorted(detail));(root/f'{modid}-detail.json').write_text(json.dumps(detail),encoding='utf8')
   continue
  assert links and links[0]['URI'].startswith('https://')
  req=urllib.request.Request(links[0]['URI'],headers={'User-Agent':'KR125-Mod-Translation-Audit'})
  with urllib.request.urlopen(req,timeout=120) as r:data=r.read()
  (root/f'{modid}-current.zip').write_bytes(data)
  print('DOWNLOADED',modid,len(data),hashlib.sha256(data).hexdigest())
