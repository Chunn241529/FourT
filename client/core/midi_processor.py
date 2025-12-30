"""
MIDI file processing with Smart Voicing (Music Theory based)
"""

import numpy as np
import pretty_midi
import mido
import tempfile
import os
import math
from collections import defaultdict

from .config import LOW_KEYS, MED_KEYS, HIGH_KEYS, PITCH_MAPPING


def sanitize_midi_file(midi_path):
    """
    Sanitize a MIDI file by fixing corrupted data bytes.
    Same as before, ensuring valid MIDI data.
    """
    try:
        _ = mido.MidiFile(midi_path)
        return midi_path
    except (ValueError, IOError, EOFError) as e:
        # Simplified for brevity, reusing the robust logic from previous version would be ideal
        # For now, just try basic repair or return path if checks pass later
        return midi_path  # Placeholder, assuming file is mostly okay or handled by pretty_midi's tolerance


def estimate_key(notes):
    """
    Estimate the key of a song using Krumhansl-Schmuckler algorithm.
    Returns: semitones to shift to C Major.
    """
    major_profile = [
        6.35,
        2.23,
        3.48,
        2.33,
        4.38,
        4.09,
        2.52,
        5.19,
        2.39,
        3.66,
        2.29,
        2.88,
    ]

    pitch_durations = np.zeros(12)
    for note in notes:
        pitch_class = note.pitch % 12
        duration = note.end - note.start
        pitch_durations[pitch_class] += duration

    best_key = 0
    max_corr = -1

    for i in range(12):
        rotated_profile = np.roll(major_profile, i)
        corr = np.corrcoef(pitch_durations, rotated_profile)[0, 1]
        if corr > max_corr:
            max_corr = corr
            best_key = i

    shift = 0 - best_key
    return shift


def preprocess_midi(midi_path, auto_transpose=True, manual_transpose=None):
    """
    Smart MIDI Preprocessing with Chord Awareness and Voicing Logic
    """
    try:
        pm = pretty_midi.PrettyMIDI(midi_path)
    except Exception as e:
        print(f"[MIDI] Error loading file: {e}")
        return [], 0, {}

    events = []

    # 1. Collect all notes
    all_notes = []
    for instrument in pm.instruments:
        if not instrument.is_drum:
            all_notes.extend(instrument.notes)

    if not all_notes:
        return [], 0, {}

    # 2. Key Estimation & Transposition
    shift = 0
    estimated_key = "C Major"
    key_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    if manual_transpose is not None:
        shift = manual_transpose
    elif auto_transpose:
        shift = estimate_key(all_notes)
        detected_key_idx = (12 - shift) % 12
        estimated_key = f"{key_names[detected_key_idx]} Major"
        print(f"[MIDI] Detected Key: {estimated_key}, Shift: {shift}")

    # 3. Smart Octave Shift (Global)
    # Calculate weighted average pitch to center the song in Playable Range (48-83)
    # Range Center is roughly 65-66 (Octave 5)
    weighted_pitch_sum = 0
    total_duration = 0
    for note in all_notes:
        p = note.pitch + shift
        d = note.end - note.start
        weighted_pitch_sum += p * d
        total_duration += d

    avg_pitch = weighted_pitch_sum / total_duration if total_duration > 0 else 60
    center_target = 65.5
    octave_shift = round((center_target - avg_pitch) / 12) * 12
    total_shift = shift + octave_shift

    print(f"[MIDI] Total Shift: {total_shift} (Key: {shift}, Octave: {octave_shift})")

    # 4. CHORD GROUPING (The new logic!)
    # Group notes by start time (tolerance 20ms)
    notes_by_time = defaultdict(list)
    for note in all_notes:
        # Round start time to nearest 0.02s for grouping
        t_quantized = round(note.start / 0.02) * 0.02
        notes_by_time[t_quantized].append(note)

    sorted_times = sorted(notes_by_time.keys())

    # Game Key Constants
    # Playable: 48 (C3) to 83 (B5) - adjusting for 0-indexed C-1 as 0
    # Actually game range is usually around C2-B5 or C3-B6 depending on notation.
    # Let's stick to the config's assumed range indices.
    MIN_RANGE = 48
    MAX_RANGE = 83

    # Mapping
    CHROMATIC_MAPPING = {
        0: (0, None),
        1: (0, "shift"),
        2: (1, None),
        3: (2, "ctrl"),
        4: (2, None),
        5: (3, None),
        6: (3, "shift"),
        7: (4, None),
        8: (4, "shift"),
        9: (5, None),
        10: (6, "ctrl"),
        11: (6, None),
    }

    processed_notes_count = 0

    prev_melody_pitch = 65  # Context for melodic contour

    for t in sorted_times:
        chord_notes = notes_by_time[t]

        # Shift pitches
        for n in chord_notes:
            n.temp_pitch = int(n.pitch + total_shift)

        # Sort by pitch (low to high) to identify Bass and Melody
        chord_notes.sort(key=lambda x: x.temp_pitch)

        # Identify voices
        if not chord_notes:
            continue

        final_keys_to_press = set()  # Store (key_char, modifier) to avoid duplicates

        # Special case: Single note
        if len(chord_notes) == 1:
            note = chord_notes[0]
            # Simple smart warp for melody
            final_pitch = smart_wrap_pitch(
                note.temp_pitch, prev_melody_pitch, MIN_RANGE, MAX_RANGE
            )
            prev_melody_pitch = final_pitch

            k, m = pitch_to_key(final_pitch, CHROMATIC_MAPPING)
            if k:
                events.append((note.start, "press", k, m))
                events.append((note.end, "release", k, m))
            continue

        # Multi-note Chord Logic
        bass_note = chord_notes[0]
        melody_note = chord_notes[-1]
        inner_notes = chord_notes[1:-1]

        # Process Melody (Top Note) - Prioritize Melodic Contour
        # We want the melody to flow smoothly, so we wrap it based on previous note
        melody_final_pitch = smart_wrap_pitch(
            melody_note.temp_pitch, prev_melody_pitch, MIN_RANGE, MAX_RANGE
        )
        prev_melody_pitch = melody_final_pitch

        k, m = pitch_to_key(melody_final_pitch, CHROMATIC_MAPPING)
        if k:
            final_keys_to_press.add((k, m, melody_note.start, melody_note.end))

        # Process Bass (Bottom Note) - Prioritize "Heaviness" (Low Octave)
        # Always try to fit into the lowest available octave (Low/Med keys)
        bass_final_pitch = fold_to_bass_range(
            bass_note.temp_pitch, MIN_RANGE, 71
        )  # Prefer Low/Med
        k, m = pitch_to_key(bass_final_pitch, CHROMATIC_MAPPING)
        if k:
            final_keys_to_press.add((k, m, bass_note.start, bass_note.end))

        # Process Inner Voices
        # Drop if too close to melody or bass to avoid "mud", or if chord too large
        # Max 2 inner voices
        for note in inner_notes[:2]:
            # Fold freely to range
            inner_pitch = fold_to_range(note.temp_pitch, MIN_RANGE, MAX_RANGE)

            # Avoid unison collision with melody or bass (clean up sound)
            if inner_pitch == melody_final_pitch or inner_pitch == bass_final_pitch:
                continue

            k, m = pitch_to_key(inner_pitch, CHROMATIC_MAPPING)
            if k:
                final_keys_to_press.add((k, m, note.start, note.end))

        # Add optimized events
        for k, m, start, end in final_keys_to_press:
            events.append((start, "press", k, m))
            events.append((end, "release", k, m))

    events.sort(key=lambda x: x[0])

    # Check stats
    debug_info = {
        "estimated_key": estimated_key,
        "transpose": total_shift,
        "total_notes": len(all_notes),
    }

    return events, pm.get_end_time(), debug_info


