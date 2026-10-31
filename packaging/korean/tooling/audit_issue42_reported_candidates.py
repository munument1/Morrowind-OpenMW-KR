#!/usr/bin/env python3
"""Source-anchored, read-only triage of issue #42 against published KR12.3.1.

Counts are *candidates*, not proven broken quests or player-accessible topics.
Requires the published release ZIP and the reporter's public Gist JSON.
Never edits ESM, ESP, .top, .mrk, source game files or saves.
"""
import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from audit_kr12_fighters_topic_candidates import package, dialogue, chunks, dec, sidecar

EXPECTED_ESP_SHA = "c0cb2f5702da067e11820e5a11ffb4b758ea28e101779fc43a721072783ed253"
CATEGORIES = {
    "동사형 링크 글자 뒤 어미": 22,
    "명사 뒤 서술격·호격 등": 65,
    "명사 + 하다·되다 등 동사": 47,
    "합성어·그 밖의 끝말": 85,
    "다른 명시 링크 안에 있음": 153,
    "앞 낱말에 붙음(합성어)": 53,
    "기타": 1,
}
LINK_RE = re.compile(r"@([^@#]*)#")
SCRIPT_RE = re.compile(r'\bAddTopic\s+("[^"]+"|[A-Za-z0-9_]+)', re.I)
HANGUL_RE = re.compile(r"[가-힣]")


def read_csv(gist, filename):
    f = gist["files"][filename]
    if f.get("truncated") or not isinstance(f.get("content"), str):
        raise ValueError("Gist CSV is missing or truncated: " + filename)
    source = f["content"].lstrip("\ufeff")
    rows = list(csv.DictReader(io.StringIO(source)))
    if not rows:
        raise ValueError("Empty Gist CSV: " + filename)
    return rows


def game_script_mentions(esp: bytes):
    """Inspect only script text actually present in Korean ESP; not original masters."""
    references = defaultdict(list)
    parent = None
    for record_type, blob in chunks(esp, 16):
        fields = dict(chunks(blob, 8))
        if record_type == b"DIAL":
            parent = dec(fields.get(b"NAME", b""))
            continue
        if record_type == b"SCPT" and b"SCTX" in fields:
            script = dec(fields.get(b"SCHD", b""))[:64]  # provenance only
            body = dec(fields[b"SCTX"])
            owner = {"record": "SCPT", "script": script}
        elif record_type == b"INFO" and b"BNAM" in fields:
            body = dec(fields[b"BNAM"])
            owner = {"record": "INFO.BNAM",
                     "DIAL": parent, "INAM": dec(fields.get(b"INAM", b""))}
        else:
            continue
        for match in SCRIPT_RE.finditer(body):
            topic = match.group(1).strip('"').strip()
            references[topic.casefold()].append({**owner, "argument": topic})
    return references


def named_aliases(data):
    return sidecar(data["top"]), sidecar(data["mrk"])


