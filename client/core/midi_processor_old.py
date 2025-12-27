"""
MIDI file processing and key estimation
"""

import numpy as np
import pretty_midi
import mido
import tempfile
import os

from .config import LOW_KEYS, MED_KEYS, HIGH_KEYS, PITCH_MAPPING


def sanitize_midi_file(midi_path):
    """
    Sanitize a MIDI file by fixing corrupted data bytes.
    MIDI data bytes must be in range 0-127. This function attempts to
    repair files with out-of-range values.
    
    Args:
        midi_path: Path to the MIDI file
        
    Returns:
        str: Path to sanitized file (may be a temp file, or original if no issues)
        
    Raises:
        ValueError: If the file cannot be repaired
    """
    try:
        # First, try loading normally - if it works, no sanitization needed
        _ = mido.MidiFile(midi_path)
        return midi_path
    except (ValueError, IOError, EOFError) as e:
        error_str = str(e).lower()
        if "data byte" not in error_str and "range" not in error_str:
            raise  # Re-raise if it's not a data byte range error
        
        print(f"[MIDI] Detected corrupted data bytes: {e}")
        print(f"[MIDI] Attempting repair...")
        
        # Read raw bytes
        with open(midi_path, 'rb') as f:
            data = bytearray(f.read())
        
        # MIDI file repair - scan through and cap any data bytes > 127
        # We need to understand MIDI structure:
        # - Bytes 0x80-0xFF are status bytes (start of messages)
        # - Bytes 0x00-0x7F are data bytes
        # 
        # The error occurs when a data byte position has a value > 127
        # Simple fix: find patterns where we have status -> data -> invalid_data
        # and clamp the invalid_data to 127
        
        fixed_count = 0
        i = 0
        
        # Skip header (MThd + size + header data, then MTrk chunks)
        # Look for track data starting after "MTrk" markers
        while i < len(data) - 1:
            # Check if we're in a track data section
            # MIDI track events: delta-time + event
            # Event can be: status byte (0x80-0xFF) followed by data bytes (0x00-0x7F)
            
            # Simple approach: if we find a byte > 127 that follows a byte < 128,
            # and it's not a valid status byte pattern, cap it
            # BUT we need to be careful not to break valid status bytes
            
            # The specific error "data byte must be in range 0..127" means mido
            # expected a data byte but got something >= 128
            # This typically happens in note_on/note_off messages where
            # velocity or note number is corrupted
            
            # More aggressive fix: after any Note On (0x90-0x9F) or Note Off (0x80-0x8F)
            # the next 2 bytes should be data bytes (0-127)
            if 0x80 <= data[i] <= 0x9F:  # Note On or Note Off
                # Next 2 bytes should be note number and velocity
                for j in range(1, 3):
                    if i + j < len(data) and data[i + j] > 127:
                        original = data[i + j]
                        data[i + j] = data[i + j] & 0x7F  # Clamp to 0-127
                        fixed_count += 1
                        print(f"[MIDI] Fixed byte at {i+j}: {original} -> {data[i+j]}")
            
            # Also fix after Control Change (0xB0-0xBF), Program Change (0xC0-0xCF),
            # Channel Pressure (0xD0-0xDF), Pitch Bend (0xE0-0xEF)
            elif 0xB0 <= data[i] <= 0xBF:  # Control Change - 2 data bytes
                for j in range(1, 3):
                    if i + j < len(data) and data[i + j] > 127:
                        original = data[i + j]
                        data[i + j] = data[i + j] & 0x7F
                        fixed_count += 1
                        print(f"[MIDI] Fixed byte at {i+j}: {original} -> {data[i+j]}")
            elif 0xC0 <= data[i] <= 0xDF:  # Program Change or Channel Pressure - 1 data byte
                if i + 1 < len(data) and data[i + 1] > 127:
                    original = data[i + 1]
                    data[i + 1] = data[i + 1] & 0x7F
                    fixed_count += 1
                    print(f"[MIDI] Fixed byte at {i+1}: {original} -> {data[i+1]}")
            elif 0xE0 <= data[i] <= 0xEF:  # Pitch Bend - 2 data bytes
                for j in range(1, 3):
                    if i + j < len(data) and data[i + j] > 127:
                        original = data[i + j]
                        data[i + j] = data[i + j] & 0x7F
                        fixed_count += 1
                        print(f"[MIDI] Fixed byte at {i+j}: {original} -> {data[i+j]}")
            
            i += 1
        
        if fixed_count == 0:
            # If we couldn't find obvious fixes, try a more aggressive approach
            # Cap ALL bytes > 127 that are not obviously status bytes
            print("[MIDI] No fixes with standard approach, trying aggressive fix...")
            for i in range(len(data)):
                # Skip if it looks like a valid status byte at message boundary
                if data[i] > 127 and i > 0:
                    prev = data[i - 1]
                    # If previous byte is a data byte (< 128), then this should be too
                    # unless it's a new status byte following data
                    if prev < 128:
                        data[i] = data[i] & 0x7F
                        fixed_count += 1
        
        print(f"[MIDI] Fixed {fixed_count} corrupted bytes")
        
        if fixed_count == 0:
            raise ValueError(f"Could not repair MIDI file: {e}")
        
        # Write to temp file
        temp_fd, temp_path = tempfile.mkstemp(suffix='.mid')
        try:
            os.write(temp_fd, bytes(data))
        finally:
            os.close(temp_fd)
        
        # Verify the fix worked
        try:
            _ = mido.MidiFile(temp_path)
            print(f"[MIDI] Repair successful!")
            return temp_path
        except (ValueError, IOError, EOFError) as verify_e:
            os.unlink(temp_path)
            raise ValueError(f"Could not repair MIDI file after {fixed_count} fixes: {verify_e}")


