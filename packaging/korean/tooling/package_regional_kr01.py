#!/usr/bin/env python3
"""Create Nexus-upload-ready kr0.1 same-name overwrite ZIPs from pinned verified distribution files.
No upstream meshes/scripts/assets or game binaries; no installed-game changes.
"""
import argparse, hashlib, json, mmap, os, shutil, struct, subprocess, sys, zipfile
from pathlib import Path

SPECS=[
 {"slug":"Cyr_Main","version":"26.09a","subdir":"openmw_kr_replacement_terms_20261102_v2/cyr-main/Data Files","plugin":"Cyr_Main.ESM",
  "source_sha256":"0e23edd68d4f374ad55e873f8a7d77ec3a8e05a5bf8da1d092bf622e8bccf87a",
  "plugin_sha256":"d16323effcbbec7a29ba8e1ef247b24b902e62e017c6666aaa284595b95b035c","records":20268,
  "sidecars":["Cyr_Main.cel","Cyr_Main.top","Cyr_Main.mrk","Cyr_Main.jrn"],"nexus":"https://www.nexusmods.com/morrowind/mods/44922"},
 {"slug":"Sky_Main","version":"26.09a","subdir":"openmw_kr_replacement_terms_20261102_v2/sky-main/Data Files","plugin":"Sky_Main.ESM",
  "source_sha256":"311907b5feca991b4232ef02d9ddaa73ece4b99673af63b676d6f57d15527888",
  "plugin_sha256":"28453abc5fb95735590667fb8d5546863035eef5cf7c36f486aa7d4533943c0f","records":11340,
  "sidecars":["Sky_Main.cel","Sky_Main.top","Sky_Main.mrk","Sky_Main.jrn"],"nexus":"https://www.nexusmods.com/morrowind/mods/44921"},
 {"slug":"Tamriel_Data","version":"26.08","subdir":"openmw_kr_replacement_terms_20261102_v2/tamriel-data/Data Files","plugin":"Tamriel_Data.esm",
  "source_sha256":"e94ca3a5c62e0228ac3782e813cae58c4e10da2e9e8b7611e0a8f5ff9a98d06f",
  "plugin_sha256":"647b7950857fc74e03fba8ad58680a75e55b90287e4044bfecf011ce9002a9b4","records":58872,
  "sidecars":["Tamriel_Data.cel","Tamriel_Data.top","Tamriel_Data.mrk","Tamriel_Data.jrn"],"nexus":"https://www.nexusmods.com/morrowind/mods/44537"},
 {"slug":"TR_Mainland","version":"26.11.2","subdir":"Tamriel Rebuilt 26.11.2-kr0.1/Data Files","plugin":"TR_Mainland.esm",
  "source_sha256":"d8c55de18c07afb7026de8354d7b71d9fe60b9a3484df5a8cd9735fbac1b3b08",
  "plugin_sha256":"1627359756ab5a429893044a8337a10b8688c5f5cdf1fa4ecdab628dbaa8a183","records":115865,
  "sidecars":["TR_Factions.esp","TR_Mainland.cel","TR_Mainland.top","TR_Mainland.mrk","TR_Mainland.jrn"],"nexus":"https://www.nexusmods.com/morrowind/mods/42145"}
]
TR_FACTIONS_HASH="7906b753a801085e5984419575834692f5ac1c618cb5925a9a42b1d8c949e2fd"
SUB=struct.Struct("<4sI")
HDR=struct.Struct("<4sIII")
def sha(p):
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def records(mm):
    p=0;i=0
    while p<len(mm):
        assert p+16<=len(mm),(i,"short")
        typ,n,u,fl=HDR.unpack_from(mm,p)
        end=p+16+n;assert end<=len(mm),(i,"overrun")
        q=p+16;subs=[]
        while q<end:
            assert q+8<=end
            tag,size=SUB.unpack_from(mm,q);a=q+8;z=a+size;assert z<=end
            subs.append((tag,a,z))
            q=z
        assert q==end
        yield i,typ,u,fl,subs
        p=end;i+=1
    assert p==len(mm)
def parse_header(mm,first):
    assert first[1]==b"TES3" and first[0]==0
    name=None;masters={}
    for typ,a,z in first[4]:
        if typ==b"MAST":name=bytes(mm[a:z]).rstrip(b"\0").decode("ascii")
        elif typ==b"DATA" and name:
            assert z-a==8
            masters[name]=struct.unpack_from("<Q",mm,a)[0];name=None
    return masters
