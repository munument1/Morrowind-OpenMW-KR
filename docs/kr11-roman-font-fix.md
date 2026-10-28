# KR11 Roman numeral font resource fix

The Korean Galmuri11 TTF already contains Roman numeral glyphs. The active
MysticCards and DejaVuLGCSansMono MyGUI resources did not enable U+2160–U+217F,
so MyGUI used SubstituteCode 95 (`_`) in book headings such as `제Ⅻ권`.

KR11 adds decimal Code range `8544 8575`. Existing ranges, font metrics, TTF,
engine, subtitles and translation payload remain unchanged. The source
Galmuri11 resource receives the same range for consistent future packaging.

`package_kr11_fonts.py` starts from the pinned KR10 release, changes only the
two packaged font definitions and the release README, then compares every
other unique ZIP member byte for byte. It refuses to overwrite any baseline
or output. No Rebirth ESP or translation archive is used by this workflow.

The Android data package can apply the same MysticCards change while keeping
the installed APK and its signing identity. A data revision does not imply
that Windows-only native patches have been ported to Android.

Daedric text uses a separate font path. This Roman range change does not
replace Daedric cipher text or fix translated Rebirth Daedric scrolls.
