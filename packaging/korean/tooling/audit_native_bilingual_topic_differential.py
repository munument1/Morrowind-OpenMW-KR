#!/usr/bin/env python3
"""Read-only source-English -> Korean native topic discovery differential.

For *mapped* regional OpenMW topic IDs only, compare the same INFO English and
Korean responses through the compiled OpenMW-KR parser. An English-matched
topic absent in Korean is a translation discovery regression candidate, NOT
an automatically confirmed broken quest. The tool never modifies translations,
binary ESM/ESP, TOP/MRK/JRN, saves or Nexus releases.
"""
import argparse
import collections
import json
import tempfile
from pathlib import Path

from audit_cross_mod_topic_gaps import build_regional,regional_datasets
from verify_kr5_links import inspect

STEM="Morrowind_Korean_ReTranslation"
HIGH_CUE=("join","quest","missions","task","rank","advance","guild","contract","agree","help","promotion","duties","order","pledge","work","initiate")
KO_HIGH=("가입","승진","승급","입단","의뢰","임무","계약","맹세","수락","선택","일거리","봉사","결정")


def scan_one(name,folder,source,overlay,stem,root,runner,max_reported=2000):
    mrk,top,rows,provenance=build_regional(name,folder,source,overlay,stem,root)
    if "RebirthCompat" in name:
        folder_sidecar=root/"translations/openmw-kr"/{"Cyr_Main":"cyr-main/26.09a","Sky_Main":"sky-main/26.09a"}[stem]
    else:folder_sidecar=folder
    korean_top=(folder_sidecar/(stem+".top")).read_bytes()
    korean_mrk=(folder_sidecar/(stem+".mrk")).read_bytes()
    topics=sorted(mrk)
    if not topics:
        return {"plugin":name,"rows":0,"error":"no mapped regional topics"}
    # Both parsers receive the exact same list of original English DIAL IDs,
    # preventing a missing target from being disguised by changing the test topic pool.
    with tempfile.TemporaryDirectory(prefix="kr-native-bilingual-") as d:
        en_folder=Path(d)/"english";ko_folder=Path(d)/"korean"
        en_folder.mkdir();ko_folder.mkdir()
        for extension in ("top","mrk","cel","jrn"):
            (en_folder/(STEM+"."+extension)).write_bytes(b"")
            (ko_folder/(STEM+"."+extension)).write_bytes(
                korean_top if extension=="top" else korean_mrk if extension=="mrk" else b"")
        by_key={}
        for idx,r in enumerate(rows):
            english=r.get("en")
            korean=r.get("ko")
            if not isinstance(english,str) or not isinstance(korean,str) or not english or not korean:
                continue
            key=f"{idx}:{r['id']}"
            by_key[key]=r
        packed=list(by_key.items())
        tested=0;en_link_occurrences=0;ko_link_occurrences=0;lost_total=0;gained_total=0
        lost_detail=[];gained_samples=[];english_linked_infos=0;uncertain=collections.Counter()
        unique_missing=collections.Counter()
        for start in range(0,len(packed),1200):
            batch=packed[start:start+1200]
            en_entries=[(key,r["en"]) for key,r in batch]
            ko_entries=[(key,r["ko"]) for key,r in batch]
            try:
                english=inspect(runner,en_folder,en_entries,topics,True,discovery=True)
                korean=inspect(runner,ko_folder,ko_entries,topics,True,discovery=True)
            except Exception as e:
                raise RuntimeError(f"OpenMW parser failed for {name} batch offset {start}: {e}")
            for key,r in batch:
                en_targets=set(t.casefold() for t in english[key]["targets"])
                ko_targets=set(t.casefold() for t in korean[key]["targets"])
                en_link_occurrences+=len(en_targets)
                ko_link_occurrences+=len(ko_targets)
                english_linked_infos+=bool(en_targets)
                tested+=1
                lost=en_targets-ko_targets
                gained=ko_targets-en_targets
                lost_total+=len(lost);gained_total+=len(gained)
                for target in sorted(lost):
                    # Match by canonical English DIAL ID (case-insensitive),
                    # retain sidecar-provided Korean keyword for manual triage.
                    english_topic=next((t for t in topics if t.casefold()==target),target)
                    keyword=mrk.get(english_topic,english_topic)
                    source=(r.get("en") or "")
                    ko=r.get("ko") or ""
                    context_flag=("Greeting" in str(r.get("parent") or "")) or any(w in source.lower() for w in HIGH_CUE)
                    known_language=any(w in keyword for w in KO_HIGH)
                    priority="HIGH_REVIEW" if context_flag and known_language else "MEDIUM_REVIEW" if context_flag or known_language else "LOW_REVIEW"
                    unique_missing[english_topic]+=1
                    uncertain[priority]+=1
                    if len(lost_detail)<max_reported:
                        lost_detail.append({
                          "plugin":name,
                          "row_key":r["id"],
                          "topic_parent":r.get("parent") or "",
                          "target_DIAL":english_topic,
                          "target_Korean_MRK":keyword,
                          "source_English":source[:650],
                          "translated_Korean":ko[:650],
                          "priority":priority,
                          "same_INFO_original_English_parser_discovers":True,
                          "same_INFO_Korean_parser_discovers":False,
                          "field_record_index":r.get("record_index"),
                          "field_subrecord_index":r.get("subrecord_index"),
                          "needs_filter_and_semantic_review":True
                        })
                if gained and len(gained_samples)<20:
                    gained_samples.append({"id":r["id"],"unexpected_Korean_topics":sorted(gained)[:20],
                                           "en":r["en"][:190],"ko":r["ko"][:190]})
        lost_detail.sort(key=lambda r:({"HIGH_REVIEW":0,"MEDIUM_REVIEW":1,"LOW_REVIEW":2}[r["priority"]],
                                       str(r["row_key"]),str(r["target_DIAL"])))
        return {
          "plugin":name,
          "source":str(folder),"rows_with_both_languages_tested":tested,
          "mapped_DIAL_topics":len(topics),
          "source_English_linked_INFOS":english_linked_infos,
          "English_discovered_edges":en_link_occurrences,
          "Korean_discovered_edges":ko_link_occurrences,
          "source_to_Korean_missing_edges":lost_total,
          "Korean_new_edges_not_in_English":gained_total,
          "missing_edges_by_priority":dict(uncertain),
          "missing_target_topics_top30":unique_missing.most_common(30),
          "missing_edges":lost_detail,
          "sample_limit":max_reported,
          "missing_edges_truncated":lost_total>max_reported,
          "gained_edges_first20":gained_samples,
          "provenance":provenance,
          "limitations":["Only topics with an explicit MRK mapping are included; held/ambiguous topics remain untested.",
             "English parser is the same OpenMW-KR keyword parser seeded with English DIAL IDs, not original game engine.",
             "Source English may match generic words that were not intended dialogue links.",
             "Actual NPC eligibility, quest journal state, original full ESM filter and load order not evaluated.",
             "The latest on-disk binary ESM is not available on GitHub; applies source-anchored translation overlays."],
        }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--repo",type=Path,required=True)
    p.add_argument("--runner",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    results=[]
    for name,folder,source,overlay,stem in regional_datasets(a.repo):
        r=scan_one(name,folder,source,overlay,stem,a.repo,a.runner)
        results.append(r)
        print("NATIVE_BILINGUAL_MOD="+json.dumps({
            "mod":name,
            "rows":r["rows_with_both_languages_tested"],
            "en_edges":r["English_discovered_edges"],
            "ko_edges":r["Korean_discovered_edges"],
            "lost":r["source_to_Korean_missing_edges"],
            "priority":r["missing_edges_by_priority"],
            "top_topics":r["missing_target_topics_top30"][:10],
            "high_examples":[{k:x[k] for k in ("row_key","topic_parent","target_DIAL","target_Korean_MRK","source_English","translated_Korean")}
                             for x in r["missing_edges"] if x["priority"]=="HIGH_REVIEW"][:12],
        },ensure_ascii=False)[:15000])
    summary={
      "status":"BILINGUAL_NATIVE_TOPIC_EDGE_DIFF_IS_REVIEW_EVIDENCE_NOT_GAMEPLAY_PROOF",
      "tested_plugin_count":len(results),
      "same_INFO_source_English_links":sum(r["English_discovered_edges"] for r in results),
      "same_INFO_Korean_links":sum(r["Korean_discovered_edges"] for r in results),
      "source_English_links_absent_Korean":sum(r["source_to_Korean_missing_edges"] for r in results),
      "priority_counts":dict(sum((collections.Counter(r["missing_edges_by_priority"]) for r in results),collections.Counter())),
      "scope":["mapped DIAL topics only; overlays 2026-11-02 applied; Rebirth compatch data considered"],
      "gameplay_tested":False,
    }
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps({"summary":summary,"reports":results},ensure_ascii=False,indent=2),encoding="utf-8")
    print("NATIVE_BILINGUAL_SUMMARY="+json.dumps(summary,ensure_ascii=False))


if __name__=="__main__":
    main()
