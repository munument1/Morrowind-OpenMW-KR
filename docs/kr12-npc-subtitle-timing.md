# KR12 NPC speech subtitle lifetime

NPC Voice INFO and script `Say` used ordinary timed message boxes. Their timeout
was translated Unicode character count times the unchanged `fMessageTimePerChar`
value, 0.1 seconds. This is separate from movie SRT subtitles.

On the locally installed English `CharGenName2.mp3`, speech lasts 7.810625 seconds.
The English script caption has 119 characters (11.9 seconds); the Korean caption
has 42 (4.2 seconds), explaining approximately 3.61 seconds of premature expiry.
Across 21 locally measured opening clips, 18 Korean text timers are shorter than
their corresponding audio. These are asset/code timing comparisons, not 21
separate rendered gameplay observations.

The fix gives each successfully started speech stream a unique identity. NPC
Voice INFO and script Say captions follow that identity until it finishes,
stops or is replaced. Queued and paused OpenAL streams remain active. Moving an
actor between cells does not change the tracked utterance identity.

Missing/disabled audio retains the ordinary finite text timeout. Dialogue-window
message history retains its existing behavior. Subtitles can still be disabled.
Ordinary notifications keep their own timers and cannot evict active speech
captions; each category retains a three-message bound. A replacement utterance
replaces the previous caption from the same speaker.

The regression uses the real opening-clip duration at 30/60/120 fps and covers
pause/queue, stop/replacement, unrelated notifications and no-audio fallback.
Rendered before/after playback and full Windows/Android builds are release gates.
