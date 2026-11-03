#!/usr/bin/env python3
"""Read back four owned 2026-11-02 Nexus regional releases for immutable audit.

This is strictly read-only: no upload, metadata edits, API key printing,
game/source file modification, or publication. Download into Actions artifacts
only, with short retention. Validates current author's ownership and SHA of
the translated plugins against the previously published release manifest.
"""
from __future__ import annotations
import hashlib,json,os,urllib.request,urllib.error,zipfile
from pathlib import Path

KEY=os.environ["NEXUS_KEY"]
OUT=Path("audit-region-download")
OUT.mkdir(exist_ok=True)
MODS={
 60846:("Project Cyrodiil","26.09a-kr0.1",{"Cyr_Main.ESM":"d16323effcbbec7a29ba8e1ef247b24b902e62e017c6666aaa284595b95b035c"}),
 60847:("Skyrim Home of the Nords","26.09a-kr0.1",{"Sky_Main.ESM":"28453abc5fb95735590667fb8d5546863035eef5cf7c36f486aa7d4533943c0f"}),
 60845:("Tamriel Data","26.08-kr0.1",{"Tamriel_Data.esm":"647b7950857fc74e03fba8ad58680a75e55b90287e4044bfecf011ce9002a9b4"}),
 60844:("Tamriel Rebuilt","26.11.2-kr0.1",{
     "TR_Mainland.esm":"1627359756ab5a429893044a8337a10b8688c5f5cdf1fa4ecdab628dbaa8a183",
     "TR_Factions.esp":"7906b753a801085e5984419575834692f5ac1c618cb5925a9a42b1d8c949e2fd"}),
}
def api(path):
    req=urllib.request.Request("https://api.nexusmods.com"+path,
         headers={"apikey":KEY,"Accept":"application/json",
                  "User-Agent":"OpenMW-KR-Regional-Immutable-QA"})
    with urllib.request.urlopen(req,timeout=50) as f:return json.load(f)

def sha_file(file):
    with file.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()

owner=str(api("/v1/users/validate.json")["user_id"])
all_meta=[]
for mid,(title,version,expected) in MODS.items():
    info=api(f"/v1/games/morrowind/mods/{mid}.json")
    if str(info["user"]["member_id"])!=owner:
        raise RuntimeError(f"Readback not owned: {mid}")
    if str(info["version"])!=version:
        raise RuntimeError(f"Version drift {mid}: {info['version']!r}")
    group=api(f"/v3/mods/{info['uid']}/files")["data"]["mod_files"]
    files=api(f"/v1/games/morrowind/mods/{mid}/files.json")["files"]
    main=[f for f in files if str(f.get("category_name","")).upper()=="MAIN"]
    if len(main)!=1:
        raise RuntimeError(f"Ambiguous Nexus main release for {mid}: {len(main)}")
    f=main[0];fid=f["file_id"]
    links=api(f"/v1/games/morrowind/mods/{mid}/files/{fid}/download_link.json")
    if not links or not links[0]["URI"].startswith("https://"):
        raise RuntimeError(f"Nexus download link unavailable for {mid}")
    out=OUT/f"{mid}-published-KR0.1.zip"
    req=urllib.request.Request(links[0]["URI"],headers={
        "User-Agent":"OpenMW-KR-Regional-Immutable-QA"})
    size=0;h=hashlib.sha256()
    with urllib.request.urlopen(req,timeout=150) as stream, out.open("xb") as dest:
        while chunk:=stream.read(1024*1024):
            size+=len(chunk)
            if size>350_000_000:raise RuntimeError("Unexpected >350 MB archive")
            h.update(chunk);dest.write(chunk)
    plugins={}
    with zipfile.ZipFile(out) as z:
        names=z.namelist()
        if z.testzip() is not None or len(names)!=len(set(names)):
            raise RuntimeError("Archive failed CRC or contains duplicate members")
        for name,expected_sha in expected.items():
            matches=[n for n in names if n.lower().endswith("/"+name.lower())]
            if len(matches)!=1:
                raise RuntimeError(f"ZIP lacks one {name}: {matches}")
            data=z.read(matches[0])
            digest=hashlib.sha256(data).hexdigest()
            if digest!=expected_sha:
                raise RuntimeError(
                    f"Published plugin differs from release manifest {mid} {name}: {digest}")
            plugins[name]={"sha256":digest,"size":len(data),"archive_path":matches[0]}
    record={"id":mid,"mod":title,"version":version,"file_id":fid,
            "mod_uid":str(info["uid"]),"source_archive_name":f.get("file_name"),
            "zip_sha256":h.hexdigest(),"zip_bytes":size,
            "source_nexus_owned":True,"plugins":plugins,
            "Nexus_key_disclosed":False}
    all_meta.append(record)
    print("REGIONAL_NEXUS_READBACK="+json.dumps(
        {"id":mid,"version":version,"zip_sha256":record["zip_sha256"],
         "plugins":plugins},ensure_ascii=False),flush=True)

(OUT/"manifest.json").write_text(
    json.dumps({"status":"READ_ONLY_VERIFIED_PUBLISHED_BASELINES",
                "release_count":len(all_meta),"releases":all_meta},
               ensure_ascii=False,indent=2)+"\n","utf8")
print("REGIONAL_NEXUS_QA_SNAPSHOT_PASS=4")
