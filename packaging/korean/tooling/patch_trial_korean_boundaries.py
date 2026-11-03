#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Experiment-only Korean grammatical suffixes for native topic QA.

This script modifies only a *GitHub Actions checkout*, not user source
or a public release. Later acceptance requires corpus-wide link diffs,
false-positive review, and independent launcher build tests.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_trial_korean_boundaries.py keywordsearch.cpp")
path = Path(sys.argv[1])
source = path.read_text(encoding="utf8")
needle = "        if (isEnding(suffix))\n            return true;\n"
assert source.count(needle) == 1
addition = """
        // Experimental noun-particle endings observed in verified Korean
        // translation corpora. Require a multi-syllable keyword. Do not
        // enable derivational suffixes (식/원/게르/강/류) which can falsely
        // link prefixes of longer proper names.
        if (keyword.size() >= 6)
        {
            constexpr std::string_view verifiedNounEndings[] = {
                "에서의", "로부터", "에서도", "만큼", "뿐", "뿐이다", "뿐입니다",
                "이여", "이며", "이고", "이니", "이거나",
                "이구나", "이었는데", "예요", "였던", "일",
                "와는", "과는", "와도", "과도", "치고는", "대로",
                "님", "님의", "님은", "님이", "님을", "님께", "님께서",
                "님과", "님한테", "님께서는"
            };
            if (std::find(std::begin(verifiedNounEndings),
                    std::end(verifiedNounEndings), suffix) != std::end(verifiedNounEndings))
                return true;
        }
"""
path.write_text(source.replace(needle, needle+addition), encoding="utf8")
print("EXPERIMENTAL_KOREAN_BOUNDARY_QA_PATCH_APPLIED", path)
