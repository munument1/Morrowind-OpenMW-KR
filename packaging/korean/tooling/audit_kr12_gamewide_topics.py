#!/usr/bin/env python3
"""Read-only, game-wide KR12.2 dialogue topic audit (never auto-fixes ESM/ESP).

Inspect every DIAL/INFO incl. faction/quest journals, not just Fighters Guild.
Unlinked candidates are lexical possibilities, NOT proven gameplay bugs.
"""
import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from audit_kr12_fighters_topic_candidates import package, dialogue, dec, hangul

STEM = "Morrowind_Korean_ReTranslation"
RE_HANGUL = re.compile(r"[가-힣]+")
RE_QUOTED = re.compile(r'"([^"]+)"')
RE_TAG = re.compile(r"@[^@#]*#")


def read_cpp_endings(source):
    """Extract the actual runtime allowlists, rather than hardcode guesses."""
    endings = set()
    contextual = set()
    for declaration in ("endings", "extendedSuffixes", "contextualNounEndings"):
        pattern = r"constexpr std::string_view " + declaration + r"\[\] = \{(.*?)\};"
        match = re.search(pattern, source, re.S)
        if match is None:
            raise ValueError("runtime missing suffix table: " + declaration)
        if declaration == "contextualNounEndings":
            contextual.update(RE_QUOTED.findall(match.group(1)))
        else:
            endings.update(RE_QUOTED.findall(match.group(1)))
    return endings, contextual


def raw_sidecar(data):
    return [(key, value) for line in data.decode("utf-8-sig").splitlines()
            if "\t" in line for key, value in [line.split("\t", 1)]]


def quote_ambiguities(infos, names, phrases, keywords):
    """Group known quotative issues into actor/journal provenance (not factions guessed from prose)."""
    detail = []
    for row in infos:
        text = row["text"]
        if not text:
            continue
        for word in re.finditer(r"([가-힣][가-힣0-9'·-]*)(이라는|라는|이란|란)(?![가-힣])", text):
            # Recorded as a discovery signal only; precise keyword matching is below.
            key = word.group(1)
            if key not in keywords:
                continue
            b = word.start()
            if b and hangul(text[b - 1]):
                continue
            if b and text[b - 1] == "@":
                continue
            detail.append({"kind":row["kind"],"parent":row["parent"],
                           "actor":row["actor"],"faction":row["faction"],
                           "topic":key, "suffix":word.group(2),"info":row["info"],
                           "context":text[max(0,b-35):word.end()+45]})
    return detail