def estimate_key(notes):
    """
    Estimate the key of a song using Krumhansl-Schmuckler key-finding algorithm.
    Returns the number of semitones to transpose to C Major.

    Args:
        notes: List of pretty_midi.Note objects

    Returns:
        int: Number of semitones to shift to C Major
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
    Preprocess MIDI file: Transpose to C Major and map to keyboard keys

    Args:
        midi_path: Path to MIDI file
        auto_transpose: Whether to automatically transpose to C Major
        manual_transpose: Manual transpose semitones (overrides auto). Use 0 to disable.

    Returns:
        tuple: (events list, total_time, debug_info)
            events: List of (time, action, key_char, modifier) tuples
            total_time: Total duration of the MIDI file
            debug_info: Dict with 'estimated_key', 'transpose', 'in_range', 'out_range'
    """
    # Sanitize MIDI file first to fix any corrupted data bytes
    sanitized_path = sanitize_midi_file(midi_path)
    temp_file = sanitized_path != midi_path  # Track if we created a temp file
    
    try:
        pm = pretty_midi.PrettyMIDI(sanitized_path)
        events = []

        # Collect all notes
        all_notes = []
        for instrument in pm.instruments:
            if not instrument.is_drum:
                all_notes.extend(instrument.notes)

        if not all_notes:
            return [], 0

        # Estimate key and transpose
        shift = 0
        estimated_key = "C Major"
        key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        if manual_transpose is not None:
            # Use manual transpose value
            shift = manual_transpose
            print(f"[MIDI] Manual transpose: {shift} semitones")
        elif auto_transpose:
            shift = estimate_key(all_notes)
            # Detected key is the one we're transposing FROM
            detected_key_idx = (12 - shift) % 12
            estimated_key = f"{key_names[detected_key_idx]} Major"
            print(f"[MIDI] Detected Key: {estimated_key}, Shift: {shift} semitones")

        # --- Smart Range Fitting (Improved) ---
        # 1. Calculate WEIGHTED average pitch (longer notes count more)
        weighted_pitch_sum = 0
        total_duration = 0
        pitch_histogram = {}  # Count notes per octave
        
        for note in all_notes:
            shifted_pitch = note.pitch + shift
            duration = note.end - note.start
            weighted_pitch_sum += shifted_pitch * duration
            total_duration += duration
            
            # Track which octave each note falls into
            octave = shifted_pitch // 12
            pitch_histogram[octave] = pitch_histogram.get(octave, 0) + 1
        
        weighted_avg_pitch = weighted_pitch_sum / total_duration if total_duration > 0 else 60
        
        # 2. Find the most populated octave range
        # Playable range is octave 4-6 (MIDI 48-83)
        # Find where most notes cluster
        if pitch_histogram:
            sorted_octaves = sorted(pitch_histogram.items(), key=lambda x: -x[1])
            dominant_octave = sorted_octaves[0][0]
            print(f"[MIDI] Dominant octave: {dominant_octave} (MIDI {dominant_octave*12}-{(dominant_octave+1)*12-1})")
        
        # 3. Calculate optimal octave shift
        # Target: center weighted average around MIDI 65.5 (center of 48-83)
        center_target = 65.5
        octave_shift = round((center_target - weighted_avg_pitch) / 12) * 12
        
        total_shift = shift + octave_shift
        print(f"[MIDI] Weighted Avg Pitch: {weighted_avg_pitch:.1f}, Octave Shift: {octave_shift}, Total Shift: {total_shift}")
        
        # 4. Pre-analyze out-of-range notes
        in_range = 0
        out_range = 0
        for note in all_notes:
            p = note.pitch + total_shift
            if 48 <= p <= 83:
                in_range += 1
            else:
                out_range += 1
        
        if out_range > 0:
            print(f"[MIDI] Notes: {in_range} in range, {out_range} out of range ({100*out_range/(in_range+out_range):.1f}%)")

        # Mapping for 12 pitch classes to (key_index, modifier)
        # The game has 7 natural notes (C D E F G A B) mapped to keys 0-6
        # Shift + key = sharp (#), Ctrl + key = flat (b)
        # 
        # Game keyboard shows: 1, #1, 2, b3, 3, 4, #4, 5, #5, 6, b7, 7
        # So the game uses FLATS for Eb (b3) and Bb (b7), not sharps
        #
        # Accidentals mapping:
        # - C# = Shift+C (key 0) → #1
        # - Eb = Ctrl+E (key 2) → b3 (NOT D#!)
        # - F# = Shift+F (key 3) → #4
        # - G# = Shift+G (key 4) → #5
        # - Bb = Ctrl+B (key 6) → b7 (NOT A#!)
        CHROMATIC_MAPPING = {
            0: (0, None),      # C → 1
            1: (0, 'shift'),   # C# → #1 (Shift + C)
            2: (1, None),      # D → 2
            3: (2, 'ctrl'),    # Eb → b3 (Ctrl + E)
            4: (2, None),      # E → 3
            5: (3, None),      # F → 4
            6: (3, 'shift'),   # F# → #4 (Shift + F)
            7: (4, None),      # G → 5
            8: (4, 'shift'),   # G# → #5 (Shift + G)
            9: (5, None),      # A → 6
            10: (6, 'ctrl'),   # Bb → b7 (Ctrl + B)
            11: (6, None)      # B → 7
        }

        # Process notes with SIMPLE CONSISTENT octave wrapping
        # This preserves interval relationships better than contextual folding
        for instrument in pm.instruments:
            if instrument.is_drum:
                continue
            for note in instrument.notes:
                pitch = int(note.pitch + total_shift)

                # Simple octave wrapping - keeps intervals consistent
                while pitch < 48:
                    pitch += 12
                while pitch > 83:
                    pitch -= 12

                # Determine range (low/mid/high)
                if 48 <= pitch < 60:
                    range_name = "low"
                elif 60 <= pitch < 72:
                    range_name = "med"
                else:
                    range_name = "high"

                # Map pitch to key and modifier
                pc = pitch % 12
                key_idx, modifier = CHROMATIC_MAPPING.get(pc, (0, None))

                # Get the actual character
                try:
                    key_char = {
                        "low": LOW_KEYS[key_idx],
                        "med": MED_KEYS[key_idx],
                        "high": HIGH_KEYS[key_idx],
                    }[range_name]
                except IndexError:
                    print(f"IndexError for pitch {pitch}, key_idx {key_idx}")
                    continue

                events.append((note.start, "press", key_char, modifier))
                events.append((note.end, "release", key_char, modifier))

        events.sort(key=lambda x: x[0])
        
        # Build debug info
        debug_info = {
            'estimated_key': estimated_key,
            'transpose': total_shift,
            'octave_shift': octave_shift,
            'in_range': in_range,
            'out_range': out_range,
            'total_notes': in_range + out_range,
            'weighted_avg_pitch': weighted_avg_pitch
        }
        
        return events, pm.get_end_time(), debug_info
    
    finally:
        # Clean up temp file if we created one
        if temp_file and os.path.exists(sanitized_path):
            try:
                os.unlink(sanitized_path)
            except OSError:
                pass  # Ignore cleanup errors
