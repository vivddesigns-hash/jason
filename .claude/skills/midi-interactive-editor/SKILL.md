---
name: "MIDI Interactive Editor"
description: "Parse a MusicXML file to map chords per measure, then generate or edit MIDI instrument parts (bass, keys, pads, drums) with scale guard rails, genre-appropriate patterns, and voice leading. Use when Dwight sends a Logic MusicXML export and asks for a new part or variation on an existing one."
metadata:
  jason:
    emoji: 🎹
    activation-hints:
      - user sends a MusicXML export and asks for a new instrument part
      - user wants a variation on an existing MIDI part staying in scale
      - needs to generate piano/Wurli pads or bass lines from chord analysis
      - interactive editing loop where the user corrects and I regenerate
    category: content
---

## When to Use

Use this skill when Dwight sends a MusicXML file exported from Logic Pro and asks for a new instrument part, a variation of an existing part, or wants to iterate on a pattern. This covers the "Interactive Mode" of the CoProducerAI workflow — analyzing actual note content, deriving chord structure, and generating parts that stay in scale with appropriate genre feel.

Do NOT use this skill for audio transcription or mixing tasks.

## Prerequisites

- `music21` installed (pip)
- `pretty_midi` installed (pip) for writing MIDI output
- `mido` installed (pip) for low-level MIDI operations if needed
- The MusicXML file from Dwight's Logic export
- The chord map JSON file (if already created) from `/workspace/blind_chord_map_corrected.json`

## Step 1 — Parse the MusicXML and extract note content per measure

Always start from what's actually in the file. Do not guess or infer chords from instrument names or track labels.

```python
import music21
from collections import defaultdict

score = music21.converter.parse('path/to/file.xml')
part = score.parts[instrument_index]  # 0-indexed

notes_by_measure = defaultdict(list)
for measure in part.recurse().getElementsByClass('Measure'):
    for n in measure.getElementsByClass('Note'):
        notes_by_measure[measure.number].append({
            'pitch': n.nameWithOctave,
            'midi': n.pitch.midi,
            'offset': float(n.offset),
            'duration': float(n.duration.quarterLength),
            'beat': float(n.offset) % 4.0,
        })
```

> ⚠️ CRITICAL: Extract notes from ALL melodic instruments, not just one. The chord structure comes from combining pitches, not guessing from guitar skank roots or bass notes alone.

## Step 2 — Map the chord structure per measure

For each active measure, collect all pitches from all melodic instruments and derive the chord.

```python
# Collect combined pitches across ALL melodic parts
all_notes_by_measure = defaultdict(set)
for idx in melodic_part_indices:  # skip drum/percussion
    part = score.parts[idx]
    for measure in part.recurse().getElementsByClass('Measure'):
        for n in measure.getElementsByClass('Note'):
            note_num = n.pitch.midi
            note_name = n.name.replace('-', 'B-')
            all_notes_by_measure[measure.number].add(note_name)
```

Determine the scale per measure:
- If notes fit A natural minor (A, B, C, D, E, F, G) → Am scale
- If notes fit D natural minor (D, E, F, G, A, Bb, C) → Dm scale
- If notes fit another scale → that scale
- If notes include out-of-scale notes → note them but use the dominant scale

Save to a chord map JSON for reuse:
```json
{
  "10": {"measure": 10, "chord": "Am", "scale": ["A", "B", "C", "D", "E", "F", "G"], "notes": ["A3"], "duration": 1.0},
  "11": {"measure": 11, "chord": "Am(bass)", "scale": [...]}
}
```

## Step 3 — Define the scale guard rails

Convert scale degrees to MIDI pitch classes:

```python
am_pcs = {0, 2, 4, 5, 7, 9, 11}  # A minor
dm_pcs = {0, 2, 4, 5, 7, 9, 10}  # D minor

def snap_to_scale(pitch, scale_pcs):
    """Snap a MIDI pitch to the nearest in-scale pitch."""
    if (pitch % 12) in scale_pcs:
        return pitch
    candidates = []
    octave = pitch // 12
    for pc in scale_pcs:
        candidates.append(octave * 12 + pc)
        candidates.append((octave + 1) * 12 + pc)
        candidates.append((octave - 1) * 12 + pc)
    return min(candidates, key=lambda c: abs(c - pitch))
```

## Step 4 — Generate the new part

Based on what Dwight asked for (pads, bass, variation on his bass, etc.):

### For pads (Wurli/Rhodes):
- Use extended voicings (9ths, 11ths)
- Voice leading between chords: choose inversions to minimize movement between measures
- Inner voice movement: middle voice steps within scale then returns
- Rhythmic variation: some anticipated entries (early by a 16th or 8th)
- Sustain notes beyond a single beat (0.75-3.0 quarter lengths)

### For bass lines (reggae):
- Root on beat 1 every measure (non-negotiable for reggae)
- Short note durations (0.09-0.26 seconds, staccato feel)
- No holding notes too long
- Approach notes into the next chord (walk from current root toward next root on the "and" of 4)
- Octave jumps for movement
- Avoid being repetitive: vary patterns across measures
- **Critical: Keep it simple. A few notes per measure. Not busy.**

### For bass line variations on an existing part:
- Leave 70%+ of measures completely untouched — preserve original feel
- Apply ONE small change per varied measure:
  - Substitute a note for a different scale tone nearby
  - Add a single passing note in a gap between two existing notes
  - Octave jump on a single note
  - Velocity shift for dynamic variation
- Never rewrite the pattern. Keep the feel.

## Step 5 — Validate everything before saving

Every generated note must be checked against its measure's scale:

```python
out_of_scale = 0
for n in inst.notes:
    m_num = int(n.start / seconds_per_measure) + 1
    scale_pcs = get_scale_for_measure(m_num)
    if (n.pitch % 12) not in scale_pcs:
        n.pitch = snap_to_scale(n.pitch, scale_pcs)
        out_of_scale += 1
```

Zero out-of-scale notes. If there are any, snap them. Report the number.

## Step 6 — Transfer to Dwight's Mac and report

Copy the generated MIDI to:
```
/Users/dwightjones/Music/Logic/LitaMarie Music/
```
via `host_file_transfer` with `direction: "to_host"`.

Also save in workspace as a jason:// link.

Report:
- Number of notes generated
- Pitch range
- Measures covered
- Zero out of scale count
- Key decisions made (patterns used, voicings, etc.)

## Step 7 — Iterate based on feedback

Dwight will tell you what's wrong. Common corrections so far:
- "too repetitive" → vary patterns more, leave more space
- "holding notes too long" → shorter durations, staccato feel
- "notes are off key" → re-check the chord map, the scale may be wrong
- "keep my feel" → minimal variation, preserve original timing/placement

When he corrects you, do not defend or explain. Regenerate immediately.

## SKILL COMPLETE WHEN

- [ ] `pretty_midi.PrettyMIDI` wrote the .mid file and saved to workspace
- [ ] `host_file_transfer` delivered the file to Dwight's Mac
- [ ] All notes validated: zero out of scale for their measure
- [ ] Dwight has confirmed the result (or the iteration loop is active)

## References

See `references/failure-modes.md` for known issues and how to avoid them.

## Critical Rules

1. Map the music first. Never generate from assumptions about key or chord.
2. Scale is the guard rail. Every note must be in scale for its measure.
3. Feel > notes. 467 notes with wrong feel fail. 200 notes with right feel win.
4. When iterating, default to smaller changes. You can always add more.
5. Tempo source: read from the MusicXML or MIDI file — do not assume 120 BPM.
6. Dwight's correct bass is the reference for feel. Variations must preserve it.
