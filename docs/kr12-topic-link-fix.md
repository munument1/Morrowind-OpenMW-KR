# KR12 topic link corrections

KR11 deliberately reused the KR10 engine. Additional false links were found in
both engine discovery and translation markup. KR12 changes both components.

* Enforce Korean word boundaries during topic discovery as well as rendering;
  overlapping discovery matches do not bypass spelling boundaries.
* Ordinary `일` (thing/event) no longer implicitly links to the work topic.
  Explicit work links and the keyword `일거리` remain usable.
* Keep old saved journal wording and timestamps. The view may use corrected
  loaded INFO markup only when its visible text exactly matches the saved text.
  Player-name expansions and changed translations therefore are not overwritten.
* Preserve original Daedric glyph input/font data and KR11 Roman numeral coverage.

The data postprocessor writes a new directory. It changes only INFO.NAME and
reviewed sidecar mappings; scripts, IDs, conditions, journal stages, BOOK records
and all other subrecords are byte-identical. It repairs split Haj-Ei name tags,
unrelated work tags, and an explicit manifest of reviewed additional errors.

Audit the full released translation against locally owned original masters with
`audit_explicit_topic_tags.py`, then select semantically reviewed corrections with
`review_kr12_topic_candidates.py`. Audit flags are not automatically all errors:
English inflections such as `enchanted` and `talking` can remain legitimate links.

Actual-parser regressions cover display, discovery, overlap resolution, historical
markup repair, explicit links, proper names and the original Korean index tests.
Full Windows/Android builds and gameplay checks remain release gates.
