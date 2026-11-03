#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zero-extra-link source-corpus suffix subset, experiment only.

The accepted suffixes below recovered original native topic links in the
published 157,475-INFO source-to-Korean corpus without introducing even one
target absent from the matching English source.
Run the full independent comparison before proposing a real engine change.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_trial_safe_korean_boundaries.py keywordsearch.cpp")
path = Path(sys.argv[1])
source = path.read_text(encoding="utf8")
needle = "        if (isEnding(suffix))\n            return true;\n"
assert source.count(needle) == 1, "Unexpected OpenMW source baseline"
addition = """
        // Source-corpus-verified grammatical endings for multi-syllable nouns.
        // These were chosen by comparing old and candidate C++ parsers across
        // every uniquely source-mapped KR INFO, not by blanket auto-linking.
        // Avoid short/general endings that produced extra links (이니, 대로,
        // 이고, 일, 님, 이여, 이며, 만큼, 에서도).
        if (keyword.size() >= 6)
        {
            constexpr std::string_view corpusVerifiedNounEndings[] = {
                "에서의", "로부터", "예요", "뿐", "와도", "였던",
                "치고는", "님을", "뿐이다", "님의", "님은", "과도", "님이"
            };
            if (std::find(std::begin(corpusVerifiedNounEndings),
                    std::end(corpusVerifiedNounEndings), suffix)
                    != std::end(corpusVerifiedNounEndings))
                return true;
        }
"""
path.write_text(source.replace(needle, needle+addition), encoding="utf8")
print("SAFE_EXPERIMENTAL_BOUNDARY_QA_PATCH_APPLIED", path)
