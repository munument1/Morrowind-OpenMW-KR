# -*- coding: utf-8 -*-
"""Isolated regional kr0.2 topic candidate ZIPs from exact user-owned Nexus kr0.1.

Nine source-English-proven INFO targets, eight noncolliding TOP aliases.
Current released ESM/ESPs and source masters never modified. No publish.
"""
from __future__ import annotations
import collections,gzip,hashlib,json,re,struct,zipfile
from pathlib import Path
ROOT=Path.cwd()
REPO=Path(__file__).resolve().parents[3]
SOURCE=ROOT/"published_regional_kr01_verified_readback.zip"
OUT=ROOT/"CANDIDATE_REGIONAL_KR02_NOT_RELEASED"
H=struct.Struct("<4sIII");SUB=struct.Struct("<4sI")
DISPLAY_LINK=re.compile(r"@([^@#]*)#")
CASES=[
 ("Cyr_Main","Cyr_Main.ESM@45291051","join the Fighters Guild","전사 길드에 가입"),
 ("Cyr_Main","Cyr_Main.ESM@45516511","join the Kingdom of Anvil","앤빌 왕국에 가입"),
 ("Cyr_Main","Cyr_Main.ESM@46099084","join the Thieves Guild","도둑 길드에 들어가"),
 ("Sky_Main","Sky_Main.ESM@29500154","join the Fighters Guild","전사 길드에 가입"),
 ("Sky_Main","Sky_Main.ESM@29755203","join the Fighters Guild","전사 길드에 가입"),
 ("Sky_Main","Sky_Main.ESM@30463186","join the Thieves Guild","도둑 길드에 가입"),
 ("Tamriel_Data","Tamriel_Data.esm@15117505","join House Indoril","인도릴 가문에 가입"),
 ("Tamriel_Data","Tamriel_Data.esm@15120535","join the Ordinators","오디네이터에 입단"),
 ("Tamriel_Data","Tamriel_Data.esm@15129808","join the Mages Guild","마법사 길드에 가입"),
]
MODS={
 "Cyr_Main":("60846-published-KR0.1.zip","Cyr_Main.ESM","openmw-kr/cyr-main/26.09a"),
 "Sky_Main":("60847-published-KR0.1.zip","Sky_Main.ESM","openmw-kr/sky-main/26.09a"),
 "Tamriel_Data":("60845-published-KR0.1.zip","Tamriel_Data.esm","openmw-kr/tamriel-data/26.08"),
}
def sha(b):return hashlib.sha256(b).hexdigest()
def display(s):return DISPLAY_LINK.sub(lambda m:m.group(1).replace("\x7f",""),s).replace("\x7f","")
def row_source(directory,key):
    path=REPO/"translations"/directory/"strings.jsonl.gz"
    with gzip.open(path,"rt",encoding="utf8") as f:
        for ln in f:
            r=json.loads(ln)
            if r["row_key"]==key:return r
    raise ValueError("Missing anchored translation row "+key)
def raw_records(raw):
    p=0;i=0
    while p<len(raw):
        if p+16>len(raw):raise ValueError("Short record")
        rt,n,u,flags=H.unpack_from(raw,p);e=p+16+n
        if e>len(raw):raise ValueError("Invalid record size")
        fields=[];q=p+16
        while q<e:
            tag,length=SUB.unpack_from(raw,q);a=q+8;b=a+length
            if b>e:raise ValueError("Bad subrecord")
            fields.append((tag,raw[a:b]));q=b
        if q!=e:raise ValueError("Misaligned subrecords")
        yield i,rt,u,flags,fields,raw[p:e]
        p=e;i+=1
