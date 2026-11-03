#!/usr/bin/env python3
"""Read-only cross-mod Korean topic discovery risk audit.

Audits the pinned KR12.6 release, committed regional source-anchored translations,
Nov 2 topic overlays and (when supplied) published Rebirth/PFP zips.
Findings are lexical *candidates*, NEVER confirmed game-breaking bugs.
No source plugin, distribution artifact, translation or game install is modified.
"""
from __future__ import annotations
import argparse
import collections
import gzip
import hashlib
import json
import re
import struct
import zipfile
from pathlib import Path

HANGUL = re.compile(r"[가-힣]+")
LINK = re.compile(r"@([^@#]*)#")
EN_BOUNDARY = r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])"
JOIN_CUE = re.compile(r"(가입|입단|승진|승급|임무|일거리|의뢰|맹세|결정|수락|선택|도와|도움|허가|용서|참회)")
ENDING_CUE = re.compile(r"^(하시겠습니까|하겠습니까|하실|해주시|하시|해주|하기|할|해야|하려|하면|한다면|해달라|해달|하라고|해주세요|하겠|하는|해서|해요|하게|해서|하겠소|하겠네|하겠다|해보|하죠|해보시|해|하거|되시|됩니까|되나요|되는|되겠|됐다|되었다|시키)")
QUESTION = re.compile(r"(겠습니까\?|합니까\?|됩니까\?|할까요\?|원하십니까\?|하시겠|맡겠|받겠|가입하|가입할)")
SUSPECT_SOURCE = re.compile(r"(join|advan|promot|mission|duties|task|quest|pledge|swear|agree|offer|choice|help|work|contract|orders|permission|recruit|member)",re.I)
RISK_TOPICS = re.compile(r"(가입|승진|승급|입단|맹세|임무|일거리|의뢰|봉사|말하기|도움|계약|명령|수락|결정|참여|승낙|입문|길드)")
SKIP_SHORT = {"일","말","도","은","나","노","행","제국","외지인"}
TOPIC_REPAIR = re.compile(r"[\x7f]")


def sha(raw:bytes)->str:
    return hashlib.sha256(raw).hexdigest()


def sidecar(raw:bytes):
    result={}
    conflicts=[]
    for line in raw.decode("utf-8-sig").splitlines():
        if "\t" not in line: continue
        key,val=line.split("\t",1)
        if key in result and result[key]!=val:
            conflicts.append((key,result[key],val))
        result.setdefault(key,val)
    return result,conflicts


def record_chunks(buf:bytes):
    off=0
    while off<len(buf):
        if off+16>len(buf):raise ValueError("TES3 record header truncated")
        tag,size=struct.unpack_from("<4sI",buf,off)
        end=off+16+size
        if end>len(buf):raise ValueError("TES3 record body truncated")
        yield tag,buf[off+16:end]
        off=end


def subs(body:bytes):
    off=0
    fields=[]
    while off<len(body):
        if off+8>len(body):raise ValueError("TES3 subrecord header truncated")
        tag,size=struct.unpack_from("<4sI",body,off)
        end=off+8+size
        if end>len(body):raise ValueError("TES3 subrecord truncated")
        fields.append((tag,body[off+8:end]))
        off=end
    return fields


def unpack(raw:bytes)->str:
    return raw.rstrip(b"\0").decode("utf-8",errors="replace")


def binary_rows(buf:bytes):
    topics=set()
    rows=[]
    parent=None; kind=None
    for tag,body in record_chunks(buf):
        if tag not in (b"DIAL",b"INFO"): continue
        f=dict(subs(body))
        if tag==b"DIAL":
            parent=unpack(f.get(b"NAME",b""))
            kind=f.get(b"DATA",b"\xff")[:1]
            if kind==b"\0" and b"DELE" not in f:topics.add(parent)
        else:
            text=unpack(f.get(b"NAME",b""))
            if not text or kind!=b"\0": continue
            rows.append({"id":unpack(f.get(b"INAM",b"")),"parent":parent,"en":None,
              "ko":text,"actor":unpack(f.get(b"ONAM",b"")),
              "faction":unpack(f.get(b"FNAM",b"")),
              "script":unpack(f.get(b"BNAM",b""))})
    return topics,rows


