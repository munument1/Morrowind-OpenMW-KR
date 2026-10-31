#!/usr/bin/env python3
"""Read-only: compare exact Rebirth v56 layout with published KR12.3/12.4 deltas.

No ESP/ESM, TOP, existing install, original game data or release is modified.
This does not replace an official KR12.4 ESP-to-ESP comparison or gameplay QA.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct
import zipfile

V56_SHA="8b07aec7d2400f22c60f9833d6339185a54acea687de9ed7f8a9c1030bf6d8f3"
KR124_QUEST_IDS={
 "26689110631261324944","24205752258151922","2569266611020420362",
 "713021754425128647","210385542530924589","685137928821210",
 "15871201801537426826","159522145792925173","29712284933271723190",
 "19294183501106417663","2572521291321832207","22806201441497819089",
}
KR123_QUEST_IDS={
 "6986172382590219429","499230085676914328",
 "20813494252707603","187538034100124510",
}
KR124_BAD_MARKUP=("@설원#곰","@설원#늑대","정@말#","@말입니까?#","@이나 다른#")
KR124_ALIASES={
 "마법부여사 아우데니안","마법부여사 아우데니안 발리우스",
 "텔바니 마법부여사 아우데니안 발리우스",
}

def digest(data):
    return sha256(data).hexdigest()

def records(data):
    at=0
    while at<len(data):
        if at+16>len(data):
            raise ValueError("Truncated TES3 record")
        name=data[at:at+4]
        n=struct.unpack_from("<I",data,at+4)[0]
        end=at+16+n
        if end>len(data):
            raise ValueError("Invalid TES3 record")
        subs={}
        off=at+16
        while off<end:
            if off+8>end:
                raise ValueError("Truncated TES3 subrecord")
            tag=data[off:off+4]
            size=struct.unpack_from("<I",data,off+4)[0]
            off+=8
            if off+size>end:
                raise ValueError("Invalid TES3 subrecord")
            subs[tag]=data[off:off+size]
            off+=size
        yield name,subs
        at=end

def decoded(value):
    return value.rstrip(b"\x00").decode("utf-8",errors="surrogateescape")

def audit(archive,verified_sha=True):
    path=Path(archive)
    if verified_sha and digest(path.read_bytes())!=V56_SHA:
        raise ValueError("Not the pinned Rebirth v56 full-layout archive")
    report={
        "schema":"rebirth_v56_kr124_release_delta_impact_audit_v1",
        "v56_zip_sha256":digest(path.read_bytes()),
        "official_kr124_esp_sha256":"2276384ad93fd3e56bc0d401aacc45418ba38993ee798e0e1a7e09564a375d3a",
        "official_kr124_esp_binary_read":False,
        "kr124_quest_id_matches":[],
        "kr123_quest_id_matches":[],
        "kr124_markup_pattern_hits":[],
        "kr124_top_alias_hits":[],
        "files":[],
    }
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        plugins=sorted(x for x in names if x.lower().endswith((".esp",".esm")))
        sides=sorted(x for x in names if x.lower().endswith(".top"))
        if len(plugins)!=15 or len(sides)!=3:
            raise ValueError("Expected 15 ESP/ESM plugins and 3 TOP sidecars")
        for name in plugins:
            raw=z.read(name)
            category="rebirth_translated" if ("[Main]" in name or "[Addon]" in name) else "unchanged_compatibility_mod"
            count=0
            parent=""
            for kind,sub in records(raw):
                if kind==b"DIAL":
                    parent=decoded(sub.get(b"NAME",b""))
                if kind!=b"INFO":
                    continue
                count+=1
                id=decoded(sub.get(b"INAM",b""))
                msg=decoded(sub.get(b"NAME",b""))
                entry={"file":name,"INFO":id,"DIAL":parent,"scope":category,
                       "korean_text":any("가"<=c<="힣" for c in msg)}
                if id in KR124_QUEST_IDS:
                    report["kr124_quest_id_matches"].append(entry)
                if id in KR123_QUEST_IDS:
                    report["kr123_quest_id_matches"].append(entry)
                for pattern in KR124_BAD_MARKUP:
                    if pattern in msg:
                        report["kr124_markup_pattern_hits"].append({
                            **entry,"pattern":pattern,"occurrences":msg.count(pattern)
                        })
            report["files"].append({"file":name,"sha256":digest(raw),
                                    "INFO":count,"scope":category})
        for name in sides:
            raw=z.read(name)
            for line in raw.decode("utf-8-sig").splitlines():
                key,separator,target=line.partition("\t")
                if separator and key in KR124_ALIASES:
                    report["kr124_top_alias_hits"].append({
                        "file":name,"alias":key,"target":target
                    })
            report["files"].append({"file":name,"sha256":digest(raw),"scope":"rebirth_top"})
    owned=sum(x["scope"]=="rebirth_translated" for x in
              report["kr124_quest_id_matches"]+report["kr123_quest_id_matches"])
    owned+=sum(x["occurrences"] for x in report["kr124_markup_pattern_hits"]
               if x["scope"]=="rebirth_translated")
    owned+=len(report["kr124_top_alias_hits"])
    report.update({
        "plugin_count":15,"top_file_count":3,
        "revised_rebirth_owned_fields":0,
        "owned_delta_candidates":owned,
        "unmodified_english_compatibility_info_matches":sum(
            x["scope"]=="unchanged_compatibility_mod"
            for x in report["kr124_quest_id_matches"]+report["kr123_quest_id_matches"]),
        "v56_unchanged":True,"KR124_runtime_tested":False,
        "official_kr124_full_dictionary_compared":False,
        "release_ready":False,
    })
    return report

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v56-zip",required=True,type=Path)
    ap.add_argument("--out",required=True,type=Path)
    args=ap.parse_args()
    if args.out.exists():
        raise ValueError("Output must be new")
    result=audit(args.v56_zip)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items()
                      if k not in ("files","kr124_quest_id_matches",
                                    "kr123_quest_id_matches","kr124_markup_pattern_hits",
                                    "kr124_top_alias_hits")},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