def real_info_and_dials(raw,updates):
    out=[];changes=[];seen=set();parent=None;count=0;topics=set()
    for ri,rt,u,flags,fields,raw_record in raw_records(raw):
        count+=1
        x=dict(fields)
        if rt==b"DIAL":
            parent=x.get(b"NAME",b"").rstrip(b"\0").decode("utf8",errors="replace")
            if x.get(b"DATA",b"\xff")[:1]==b"\0" and b"DELE" not in x:topics.add(parent)
        change=[z for z in updates if z["ri"]==ri]
        if not change:
            out.append(raw_record);continue
        if len(change)!=1 or rt!=b"INFO":raise ValueError("Unsafe non-INFO or duplicate row")
        item=change[0];si=item["si"]
        if si>=len(fields) or fields[si][0]!=b"NAME":
            raise ValueError(f"Wrong INFO subrecord {ri}/{si}")
        before=fields[si][1];old=before.rstrip(b"\0").decode("utf8")
        if old.count(item["label"])!=1:
            raise ValueError(f"Old label missing or ambiguous {ri}/{si}: {item['label']!r} in {old!r}")
        if parent and item["parent"] and parent!=item["parent"]:
            raise ValueError(f"Parent DIAL mismatches source field: {parent} vs {item['parent']}")
        k=old.index(item["label"])
        # No insertion inside an existing explicit hyperlink span.
        intervals=[(m.start(),m.end()) for m in DISPLAY_LINK.finditer(old)]
        if any(a<k+len(item["label"]) and k<b for a,b in intervals):
            raise ValueError("Attempted nested @link#")
        new=old[:k]+"@"+item["label"]+("\x7f"*item["alias_n"])+"#"+old[k+len(item["label"]):]
        if display(old)!=display(new):raise ValueError("User visible Korean changed")
        if old==new:raise ValueError("No-op edit")
        # Protect placeholders / numeric cues by exact unchanged displayed Korean.
        suffix=before[len(before.rstrip(b"\0")):]
        replacement=new.encode("utf8")+suffix
        patched=list(fields);patched[si]=(b"NAME",replacement)
        body=b"".join(SUB.pack(tag,len(val))+val for tag,val in patched)
        out.append(H.pack(rt,len(body),u,flags)+body)
        changes.append({"row_key":item["row_key"],"record_index":ri,"subrecord_index":si,
                        "DIAL":parent,"target_DIAL":item["target"],"old_ko":old,
                        "new_ko":new,"source_field_sha256":sha(before),
                        "candidate_field_sha256":sha(replacement),"visible_Korean_unchanged":True})
        seen.add((ri,si))
    if seen!={(z["ri"],z["si"]) for z in updates}:raise ValueError("Not all requested info records found")
    if not all(z["target"] in topics for z in updates):raise ValueError("Target DIAL not found in same ESM")
    newraw=b"".join(out)
    before=list(raw_records(raw));after=list(raw_records(newraw))
    if len(before)!=len(after) or len(before)!=count:raise ValueError("Record count changed")
    changes_seen=0
    for a,b in zip(before,after):
        if a[:4]!=b[:4]:raise ValueError("Record header metadata changed")
        for si,((tag,old),(tag2,new)) in enumerate(zip(a[4],b[4])):
            if tag!=tag2:raise ValueError("Subrecord type changed")
            if old!=new:
                if (a[0],si) not in seen or a[1]!=b"INFO" or tag!=b"NAME":
                    raise ValueError("Non-target subrecord was modified")
                changes_seen+=1
    if changes_seen!=len(updates):raise ValueError("Changed INFO count mismatch")
    return newraw,changes,count

