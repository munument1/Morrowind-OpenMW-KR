#!/usr/bin/env python3
"""Isolated, read-only audit of KR12.6 guild entry INFO links.

Checks exact (DIAL, INFO.INAM), loaded NPC/faction selectors, target INFO
scripts, known TOP aliases, and tests before/after using the actual native
OpenMW Korean KeywordSearch. Only emits JSON proposals. Never writes ESP/ESM,
installs mods, or publishes a release.

A patched phrase passing parser QA is NOT proof that the target is offered in
the player's specific quest state; INFO/SCVR runtime filtering is not simulated.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

from audit_cross_mod_topic_gaps import record_chunks, subs, sha, sidecar
from verify_kr5_links import inspect

STEM = "Morrowind_Korean_ReTranslation"
PAT = re.compile(r"@([^@#]*)#")
# Hand-reviewed high priority source INFO+target pair. Intentional exclusions:
# same-DIAL self mentions, generic rank advice, one-off faction rumours.
SPECS = [
    ("1341756011233729353", "평신도 회원", "제국 교단에 가입", "Lalatia route / lay membership invitation"),
    ("13288348632198840", "전사 길드", "전사 길드에 가입", "Hrundi introductory invitation"),
    ("2435795662798020478", "전사 길드", "전사 길드에 가입", "Eydis introductory invitation"),
    ("1403130214698924047", "승진", "도둑 길드에 가입", "Thieves Guild promotion asks to join"),
    ("22990247762784528944", "승진", "텔바니 가문에 가입", "Telvanni promotion asks to join"),
    ("41295659805015760", "임무", "마법사 길드에 가입", "Mages Guild duties asks to join"),
    ("571631012022329261", "레도란 가문에 가입", "레도란 가문에 가입", "Neminda topic, may be a self-link"),
    ("24498209033079022986", "전사 길드", "전사 길드에 가입", "Fighters Guild generic gate"),
    ("26291148261399015653", "전사 길드", "전사 길드에 가입", "Fighters Guild alternate generic gate"),
    ("27028129091479724559", "발모라 마법사 길드", "마법사 길드에 가입", "Balmora Mages invitation"),
]


def dec(raw:bytes)->str:
    return raw.rstrip(b"\0").decode("utf-8",errors="replace")


def visible(text):
    return PAT.sub(lambda m: m.group(1).replace("\x7f", ""),text).replace("\x7f","")


def extract(raw):
    bykey=collections.defaultdict(list)
    topics=set()
    topic_infos=collections.defaultdict(list)
    parent=None;kind=None
    for i,(tag,payload) in enumerate(record_chunks(raw)):
        if tag not in (b"DIAL",b"INFO"):continue
        items=subs(payload)
        fs=dict(items)
        if tag==b"DIAL":
            parent=dec(fs.get(b"NAME",b""))
            kind=fs.get(b"DATA",b"\xff")[:1]
            if kind==b"\0" and b"DELE" not in fs:topics.add(parent)
        elif tag==b"INFO":
            row={
                "record_index":i,
                "parent":parent,
                "kind":kind.hex() if kind is not None else None,
                "inamed":dec(fs.get(b"INAM",b"")),
                "actor":dec(fs.get(b"ONAM",b"")),
                "faction":dec(fs.get(b"FNAM",b"")),
                "race":dec(fs.get(b"RNAM",b"")),
                "class":dec(fs.get(b"CNAM",b"")),
                "cell":dec(fs.get(b"ANAM",b"")),
                "text":dec(fs.get(b"NAME",b"")),
                "script":dec(fs.get(b"BNAM",b"")),
                "info_other_conditions":[
                    {"tag":key.decode("ascii","replace"),"hex":value.hex()}
                    for key,value in items if key in (
                        b"SCVR",b"QSTI",b"QSTN",b"QSTF",b"DATA",b"INTV",b"FLTV"
                    )
                ],
                "name_sha256":sha(fs.get(b"NAME",b"")),
                "subrecord_types":[key.decode("ascii","replace") for key,_ in items],
            }
            bykey[(parent,row["inamed"])].append(row)
            topic_infos[parent].append(row)
    return topics,bykey,topic_infos


def safe_tag(text,topic):
    marker="@"+topic+"#"
    if marker in text:
        return None,"explicit_tag_already_present"
    occurrences=[m.start() for m in re.finditer(re.escape(topic),text)]
    if not occurrences:
        return None,"displayed_topic_phrase_absent"
    link_intervals=[(m.start(),m.end()) for m in PAT.finditer(text)]
    eligible=[]
    for start in occurrences:
        end=start+len(topic)
        if any(a<end and start<b for a,b in link_intervals):
            continue
        if start>0 and "가"<=text[start-1]<="힣":
            continue
        eligible.append(start)
    if not eligible:
        return None,"topic_phrase_inside_another_link_or_word"
    # Prefer phrase immediately followed by inflected Korean verbs.
    question_positions=[p for p in eligible if "?" in text[p:p+len(topic)+27] or "？" in text[p:p+len(topic)+27]]
    if len(question_positions)!=1:
        return None,("multiple_question_candidates" if len(question_positions)>1
            else "not_direct_question_or_ambiguous")
    start=question_positions[0]
    next_text=text[:start]+marker+text[start+len(topic):]
    if visible(text)!=visible(next_text):
        raise ValueError("Displayed Korean dialogue changed")
    return next_text,None


def classify_edge(row,target_infos):
    actor=row["actor"].casefold()
    faction=row["faction"].casefold()
    direct=[r for r in target_infos if actor and r["actor"].casefold()==actor]
    same_faction=[r for r in target_infos if faction and r["faction"].casefold()==faction]
    general=[r for r in target_infos if not r["actor"] and not r["faction"]]
    join=[r for r in direct+same_faction+general if re.search(r"\bPCJoinFaction\b",r["script"],re.I)]
    choice=[r for r in direct+same_faction+general if re.search(r"\bChoice\b",r["script"],re.I)]
    return {
        "same_actor_target_info":len(direct),
        "same_faction_target_info":len(same_faction),
        "generic_target_info":len(general),
        "script_PCJoinFaction_on_relevant_target":bool(join),
        "script_Choice_on_relevant_target":bool(choice),
        "sample_target_join_script":[r["script"][:450] for r in join[:2]],
        "sample_target_choice_script":[r["script"][:450] for r in choice[:2]],
        "target_INFO_count":len(target_infos),
        "warnings":["Actor/faction match is not sufficient: source and target SCVR, PCFaction, journal state, dialogue priorities not evaluated."]
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--zip",type=Path,required=True)
    p.add_argument("--runner",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    with zipfile.ZipFile(a.zip) as z:
        base=next(name[:-len(STEM+".esp")] for name in z.namelist() if name.endswith(STEM+".esp"))
        esp=z.read(base+STEM+".esp")
        topraw=z.read(base+STEM+".top")
        mrkraw=z.read(base+STEM+".mrk")
    if sha(esp)!="c52a5355752ef0be93fadeca9c95ca00d7cad808f713ce92a624a67d0cc277df":
        raise ValueError("Not the official KR12.6 ESP")
    topics,bykey,topic_infos=extract(esp)
    mapping,conflicts=sidecar(topraw)
    if conflicts:raise ValueError("Ambiguous TOP alias conflict")
    before=[]
    after=[]
    evidence=[]
    for index,(inamed,parent,target,note) in enumerate(SPECS):
        source=bykey.get((parent,inamed),[])
        if len(source)!=1: raise ValueError(f"Missing or duplicate INFO: {parent}/{inamed}/{len(source)}")
        row=source[0]
        if parent not in topics or target not in topics or row["kind"]!="00":
            raise ValueError(f"Unexpected non-topic DIAL or missing topic: {parent}/{target}")
        proposed,blocker=safe_tag(row["text"],target)
        if mapping.get(target,target)!=target:
            blocker="TOP_redirects_explicit_label"
            proposed=None
        if parent==target:
            # No claim that self-mentions must be clickable.
            blocker="self_topic_needs_manual_review"
            proposed=None
        if row["faction"]=="" and row["actor"]=="":
            # Generic guild question may already be activated by greeting or via script.
            confidence="MODERATE"
        else:
            confidence="HIGH_SOURCE_REVIEW" if "?" in row["text"] else "MODERATE"
        record={
          "INFO_ID":inamed,"source_DIAL":parent,"target_DIAL":target,
          "case":note,"record_index":row["record_index"],
          "actor":row["actor"],"faction":row["faction"],
          "original_INFO_NAME":row["text"],
          "expected_source_NAME_sha256":row["name_sha256"],
          "proposed_INFO_NAME":proposed,"candidate_blocker":blocker,
          "source_conditions":row["info_other_conditions"],
          "source_result_script":row["script"],
          "target_evidence":classify_edge(row,topic_infos[target]),
          "confidence":confidence,
        }
        if proposed:
            record["proposed_INFO_NAME_sha256"]=sha(proposed.encode("utf-8"))
            if visible(proposed)!=visible(row["text"]):
                raise ValueError("A proposed change altered visible text")
        evidence.append(record)
        before.append((f"probe-{index}",row["text"]))
        after.append((f"probe-{index}",proposed if proposed else row["text"]))
    with tempfile.TemporaryDirectory(prefix="kr126_guild_entry_") as tmp:
        folder=Path(tmp)
        for extension,data in (("top",topraw),("mrk",mrkraw),("cel",b""),("jrn",b"")):
            (folder/(STEM+"."+extension)).write_bytes(data)
        baseline=inspect(a.runner,folder,before,sorted(topics),True,discovery=True)
        patched=inspect(a.runner,folder,after,sorted(topics),True,discovery=True)
    for i,item in enumerate(evidence):
        target=item["target_DIAL"].casefold()
        b={x.casefold() for x in baseline[f"probe-{i}"]["targets"]}
        aft={x.casefold() for x in patched[f"probe-{i}"]["targets"]}
        item["native_source_expected_target_found"]=target in b
        item["native_candidate_expected_target_found"]=target in aft
        item["native_before_targets"]=baseline[f"probe-{i}"]["targets"]
        item["native_after_targets"]=patched[f"probe-{i}"]["targets"]
        item["native_unrelated_topic_targets_preserved"]=(b-{target})==(aft-{target})
        item["full_NPC_quest_state_verified"]=False
        if item["proposed_INFO_NAME"]:
            if target in b or target not in aft or not item["native_unrelated_topic_targets_preserved"]:
                raise ValueError("Unsafe proposed link: "+item["INFO_ID"])
    summary={
      "status":"NATIVE_TESTED_ISOLATED_LINK_CANDIDATES_NOT_RELEASED",
      "core_esp_sha256":sha(esp),
      "source_INFO_checked":len(evidence),
      "proposals_native_passed":sum(bool(e["proposed_INFO_NAME"]) for e in evidence),
      "proposals_skipped":sum(not bool(e["proposed_INFO_NAME"]) for e in evidence),
      "unchanged_source_ESP":True,
      "native_parser_used":True,
      "gameplay_tested":False,
      "limitations":[
         "A native keyword link parser success does not imply any actor or player can open the target INFO.",
         "All DIAL topics were seeded as known; real actor-known topics and quest conditions require separate tests.",
         "These are proposals only, not edits to the official KR12.6 release.",
       ],
    }
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps({"summary":summary,"cases":evidence},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("GUILD_ENTRY_REVIEW_SUMMARY="+json.dumps(summary,ensure_ascii=False))
    for e in evidence:
        print("GUILD_ENTRY_REVIEW_CASE="+json.dumps({
           "id":e["INFO_ID"],"dial":e["source_DIAL"],"target":e["target_DIAL"],"actor":e["actor"],"faction":e["faction"],
           "proposed":e["proposed_INFO_NAME"],"blocked":e["candidate_blocker"],
           "before":e["native_source_expected_target_found"],"after":e["native_candidate_expected_target_found"],
           "target":e["target_evidence"],"conditions_count":len(e["source_conditions"]),
        },ensure_ascii=False)[:5000])


if __name__=="__main__":
    main()