def inspect(data, gist):
    actual_sha = hashlib.sha256(data["esp"]).hexdigest()
    if actual_sha != EXPECTED_ESP_SHA:
        raise ValueError("Must use unchanged published KR12.3.1 ESP: " + actual_sha)
    topics, infos = dialogue(data["esp"])
    by_id = defaultdict(list)
    for row in infos:
        by_id[row["info"]].append(row)
    top, mrk = named_aliases(data)
    raw_misses = read_csv(gist, "morrowind_link_misses.csv")
    raw_unlearnable = read_csv(gist, "morrowind_unlearnable_topics.csv")
    if len(raw_misses) != 426 or len(raw_unlearnable) != 71:
        raise ValueError("Reporter lists changed; review new baseline before proceeding")
    if Counter(x["유형"] for x in raw_misses) != CATEGORIES:
        raise ValueError("Reporter category counts changed unexpectedly")
    scripts = game_script_mentions(data["esp"])
    detail_misses = []
    inconsistencies = Counter()
    for item in raw_misses:
        info_id = item["INFO ID"].strip()
        texts = by_id.get(info_id, [])
        token = item["링크 글자(.mrk)"] or item["토픽"]
        full = []
        for row in texts:
            text = row["text"]
            term = token in text
            links = [(m.group(1), top.get(m.group(1), m.group(1))) for m in LINK_RE.finditer(text)]
            # The reporter's excerpt may show a word, not the full entity.
            full.append({"DIAL": row["parent"], "actor": row["actor"],
                         "faction": row["faction"], "kind": row["kind"],
                         "keyword_in_full_text": term,
                         "explicit_links": [{"phrase": a, "target": b} for a,b in links],
                         "full_source_response": text})
        if not full:
            inconsistencies["INFO_missing_from_published_ESP"] += 1
        elif not any(r["keyword_in_full_text"] for r in full):
            inconsistencies["keyword_missing_from_full_source"] += 1
        detail_misses.append({
            "reported_type": item["유형"],
            "topic": item["토픽"],
            "keyword": token, "suffix": item["토픽 뒤 끝말"],
            "INFO": info_id,
            "reported_actor": item["말하는 NPC"],
            "reporter_other_link_count": item["같은 NPC의 다른 대사에서 링크된 수"],
            "candidate_not_proven_bug": True,
            "source_anchored": full,
        })

    unlearnable = []
    for item in raw_unlearnable:
        name = item["토픽"]
        normalized = name.casefold()
        source_script = scripts.get(normalized, [])
        aliased_to = sorted(key for key, value in top.items() if value == name)
        elsewhere = [
            {"INAM": row["info"], "actor": row["actor"], "DIAL": row["parent"]}
            for row in infos if (name in row["text"] or any(tag == name for tag in
               (m.group(1) for m in LINK_RE.finditer(row["text"]))))
        ][:60]
        unlearnable.append({
            "reported_class": item["구분"],
            "topic": name, "has_DIAL": name in topics,
            "answer_conditions_reported": item["답이 있는 NPC·조건"],
            "script_AddTopic_in_translated_ESP": source_script[:30],
            "script_AddTopic_count_in_translated_ESP": len(source_script),
            "explicit_aliases_targeting_topic": aliased_to[:30],
            "mentions_in_translated_ESP_sample": elsewhere,
            "mentions_in_translated_ESP_count_capped": len(elsewhere),
            "not_proven_unlearnable": True,
        })

    # Review concrete misplaced/semantically surprising explicit links before editing.
    observed_tags = []
    targeted = {"말입니까?", "이나 다른", "는 제국", "말"}
    for row in infos:
        source = row["text"]
        for m in LINK_RE.finditer(source):
            label = m.group(1).replace("\x7f", "")
            if label not in targeted:
                continue
            prev = source[max(0, m.start()-12):m.start()]
            nxt = source[m.end():m.end()+32]
            observed_tags.append({
                "INFO": row["info"], "DIAL": row["parent"], "actor": row["actor"],
                "label": label, "top_target": top.get(label, label),
                "target_DIAL_exists": top.get(label, label) in topics,
                "preceding": prev, "following": nxt,
                "full_text": source[:1200]
            })

    wrong_alias = []
    for label in ("마법부여사 아우데니안",
                  "마법부여사 아우데니안 발리우스",
                  "텔바니 마법부여사 아우데니안 발리우스"):
        wrong_alias.append({
            "alias": label, "published_target": top.get(label),
            "expected_target": "아우데니안 발리우스",
            "expected_target_DIAL_present": "아우데니안 발리우스" in topics,
            "target_mismatch": top.get(label) != "아우데니안 발리우스",
        })

    explicit = []
    for row in infos:
        source = row["text"]
        for m in LINK_RE.finditer(source):
            label = m.group(1).replace("\x7f", "")
            target = top.get(label, label)
            prev = source[m.start()-1:m.start()] if m.start() else ""
            nxt = source[m.end():m.end()+1]
            if not (HANGUL_RE.fullmatch(prev) or HANGUL_RE.fullmatch(nxt)):
                continue
            explicit.append({
                "INAM": row["info"], "DIAL": row["parent"], "actor": row["actor"],
                "label": label, "resolved_target": target,
                "starts_inside_Hangul": bool(HANGUL_RE.fullmatch(prev)),
                "ends_inside_Hangul": bool(HANGUL_RE.fullmatch(nxt)),
                "context": source[max(0,m.start()-35):min(len(source),m.end()+40)],
                "needs_individual_manual_review": True
            })

    investigated_fragments = [
        "@설원#곰", "@설원#늑대", "정@말#", "@말입니까?#",
        "@이나 다른#", "@는 제국#", "@가 제국#"
    ]
    fragment_evidence = {}
    for needle in investigated_fragments:
        hits = [
            {"INFO": row["info"], "DIAL": row["parent"], "actor": row["actor"],
             "context": row["text"][max(0,row["text"].find(needle)-35):
                                     row["text"].find(needle)+len(needle)+55]}
            for row in infos if needle in row["text"]
        ]
        fragment_evidence[needle] = {"count":len(hits),"examples":hits[:14]}
    relevant_topic_names = [
        "설원곰", "설원늑대", "설원", "제국", "임페리얼",
        "말", "대화", "은신", "아우데니안 발리우스"
    ]
    topic_evidence = {
        name: {"present_DIAL": name in topics,
               "top_alias_target": top.get(name),
               "mrk_keyword": mrk.get(name)}
        for name in relevant_topic_names
    }

    result = {
        "status": "READ_ONLY_LEXICAL_TRIAGE_NO_GAMEPLAY_OR_MASTER_COMPARISON",
        "source": "published KR12.3.1 ESP and public issue #42 Gist",
        "source_esp_sha256": actual_sha,
        "source_top_sha256": hashlib.sha256(data["top"]).hexdigest(),
        "investigated_fragment_evidence": fragment_evidence,
        "relevant_topic_evidence": topic_evidence,
        "topic_count": len(topics), "info_count": len(infos),
        "reported_link_rows": len(raw_misses),
        "reported_link_types": dict(Counter(x["유형"] for x in raw_misses)),
        "reported_topic_rows": len(raw_unlearnable),
        "source_anchor_discrepancies": dict(inconsistencies),
        "translated_esp_AddTopic_text_only": {
            "topics_with_arguments": len(scripts),
            "not_definitive_without_original_masters": True,
        },
        "unlearnable_with_script_refs_in_translated_esp": [
            {"topic": x["topic"], "count": x["script_AddTopic_count_in_translated_ESP"]}
            for x in unlearnable if x["script_AddTopic_count_in_translated_ESP"] > 0
        ],
        "confirmed_sidecar_wrong_aliases": wrong_alias,
        "explicit_tags_touching_Hangul_count": len(explicit),
        "explicit_tags_start_inside_Hangul_count": sum(x["starts_inside_Hangul"] for x in explicit),
        "suspect_explicit_tag_rows": observed_tags[:150],
        "explicit_tags_touching_Hangul_examples": explicit[:300],
        "link_candidates": detail_misses,
        "reported_unlearnable_topics": unlearnable,
        "reported_source_keyword_mismatch_examples": [
            {"INFO": x["INFO"], "topic": x["topic"], "keyword": x["keyword"],
             "record": x["source_anchored"][0]["full_source_response"][:500]}
            for x in detail_misses
            if x["source_anchored"] and not any(
                y["keyword_in_full_text"] for y in x["source_anchored"])
        ][:40],
        "limitations": [
            "No English original Morrowind/Tribunal/Bloodmoon master data; not a proof of quest progression.",
            "SCPT/INFO.BNAM in the translation ESP is only an incomplete subset of runtime scripts.",
            "No complete load order, journal stage filters or NPC dynamic availability.",
            "No player gameplay testing; no dataset or save was rewritten."
        ],
    }
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zip", required=True, type=Path)
    ap.add_argument("--gist", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    data = package(args.zip)
    report = inspect(data, json.loads(args.gist.read_text(encoding="utf-8")))
    if args.output.exists():
        raise ValueError("Output report already exists; new-only")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for key in ("investigated_fragment_evidence", "relevant_topic_evidence",
                "topic_count", "info_count", "reported_link_rows",
                "reported_topic_rows", "source_anchor_discrepancies",
                "unlearnable_with_script_refs_in_translated_esp",
                "confirmed_sidecar_wrong_aliases",
                "explicit_tags_touching_Hangul_count",
                "explicit_tags_start_inside_Hangul_count",
                "suspect_explicit_tag_rows",
                "reported_source_keyword_mismatch_examples"):
        print(key, json.dumps(report[key], ensure_ascii=False))
    print("OUTPUT", args.output)


if __name__ == "__main__":
    main()