def regional_datasets(root:Path):
    return [
      ("Cyr_Main",root/"translations/openmw-kr/cyr-main/26.09a",
       "strings.jsonl.gz","topic_link_overlay_20261102.jsonl.gz","Cyr_Main"),
      ("Sky_Main",root/"translations/openmw-kr/sky-main/26.09a",
       "strings.jsonl.gz","topic_link_overlay_20261102.jsonl.gz","Sky_Main"),
      ("Tamriel_Data",root/"translations/openmw-kr/tamriel-data/26.08",
       "strings.jsonl.gz","topic_link_overlay_20261102.jsonl.gz","Tamriel_Data"),
      ("TR_Mainland",root/"translations/tamriel-rebuilt/26.11.2-kr0.1",
       "TR_Mainland.en_ko.jsonl.gz","topic_link_overlay_20261102.jsonl.gz","TR_Mainland"),
      ("Cyr_RebirthCompat",root/"translations/openmw-kr/rebirth-compat/7.2",
       "cyr_compatch_translation_delta.jsonl.gz",None,"Cyr_Main"),
      ("Sky_RebirthCompat",root/"translations/openmw-kr/rebirth-compat/7.2",
       "sky_compatch_translation_delta.jsonl.gz",None,"Sky_Main"),
    ]


def rows_jsonl(path:Path):
    with gzip.open(path,"rt",encoding="utf-8") as f:
        for line in f:
            if line.strip():yield json.loads(line)


def build_regional(name,folder,source_name,overlay_name,sidecar_stem,root):
    if "RebirthCompat" in name:
        shadow={"Cyr_Main":"cyr-main/26.09a","Sky_Main":"sky-main/26.09a"}[sidecar_stem]
        sidecar_dir=root/"translations/openmw-kr"/shadow
        overlay={}
    else:
        sidecar_dir=folder
        overlay={}
        if overlay_name:
            for r in rows_jsonl(folder/overlay_name):
                key=(int(r["record_index"]),int(r["subrecord_index"]))
                if key in overlay:raise ValueError(f"duplicate overlay record: {name}/{key}")
                overlay[key]=r
    toprow,conflicts=sidecar((sidecar_dir/(sidecar_stem+".top")).read_bytes())
    mrkrow,mc=sidecar((sidecar_dir/(sidecar_stem+".mrk")).read_bytes())
    rows=[]
    matched=set()
    missing_fields=collections.Counter()
    for r in rows_jsonl(folder/source_name):
        if r.get("record_type")!="INFO" or r.get("field")!="NAME":continue
        if r.get("applied") is False:continue
        ko=r.get("ko")
        if not isinstance(ko,str) or not ko:continue
        key=(int(r["record_index"]),int(r["subrecord_index"]))
        if key in overlay:
            # Identity is the TES3 physical record/subrecord tuple, never guessed from text.
            ko=overlay[key]["after"]
            matched.add(key)
        rows.append({
           "id":str(r.get("row_key",str(key))),"parent":r.get("topic_id",r.get("topic","")),
           "en":r.get("en"),"ko":ko,"actor":"","faction":"","script":"",
           "record_index":key[0],"subrecord_index":key[1]})
    return mrkrow,toprow,rows,{
        "rows_scanned":len(rows),
        "overlay_records":len(overlay),
        "overlay_matched_INFO_NAME":len(matched),
        "overlay_unmatched":len(overlay.keys()-matched),
        "sidecar_conflicts":conflicts+mc,
        "mod_data_only":True,
        "live_ESM_binary_not_present_in_GitHub":True,
        "sidecar_held_topics":str(sidecar_dir/"sidecar_holds.json"),
    }


def find_occurrences(text:str, phrase_index:dict):
    explicit_ranges=[(m.start(),m.end()) for m in LINK.finditer(text)]
    for pos,ch in enumerate(text):
        choices=phrase_index.get(ch)
        if not choices:continue
        if pos>0 and "가"<=text[pos-1]<="힣":continue
        if pos>0 and text[pos-1] in "-·‐‑–—":continue
        if any(a<=pos<b for a,b in explicit_ranges):continue
        for word,topic in choices:
            if not text.startswith(word,pos):continue
            end=pos+len(word)
            if end>=len(text) or not ("가"<=text[end]<="힣"):continue
            if any(a<end and b>pos for a,b in explicit_ranges):continue
            m=HANGUL.match(text,end)
            if m is None:continue
            suffix=m.group()
            # These are likely prefixes embedded in longer natural Korean words,
            # and neither an automatic fix nor a proven intended topic mention.
            if suffix in ("은","는","이","가","을","를","의","에","에서","에게","로","으로","와","과","도","만","라고","이라는","라는","이라","인가","입니다","으로는","에게는","까지","부터","께","께서","들을","들에게","들을","들과","들"):
                break
            yield pos,word,topic,suffix
            break


