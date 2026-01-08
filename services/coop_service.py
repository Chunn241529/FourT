import threading
import asyncio
import json
import time
from typing import Optional, Callable
import logging

# Ensure websockets is installed
try:
    import websockets
except ImportError:
    websockets = None

from core.config import get_license_server_url


class CoopService:
    _instance = None

    def __init__(self):
        self.ws = None
        self.loop = None
        self.thread = None
        self.is_connected = False
        self.room_code = None
        self.client_id = None
        self.clock_offset = 0  # server_time - local_time
        self.last_state = None
        self.players = []

        # Callbacks
        self.on_state_update = None
        self.on_error = None
        self.on_game_start = None
        self.on_room_created = None
        self.on_song_uploaded = None  # New callback for toasts
        self.on_connected = None

    def upload_song(self, name: str, data_base64: str):
        self.send_action("upload_song", name=name, data=data_base64)

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = CoopService()
        return cls._instance

    def is_available(self):
        return websockets is not None

    def connect(self, room_code: str, client_id: str):
        if not self.is_available():
            if self.on_error:
                self.on_error("Module 'websockets' not installed.")
            return

        if self.is_connected:
            self.disconnect()

        self.room_code = room_code
        self.client_id = client_id

        # Start background thread
        self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.thread.start()

    def disconnect(self):
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._close(), self.loop)
        self.is_connected = False
        # Thread will exit when loop stops? tricky with run_forever.
        # usually easier to just let it die or restart.

    def send_action(self, action_type: str, **kwargs):
        if not self.is_connected or not self.loop:
            return

        msg = {"type": action_type, **kwargs}
        asyncio.run_coroutine_threadsafe(self._send_json(msg), self.loop)

    # --- Async Logic ---

    def _run_async_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connect_routine())
        # self.loop.run_forever()

    async def _connect_routine(self):
        base_url = get_license_server_url()
        # Convert http/https to ws/wss
        if base_url.startswith("https"):
            ws_url = base_url.replace("https", "wss")
        else:
            ws_url = base_url.replace("http", "ws")

        uri = f"{ws_url}/api/coop/ws/{self.room_code}/{self.client_id}"
        print(f"[Coop] Connecting to {uri}")

        try:
            # First, fetch server time for sync (via HTTP)
            # We assume requests is available
            import requests

            try:
                t1 = time.time()
                r = requests.get(f"{base_url}/api/coop/time", timeout=2)
                t2 = time.time()
                server_time = r.json()["time"]
                # RTT/2 latency assumption
                estimated_server_time = server_time + (t2 - t1) / 2
                self.clock_offset = estimated_server_time - t2
                print(f"[Coop] Clock Offset: {self.clock_offset:.4f}s")
            except Exception as e:
                print(f"[Coop] Time sync failed: {e}")

            async with websockets.connect(uri) as websocket:
                self.ws = websocket
                self.is_connected = True
                print("[Coop] Connected!")
                if self.on_connected:
                    self.on_connected()

                async for message in websocket:
                    data = json.loads(message)
                    self._handle_message(data)

        except Exception as e:
            print(f"[Coop] Connection error: {e}")
            self.is_connected = False
            if self.on_error:
                self.on_error(str(e))
        finally:
            self.is_connected = False

    async def _send_json(self, data):
        if self.ws:
            try:
                await self.ws.send(json.dumps(data))
            except Exception as e:
                print(f"[Coop] Send error: {e}")

    async def _close(self):
        if self.ws:
            await self.ws.close()

    def _handle_message(self, data):
        msg_type = data.get("type")

        if msg_type == "room_created":
            if self.on_room_created:
                self.on_room_created(data.get("code"))

        elif msg_type == "state_update":
            self.last_state = data
            self.players = data.get("players", [])
            if self.on_state_update:
                self.on_state_update(data)

        elif msg_type == "game_start":
            start_at = data.get("start_at")
            if self.on_game_start:
                # Calculate wait time adjusted for clock offset
                # start_at is in Server Time
                # Local Time needed = start_at - offset
                local_start_time = start_at - self.clock_offset
                wait_seconds = local_start_time - time.time()
                self.on_game_start(max(0, wait_seconds))

        elif msg_type == "song_uploaded":
            if self.on_song_uploaded:
                self.on_song_uploaded(data.get("name"), data.get("uploader"))

        elif msg_type == "pong":
            pass


def get_coop_service():
    return CoopService.get_instance()
