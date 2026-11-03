#!/usr/bin/env python3
"""Confirm shortlisted Morrowind topic-edge candidates using real OpenMW KR12.6 C++ parser.

An unmatched phrase is NOT proof of an NPC/quest blocker. This only asserts the
literal Korean text fails to discover the target when every candidate topic is
seeded as already known; it does not evaluate INFO filters or load order.
"""
from __future__ import annotations
import argparse
import collections
import json
import tempfile
import zipfile
from pathlib import Path

from audit_cross_mod_topic_gaps import (
    sha, sidecar, binary_rows, build_regional, regional_datasets,
)
from verify_kr5_links import inspect

STEM="Morrowind_Korean_ReTranslation"


def sidecars_for(mod,root,core_zip,reviewed_dir):
    if mod=="KR12.6_CORE":
        with zipfile.ZipFile(core_zip) as z:
            prefix=next(n[:-len(STEM+".top")] for n in z.namelist() if n.endswith(STEM+".top"))
            raw=z.read(prefix+STEM+".esp")
            topics,rows=binary_rows(raw)
            top=z.read(prefix+STEM+".top")
            mrk=z.read(prefix+STEM+".mrk")
        return topics,rows,top,mrk
    for name,folder,source,overlay,stem in regional_datasets(root):
        if name==mod:
            mrk,top,rows,_=build_regional(name,folder,source,overlay,stem,root)
            folder_sidecar=folder
            if "RebirthCompat" in name:
                folder_sidecar=root/"translations/openmw-kr"/{"Cyr_Main":"cyr-main/26.09a","Sky_Main":"sky-main/26.09a"}[stem]
            topraw=(folder_sidecar/(stem+".top")).read_bytes()
            mrkraw=(folder_sidecar/(stem+".mrk")).read_bytes()
            return set(mrk)|set(top.values()),rows,topraw,mrkraw
    for zippath in sorted(reviewed_dir.glob("*.zip")):
        with zipfile.ZipFile(zippath) as z:
            all_names=z.namelist()
            for member in all_names:
                if Path(member).stem!=mod or not member.lower().endswith((".esp",".esm")):continue
                topics,rows=binary_rows(z.read(member))
                top_name=next((n for n in all_names if n.casefold().endswith((mod+".top").casefold())),None)
                mrk_name=next((n for n in all_names if n.casefold().endswith((mod+".mrk").casefold())),None)
                return topics,rows,z.read(top_name) if top_name else b"",z.read(mrk_name) if mrk_name else b""
    raise ValueError("Requested plugin data unavailable: "+mod)


