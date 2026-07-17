# Known Failure Modes

## Guessing Chords from Guitar Skank Roots

**Symptom:** Notes are off-key. User says "some notes right, a lot definitely off key."
**Root cause:** Looked at guitar skank root notes (single A and D) and assumed A major and D major scales instead of analyzing actual note content from all melodic instruments.
**Fix:** Extract notes from ALL melodic parts (piano, organ, melody lines) to determine the actual chord structure per measure. The guitar skank only plays roots. The full picture comes from everything playing at once.

## Holding Notes Too Long (Bass)

**Symptom:** User says "your notes are too repetitive and you are holding them too long."
**Root cause:** Generated bass with 0.5-1.0 quarter-length durations instead of 0.09-0.26 second staccato hits.
**Fix:** Default to note durations under 0.3 seconds for reggae bass. Short and punchy. Leave space.

## Phone Audio Transcription Failure

**Symptom:** liborsa's pyin pitch tracking detects 12 pitch classes instead of 7, notes jump wildly between octaves, and tracking is noisy.
**Root cause:** Phone mic + WhatsApp compression destroys the harmonic information needed for accurate transcription. This is not a toolchain problem — it's a signal quality problem.
**Fix:** Have the user convert the audio to MIDI in Logic Pro using Flex Pitch. Logic has access to the uncompressed DAW signal and produces usable note data. Then clean up pitch corrections and export MIDI for further processing.

## Velocity Blindness

**Symptom:** Generated parts feel mechanical.
**Root cause:** Defaulting all velocities to 80 (the value in Dwight's existing files). But Dwight's files also suffer from this — no velocity variation is a limitation of the original, not a target.
**Fix:** Add intentional velocity variation: accented beats 10-20% louder, ghost notes softer, fills with dynamic shape. This is especially critical for drums.

## Repetitive Patterns

**Symptom:** User says "too repetitive."
**Root cause:** Generated the same pattern for every measure instead of varying across the song.
**Fix:** Use 3-6 different pattern templates and rotate through them. Vary by section (verse, chorus, bridge). Leave 70%+ of measures with only small variations from the original feel.

## Assumed Tempo

**Symptom:** Generated notes at wrong speed relative to arrangement.
**Root cause:** Hardcoded 120 BPM instead of reading from the file.
**Fix:** Always read the actual tempo from the MusicXML or MIDI file header.

## Chords Extracted from Only One Part

**Symptom:** Missing chords, wrong scale assignments for some measures.
**Root cause:** Analyzed only the bass or guitar track instead of all melodic instruments.
**Fix:** Iterate over all parts 10-18 (non-percussion) and collect every note that overlaps in time to determine the full chord voicing.