def inspect(data, cpp_source, limit=500):
    topics, infos = dialogue(data["esp"])
    # KeywordSearch::seed(topicKeyword(DIAL.NAME), DIAL.NAME)
    mrk_rows = raw_sidecar(data["mrk"])
    top_rows = raw_sidecar(data["top"])
    keywords = {}
    for key, value in mrk_rows:
        keywords.setdefault(key, value)
    aliases = {}
    for key, value in top_rows:
        aliases.setdefault(key, value)
    reverse = defaultdict(list)
    for topic in sorted(topics):
        keyword = keywords.get(topic, topic)
        if keyword and len(keyword) >= 2 and hangul(keyword[0]) and hangul(keyword[-1]):
            reverse[keyword[0]].append((keyword, topic))
    for key in reverse:
        reverse[key].sort(key=lambda t: -len(t[0]))

    permitted, contextual = read_cpp_endings(cpp_source)
    source_groups, unhandled, covered = Counter(), [], Counter()
    missing_by_suffix, missing_by_topic, missing_by_actor, missing_by_parent = Counter(), Counter(), Counter(), Counter()
    covered_by_suffix = Counter()
    short_ambiguous = 0
    for row in infos:
        text = row["text"]
        if not text:
            continue
        masked = [(x.start(), x.end()) for x in RE_TAG.finditer(text)]
        for idx, char in enumerate(text):
            choices = reverse.get(char)
            if not choices or (idx and hangul(text[idx-1])):
                continue
            if idx and text[idx-1] in "-·‐‑–—" and idx > 1 and hangul(text[idx-2]):
                continue
            best = None
            for keyword, topic in choices:
                end = idx + len(keyword)
                if end >= len(text) or not hangul(text[end]):
                    continue
                if text.startswith(keyword, idx):
                    best = (keyword, topic, end)
                    break
            if best is None:
                continue
            keyword, topic, end = best
            if any(start <= idx < finish or idx < start < end for start, finish in masked):
                continue
            tail = RE_HANGUL.match(text, end).group()
            if not tail:
                continue
            if (tail in permitted or (len(keyword) >= 2 and tail in contextual)
                    or (tail.startswith("들") and tail[1:] in permitted)):
                covered[topic] += 1
                covered_by_suffix[tail] += 1
                continue
            # Single-character topic prefixes and embedded words produce excessive
            # false positives; preserve a separate count, never mark as fixable.
            if len(keyword) < 2:
                short_ambiguous += 1
                continue
            source_kind = "journal" if row["kind"] == 4 else ("npc_dialogue" if row["kind"] in (0,2,3) else "other")
            source_groups[source_kind] += 1
            missing_by_suffix[tail] += 1
            missing_by_topic[topic] += 1
            missing_by_actor[row["actor"] or "(unspecified)"] += 1
            missing_by_parent[row["parent"] or "(unknown)"] += 1
            if len(unhandled) < limit:
                unhandled.append({
                    "INFO": row["info"], "DIAL":row["parent"],"kind":row["kind"],
                    "actor":row["actor"],"faction":row["faction"],
                    "topic":topic,"keyword":keyword,"suffix":tail,
                    "context":text[max(0,idx-40):min(len(text),end+len(tail)+50)],
                    "status":"review_only_not_confirmed_bug"
                })
    # Verify cross-reference integrity without claiming that every unreferenced
    # alias is a bug (aliases can exist for deleted or external-mod topics).
    conflicts = []
    grouped = defaultdict(set)
    for k,v in top_rows:
        grouped[k].add(v)
    for key, values in grouped.items():
        if len(values)>1:
            conflicts.append({"alias":key,"targets":sorted(values)})
    unmapped_mrk = sorted({key for key, value in mrk_rows if key not in topics})
    bad_target_top = sorted({value for key, value in top_rows if value not in topics})
    report = {
        "status":"GAMEWIDE_LEXICAL_AND_SIDECAR_TRIAGE_NOT_GAMEPLAY_QA",
        "scope":"ALL_DIAL_INFO_IN_RELEASED_KR12.2",
        "topic_count":len(topics),
        "info_count":len(infos),
        "allowed_suffix_count":len(permitted),
        "contextual_noun_suffix_count":len(contextual),
        "existing_accepted_suffix_matches":sum(covered.values()),
        "additional_missing_suffix_candidates":sum(missing_by_suffix.values()),
        "missing_by_record_kind":dict(source_groups),
        "top_unhandled_suffixes":missing_by_suffix.most_common(80),
        "top_candidate_topics":missing_by_topic.most_common(50),
        "top_candidate_actors":missing_by_actor.most_common(50),
        "top_candidate_dialogues":missing_by_parent.most_common(50),
        "top_accepted_suffixes":covered_by_suffix.most_common(30),
        "sidecar_alias_conflicts":conflicts,
        "top_target_not_in_translation_dial_count":len(bad_target_top),
        "top_target_not_in_translation_dial_examples":bad_target_top[:40],
        "mrk_key_not_in_translation_dial_count":len(unmapped_mrk),
        "mrk_key_not_in_translation_dial_examples":unmapped_mrk[:40],
        "examples_capped":limit,
        "candidate_examples":unhandled,
        "limitations":["No full original English master or plugin load order",
                       "No quest/NPC condition checks; candidate does not imply clickable in game",
                       "Korean words can merely start with a topic; no blanket replacements",
                       "Journal phrases might not be current NPC dialogue"],
    }
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip",required=True,type=Path)
    p.add_argument("--cpp",type=Path,default=Path("apps/openmw/mwdialogue/keywordsearch.cpp"))
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--examples",type=int,default=500)
    args=p.parse_args()
    data=package(args.zip)
    if not 0 <= args.examples <= 10000:
        raise ValueError("--examples must be 0..10000")
    result=inspect(data,args.cpp.read_text(encoding="utf-8"),args.examples)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    concise={key:value for key,value in result.items() if key not in ("candidate_examples", "limitations")}
    print(json.dumps(concise,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