def main():
    if OUT.exists():raise RuntimeError("Refusing existing output dir")
    with zipfile.ZipFile(SOURCE) as outer:
        if outer.testzip():raise ValueError("Outer verified ZIP corrupt")
        meta=json.loads(outer.read("manifest.json"))
        expected={r["id"]:r for r in meta["releases"]}
        snapshot={}
        for mod,(name,plugin,folder) in MODS.items():
            mid=int(name.split("-")[0])
            with zipfile.ZipFile(outer.open(name)) as pkg:
                if pkg.testzip():raise ValueError("Owned Nexus package corrupt")
                contents={n:pkg.read(n) for n in pkg.namelist() if not n.endswith("/")}
            plugin_key=next((n for n in contents if n.lower().endswith("/"+plugin.lower())),None)
            top_key=next((n for n in contents if n.lower().endswith("/"+mod.lower()+".top")),None)
            if not plugin_key or not top_key:raise ValueError("Missing published ESP/TOP")
            raw=contents[plugin_key]
            if sha(raw)!=expected[mid]["plugins"][plugin]["sha256"]:
                raise ValueError("Published plugin SHA mismatch")
            source_path=REPO/"translations"/folder
            snapshot[mod]={"package":name,"plugin":plugin,
                "plugin_key":plugin_key,"top_key":top_key,
                "contents":contents,"original_sha":sha(raw),"original_top_sha":sha(contents[top_key]),
                "member_names":[n for n in pkg.namelist()]}
    global_aliases=set()
    for mod,s in snapshot.items():
        for line in s["contents"][s["top_key"]].decode("utf-8-sig").splitlines():
            if "\t" in line:global_aliases.add(line.split("\t",1)[0].casefold())
    updates=collections.defaultdict(list);unique_alias={};added_aliases=collections.defaultdict(dict)
    for mod,rowkey,target,label in CASES:
        _,_,src_dir=MODS[mod]
        row=row_source(src_dir,rowkey)
        if row["record_type"]!="INFO" or row["field"]!="NAME":
            raise ValueError("Non-dialogue translation source")
        key=(mod,label,target)
        if key not in unique_alias:
            for n in range(1,30):
                alias=label+"*"*n
                if alias.casefold() not in global_aliases:
                    unique_alias[key]=(alias,n);global_aliases.add(alias.casefold());break
            else:raise ValueError("No unique TOP alias")
        alias,n=unique_alias[key]
        added_aliases[mod][alias]=target
        updates[mod].append({
            "ri":row["record_index"],"si":row["subrecord_index"],
            "row_key":rowkey,"parent":row["topic_id"],"target":target,
            "label":label,"alias":alias,"alias_n":n,
        })
    OUT.mkdir()
    reports=[]
    for mod,s in snapshot.items():
        source=s["contents"][s["plugin_key"]]
        patched,edits,records=real_info_and_dials(source,updates[mod])
        old_top=s["contents"][s["top_key"]]
        if not old_top.startswith(b"\xef\xbb\xbf"):
            raise ValueError("Published sidecar UTF-8 BOM missing")
        already={k:v for line in old_top.decode("utf-8-sig").splitlines()
                 if "\t" in line for k,v in [line.split("\t",1)]}
        if any(k in already for k in added_aliases[mod]):
            raise ValueError("TOP overwritten unexpectedly")
        tail=b"" if old_top.endswith((b"\n",b"\r")) else b"\r\n"
        extra=b"".join((a+"\t"+b+"\r\n").encode("utf8") for a,b in sorted(added_aliases[mod].items()))
        new_top=old_top+tail+extra
        for k,v in already.items():
            # Every original key/value stays identical.
            if dict(line.split("\t",1) for line in new_top.decode("utf-8-sig").splitlines() if "\t" in line)[k]!=v:
                raise ValueError("Old TOP alias altered")
        new_contents=dict(s["contents"])
        new_contents[s["plugin_key"]]=patched
        new_contents[s["top_key"]]=new_top
        filename=f"{mod}-kr0.2-topic-fix-TEST-ONLY.zip"
        output=OUT/filename
        with zipfile.ZipFile(output,"x",zipfile.ZIP_DEFLATED,compresslevel=6) as zip:
            for name in s["member_names"]:
                if name.endswith("/"):zip.writestr(name,b"")
                else:zip.writestr(name,new_contents[name])
            zip.writestr("README_KR0.2_TEST_ONLY.txt",
              ("KR0.2 TEST CANDIDATE — do not release without integrated gameplay QA.\n"
               f"Only {len(edits)} INFO.NAME / {len(added_aliases[mod])} TOP aliases changed from exact current user-owned Nexus kr0.1.\n"
               "Original source mods, game installs and saves never modified.\n").encode("utf8"))
        with zipfile.ZipFile(output) as zip:
            if zip.testzip() is not None:raise ValueError("Output ZIP CRC mismatch")
            for n in s["contents"]:
                if n not in (s["plugin_key"],s["top_key"]):
                    if zip.read(n)!=s["contents"][n]:raise ValueError("Unexpected ZIP member changed")
            if zip.read(s["plugin_key"])!=patched or zip.read(s["top_key"])!=new_top:
                raise ValueError("Output package differs from candidate")
        report={"mod":mod,"release_version":"kr0.2-candidate","source_published_zip_sha256":sha(
                   next(z for z in (ROOT/"published_regional_kr01_verified_readback.zip",) if z.is_file()).read_bytes()
                   )[:12],
                "source_published_plugin_sha256":s["original_sha"],
                "candidate_plugin_sha256":sha(patched),
                "published_top_sha256":s["original_top_sha"],"candidate_top_sha256":sha(new_top),
                "package_sha256":sha(output.read_bytes()),
                "record_count":records,"changed_INFO_NAME":len(edits),
                "added_TOP_aliases":added_aliases[mod],
                "all_other_binary_subrecords_unchanged":True,
                "all_non_target_zip_members_unchanged":True,
                "parser_source_English_to_KO_proof":
                   "https://github.com/munument1/Morrowind-OpenMW-KR/actions/runs/41644351838",
                "gameplay_tested":False,"release_published":False,"changes":edits}
        reports.append(report)
        print("REGIONAL_CANDIDATE_PASS="+json.dumps(
           {k:report[k] for k in ("mod","changed_INFO_NAME","record_count",
                "candidate_plugin_sha256","candidate_top_sha256","package_sha256")},
                ensure_ascii=False),flush=True)
    (OUT/"verify_candidates.json").write_text(json.dumps(reports,ensure_ascii=False,indent=2)+"\n","utf8")
    print("REGIONAL_TESTS_COMPLETE=9_INFO_8_TOP_NO_RELEASE")
if __name__=="__main__":main()

[executed on device: Deck_Seung (a3b70f16-4906-418e-a5c0-ee1efec6a325)]