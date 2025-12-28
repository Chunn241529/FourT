"""
Macro Player Core Logic
"""

import time
import threading
import random
from pynput import mouse, keyboard


class MacroPlayer:
    def __init__(self):
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()
        self.running = False
        self.speed_multiplier = 1.0
        # Callback for delay countdown overlay
        self.on_delay_start = (
            None  # Callable[[float], None] - receives delay in seconds
        )

    def play(
        self,
        events,
        on_finish=None,
        loop_count=1,
        speed=1.0,
        randomize=True,
        on_delay_start=None,
    ):
        """
        Play macro events with optional anti-cheat randomization

        Args:
            events: List of macro events
            on_finish: Callback when playback finishes
            loop_count: Number of times to loop (0 = infinite)
            speed: Speed multiplier (1.0 = normal, 2.0 = 2x speed)
            randomize: Enable anti-cheat timing/position randomization
            on_delay_start: Callback when delay starts, receives delay seconds
        """
        self.running = True
        self.speed_multiplier = speed
        self.randomize = randomize
        self.on_delay_start = on_delay_start
        threading.Thread(
            target=self._play_thread, args=(events, on_finish, loop_count), daemon=True
        ).start()

    def stop(self):
        self.running = False

    def _apply_timing_variation(self, delay):
        """Apply human-like timing variation to delays"""
        if not self.randomize or delay == 0:
            return delay

        # Add ±5-15% random variation to timing
        variation = random.uniform(0.05, 0.15)
        if random.random() > 0.5:
            return delay * (1 + variation)
        else:
            return delay * (1 - variation)

    def _apply_position_jitter(self, x, y):
        """Apply subtle mouse position jitter"""
        if not self.randomize:
            return x, y

        # Add ±1-2 pixel jitter to mouse position
        jitter_x = random.randint(-2, 2)
        jitter_y = random.randint(-2, 2)
        return x + jitter_x, y + jitter_y

    def _play_thread(self, events, on_finish, loop_count):
        iterations = 0
        while self.running:
            if loop_count > 0 and iterations >= loop_count:
                break

            for event in events:
                if not self.running:
                    break

                # Sleep for delay with optional randomization
                delay = self._apply_timing_variation(event["delay"])

                # Notify UI about delay for countdown overlay (only for delays >= 1s)
                if delay >= 1 and self.on_delay_start:
                    try:
                        self.on_delay_start(delay / self.speed_multiplier)
                    except Exception as e:
                        print(f"[MacroPlayer] on_delay_start error: {e}")

                time.sleep(delay / self.speed_multiplier)

                data = event["data"]
                event_type = event["type"]
                hold_duration = event.get("hold", 0)

                if event_type == "mouse_click":
                    # Apply position jitter for anti-cheat
                    x, y = self._apply_position_jitter(data["x"], data["y"])
                    self.mouse_controller.position = (x, y)

                    button = getattr(
                        mouse.Button, data["button"].split(".")[-1], mouse.Button.left
                    )
                    if data["action"] == "pressed":
                        self.mouse_controller.press(button)
                        if hold_duration > 0:
                            time.sleep(self._apply_timing_variation(hold_duration))
                            self.mouse_controller.release(button)
                    else:
                        self.mouse_controller.release(button)

                elif event_type == "mouse_scroll":
                    x, y = self._apply_position_jitter(data["x"], data["y"])
                    self.mouse_controller.position = (x, y)
                    self.mouse_controller.scroll(data["dx"], data["dy"])

                elif event_type == "key_press":
                    key = self._parse_key(data["key"])
                    self.keyboard_controller.press(key)
                    if hold_duration > 0:
                        time.sleep(self._apply_timing_variation(hold_duration))
                        self.keyboard_controller.release(key)

                elif event_type == "key_release":
                    key = self._parse_key(data["key"])
                    self.keyboard_controller.release(key)

                elif event_type == "delay_only":
                    # Special event type for trailing delays - just sleep, no action
                    pass  # Delay already handled above

            iterations += 1
            if loop_count == 0:  # Infinite loop
                continue

        self.running = False
        if on_finish:
            on_finish()

    def _parse_key(self, key_str):
        # Handle "Key.enter" format
        if key_str.startswith("Key."):
            attr = key_str.split(".")[-1]
            return getattr(keyboard.Key, attr, key_str)

        # Handle "ENTER", "END", "F9" format (from macro_window)
        if hasattr(keyboard.Key, key_str.lower()):
            return getattr(keyboard.Key, key_str.lower())

        # Handle single characters
        return key_str