def scan_one(name,root,keywords,aliases,rows,source_note,max_samples=500):
    pairs={}
    for topic,key in keywords.items():
        if not key or len(key)<2 or "\x7f" in key or key in SKIP_SHORT:continue
        if not HANGUL.search(key):continue
        # In the release, an alias key can shadow another topic. Warn separately.
        pairs.setdefault(key,topic)
    first=collections.defaultdict(list)
    for key,topic in pairs.items():
        first[key[0]].append((key,topic))
    for wordlist in first.values():wordlist.sort(key=lambda x:-len(x[0]))
    total=0;by_topic=collections.Counter();by_suffix=collections.Counter()
    by_parent=collections.Counter();by_priority=collections.Counter()
    candidates=[];other=[]
    skipped_explicit=0
    for row in rows:
        ko=row["ko"]
        if "@" in ko: skipped_explicit+=1
        for pos,key,topic,suffix in find_occurrences(ko,first):
            total+=1
            by_topic[topic]+=1;by_suffix[suffix]+=1;by_parent[row["parent"] or "(unknown)"]+=1
            en=row.get("en")
            en_match=False
            if isinstance(en,str) and len(topic)>=3 and len(topic)<=100:
                en_match=bool(re.search(EN_BOUNDARY%re.escape(topic),en,re.I))
            quest=bool(JOIN_CUE.search(topic))
            suffix_verbal=bool(ENDING_CUE.search(suffix))
            question=bool(QUESTION.search(ko))
            critical_source=bool(isinstance(en,str) and SUSPECT_SOURCE.search(en))
            greet=bool(re.search(r"Greeting\s*[1-9]",row["parent"] or "",re.I))
            score=(5 if quest else 0)+(4 if en_match else 0)+(4 if suffix_verbal else 0)
            score+=(2 if question else 0)+(2 if critical_source else 0)+(1 if greet else 0)
            # Keep a candidate if genuinely worth reviewing, even if not the intent.
            level="HIGH_REVIEW" if score>=11 and (en_match or (quest and question)) else "MEDIUM_REVIEW" if score>=7 else "LOW_REVIEW"
            by_priority[level]+=1
            entry={k:row.get(k) for k in ("id","parent","actor","faction","record_index","subrecord_index")}
            entry.update({"topic":topic,"keyword":key,"suffix":suffix,
                "same_english_topic_literal":en_match,"source_relevant":critical_source,
                "score":score,"priority":level,
                "context":ko[max(0,pos-65):min(len(ko),pos+len(key)+len(suffix)+85)],
                "original_context":(en or "")[:320],
                "classification":"LEXICAL_REVIEW_CANDIDATE_NOT_CONFIRMED_BUG"})
            if level=="LOW_REVIEW":
                if len(other)<50:other.append(entry)
            else:candidates.append(entry)
    candidates.sort(key=lambda x:(-x["score"],x.get("id","")))
    return {
     "plugin":name,"source":source_note,"rows":len(rows),
     "topic_keywords":len(pairs),"unrecognized_suffix_candidates":total,
     "priority_counts":dict(by_priority),"top_suffixes":by_suffix.most_common(25),
     "top_topics":by_topic.most_common(30),
     "top_parent_DIAL":by_parent.most_common(25),
     "high_medium_candidates":len(candidates),
     "candidates":candidates[:max_samples],
     "candidate_list_truncated":len(candidates)>max_samples,
     "low_examples":other[:20],
     "limitations":["Only candidate string analysis, not full OpenMW NPC/player-condition or load-order simulation",
                    "Bilingual source literal support is a heuristic, not proof of broken topic reachability",
                    "No mass replacement or unconditional AddTopic should follow these observations"],
    }


