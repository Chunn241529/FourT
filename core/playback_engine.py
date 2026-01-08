"""
Playback engine for MIDI playback control
"""

import time
import threading
import random


class PlaybackEngine:
    """Manages MIDI playback state and execution"""

    def __init__(self, keyboard_controller):
        """
        Initialize playback engine

        Args:
            keyboard_controller: KeyboardController instance
        """
        self.keyboard = keyboard_controller
        self.playback_speed = 1.0
        self.stop_playback = False
        self.is_playing = False
        self.loop_enabled = False
        self.humanize_enabled = True  # Default to True for safety

    def set_speed(self, speed):
        """Set playback speed multiplier"""
        self.playback_speed = float(speed)

    def set_loop(self, enabled):
        """Enable or disable loop playback"""
        self.loop_enabled = enabled

    def set_humanize(self, enabled):
        """Enable or disable humanization (anti-cheat)"""
        self.humanize_enabled = enabled

    def set_hand_mode(self, mode):
        """
        Set hand playback mode
        0: Both Hands (Default)
        1: Left Hand Only (Bass)
        2: Right Hand Only (Melody)
        """
        self.hand_mode = int(mode)

    def stop(self):
        """Stop current playback"""
        self.stop_playback = True

    def is_active(self):
        """Check if playback is currently active"""
        return self.is_playing

    def play_events(self, events, on_complete=None):
        """
        Play MIDI events in a background thread

        Args:
            events: List of (time, action, key_char, modifier, hand) tuples
            on_complete: Optional callback when playback completes
        """

        def play_thread():
            self.is_playing = True
            self.stop_playback = False

            while True:
                start_time = time.time()
                active_keys = set()

                # Pre-calculate humanization with Chord Preservation
                current_events = []
                if self.humanize_enabled:
                    # Group events by timestamp (approximate) to keep chords tight
                    i = 0
                    n = len(events)
                    while i < n:
                        batch = [events[i]]
                        curr_t = events[i][0]
                        j = i + 1
                        # Group notes within 5ms as a single "chord/strum"
                        while j < n and abs(events[j][0] - curr_t) < 0.005:
                            batch.append(events[j])
                            j += 1

                        # Calculate one main jitter for this whole group (preserve harmonic integrity)
                        # Reduced sigma to 8ms for tighter timing
                        group_offset = random.gauss(0, 0.008)

                        for ev in batch:
                            # Tiny micro-jitter (±1ms) to avoid robotic simultaneous outputs
                            micro_jitter = random.uniform(-0.001, 0.001)
                            final_time = max(0, ev[0] + group_offset + micro_jitter)

                            # Handle backward compatibility (4 vs 5 items)
                            if len(ev) == 5:
                                current_events.append(
                                    (final_time, ev[1], ev[2], ev[3], ev[4])
                                )
                            else:
                                current_events.append(
                                    (final_time, ev[1], ev[2], ev[3], 0)
                                )  # Default Left

                        i = j

                    # Resort ensures we process in time order
                    current_events.sort(key=lambda x: x[0])
                else:
                    # Backward compat copy
                    current_events = []
                    for ev in events:
                        if len(ev) == 5:
                            current_events.append(ev)
                        else:
                            current_events.append(ev + (0,))  # Append default hand

                event_index = 0
                while event_index < len(current_events) and not self.stop_playback:
                    current_time = (time.time() - start_time) * self.playback_speed

                    # Unpack 5 elements
                    event_data = current_events[event_index]
                    event_time = event_data[0]
                    event_type = event_data[1]
                    key_char = event_data[2]
                    modifier = event_data[3]
                    hand = event_data[4]

                    # Filter by Hand Mode
                    # Mode 1 (Left Only): Skip if hand != 0
                    if getattr(self, "hand_mode", 0) == 1 and hand != 0:
                        event_index += 1
                        continue
                    # Mode 2 (Right Only): Skip if hand != 1
                    if getattr(self, "hand_mode", 0) == 2 and hand != 1:
                        event_index += 1
                        continue

                    # Buffer of 3ms
                    if current_time >= event_time:
                        if event_type == "press":
                            if key_char not in active_keys:
                                threading.Thread(
                                    target=self.keyboard.press_key,
                                    args=(key_char, True, modifier),
                                    daemon=True,
                                ).start()
                                active_keys.add(key_char)
                        else:  # release
                            if key_char in active_keys:
                                threading.Thread(
                                    target=self.keyboard.press_key,
                                    args=(key_char, False, modifier),
                                    daemon=True,
                                ).start()
                                active_keys.discard(key_char)
                        event_index += 1
                    else:
                        sleep_time = (event_time - current_time) / self.playback_speed
                        if sleep_time > 0.002:  # Sleep only if gap is big enough
                            time.sleep(min(sleep_time, 0.01))

                # Release all active keys
                for key in active_keys.copy():
                    threading.Thread(
                        target=self.keyboard.press_key, args=(key, False), daemon=True
                    ).start()

                # Check if we should loop
                if not self.loop_enabled or self.stop_playback:
                    break

                # Wait before repeating
                time.sleep(1)

            self.is_playing = False

            if on_complete:
                on_complete()

        threading.Thread(target=play_thread, daemon=True).start()
