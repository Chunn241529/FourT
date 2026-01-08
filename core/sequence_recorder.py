"""
Macro Recorder Core Logic
"""

import time
from pynput import mouse, keyboard


class SequenceRecorder:
    def __init__(self):
        self.events = []
        self.start_time = 0
        self.running = False
        self.mouse_listener = None
        self.keyboard_listener = None

    def start(self):
        self.events = []
        self.start_time = time.time()
        self.running = True

        # Start listeners
        self.mouse_listener = mouse.Listener(
            on_click=self.on_click, on_scroll=self.on_scroll
        )
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_press, on_release=self.on_release
        )

        self.mouse_listener.start()
        self.keyboard_listener.start()

    def stop(self):
        self.running = False
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()

    def add_event(self, event_type, data):
        if not self.running:
            return

        current_time = time.time()
        delay = current_time - self.start_time
        self.start_time = current_time  # Reset for relative delay

        event = {"type": event_type, "delay": delay, "data": data}
        self.events.append(event)

    def on_click(self, x, y, button, pressed):
        action = "pressed" if pressed else "released"
        self.add_event(
            "mouse_click", {"x": x, "y": y, "button": str(button), "action": action}
        )

    def on_scroll(self, x, y, dx, dy):
        self.add_event("mouse_scroll", {"x": x, "y": y, "dx": dx, "dy": dy})

    def on_press(self, key):
        try:
            key_char = key.char
        except AttributeError:
            key_char = str(key)
        self.add_event("key_press", {"key": key_char})

    def on_release(self, key):
        if key == keyboard.Key.esc:
            self.stop()
            return

        try:
            key_char = key.char
        except AttributeError:
            key_char = str(key)
        self.add_event("key_release", {"key": key_char})
