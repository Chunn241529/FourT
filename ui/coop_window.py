import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import threading
import time
import base64
import os

from .components import FramelessWindow
from .theme import (
    COLORS,
    FONTS,
    ModernButton,
    GradientCard,
    RoundedCard,
    LoadingSpinner,
    RoundedButton,
    colors,
)
from .i18n import t
from services.coop_service import get_coop_service


class CoopWindow(FramelessWindow):
    """
    Real-time Co-op Room Window
    """

    def __init__(self, parent, on_start_playback=None):
        super().__init__(
            parent.winfo_toplevel(), title="Chế độ Co-op", width=400, height=550
        )
        self.parent = parent
        self.on_start_playback = on_start_playback
        self.service = get_coop_service()

        # State
        self.client_id = str(int(time.time() * 1000))[-6:]  # Simple ID
        self.room_code = ""
        self.players = []
        self.is_playing = False
        self.loaded_song_name = None
        self.pending_name = None

        # Callbacks
        self.service.on_state_update = self._on_state_update
        self.service.on_room_created = self._on_room_created
        self.service.on_error = self._on_error
        self.service.on_game_start = self._on_game_start
        self.service.on_song_uploaded = self._on_song_uploaded
        self.service.on_connected = self._on_connected

        self.container = tk.Frame(self.content_frame, bg=COLORS["bg"])
        self.container.pack(fill="both", expand=True, padx=20, pady=20)

        if not self.service.is_available():
            self._show_install_prompt()
        elif self.service.is_connected:
            # Restore state
            self.room_code = self.service.room_code
            self.client_id = self.service.client_id
            self.players = self.service.players
            self._show_room()
        else:
            self._show_lobby()

    # ... (omitting lines for brevity, need to be careful with replace_file_content target)

    def _join_room(self):
        code = self.code_entry.get().strip().upper()
        name = self.name_entry.get().strip()
        if not code or len(code) != 6:
            messagebox.showerror("Lỗi", "Mã phòng phải có 6 ký tự")
            return

        self.client_id = str(int(time.time() * 1000))[-6:]  # Regenerate
        self.pending_name = name
        self.service.connect(code, self.client_id)
        self.room_code = code

    def _create_room(self):
        name = self.name_entry.get().strip()
        self.client_id = str(int(time.time() * 1000))[-6:]
        self.pending_name = name
        self.service.connect("NEW", self.client_id)  # Special code

    def _show_install_prompt(self):
        for w in self.container.winfo_children():
            w.destroy()

        tk.Label(
            self.container,
            text="⚠️ Thiếu Thư Viện",
            font=FONTS["h2"],
            bg=COLORS["bg"],
            fg=COLORS["error"],
        ).pack(pady=20)
        tk.Label(
            self.container,
            text="Chức năng Co-op cần thư viện 'websockets'.",
            font=FONTS["body"],
            bg=COLORS["bg"],
            fg=COLORS["fg_dim"],
        ).pack()
        tk.Label(
            self.container,
            text="Vui lòng chạy lệnh sau trong terminal:",
            font=FONTS["body"],
            bg=COLORS["bg"],
            fg=COLORS["fg_dim"],
        ).pack(pady=10)

        entry = tk.Entry(
            self.container,
            font=("Consolas", 10),
            bg=COLORS["input_bg"],
            fg=COLORS["accent"],
            justify="center",
        )
        entry.insert(0, "pip install websockets")
        entry.pack(fill="x", pady=5)

        ModernButton(
            self.container, text="Đã Hiểu", command=self.destroy, kind="secondary"
        ).pack(pady=20)

    def _show_lobby(self):
        # Fade out existing children
        self._animate_clear()

        # Center Card
        card = RoundedCard(
            self.container, width=320, height=500, radius=20, bg=COLORS["bg"]
        )
        card.pack(expand=True)

        inner = card.content

        # Header with Icon
        tk.Label(
            inner,
            text="👥",
            font=("Segoe UI Emoji", 42),
            bg=COLORS["card"],
            fg=COLORS["accent"],
        ).pack(pady=(5, 0))

        tk.Label(
            inner,
            text="Co-op MIDI",
            font=("Segoe UI", 20, "bold"),
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(pady=(0, 10))

        # Name Input
        tk.Label(
            inner,
            text="Tên hiển thị",
            font=FONTS["small"],
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
            anchor="w",
        ).pack(fill="x", padx=20, pady=(5, 0))

        self.name_entry = tk.Entry(
            inner,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
            insertbackground=COLORS["accent"],
        )
        self.name_entry.pack(fill="x", padx=20, pady=(5, 10), ipady=8)
        self.name_entry.insert(0, f"Player {self.client_id[:4]}")

        # Code Input
        tk.Label(
            inner,
            text="Mã phòng (Nếu có)",
            font=FONTS["small"],
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
            anchor="w",
        ).pack(fill="x", padx=20, pady=(5, 0))

        self.code_entry = tk.Entry(
            inner,
            font=("Consolas", 14, "bold"),
            bg=COLORS["input_bg"],
            fg=COLORS["accent"],
            justify="center",
            relief="flat",
            highlightthickness=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
            insertbackground=COLORS["accent"],
        )
        self.code_entry.pack(fill="x", padx=20, pady=(5, 15), ipady=8)

        # Buttons
        btn_frame = tk.Frame(inner, bg=COLORS["card"])
        btn_frame.pack(fill="x", padx=20, pady=5)

        RoundedButton(
            btn_frame,
            text="Tham Gia",
            command=self._join_room,
            kind="primary",
            width=260,
            height=45,
            radius=22,
        ).pack(fill="x", pady=5)

        RoundedButton(
            btn_frame,
            text="Tạo Phòng Mới",
            command=self._create_room,
            kind="secondary",
            width=260,
            height=45,
            radius=22,
        ).pack(fill="x", pady=5)

    def _animate_clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def _set_loading(self, is_loading, text="Đang kết nối..."):
        if is_loading:
            self.loading_overlay = tk.Frame(
                self.content_frame, bg="black"
            )  # Semi-transparent hack requires Toplevel usually
            # But we can just overlay opaque for now
            self.loading_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

            spinner = LoadingSpinner(self.loading_overlay, bg="black")
            spinner.place(relx=0.5, rely=0.4, anchor="center")
            spinner.start()

            tk.Label(
                self.loading_overlay,
                text=text,
                font=FONTS["body"],
                fg="white",
                bg="black",
            ).place(relx=0.5, rely=0.55, anchor="center")
        else:
            if hasattr(self, "loading_overlay") and self.loading_overlay:
                self.loading_overlay.destroy()
                self.loading_overlay = None

    def _show_room(self):
        for w in self.container.winfo_children():
            w.destroy()

        # Room Header
        header = tk.Frame(self.container, bg=COLORS["bg"])
        header.pack(fill="x", pady=(0, 15))

        # Exit button (Right)
        ModernButton(
            header, text="🚪", command=self._leave_room, kind="danger", width=4
        ).pack(side="right")

        # Room Info (Left - Rounded Chip style)
        code_chip = RoundedCard(
            header, width=150, height=36, radius=18, bg=COLORS["input_bg"]
        )
        code_chip.pack(side="left")

        # Inner content hack for placement center (RoundedCard centers its content frame)
        cc_inner = code_chip.content
        cc_inner.configure(bg=COLORS["input_bg"])

        tk.Label(
            cc_inner,
            text="Phòng:",
            font=FONTS["small"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg_dim"],
        ).pack(side="left", padx=(10, 5))

        code_lbl = tk.Label(
            cc_inner,
            text=self.room_code,
            font=("Consolas", 14, "bold"),
            bg=COLORS["input_bg"],
            fg=COLORS["accent"],
        )
        code_lbl.pack(side="left", padx=(0, 10))
        code_lbl.bind("<Button-1>", lambda e: self._copy_code())
        code_chip.bind("<Button-1>", lambda e: self._copy_code())

        # Player List Header
        tk.Label(
            self.container,
            text=f"Thành viên ({len(self.players)})",
            font=FONTS["bold"],
            bg=COLORS["bg"],
            fg=COLORS["fg_dim"],
        ).pack(anchor="w", pady=(10, 5))

        # Player List Container (Scrollable? For now just stacked RoundedCards)
        self.list_frame = tk.Frame(self.container, bg=COLORS["bg"])
        self.list_frame.pack(fill="both", expand=True)

        # --- Song Info Section ---
        song_card = RoundedCard(
            self.container, width=360, height=70, radius=15, bg=COLORS["card"]
        )
        song_card.pack(fill="x", pady=(0, 10))
        sf_inner = song_card.content

        # Icon
        tk.Label(
            sf_inner,
            text="🎵",
            font=("Segoe UI Emoji", 20),
            bg=COLORS["card"],
            fg=COLORS["accent"],
        ).pack(side="left", padx=10)

        # Upload Button (Right)
        ModernButton(
            sf_inner,
            text="Upload",
            command=self._upload_midi,
            kind="secondary",
            width=8,
        ).pack(side="right", padx=10)

        # Song Name (Truncate if too long)
        current_song = (
            self.service.last_state.get("song_name")
            if self.service.last_state
            else None
        )
        display_name = current_song if current_song else "Chưa có bài hát"

        if len(display_name) > 20:
            display_name = display_name[:17] + "..."

        fg_color = COLORS["fg"] if current_song else COLORS["fg_dim"]

        info_box = tk.Frame(sf_inner, bg=COLORS["card"])
        info_box.pack(side="left", fill="x", expand=True)

        tk.Label(
            info_box,
            text="Đang phát:",
            font=("Segoe UI", 8),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
        ).pack(anchor="w")

        tk.Label(
            info_box,
            text=display_name,
            font=("Segoe UI", 11, "bold"),
            bg=COLORS["card"],
            fg=fg_color,
        ).pack(anchor="w")

        self.after(0, self._render_players)

        # Controls Footer
        footer = tk.Frame(self.container, bg=COLORS["bg"])
        footer.pack(fill="x", pady=(15, 0))

        # Role Toggles
        role_frame = tk.Frame(footer, bg=COLORS["bg"])
        role_frame.pack(fill="x", pady=(0, 10))

        tk.Label(
            role_frame,
            text="Vai Trò:",
            font=FONTS["bold"],
            bg=COLORS["bg"],
            fg=COLORS["fg_dim"],
        ).pack(side="left")

        # Get my current role
        my_role = 1
        me = next((p for p in self.players if p["id"] == self.client_id), None)
        if me:
            my_role = me["role"]

        ModernButton(
            role_frame,
            text="👐 Both",
            command=lambda: self._set_role(0),
            kind="accent" if my_role == 0 else "secondary",
            width=12,
        ).pack(side="left", padx=(0, 10))
        ModernButton(
            role_frame,
            text="🤚L (Bass)",
            command=lambda: self._set_role(1),
            kind="accent" if my_role == 1 else "secondary",
            width=12,
        ).pack(side="left", padx=0)
        ModernButton(
            role_frame,
            text="🤚R (Melody)",
            command=lambda: self._set_role(2),
            kind="accent" if my_role == 2 else "secondary",
            width=12,
        ).pack(side="left", padx=10)

        # Ready/Start
        action_frame = tk.Frame(footer, bg=COLORS["bg"])
        action_frame.pack(fill="x")

        is_ready = me["is_ready"] if me else False
        is_host = me["is_host"] if me else False

        ModernButton(
            action_frame,
            text="Sẵn Sàng" if not is_ready else "Hủy Sẵn Sàng",
            command=lambda: self._set_ready(not is_ready),
            kind="success" if is_ready else "secondary",
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))

        if is_host:
            all_ready = all(p["is_ready"] for p in self.players)
            has_song = bool(
                self.service.last_state and self.service.last_state.get("song_name")
            )

            can_start = all_ready and has_song

            self.start_btn = ModernButton(
                action_frame,
                text="Bắt Đầu Game",
                command=self._start_match,
                kind="primary" if can_start else "secondary",
                state="normal" if can_start else "disabled",
            )  # Disable if not all ready? optional
            self.start_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))

    def _render_players(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        for p in self.players:
            card = GradientCard(self.list_frame)
            card.pack(fill="x", pady=4)
            card.configure(height=50)  # Force height

            row = tk.Frame(card.content, bg=COLORS["card"])
            row.pack(fill="both", expand=True, padx=10)

            # Ready Status (Pack RIGHT first)
            status = "✅ Sẵn Sàng" if p["is_ready"] else "⏳ Đang Chờ"
            color = COLORS["success"] if p["is_ready"] else COLORS["fg_dim"]
            tk.Label(
                row, text=status, font=("Segoe UI", 10), bg=COLORS["card"], fg=color
            ).pack(side="right", padx=(10, 0))

            # Role Icon (Left)
            if p["role"] == 0:
                role_icon = "👐"
            elif p["role"] == 1:
                role_icon = "🤚L"
            else:
                role_icon = "🤚R"

            tk.Label(
                row,
                text=role_icon,
                font=("Segoe UI Emoji", 14),
                bg=COLORS["card"],
                fg=COLORS["fg"],
            ).pack(side="left")

            # Name (Fill remaining space)
            name_txt = (
                p["name"]
                + (" (Host)" if p["is_host"] else "")
                + (" (Bạn)" if p["id"] == self.client_id else "")
            )
            tk.Label(
                row,
                text=name_txt,
                font=("Segoe UI", 11, "bold"),
                bg=COLORS["card"],
                fg=COLORS["fg"],
                anchor="w",
            ).pack(side="left", padx=10, fill="x", expand=True)

    # --- Actions ---

    def _join_room(self):
        code = self.code_entry.get().strip().upper()
        name = self.name_entry.get().strip()
        if not code or len(code) != 6:
            messagebox.showerror("Lỗi", "Mã phòng phải có 6 ký tự")
            return

        self.client_id = str(int(time.time() * 1000))[-6:]  # Regenerate
        self.pending_name = name
        self.service.connect(code, self.client_id)
        self.room_code = code

    def _create_room(self):
        name = self.name_entry.get().strip()
        self.client_id = str(int(time.time() * 1000))[-6:]
        self.pending_name = name
        self.service.connect("NEW", self.client_id)  # Special code

    def _leave_room(self):
        self.service.disconnect()
        self._show_lobby()

    def _set_role(self, role):
        self.service.send_action("set_role", role=role)

    def _set_ready(self, ready):
        self.service.send_action("set_ready", ready=ready)

    def _start_match(self):
        self.service.send_action("start_match")

    def _copy_code(self):
        self.clipboard_clear()
        self.clipboard_append(self.room_code)
        messagebox.showinfo("Copy", "Đã copy mã phòng!")

    # --- Callbacks ---

    def _on_error(self, error):
        self.after(0, lambda: messagebox.showerror("Lỗi Loop", str(error)))

    def _on_connected(self):
        if self.pending_name:
            self.service.send_action("set_name", name=self.pending_name)
            self.pending_name = None

    def _on_room_created(self, code):
        self.room_code = code
        self.after(0, self._show_room)

    def _on_state_update(self, data):
        self.room_code = data.get("room_code")
        self.players = data.get("players", [])
        self.is_playing = data.get("is_playing", False)

        # Check for new song data
        song_name = data.get("song_name")
        song_data = data.get("song_data")

        # Only process if we have data AND it's different from what we loaded
        if song_name and song_data:
            if song_name != self.loaded_song_name:
                self._handle_new_song(song_name, song_data)

        self.after(0, self._show_room)

    def _handle_new_song(self, name, data_b64):
        # Avoid reloading if same (double check)
        if name == self.loaded_song_name:
            return

        try:
            temp_dir = "temp"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            else:
                # Clear existing files in temp
                for f in os.listdir(temp_dir):
                    fp = os.path.join(temp_dir, f)
                    try:
                        if os.path.isfile(fp):
                            os.unlink(fp)
                    except Exception as e:
                        print(f"Error deleting {fp}: {e}")

            # Use a fixed name for the file on disk to avoid clutter,
            # BUT we rely on 'name' param for duplication check.
            # Maybe use name in filename to avoid lock issues?
            # Let's try sticking to fixed filename first, but ensure we update tracking var.
            temp_path = os.path.join(temp_dir, "coop_song.mid")

            with open(temp_path, "wb") as f:
                f.write(base64.b64decode(data_b64))

            # Tell parent to load it WITHOUT playing
            if hasattr(self.parent, "playlist"):
                self.after(0, lambda: self._load_song_safe(temp_path, name))
                # Update tracker immediately
                self.loaded_song_name = name

        except Exception as e:
            print(f"Error saving song: {e}")

    def _load_song_safe(self, path, name):
        if hasattr(self.parent, "playlist"):
            # Clear previous songs to keep playlist clean for Co-op
            self.parent.playlist.clear()

            # Add to playlist
            self.parent.playlist.add_song(path, name)

            # Select it (last one)
            count = self.parent.playlist.get_song_count()
            if count > 0:
                self.parent.playlist.set_current_index(count - 1)

            # Ensure engine is stopped initially
            if hasattr(self.parent, "playback_engine"):
                self.parent.playback_engine.stop()  # Don't auto play

    def _on_game_start(self, wait_seconds):
        self.after(0, lambda: self._start_countdown(wait_seconds))

    def _start_countdown(self, wait_seconds):
        # Create overlay
        overlay = tk.Toplevel(self)
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-topmost", True)
        overlay.configure(bg="black")
        overlay.attributes("-alpha", 0.8)

        lbl = tk.Label(
            overlay, text="3", font=("Segoe UI", 72, "bold"), bg="black", fg="white"
        )
        lbl.place(relx=0.5, rely=0.5, anchor="center")

        # Setup precise start
        target_time = time.time() + wait_seconds

        def update_timer():
            remaining = target_time - time.time()
            if remaining <= 0:
                overlay.destroy()
                self._trigger_play()
                return

            if remaining < 1:
                lbl.config(text="GO!", fg=COLORS["success"])
            else:
                lbl.config(text=f"{int(remaining)}", fg="white")

            overlay.after(50, update_timer)

        update_timer()

    def _upload_midi(self):
        file_path = filedialog.askopenfilename(
            title="Chọn File MIDI", filetypes=[("MIDI Files", "*.mid *.midi")]
        )
        if not file_path:
            return

        try:
            filename = os.path.basename(file_path)
            with open(file_path, "rb") as f:
                data = f.read()
                data_b64 = base64.b64encode(data).decode("utf-8")

            self.service.upload_song(filename, data_b64)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc file: {e}")

    def _on_song_uploaded(self, name, uploader):
        # Toast notification logic could go here, for now just simple print/log or ignore
        # State update handles the UI refresh
        pass

    def _trigger_play(self):
        # Auto-focus game window
        try:
            from core.window_utils import focus_game_window

            focus_game_window()
        except Exception as e:
            print(f"Error focusing window: {e}")

        # Enforce Role
        try:
            me = next((p for p in self.players if p["id"] == self.client_id), None)
            if me and hasattr(self.parent, "playback_engine"):
                role = me["role"]  # 1=L, 2=R
                self.parent.playback_engine.set_hand_mode(role)
                self.parent.hand_mode = role
                self.parent._update_mode_buttons()  # Ensure UI reflects
        except:
            pass

        if self.on_start_playback:
            self.on_start_playback()