def archive_mod(path:Path,main_keywords:dict,main_top:dict):
    with zipfile.ZipFile(path) as z:
        if z.testzip(): raise ValueError("Bad published ZIP CRC: "+str(path))
        names=[n for n in z.namelist() if n.lower().endswith((".esp",".esm",".mrk",".top"))]
        plugins=[n for n in names if n.lower().endswith((".esp",".esm"))]
        if not plugins:raise ValueError("No plugins in "+str(path))
        reports=[]
        for plugin in plugins:
            data=z.read(plugin)
            topics,rows=binary_rows(data)
            stem=Path(plugin).stem
            mpath=next((n for n in names if Path(n).stem.casefold()==stem.casefold() and n.lower().endswith(".mrk")),None)
            tpath=next((n for n in names if Path(n).stem.casefold()==stem.casefold() and n.lower().endswith(".top")),None)
            mod_mrk,_=sidecar(z.read(mpath)) if mpath else ({},[])
            mod_top,_=sidecar(z.read(tpath)) if tpath else ({},[])
            # Do not seed a standalone unrelated mod with all core topic aliases
            # and imply its in-game load order; bound the scope to its DIAL.
            keywords={topic:mod_mrk.get(topic,topic) for topic in topics}
            aliases={**main_top,**mod_top}
            out=scan_one(stem,path.name,keywords,aliases,rows,
                         {"source_zip_sha256":sha(path.read_bytes()),"plugin_sha256":sha(data),"member":plugin,
                          "global_core_topics_not_simulated":True},max_samples=300)
            out["plugin_topic_count"]=len(topics)
            out["plugin_INFO_count"]=len(rows)
            reports.append(out)
        return reports


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo",type=Path,default=Path("."))
    p.add_argument("--core-zip",type=Path,required=True)
    p.add_argument("--reviewed-mods-dir",type=Path)
    p.add_argument("--output",type=Path,required=True)
    x=p.parse_args()
    with zipfile.ZipFile(x.core_zip) as z:
        main_esp=z.read(next(n for n in z.namelist() if n.endswith("Morrowind_Korean_ReTranslation.esp")))
        main_top=z.read(next(n for n in z.namelist() if n.endswith("Morrowind_Korean_ReTranslation.top")))
        main_mrk=z.read(next(n for n in z.namelist() if n.endswith("Morrowind_Korean_ReTranslation.mrk")))
    if sha(x.core_zip.read_bytes())!="2f4bb6b9cfd5916fd9574b6207628e4bb16f8bdc4f1c68fc1ef7581c970989e9":
        raise ValueError("Wrong core release ZIP")
    if sha(main_esp)!="c52a5355752ef0be93fadeca9c95ca00d7cad808f713ce92a624a67d0cc277df":
        raise ValueError("Wrong KR12.6 ESP")
    core_topics,core_rows=binary_rows(main_esp)
    mrk,_=sidecar(main_mrk);top,_=sidecar(main_top)
    reports=[scan_one("KR12.6_CORE","GitHub official pinned KR12.6",{
      topic:mrk.get(topic,topic) for topic in core_topics},top,core_rows,
      {"core_esp_sha256":sha(main_esp),"core_zip_sha256":sha(x.core_zip.read_bytes())})]
    reports[0]["plugin_topic_count"]=len(core_topics)
    for name,folder,source_file,overlay_file,stem in regional_datasets(x.repo):
        kw,aliases,rows,provenance=build_regional(name,folder,source_file,overlay_file,stem,x.repo)
        reports.append(scan_one(name,folder.as_posix(),kw,aliases,rows,provenance))
        reports[-1]["input_details"]=provenance
    if x.reviewed_mods_dir and x.reviewed_mods_dir.exists():
        for source in sorted(x.reviewed_mods_dir.glob("*.zip")):
            if "Rebirth" in source.name or "PFP_" in source.name:
                reports.extend(archive_mod(source,mrk,top))
    summary={
      "status":"READ_ONLY_CROSS_MOD_AUTOTOPIC_TRIAGE_NOT_GAMEPLAY_QA",
      "source_commit":None,
      "scopes":len(reports),
      "total_input_INFO_NAME_rows":sum(r.get("rows",0) for r in reports),
      "total_lexical_candidates":sum(r["unrecognized_suffix_candidates"] for r in reports),
      "total_high_review_candidates":sum(r["priority_counts"].get("HIGH_REVIEW",0) for r in reports),
      "reports":[{k:v for k,v in r.items() if k not in ("candidates","low_examples")} for r in reports],
      "important_warning":"Nonzero candidates do not prove defects; terms can be ordinary Korean words. No file changed.",
    }
    x.output.parent.mkdir(parents=True,exist_ok=True)
    x.output.write_text(json.dumps({"summary":summary,"full_reports":reports},ensure_ascii=False,indent=2),encoding="utf-8")
    print("CROSS_MOD_SUMMARY="+json.dumps(summary,ensure_ascii=False)[:18000])
    for r in reports:
        print("CROSS_MOD_HIGH_EXAMPLES="+json.dumps({
           "mod":r["plugin"],"high":r["priority_counts"].get("HIGH_REVIEW",0),
           "sample":[e for e in r["candidates"] if e["priority"]=="HIGH_REVIEW"][:8]
        },ensure_ascii=False)[:10000])


if __name__=="__main__":
    main()