def test_mod(mod,report,root,corezip,revieweddir,runner):
    candidates=report["candidates"]
    if not candidates:
        return {"plugin":mod,"tested":0,"unmatched":0,"reason":"No HIGH/MEDIUM candidates selected","records":[]}
    topics,rows,top,mrk=sidecars_for(mod,root,corezip,revieweddir)
    if not topics: return {"plugin":mod,"tested":0,"reason":"No DIAL topics available","records":[]}
    byid=collections.defaultdict(list)
    for row in rows:
        byid[(str(row["id"]),row.get("parent") or "")].append(row)
    selected=[];entries=[];missing=[]
    for index,c in enumerate(candidates):
        key=(str(c["id"]),c.get("parent") or "")
        matching=[r for r in byid[key] if c["context"] in r["ko"]]
        if len(matching)!=1:
            missing.append({"key":key,"row_matches":len(matching)})
            continue
        entryid=f"candidate-{index}-{c['id']}"
        selected.append((entryid,c))
        entries.append((entryid,matching[0]["ko"]))
    with tempfile.TemporaryDirectory(prefix="native-morrowind-topics-") as temporary:
        folder=Path(temporary)
        for ext,data in (("top",top),("mrk",mrk),("cel",b""),("jrn",b"")):
            (folder/(STEM+"."+ext)).write_bytes(data)
        # Same parser, same TOP/MRK loader and UTF-8 BOM reader as runtime.
        results=inspect(runner,folder,entries,sorted(topics),True,discovery=True)
    out=[]
    bylevel=collections.Counter()
    for id,c in selected:
        result=results[id]
        targets=set(x.casefold() for x in result["targets"])
        matched=c["topic"].casefold() in targets
        status="PARSER_MATCHED" if matched else "PARSER_NOT_DISCOVERED"
        bylevel[(c["priority"],status)]+=1
        out.append({
          **c, "native_parser_status":status,
          "expected_topic":c["topic"],
          "parsed_targets":result["targets"][:25],
          "not_a_gameplay_proof":True
        })
    # Do not silently omit a candidate when the source row changed.
    if missing: raise ValueError(f"Lost candidate source rows in {mod}: {missing[:6]}")
    return {
        "plugin":mod,"tested":len(selected),"unmatched":sum(r["native_parser_status"]=="PARSER_NOT_DISCOVERED" for r in out),
        "matched":sum(r["native_parser_status"]=="PARSER_MATCHED" for r in out),
        "by_level_and_native_status":{" / ".join(k):v for k,v in sorted(bylevel.items())},
        "records":out,
        "note":"No NPC-specific conditions, quest stages, original English master parity or other mod priorities were simulated",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo",type=Path,default=Path("."))
    p.add_argument("--core-zip",type=Path,required=True)
    p.add_argument("--reviewed-mods-dir",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--runner",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if not a.runner.exists():raise ValueError("Native C++ parser binary missing")
    report=json.loads(a.report.read_text(encoding="utf-8"))
    all_reports=[]
    for mod_report in report["full_reports"]:
        mod=mod_report["plugin"]
        output=test_mod(mod,mod_report,a.repo,a.core_zip,a.reviewed_mods_dir,a.runner)
        all_reports.append(output)
        print("NATIVE_TOPIC_MOD="+json.dumps({
            "mod":mod, "checked":output["tested"],
            "unmatched":output.get("unmatched"),"matched":output.get("matched"),
            "breakdown":output.get("by_level_and_native_status",{}),
            "high_examples":[{k:r[k] for k in ("id","parent","topic","suffix","context","native_parser_status")}
                for r in output["records"]
                if r["priority"]=="HIGH_REVIEW" and r["native_parser_status"]=="PARSER_NOT_DISCOVERED"][:10],
        },ensure_ascii=False)[:11000])
    core=next(r for r in all_reports if r["plugin"]=="KR12.6_CORE")
    known=[r for r in core["records"] if r["id"]=="1341756011233729353" and r["topic"]=="제국 교단에 가입"]
    if len(known)!=1 or known[0]["native_parser_status"]!="PARSER_NOT_DISCOVERED":
        raise ValueError("Known Lalatia defect not reproduced by full native C++ parser")
    summary={
      "status":"NATIVE_PARSER_VERIFIED_CANDIDATES_NOT_PLAYTESTED",
      "scope_count":len(all_reports),
      "tested":sum(r["tested"] for r in all_reports),
      "not_discovered":sum(r.get("unmatched",0) for r in all_reports),
      "matched":sum(r.get("matched",0) for r in all_reports),
      "known_lalatia_case_reproduced":True,
      "per_mod":[{k:v for k,v in r.items() if k!="records"} for r in all_reports],
      "limitations":["Cannot assert any flagged row is a quest-blocker without original topic/actor/SCVR/journal/load-order verification",
                     "Sidecar TOP MRK from current repository release snapshot, not from a reporter's installed game",
                     "Only HIGH/MEDIUM heuristic candidates are natively checked, not every INFO; lexical filter is conservative."],
    }
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps({"summary":summary,"detail":all_reports},ensure_ascii=False,indent=2),encoding="utf-8")
    print("NATIVE_TOPIC_SUMMARY="+json.dumps(summary,ensure_ascii=False)[:14000])


if __name__=="__main__":
    main()
