# KR5 journal and potion correction

The English-only EET database is source material, not a Korean completion tracker.
Compare its ALCH/FNAM IDs against the loaded translation and all three original masters.
The missing records are `p_restore_health_b`, `p_restore_health_c`, and `p_restore_health_s`.
Only FNAM is changed; all other potion fields come verbatim from Morrowind.esm.

The journal's `.mrk` search phrase can differ from the canonical topic name. Patch
0006 seeds both names, then adds explicitly reviewed journal aliases from the new
optional UTF-8 BOM `.jrn` sidecar. Each line is `display phrase<TAB>canonical topic`.
Aliases are seeded only for topics with recorded dialogue in the current journal.
Saved text, actor substitutions, quest indices, timestamps and player knowledge
are preserved; no unknown topics are added to the journal.

For the reported Caldera case, the aliases are `칼데라의 에보니 광산` and
`에보니 광산`, both targeting `칼데라 에보니 광산`. The latter occurs in the
Caldera donation quest; it is not an alias for unrelated ebony mines.
An English A-Z index remains a separate issue.

Build `yampt-journal-tagger.cpp` with the unmodified `topic_tagger.cpp` and
`keyword_trie.cpp` from [YAMPT](https://github.com/raffll/yampt), commit
`6070d0a88acd6ea7b29982b6a3d61e06a0520f2f` (MIT). The adapter reads canonical
topics, reviewed inflection pairs, then text spans as little-endian uint32 counts
and UTF-8 length-prefixed strings. Existing tags are preserved outside the adapter.

Run `build_kr5_data.py --help` for required input paths. Output must be a new folder.
The JSON allowlist limits changes to entries reviewed with the actual OpenMW parser;
the three reported Caldera entries are added explicitly. Every journal change is
checked for identical displayed text and preserved existing tags.

Compile `verify-journal-links.cpp` with OpenMW's keywordsearch, translation, files,
toutf8 and debuglog implementations. It loads actual CEL/MRK/TOP/JRN files and
can compare legacy and patched seeding against the same text. A saved-text test
must use the original KR4 text with the new `.jrn` file, without rewriting the save.

## Daedric shrine voice subtitles

The seven Daedric shrine quests already have translated DA_* journal INFO
records. The spoken subtitles come from Player->Say in eight Daedra* SCPT
scripts, which still contained 22 English lines in the installed translation
and KR5 release.

Run patch_daedric_shrine_dialogue.py with --source-mod (the directory holding
Morrowind_Korean_ReTranslation.esp), --master (the original Morrowind.esm),
and --output (a new directory). It copies the translation mod and replaces
22 voice subtitle strings, keeping the original WAV names, quest logic,
script metadata, and all other records. The source directories are untouched.

Run verify_daedric_shrine_dialogue.py with --master, --source-esp,
and --patched-esp to check that every non-subtitle byte is unchanged.
The source may be the installed Korean mod or the extracted KR5 release at
payload/mods/Morrowind_Korean_ReTranslation.

## Daedric scroll lettering and readable Korean

Scroll text displayed on opening an item comes from `BOOK/TEXT`. In KR5,
134 enchanted scrolls and one other `sc_*` scroll have a Korean translation
*inside* a `<FONT FACE="Daedric">` span. `DemonicLetters` cannot display Hangul,
so the line appears blank even though `BOOK/FNAM` (the item name) is translated.

`restore_daedric_book_glyphs.py` restores the original Latin text in the
Daedric font span, where the font renders it as Daedric lettering, and appends
the existing Korean translation as a separate line in the default font.
`verify_daedric_scrolls.py` compares those spans with the three original ESMs.
The data correction needs no font or engine change.

### Build both fixes into a new mod folder

From the repository root, run this in PowerShell with your own game/mod paths:

```powershell
$gameData = 'C:\Games\Steam\steamapps\common\Morrowind\Data Files'
$koreanMod = 'D:\OpenMW 0.51.0\mods\Morrowind_Korean_ReTranslation'
python packaging/korean/tooling/build_daedric_feedback_patch.py `
  --source-mod $koreanMod `
  --master "$gameData\Morrowind.esm" `
  --master "$gameData\Tribunal.esm" `
  --master "$gameData\Bloodmoon.esm" `
  --output 'D:\Codex_Trans\Morrowind_Korean_Daedric_Fix'
```

The command runs both standalone patchers and both validators. The destination
must be a **new** directory outside the source mod. On success it contains the
complete mod data and patched ESP plus JSON verification reports; the original
mod, master ESMs and installed OpenMW files are untouched. To deploy, back up
the installed `Morrowind_Korean_ReTranslation.esp` and replace just that ESP
with the generated file. The current game's other translation sidecars and
mod load order are preserved. Run OpenMW and visually check a Daedric statue
and an opened magic scroll before distributing a public release.

The regression suite for glyph formatting is:

```powershell
python -m unittest discover -s packaging/korean/tooling -p 'test_restore_daedric_book_glyphs.py' -v
```