def check_plugin(path,sha_expected,n_expected,esmtool):
    assert sha(path)==sha_expected,("source_or_data_drift",path,sha(path),sha_expected)
    with path.open("rb") as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:
        total=0;masters={}
        for item in records(mm):
            if total==0:masters=parse_header(mm,item)
            total+=1
    assert total==n_expected,(path,total,n_expected)
    if esmtool:
        p=subprocess.run([str(esmtool),"-q","dump",str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=180)
        assert p.returncode==0,(path,p.stderr[:2000])
    return {"sha256":sha_expected,"bytes":path.stat().st_size,"TES3_records":total,"master_size_hints":masters,"esmtool":"PASS" if esmtool else "NOT_RUN"}
def make_readme(s):
    version=s["version"]
    intro=("Tamriel Rebuilt 26.11.2 (Nexus 2026-11-01 update)" if s["slug"]=="TR_Mainland" else s["slug"]+" "+version)
    extras="TR_Factions.esp is included as a translated OPTIONAL plugin. Enable it only if using Faction Integration.\n" if s["slug"]=="TR_Mainland" else ""
    return ("OpenMW Korean Translation - "+s["slug"]+"-kr0.1\n"
            "Source mod: "+intro+"\n"
            "Project: "+s["nexus"]+"\n\n"
            "INSTALL: Install the original mod and all its original meshes, textures, scripts and other assets FIRST.\n"
            "Then install this ZIP as an overwrite/replacement mod in MO2 or copy its Data Files contents over the existing source mod's Data Files.\n"
            "The same-named ESM/ESP and *.cel/*.top/*.mrk/*.jrn files must replace the originals; do not install two copies.\n"
            "Do not remove the upstream resource assets. Requires Morrowind + Tribunal + Bloodmoon + matching Tamriel_Data 26.08.\n"
            "OpenMW 0.51 KR12.6 integration expected; no separate translation ESP, plugin list must retain original names.\n"
            +extras+
            "\nSTATUS: kr0.1 early static-tested release candidate. No actual gameplay/quest-stage/Save test.\n"
            "Language reviews are not comprehensive. Reserved internal IDs, uncertain location/keyword links and 3 TR numeric/source anomalies remain unchanged where applicable.\n"
            "No original third-party mod assets or game binaries are included in this translation override.\n"
            "Original upstream ESM/ESP backed up before overwrite is recommended.\n").encode("utf-8")
def main():
    a=argparse.ArgumentParser()
    a.add_argument("--source-output-root",type=Path,required=True)
    a.add_argument("--out",type=Path,required=True)
    a.add_argument("--no-esmtool",action="store_true")
    o=a.parse_args();ROOT=o.source_output_root.resolve();TARGET=o.out.resolve()
    assert ROOT.exists()
    TARGET.mkdir(parents=True,exist_ok=True)
    esmtool=Path(r"D:\OpenMW 0.51.0\esmtool.exe")
    if o.no_esmtool:esmtool=None
    else:assert esmtool.exists()
    actual={}
    for s in SPECS:
        stem=s["slug"];title=stem+"-kr0.1";directory=ROOT/s["subdir"]
        assert directory.is_dir()
        plugin=directory/s["plugin"]
        info=check_plugin(plugin,s["plugin_sha256"],s["records"],esmtool)
        if stem=="TR_Mainland":
            assert sha(directory/"TR_Factions.esp")==TR_FACTIONS_HASH
        assets=[s["plugin"]]+s["sidecars"]
        assert len(set(assets))==len(assets)
        for name in assets:assert (directory/name).is_file()
        # Dependency hints must reflect the 26.08 translation ESM and latest TR ESM bytes.
        if stem in ("Cyr_Main","Sky_Main","TR_Mainland"):
            assert info["master_size_hints"].get("Tamriel_Data.esm")==18536570,(stem,info["master_size_hints"])
        if stem=="TR_Mainland":
            fa=check_plugin(directory/"TR_Factions.esp",TR_FACTIONS_HASH,247,esmtool)
            assert fa["master_size_hints"].get("TR_Mainland.esm")==plugin.stat().st_size
            assert fa["master_size_hints"].get("Tamriel_Data.esm")==18536570
            info["factions"]=fa
        out_zip=TARGET/(title+".zip")
        assert not out_zip.exists(),("refuse_overwrite",out_zip)
        with zipfile.ZipFile(out_zip,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
            for name in assets:
                z.write(directory/name,arcname="Data Files/"+name)
            z.writestr("README_KO_kr0.1.txt",make_readme(s))
        assert zipfile.ZipFile(out_zip).testzip() is None
        with zipfile.ZipFile(out_zip) as z:
            assert set(z.namelist())==set("Data Files/"+x for x in assets)|{"README_KO_kr0.1.txt"}
            for name in assets:
                with z.open("Data Files/"+name) as f:
                    assert hashlib.file_digest(f,"sha256").hexdigest()==sha(directory/name)
        digest=sha(out_zip)
        (TARGET/(out_zip.name+".sha256")).write_text(digest+"  "+out_zip.name+"\n",encoding="ascii")
        actual[stem]={"display_title":title,"source_version":s["version"],"source_plugin_sha256":s["source_sha256"],
                      "overwrite_zip":out_zip.name,"zip_sha256":digest,"zip_size_bytes":out_zip.stat().st_size,
                      "files":{name:{"bytes":(directory/name).stat().st_size,"sha256":sha(directory/name)} for name in assets},
                      "verification":info,"install":"same-named plugin overwrite only; original mod assets required",
                      "runtime_tested":False,"all_translation_human_reviewed":False,"no_original_game_files_modified":True}
        print("PACKAGE_PASS",json.dumps({"title":title,"sha256":digest,"bytes":out_zip.stat().st_size,"esmtool":"PASS"},ensure_ascii=True),flush=True)
    (TARGET/"RELEASE_INDEX.json").write_text(json.dumps(actual,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("ALL_FOUR_PACKAGES_READY",len(actual),flush=True)
if __name__=="__main__":main()