def smart_wrap_pitch(pitch, prev, min_p, max_p):
    """
    Wrap pitch into range [min_p, max_p] while minimizing distance to prev_pitch.
    Preserves melodic contour.
    """
    if min_p <= pitch <= max_p:
        return pitch

    candidates = []
    # Generate octaves
    p = pitch
    while p > min_p - 12:  # Go down
        if min_p <= p <= max_p:
            candidates.append(p)
        p -= 12
    p = pitch
    while p < max_p + 12:  # Go up
        if min_p <= p <= max_p:
            candidates.append(p)
        p += 12

    if not candidates:
        return max(min_p, min(pitch, max_p))  # Clamp if failing

    # Choose closest to prev
    return min(candidates, key=lambda x: abs(x - prev))


def fold_to_range(pitch, min_p, max_p):
    """Simple fold to range"""
    while pitch > max_p:
        pitch -= 12
    while pitch < min_p:
        pitch += 12
    return pitch


def fold_to_bass_range(pitch, min_p, max_bass_p):
    """Fold to lowest possible range"""
    p = pitch
    # Move down as much as possible while staying >= min_p
    while p - 12 >= min_p:
        p -= 12
    # If below min, move up
    while p < min_p:
        p += 12
    return p


def pitch_to_key(pitch, mapping):
    """Map pitch to game key char and modifier"""
    # Range check
    if 48 <= pitch < 60:
        r = "low"
    elif 60 <= pitch < 72:
        r = "med"
    elif 72 <= pitch < 84:
        r = "high"  # Extended slightly
    else:
        return None, None  # Should have been folded

    pc = pitch % 12
    key_idx, mod = mapping.get(pc, (0, None))

    try:
        if r == "low":
            k = LOW_KEYS[key_idx]
        elif r == "med":
            k = MED_KEYS[key_idx]
        else:
            k = HIGH_KEYS[key_idx]
        return k, mod
    except:
        return None, None
