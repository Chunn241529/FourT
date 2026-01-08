"""
MIDI file processing with Smart Voicing (Music Theory based)
Based on proven old logic + Hand Separation (Left=Bass, Right=Melody)
"""

import numpy as np
import pretty_midi
import mido
import tempfile
import os
from collections import defaultdict

from .config import LOW_KEYS, MED_KEYS, HIGH_KEYS, PITCH_MAPPING


def sanitize_midi_file(midi_path):
    """
    Sanitize a MIDI file by fixing corrupted data bytes.
    """
    try:
        _ = mido.MidiFile(midi_path)
        return midi_path
    except (ValueError, IOError, EOFError) as e:
        return midi_path


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


def preprocess_midi(
    midi_path, auto_transpose=True, manual_transpose=None, smart_bass_enabled=True
):
    """
    MIDI Preprocessing based on PROVEN OLD LOGIC + Hand Separation

    Args:
        smart_bass_enabled: If True, enable 2-hand mode (left=bass, right=melody)
                           If False, all notes played by right hand
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

    # 2. Key Estimation & Transposition (from old proven logic)
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

    # 3. Smart Octave Shift (from old proven logic)
    weighted_pitch_sum = 0
    total_duration = 0
    for note in all_notes:
        p = note.pitch + shift
        d = note.end - note.start
        weighted_pitch_sum += p * d
        total_duration += d

    avg_pitch = weighted_pitch_sum / total_duration if total_duration > 0 else 60
    center_target = 65.5  # Center of [48, 83]
    octave_shift = round((center_target - avg_pitch) / 12) * 12
    total_shift = shift + octave_shift

    print(f"[MIDI] Total Shift: {total_shift} (Key: {shift}, Octave: {octave_shift})")

    # CHROMATIC_MAPPING from OLD FILE (PROVEN TO WORK!)
    # Game uses Eb (Ctrl+E) and Bb (Ctrl+B), NOT D# and A#
    CHROMATIC_MAPPING = {
        0: (0, None),  # C → 1
        1: (0, "shift"),  # C# → #1 (Shift + C)
        2: (1, None),  # D → 2
        3: (2, "ctrl"),  # Eb → b3 (Ctrl + E) ← GAME USES FLAT!
        4: (2, None),  # E → 3
        5: (3, None),  # F → 4
        6: (3, "shift"),  # F# → #4 (Shift + F)
        7: (4, None),  # G → 5
        8: (4, "shift"),  # G# → #5 (Shift + G)
        9: (5, None),  # A → 6
        10: (6, "ctrl"),  # Bb → b7 (Ctrl + B) ← GAME USES FLAT!
        11: (6, None),  # B → 7
    }

    def map_pitch_to_key(pitch):
        """Map a single pitch to (key_char, modifier) using proven logic"""
        # Simple octave wrapping (FROM OLD PROVEN LOGIC)
        while pitch < 48:
            pitch += 12
        while pitch > 83:
            pitch -= 12

        # Determine range
        if 48 <= pitch < 60:
            range_keys = LOW_KEYS
        elif 60 <= pitch < 72:
            range_keys = MED_KEYS
        else:
            range_keys = HIGH_KEYS

        # Map pitch class
        pc = pitch % 12
        key_idx, modifier = CHROMATIC_MAPPING.get(pc, (0, None))

        try:
            key_char = range_keys[key_idx]
            return key_char, modifier
        except IndexError:
            print(f"[MIDI] IndexError for pitch {pitch}, key_idx {key_idx}")
            return None, None

    if smart_bass_enabled:
        # === 2-HAND MODE: Left=Bass (lowest), Right=Melody (highest) ===
        # Group notes by time for chord detection
        notes_by_time = defaultdict(list)
        for instrument in pm.instruments:
            if instrument.is_drum:
                continue
            for note in instrument.notes:
                # Group notes within 10ms as chord
                t_quantized = round(note.start / 0.010) * 0.010
                notes_by_time[t_quantized].append(note)

        sorted_times = sorted(notes_by_time.keys())

        for t in sorted_times:
            chord_notes = notes_by_time[t]
            if not chord_notes:
                continue

            # Sort by pitch
            chord_notes_sorted = sorted(chord_notes, key=lambda n: n.pitch)

            # Melody: highest note -> Right Hand (always play)
            melody_note = chord_notes_sorted[-1]
            melody_pitch = int(melody_note.pitch + total_shift)
            key_char, modifier = map_pitch_to_key(melody_pitch)

            if key_char:
                events.append(
                    (melody_note.start, "press", key_char, modifier, 1)
                )  # 1 = right
                events.append((melody_note.end, "release", key_char, modifier, 1))

            # Bass: lowest note -> Left Hand (only if different from melody)
            if len(chord_notes_sorted) > 1:
                bass_note = chord_notes_sorted[0]
                if bass_note != melody_note:
                    bass_pitch = int(bass_note.pitch + total_shift)
                    key_char, modifier = map_pitch_to_key(bass_pitch)

                    if key_char:
                        events.append(
                            (bass_note.start, "press", key_char, modifier, 0)
                        )  # 0 = left
                        events.append((bass_note.end, "release", key_char, modifier, 0))
    else:
        # === SIMPLE MODE: All notes with right hand (original behavior) ===
        for instrument in pm.instruments:
            if instrument.is_drum:
                continue
            for note in instrument.notes:
                pitch = int(note.pitch + total_shift)
                key_char, modifier = map_pitch_to_key(pitch)

                if key_char:
                    events.append(
                        (note.start, "press", key_char, modifier, 1)
                    )  # Default right
                    events.append((note.end, "release", key_char, modifier, 1))

    events.sort(key=lambda x: x[0])

    debug_info = {
        "key_shift": shift,
        "octave_shift": octave_shift,
        "total_notes": len(all_notes),
        "estimated_key": estimated_key,
    }

    print(f"[MIDI] Processed {len(events)} events")
    return events, pm.get_end_time(), debug_info
