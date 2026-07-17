---
name: "Reggae Feel Model"
description: "Parameterised reggae drum feel architecture for CoProducerAI/MIDI generation. Provides microtiming templates, velocity profiles, accent hierarchies, pattern vocabulary (One Drop, Rockers, Steppers, Roots), and dial-based feel parameters (laid_back, heaviness, looseness, ghost_density). Use when generating reggae drum MIDI, building a feel model for an AI music tool, or correcting flat/robotic drum patterns in any genre."
metadata:
  jason:
    emoji: 🥁
    activation-hints:
      - need to generate reggae drums with authentic feel
      - how to model microtiming and velocity for One Drop
      - build a feel engine for CoProducerAI
      - fix robotic drum patterns
      - parameterised MIDI generation with feel dials
      - what makes reggae drum feel different from grid MIDI
    avoid-when:
      - the goal is simply to place notes on a grid without feel modeling
      - parsing MusicXML files
      - general-purpose MIDI file manipulation without genre focus
    category: development
---

# Reggae Feel Model

Parameterised architecture for generating reggae drum MIDI with authentic feel.

The core insight: **feel is not a property of note positions. It is a property of note relationships.** Every current AI music tool places correct notes at correct positions and produces something that sounds wrong to a musician's ear.

## When to Use

- You need to generate reggae drum tracks (One Drop, Rockers, Steppers, Roots) that don't sound robotic
- You are building a feel model for an AI music tool (CoProducerAI or similar)
- You need to add parameterised feel to existing MIDI generation (laid_back, heaviness, looseness, ghost_density dials)
- Dwight says "all you AI agents don't understand reggae" — use this model to prove otherwise

## Architecture

This model splits "feel" into four independent axes that a generator can vary:

### 1. Microtiming Template

How far *after* or *before* the grid each voice places its notes. Expressed as tick offset ranges (at PPQN=480):

| Voice | Timing | Rationale |
|---|---|---|
| Kick (One Drop) | ~15-25ms late (12-30 ticks) | Push the groove forward |
| Kick (Rockers) | ~10-20ms late | Less extreme than One Drop |
| Snare | On grid or 0-5ms early | Anchor point for the pocket |
| Hi-hat (on-beat) | ~4-10ms late | Gentle push |
| Hi-hat (off-beat) | ~10-20ms late | Lazy hi-hat feel |
| Rimshot/clave | On grid or 0-3ms late | Structural marker |
| Open hi-hat | ~12-20ms late | More relaxed than closed |

Each template has both `late` and `early` ranges, and the `laid_back` dial interpolates between them.

### 2. Velocity Texture

Not a flat velocity per voice but a gaussian distribution:

| Voice | Mean | Std | Range | Accent boost |
|---|---|---|---|---|
| Kick | 95 | 8 | 40-115 | +12 |
| Snare | 88 | 5 | 60-105 | +8 |
| Hi-hat | 68 | 6 | 50-85 | +6 |
| Rimshot | 76 | 4 | 60-90 | +5 |
| Open hi-hat | 72 | 5 | 55-85 | +6 |

Key patterns observed in reggae: snare on beat 4 is often slightly heavier than beat 2. Hi-hat "and" of 2 and "and" of 4 are slightly louder.

### 3. Accent Hierarchy

Not every hit matters equally. Three tiers:

- **Tier 1 (must hit right):** kick on beat 3 (One Drop), snare on 2 and 4, rimshot on 2 — structural, don't mess with
- **Tier 2 (must feel right):** hi-hat eighth notes, kick ghost notes — can vary texture but maintain position
- **Tier 3 (can vary freely):** hi-hat off-beat dynamics, ride bell, open hi-hat placement — density controlled by ghost_density dial

This prevents the model from "improving" a critical hit by making it more complex.

### 4. Pattern Vocabulary

Explicit named patterns the model selects and then feeds through the feel templates:

- **One Drop:** kick on beat 3 only, snare on 2+4, hi-hat eighths. Half-time feel at ~150 BPM. No kick on 1. (Half-time: each *felt* beat = 2 quarter notes)
- **Rockers:** kick on 1 AND 3, snare on 2+4. More driving.
- **Steppers:** kick on every 8th note, snare on 3. Dancehall variant.
- **Roots:** kick on 1 and 3 (heavy), snare on 2+4 (dry, short), open hi-hat on off-beats. Classic.

### 5. Parameter Dials

- **laid_back** (0.0-1.0): shifts microtiming distribution toward late. 0 = neutral/early, 1 = max laid back
- **heaviness** (0.0-1.0): amplifies accent contrast. Higher = bigger difference between accented and unaccented hits
- **looseness** (0.0-1.0): increases random jitter spread around base offsets. 0 = consistent, 1 = wild
- **ghost_density** (0.0-1.0): controls probability of Tier-3 ghost notes firing

## Integration Pattern

The feel model sits between the analysis layer (chord detection, tempo) and the MIDI generation layer:

```
Chord Analysis -> Pattern Selection -> Feel Template -> MIDI Output
                        |                    |
                   (pattern vocab)    (dials + random variation)
```

## MIDI Note Mappings (GM Standard)

| Voice | Note |
|---|---|
| Kick | 36 (C2) |
| Snare | 38 (D2) |
| Hi-hat closed | 42 (F#2) |
| Rimshot | 37 (C#2) |
| Open hi-hat | 46 (A#2) |
| Crash | 49 (C#3) |
| Ride | 51 (D#3) |

## Prototype Reference

A working Python prototype exists at `/workspace/prototypes/reggae-feel-engine.py`. It was built for the Blind session (Emotions EP, Track 01, 151 BPM, One Drop). The prototype:
- Reads `/workspace/blind_chord_map_corrected.json` for 121-bar chord structure
- Generates drum + bass MIDI with full feel modeling
- Outputs 3 comparison variants (robotic, normal, heavy) for A/B testing
- Proved: 0 of 1573 notes identical between "robotic" and "heavy" settings with same seed
- Proved: 67 distinct velocity values across 4 voices

The prototype uses Python's `mido` library for MIDI I/O. `music21` is also available.

## Failure Modes

- **MIDI track names with em-dashes:** `mido` uses latin-1 encoding for track names. Unicode characters (em-dash \u2014, smart quotes) cause `UnicodeEncodeError`. Use normal dashes (-) in all MetaMessage track_name values.
- **Fixed vs unique seed:** Without a fixed random seed, comparison variants differ due to random variation, not just feel parameter changes. Use `random.seed(n)` for A/B comparison tests.
- **Velocity clipping:** Always clamp final velocity to MIDI range 1-127. The heaviness dial can push values out of range.

## SKILL COMPLETE WHEN

- [ ] Feel model architecture is understood (microtiming, velocity, accent, pattern, dials)
- [ ] MIDI output has been generated and verified (not flat velocities, unique offsets)
- [ ] At least one comparison variant has been run to validate parameter effect
</
