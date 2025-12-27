"""
Playback engine for MIDI playback control
"""

import time
import threading


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

    def set_speed(self, speed):
        """Set playback speed multiplier"""
        self.playback_speed = float(speed)

    def set_loop(self, enabled):
        """Enable or disable loop playback"""
        self.loop_enabled = enabled

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
            events: List of (time, action, key_char) tuples
            on_complete: Optional callback when playback completes
        """

        def play_thread():
            self.is_playing = True
            self.stop_playback = False

            while True:
                start_time = time.time()
                event_index = 0
                active_keys = set()

                while event_index < len(events) and not self.stop_playback:
                    current_time = (time.time() - start_time) * self.playback_speed
                    event_time, event_type, key_char, modifier = events[event_index]

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
                        if sleep_time > 0.001:
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
