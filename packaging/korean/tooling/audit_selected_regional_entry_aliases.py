#!/usr/bin/env python3
"""Read-only native proof of selected regional guild-entry link+TOP proposals.

The original English source INFO is required to discover target, the Korean
INFO must not already discover it, and a single explicit Korean span plus a
globally noncolliding TOP disambiguation alias must restore the target with
identical visible Korean text. No source or release ESM is edited.
"""
import argparse
import json
import re
import tempfile
import zipfile
from pathlib import Path

from audit_cross_mod_topic_gaps import build_regional, regional_datasets, sidecar, sha
from verify_kr5_links import inspect

STEM="Morrowind_Korean_ReTranslation"
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


def visible(s):
    return re.sub(r"@([^@#]*)#",lambda m:m.group(1).rstrip("\x7f"),s)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--runner",type=Path,required=True)
    p.add_argument("--core-zip",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    # Get exact current core disambiguation aliases to avoid clobbering the
    # globally loaded core translation's well-known Korean keys.
    with zipfile.ZipFile(a.core_zip) as z:
        b=z.read(next(n for n in z.namelist() if n.endswith(STEM+".top")))
        core_top,conflicts=sidecar(b)
    if conflicts:raise ValueError("Invalid source core TOP aliases")
    global_keys=set(core_top)
    datasets={}
    for name,folder,src,overlay,stem in regional_datasets(a.repo):
        if name.endswith("RebirthCompat"):continue
        mrk,top,rows,info=build_regional(name,folder,src,overlay,stem,a.repo)
        if name=="TR_Mainland":
            continue
        global_keys.update(top)
        datasets[name]=(folder,stem,mrk,top,rows,info)
    proposals=[]
    same_mod_aliases={}
    for i,(mod,rowkey,target,label) in enumerate(CASES):
        folder,stem,mrk,top,rows,info=datasets[mod]
        matched=[r for r in rows if r["id"]==rowkey]
        if len(matched)!=1:raise ValueError("Missing/duplicate row: "+rowkey)
        r=matched[0]
        if target not in mrk or not isinstance(r["en"],str) or not isinstance(r["ko"],str):
            raise ValueError("Missing bilingual DIAL mapping: "+rowkey)
        if label not in r["ko"]:
            raise ValueError("Curated label no longer present: "+rowkey)
        occurrences=[m.start() for m in re.finditer(re.escape(label),r["ko"])]
        intervals=[(m.start(),m.end()) for m in re.finditer(r"@[^@#]*#",r["ko"])]
        eligible=[idx for idx in occurrences
                  if not any(left < idx+len(label) and idx < right for left,right in intervals)]
        if len(eligible)!=1:
            raise ValueError(f"Ambiguous display label {rowkey}: {eligible}")
        group=(mod,target,label)
        if group in same_mod_aliases:
            key,n=same_mod_aliases[group]
        else:
            key=None;n=None
            for v in range(1,35):
                candidate=label+"*"*v
                if candidate not in global_keys and candidate not in top:
                    key=candidate;n=v;break
            if key is None:raise ValueError("No unique disambiguator for "+rowkey)
            # Reserve once per (mod, target, label), so two INFO lines
            # in the same plugin reuse the same TOP disambiguation alias.
            same_mod_aliases[group]=(key,n)
            global_keys.add(key)
        start=eligible[0]
        new=r["ko"][:start]+"@"+label+"\x7f"*n+"#"+r["ko"][start+len(label):]
        if visible(new)!=visible(r["ko"]):raise ValueError("Display text changed")
        topic_pairs=sorted(mrk)
        topraw=(folder/(stem+".top")).read_bytes()
        mrkraw=(folder/(stem+".mrk")).read_bytes()
        if not topraw.startswith(b"\xef\xbb\xbf") or not mrkraw.startswith(b"\xef\xbb\xbf"):
            raise ValueError("Expected BOM in OpenMW-KR regional sidecars")
        extra_line=(key+"\t"+target+"\r\n").encode("utf-8")
        newtop=topraw+(b"" if topraw.endswith((b"\n",b"\r")) else b"\r\n")+extra_line
        with tempfile.TemporaryDirectory(prefix="regional_topic_native_") as tmp:
            old=Path(tmp)/"source";patched=Path(tmp)/"candidate";en=Path(tmp)/"original-English"
            for dir in (old,patched,en):dir.mkdir()
            for ext,before,after in [
                ("top",topraw,newtop),("mrk",mrkraw,mrkraw),
                ("cel",b"",b""),("jrn",b"",b""),
            ]:
                (old/(STEM+"."+ext)).write_bytes(before)
                (patched/(STEM+"."+ext)).write_bytes(after)
                (en/(STEM+"."+ext)).write_bytes(b"")
            input_english=[("probe",r["en"])]
            input_before=[("probe",r["ko"])]
            input_after=[("probe",new)]
            enparsed=inspect(a.runner,en,input_english,topic_pairs,True,discovery=True)["probe"]["targets"]
            bparsed=inspect(a.runner,old,input_before,topic_pairs,True,discovery=True)["probe"]["targets"]
            aparsed=inspect(a.runner,patched,input_after,topic_pairs,True,discovery=True)["probe"]["targets"]
        target_lower=target.casefold()
        enfound=target_lower in [x.casefold() for x in enparsed]
        beforefound=target_lower in [x.casefold() for x in bparsed]
        afterfound=target_lower in [x.casefold() for x in aparsed]
        added=set(x.casefold() for x in aparsed)-set(x.casefold() for x in bparsed)
        lost=set(x.casefold() for x in bparsed)-set(x.casefold() for x in aparsed)
        status=("NATIVE_PROPOSAL_PASS" if enfound and not beforefound and afterfound and
                all(x.casefold() in target_lower for x in lost) and
                added=={target_lower}
                else "NATIVE_PROPOSAL_REVIEW")
        proposal={
            "mod":mod,
            "source_row_key":rowkey,
            "source_EN":r["en"],
            "target_DIAL":target,
            "source_topic_DIAL":r.get("parent"),
            "before_KO":r["ko"],
            "candidate_KO":new,
            "new_TOP_mapping":{key:target},
            "source_field_record_index":r["record_index"],
            "source_field_subrecord_index":r["subrecord_index"],
            "source_fields_source_offset":info,
            "source_EN_parser_target_found":enfound,
            "current_KO_parser_target_found":beforefound,
            "candidate_KO_parser_target_found":afterfound,
            "parser_existing_targets_masked":sorted(lost),
            "parser_new_targets":sorted(added),
            "candidate_Korean_display_unchanged":True,
            "QA_status":status,
            "not_tested":"Actual ESM actor filters, quest stages, NPC availability, load order.",
        }
        proposals.append(proposal)
        print("REGION_ENTRY_PROPOSAL="+json.dumps({
            k:proposal[k] for k in ("mod","source_row_key","target_DIAL","before_KO","candidate_KO","new_TOP_mapping",
              "source_EN_parser_target_found","current_KO_parser_target_found","candidate_KO_parser_target_found",
              "parser_existing_targets_masked","QA_status")},ensure_ascii=False)[:6000])
    summary={
      "status":"SELECTED_NATIVE_REGIONAL_ENTRY_PROPOSALS_NO_ESM_CHANGES",
      "cases":len(proposals),
      "passed":sum(x["QA_status"]=="NATIVE_PROPOSAL_PASS" for x in proposals),
      "needs_review":sum(x["QA_status"]!="NATIVE_PROPOSAL_PASS" for x in proposals),
      "visible_text_preserved":True,
      "top_aliases_noncolliding_with_current_core_and_regions":True,
      "unique_new_top_aliases":len(same_mod_aliases),
      "release_modified":False,
      "actual_actor_conditions_validated":False,
    }
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps({"summary":summary,"cases":proposals},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("REGION_ENTRY_SUMMARY="+json.dumps(summary,ensure_ascii=False))


if __name__=="__main__":
    main()
