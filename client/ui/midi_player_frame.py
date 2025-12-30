"""
MIDI Auto Player - Main UI (Merged with Playlist)
Modern UI with playback, playlist, speed control, MP3 conversion
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import os
import threading

from core.config import *
from core import preprocess_midi
from .theme import colors, FONTS, ModernButton, GradientCard, COLORS
from .animations import FadeEffect, hex_to_rgb, rgb_to_hex
from services.playlist_service import get_playlist_service, PlaylistService
from .i18n import t


class SongListItem(tk.Frame):
    """Individual song item with hover animation"""

    def __init__(
        self,
        parent,
        index,
        song,
        is_current=False,
        on_click=None,
        on_remove=None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.configure(bg=colors["card"], cursor="hand2")

        self.index = index
        self.song = song
        self.is_current = is_current
        self.on_click = on_click
        self.on_remove = on_remove
        self._hover = False

        # Highlight for current song
        self.indicator = tk.Frame(
            self, width=3, bg=colors["accent"] if is_current else colors["card"]
        )
        self.indicator.pack(side="left", fill="y")

        # Content
        content = tk.Frame(self, bg=colors["card"])
        content.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        # Index
        self.index_label = tk.Label(
            content,
            text=f"{index + 1}.",
            font=("Segoe UI", 10),
            bg=colors["card"],
            fg=colors["accent"] if is_current else colors["fg_dim"],
            width=3,
            anchor="e",
        )
        self.index_label.pack(side="left")

        # Now playing indicator
        self.play_icon = tk.Label(
            content,
            text="▶" if is_current else "  ",
            font=("Segoe UI", 8),
            bg=colors["card"],
            fg=colors["accent"],
            width=2,
        )
        self.play_icon.pack(side="left", padx=(5, 0))

        # Song name - truncate if too long
        name = song.get("name", "Unknown")
        max_len = 25
        if len(name) > max_len:
            name = name[: max_len - 3] + "..."

        self.name_label = tk.Label(
            content,
            text=name,
            font=("Segoe UI", 10, "bold") if is_current else ("Segoe UI", 10),
            bg=colors["card"],
            fg=colors["fg"] if is_current else colors["fg_dim"],
            anchor="w",
        )
        self.name_label.pack(side="left", fill="x", expand=True, padx=(8, 0))

        # Remove button (hidden until hover)
        self.remove_btn = tk.Label(
            self,
            text="✕",
            font=("Segoe UI", 10),
            bg=colors["card"],
            fg=colors["card"],
            cursor="hand2",
            width=3,
        )
        self.remove_btn.pack(side="right", padx=5)

        # Bind events
        for widget in [
            self,
            content,
            self.index_label,
            self.play_icon,
            self.name_label,
        ]:
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
            widget.bind("<Button-1>", self._on_click)
            widget.bind("<Double-Button-1>", self._on_double_click)

        self.remove_btn.bind("<Enter>", self._on_remove_enter)
        self.remove_btn.bind("<Leave>", self._on_remove_leave)
        self.remove_btn.bind("<Button-1>", self._on_remove_click)

    def _on_enter(self, e):
        self._hover = True
        self.configure(bg=colors["card_hover"])
        for w in [self.indicator, self.index_label, self.play_icon, self.name_label]:
            try:
                w.configure(bg=colors["card_hover"])
            except:
                pass
        self.remove_btn.configure(fg=colors["fg_dim"], bg=colors["card_hover"])

    def _on_leave(self, e):
        self._hover = False
        bg = colors["card"]
        self.configure(bg=bg)
        for w in [
            self.indicator,
            self.index_label,
            self.play_icon,
            self.name_label,
            self.remove_btn,
        ]:
            try:
                w.configure(bg=bg)
            except:
                pass
        self.remove_btn.configure(fg=bg)
        self.indicator.configure(
            bg=colors["accent"] if self.is_current else colors["card"]
        )

    def _on_remove_enter(self, e):
        self.remove_btn.configure(fg=colors["error"])

    def _on_remove_leave(self, e):
        if self._hover:
            self.remove_btn.configure(fg=colors["fg_dim"])

    def _on_click(self, e):
        if self.on_click:
            self.on_click(self.index)

    def _on_double_click(self, e):
        if self.on_click:
            self.on_click(self.index, play=True)

    def _on_remove_click(self, e):
        if self.on_remove:
            self.on_remove(self.index)


class ToggleButton(tk.Canvas):
    """Animated toggle button"""

    def __init__(
        self, parent, text, command=None, active=False, width=50, height=32, **kwargs
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=colors["card"],
            highlightthickness=0,
            **kwargs,
        )
        self.text = text
        self.command = command
        self._active = active
        self._width = width
        self._height = height
        self._hover = False
        self._draw()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _draw(self):
        self.delete("all")
        w, h, r = self._width, self._height, 6

        if self._active:
            fill, text_color = colors["card"], colors["accent"]
        elif self._hover:
            fill, text_color = colors["card_hover"], colors["fg"]
        else:
            fill, text_color = colors["card"], colors["fg_dim"]

        points = [
            r,
            0,
            w - r,
            0,
            w,
            0,
            w,
            r,
            w,
            h - r,
            w,
            h,
            w - r,
            h,
            r,
            h,
            0,
            h,
            0,
            h - r,
            0,
            r,
            0,
            0,
        ]
        self.create_polygon(points, smooth=True, fill=fill, outline="")
        self.create_text(
            w / 2, h / 2, text=self.text, fill=text_color, font=("Segoe UI Emoji", 11)
        )
        self.config(cursor="hand2")

    def _on_enter(self, e):
        self._hover = True
        self._draw()

    def _on_leave(self, e):
        self._hover = False
        self._draw()

    def _on_click(self, e):
        if self.command:
            self.command()

    def set_active(self, active):
        self._active = active
        self._draw()

    def set_text(self, text):
        self.text = text
        self._draw()


class MidiPlayerFrame(tk.Frame):
    """Main MIDI Player UI - Merged with Playlist functionality"""

    def __init__(
        self, parent, playback_engine, library_service, update_service, **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.configure(bg=colors["bg"])

        self.playback_engine = playback_engine
        self.library_service = library_service
        self.update_service = update_service
        self.current_midi_path = None
        self.generated_events = None
        self.auto_transpose = True
        self.script_viewer_window = None  # Track script viewer window
        self.stop_all_requested = False  # Flag to prevent auto-advance after stop all

        self.playlist = get_playlist_service()
        self.playlist.set_on_playlist_change(self._refresh_list)
        self.playlist.set_on_song_change(self._on_song_change)

        self._create_widgets()
        self._refresh_list()

    def _create_widgets(self):
        """Create modern UI"""

        # ===== HEADER =====
        header = tk.Frame(self, bg=colors["bg"])
        header.pack(fill="x", padx=15, pady=(15, 10))

        # Title
        title_frame = tk.Frame(header, bg=colors["bg"])
        title_frame.pack(side="left")

        tk.Label(
            title_frame,
            text="🎹",
            font=("Segoe UI Emoji", 18),
            bg=colors["bg"],
            fg=colors["accent"],
        ).pack(side="left")
        tk.Label(
            title_frame,
            text="MIDI Auto Player",
            font=("Segoe UI", 16, "bold"),
            bg=colors["bg"],
            fg=colors["fg"],
        ).pack(side="left", padx=(8, 0))

        # Add button
        self.add_btn = ModernButton(
            header,
            text=f"+ {t('add')}",
            command=self._show_add_menu,
            kind="accent",
            width=8,
        )
        self.add_btn.pack(side="right")

        # ===== SONG LIST =====
        list_container = GradientCard(self)
        list_container.pack(fill="x", padx=15, pady=8)
        list_container.configure(height=160)  # Height for empty state + 3 songs
        list_container.pack_propagate(False)

        self.canvas = tk.Canvas(
            list_container.content, bg=colors["card"], highlightthickness=0, bd=0
        )
        self.scrollbar = ttk.Scrollbar(
            list_container.content, orient="vertical", command=self.canvas.yview
        )

        self.songs_frame = tk.Frame(self.canvas, bg=colors["card"])
        self._songs_window_id = self.canvas.create_window(
            (0, 0), window=self.songs_frame, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # ===== CONTROLS =====
        controls_card = GradientCard(self)
        controls_card.pack(fill="x", padx=15, pady=10)

        controls_row = tk.Frame(controls_card.content, bg=colors["card"])
        controls_row.pack(fill="x")

        # Left: Playback
        playback_frame = tk.Frame(controls_row, bg=colors["card"])
        playback_frame.pack(side="left")

        self.prev_btn = ToggleButton(
            playback_frame, "⏮", command=self._prev_song, width=42, height=36
        )
        self.prev_btn.pack(side="left", padx=2)

        self.play_btn = ToggleButton(
            playback_frame,
            "▶",
            command=self._play_current,
            active=True,
            width=42,
            height=36,
        )
        self.play_btn.pack(side="left", padx=2)

        self.next_btn = ToggleButton(
            playback_frame, "⏭", command=self._next_song, width=42, height=36
        )
        self.next_btn.pack(side="left", padx=2)

        # Separator
        tk.Frame(playback_frame, width=1, bg=colors["border"]).pack(
            side="left", fill="y", padx=8
        )

        # Preview button
        self.preview_btn = ToggleButton(
            playback_frame, "👁️", command=self._generate_script, width=42, height=36
        )
        self.preview_btn.pack(side="left", padx=2)

        # Speed label (clickable)
        self.current_speed = DEFAULT_PLAYBACK_SPEED
        self.speed_label = tk.Label(
            playback_frame,
            text=f"{self.current_speed:.1f}x",
            font=("Segoe UI", 11, "bold"),
            bg=colors["card"],
            fg=colors["accent"],
            cursor="hand2",
        )
        self.speed_label.pack(side="left", padx=(8, 2))
        self.speed_label.bind("<Button-1>", self._on_speed_click)

        # Right: Mode toggles
        mode_frame = tk.Frame(controls_row, bg=colors["card"])
        mode_frame.pack(side="right")

        self.shuffle_btn = ToggleButton(
            mode_frame,
            "🔀",
            command=self._toggle_shuffle,
            active=self.playlist.shuffle_enabled,
            width=42,
            height=36,
        )
        self.shuffle_btn.pack(side="left", padx=2)

        self.repeat_btn = ToggleButton(
            mode_frame,
            "🔁",
            command=self._toggle_repeat,
            active=self.playlist.repeat_mode != PlaylistService.REPEAT_NONE,
            width=42,
            height=36,
        )
        self.repeat_btn.pack(side="left", padx=2)

        # ===== STATUS =====
        status_frame = tk.Frame(self, bg=colors["bg"])
        status_frame.pack(fill="x", padx=15)

        self.status_label = tk.Label(
            status_frame,
            text=t("ready"),
            font=("Segoe UI", 10),
            bg=colors["bg"],
            fg=colors["fg_dim"],
        )
        self.status_label.pack(side="left")

        # ===== FOOTER =====
        footer = tk.Frame(self, bg=colors["bg"])
        footer.pack(fill="x", padx=15, pady=(5, 15))

        self.count_label = tk.Label(
            footer,
            text="0 bài",
            font=("Segoe UI", 9),
            bg=colors["bg"],
            fg=colors["fg_dim"],
        )
        self.count_label.pack(side="left")

        actions = tk.Frame(footer, bg=colors["bg"])
        actions.pack(side="right")

        ModernButton(
            actions,
            text="💾",
            command=self._save_playlist,
            kind="secondary",
            width=4,
            font=("Segoe UI Emoji", 11),
        ).pack(side="left", padx=2)
        ModernButton(
            actions,
            text="📂",
            command=self._load_playlist,
            kind="secondary",
            width=4,
            font=("Segoe UI Emoji", 11),
        ).pack(side="left", padx=2)
        self.clear_btn = ModernButton(
            actions,
            text="🗑",
            command=self._clear_playlist,
            kind="secondary",
            width=4,
            font=("Segoe UI Emoji", 11),
        )
        self.clear_btn.pack(side="left", padx=2)

        # Community button - open MIDI sharing community
        self.community_btn = ModernButton(
            actions,
            text="🌐",
            command=self._open_community,
            kind="secondary",
            width=4,
            font=("Segoe UI Emoji", 11),
        )
        self.community_btn.pack(side="left", padx=2)

        self.stop_all_btn = ModernButton(
            actions,
            text="⏹",
            command=self._stop_all,
            kind="danger",
            width=4,
            font=("Segoe UI Emoji", 11),
        )
        self.stop_all_btn.pack(side="left", padx=2)

    # ==================== UI Updates ====================

    def _on_mousewheel(self, event):
        if self.playlist.get_song_count() > 0:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._songs_window_id, width=event.width)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _refresh_list(self):
        for widget in self.songs_frame.winfo_children():
            widget.destroy()

        songs = self.playlist.get_all_songs()
        current_idx = self.playlist.get_current_index()

        if not songs:
            tk.Label(
                self.songs_frame,
                text=t("playlist_empty"),
                font=("Segoe UI", 11),
                bg=colors["card"],
                fg=colors["fg_dim"],
                justify="center",
                anchor="center",
            ).pack(fill="both", expand=True)
        else:
            is_playing = self.playback_engine.is_active()
            for i, song in enumerate(songs):
                SongListItem(
                    self.songs_frame,
                    index=i,
                    song=song,
                    is_current=(i == current_idx),
                    on_click=self._on_song_click,
                    on_remove=self._on_song_remove if not is_playing else None,
                ).pack(fill="x", pady=1)
        # Update count with truncation
        count = len(songs)
        if count > 0 and current_idx >= 0:
            name = songs[current_idx].get("name", "")
            if len(name) > 20:
                name = name[:17] + "..."
            self.count_label.config(text=t("songs_with_name", count=count, name=name))
        else:
            self.count_label.config(text=t("songs", count=count))
        self._update_mode_buttons()
        self._update_playback_state()
        self.songs_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_song_change(self, song):
        self._refresh_list()
        current_idx = self.playlist.get_current_index()
        if current_idx >= 0:
            self.canvas.yview_moveto(
                current_idx / max(1, self.playlist.get_song_count())
            )

    def _update_mode_buttons(self):
        self.shuffle_btn.set_active(self.playlist.shuffle_enabled)
        mode = self.playlist.repeat_mode
        if mode == PlaylistService.REPEAT_NONE:
            self.repeat_btn.set_active(False)
            self.repeat_btn.set_text("🔁")
        elif mode == PlaylistService.REPEAT_ALL:
            self.repeat_btn.set_active(True)
            self.repeat_btn.set_text("🔁")
        else:
            self.repeat_btn.set_active(True)
            self.repeat_btn.set_text("🔂")

    def _update_playback_state(self):
        """Update UI based on playback state"""
        is_playing = self.playback_engine.is_active()
        # Disable clear button when playing
        if is_playing:
            self.clear_btn.configure(state="disabled")
            self.stop_all_btn.configure(state="normal")
        else:
            self.clear_btn.configure(state="normal")
            # Keep stop button enabled if user might want to stop

    def _stop_all(self):
        """Stop playback and prevent auto-advance"""
        self.stop_all_requested = True  # Prevent auto-advance
        if self.playback_engine.is_active():
            self.playback_engine.stop()
        self.play_btn.set_text("▶")
        self.status_label.config(text=t("stopped_all"), fg=colors["warning"])
        self._refresh_list()

    def _open_community(self):
        """Open the MIDI community page in browser"""
        import webbrowser
        from core.config import get_community_url

        try:
            url = get_community_url()
            webbrowser.open(url)
            self.status_label.config(text=t("opening_community"), fg=colors["accent"])
        except Exception as e:
            print(f"[Community] Error opening: {e}")
            self.status_label.config(text="Không thể mở Community", fg=colors["error"])

    def _update_speed(self, speed):
        """Update speed value"""
        self.current_speed = float(speed)
        self.speed_label.config(text=f"{self.current_speed:.1f}x")
        self.playback_engine.set_speed(self.current_speed)

    def _on_speed_click(self, event):
        """Show dialog to enter speed"""
        result = simpledialog.askfloat(
            "Tốc độ phát",
            f"Nhập tốc độ ({MIN_PLAYBACK_SPEED:.1f} - {MAX_PLAYBACK_SPEED:.1f}):",
            initialvalue=self.current_speed,
            minvalue=MIN_PLAYBACK_SPEED,
            maxvalue=MAX_PLAYBACK_SPEED,
            parent=self,
        )
        if result is not None:
            self._update_speed(result)

    def _on_canvas_configure(self, event):
        """Handle canvas resize - update songs_frame width"""
        self.canvas.itemconfig(self._songs_window_id, width=event.width)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling"""
        # Only scroll if content exceeds visible area
        bbox = self.canvas.bbox("all")
        if bbox and bbox[3] > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ==================== Add Songs ====================

    def _show_add_menu(self):
        menu = tk.Menu(
            self,
            tearoff=0,
            bg=colors["card"],
            fg=colors["fg"],
            activebackground=colors["accent"],
            activeforeground="white",
            font=("Segoe UI", 10),
            bd=0,
        )
        menu.add_command(label=t("from_library"), command=self._add_from_library)
        menu.add_command(label=t("browse_file"), command=self._add_from_file)
        menu.add_separator()
        menu.add_command(label=t("mp3_to_midi"), command=self._convert_mp3_to_midi)

        try:
            x = self.add_btn.winfo_rootx()
            y = self.add_btn.winfo_rooty() + self.add_btn.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _add_from_library(self):
        from .midi_library_window import MidiLibraryWindow

        MidiLibraryWindow(self, self.library_service, self.playlist)

    def _add_from_file(self):
        paths = filedialog.askopenfilenames(
            filetypes=[("MIDI files", "*.mid *.midi")], title="Chọn file MIDI"
        )
        for path in paths:
            self.playlist.add_song(path)

    def _convert_mp3_to_midi(self):
        """Convert MP3/audio to MIDI via server"""
        from feature_manager import get_feature_manager

        fm = get_feature_manager()
        if not fm.has_feature(Features.MP3_CONVERSION):
            messagebox.showinfo(t("upgrade_premium"), t("mp3_upgrade"))
            return

        path = filedialog.askopenfilename(
            title="Chọn file âm thanh",
            filetypes=[("Audio files", "*.mp3 *.wav *.ogg *.flac *.m4a")],
        )
        if not path:
            return

        self.status_label.config(text=t("converting"), fg=colors["accent"])
        self.update()

        def convert_thread():
            try:
                from core.config import get_license_server_url
                from services.connection_manager import is_server_offline
                import requests

                if is_server_offline():
                    self.after(
                        0,
                        lambda: self.status_label.config(
                            text=t("server_offline"), fg=colors["error"]
                        ),
                    )
                    return

                server_url = get_license_server_url()
                with open(path, "rb") as f:
                    files = {"file": (os.path.basename(path), f)}
                    response = requests.post(
                        f"{server_url}/midi/convert", files=files, timeout=300
                    )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        midi_filename = data.get("filename", "")
                        midi_url = f"{server_url}/midi/{midi_filename}"
                        midi_response = requests.get(midi_url, timeout=30)

                        if midi_response.status_code == 200:
                            local_dir = os.path.join(
                                os.path.dirname(os.path.dirname(__file__)), "midi_files"
                            )
                            os.makedirs(local_dir, exist_ok=True)
                            local_path = os.path.join(local_dir, midi_filename)

                            with open(local_path, "wb") as f:
                                f.write(midi_response.content)

                            def on_success():
                                self.status_label.config(
                                    text=t("created", filename=midi_filename),
                                    fg=colors["success"],
                                )
                                self.playlist.add_song(local_path, midi_filename)

                            self.after(0, on_success)
                        else:
                            raise Exception("Download failed")
                    else:
                        raise Exception(data.get("message", "Conversion failed"))
                else:
                    raise Exception(response.text)
            except Exception as e:
                self.after(
                    0,
                    lambda: self.status_label.config(
                        text=t("convert_error", error=str(e)[:30]), fg=colors["error"]
                    ),
                )

        threading.Thread(target=convert_thread, daemon=True).start()

    # ==================== Song Actions ====================

    def _on_song_click(self, index, play=False):
        self.playlist.set_current_index(index)
        if play:
            self._play_current()

    def _on_song_remove(self, index):
        self.playlist.remove_song(index)

    # ==================== Playback ====================

    def _play_current(self):
        song = self.playlist.get_current_song()
        if not song:
            return

        path = song.get("path")
        if not path or not os.path.exists(path):
            messagebox.showerror("Lỗi", "File không tồn tại!")
            return

        # Check feature
        from feature_manager import get_feature_manager

        fm = get_feature_manager()
        if not fm.has_feature(Features.MIDI_PLAYBACK):
            messagebox.showinfo(t("expired"), t("upgrade_to_continue"))
            return

        # Toggle stop if playing
        if self.playback_engine.is_active():
            self.playback_engine.stop()
            self.play_btn.set_text("▶")
            self.status_label.config(text=t("stopped"), fg=colors["warning"])
            return
        # Reset events if switching to different song (not on first play of same song)
        if self.current_midi_path and path != self.current_midi_path:
            self.generated_events = None
            self.last_debug_info = None

        self.current_midi_path = path

        # Process MIDI
        self.status_label.config(text=t("processing"), fg=colors["accent"])
        self.update()

        try:
            # Use existing generated_events if available (from script viewer reprocess)
            if self.generated_events and len(self.generated_events) > 0:
                events = self.generated_events
            else:
                events, total_time, debug_info = preprocess_midi(
                    path, auto_transpose=self.auto_transpose
                )
                self.generated_events = events
                self.last_debug_info = debug_info
        except Exception as e:
            messagebox.showerror(t("error"), t("midi_error", error=str(e)))
            self.status_label.config(text="❌ " + t("error") + "!", fg=colors["error"])
            return

        if len(events) == 0:
            messagebox.showwarning(t("warning"), t("midi_empty"))
            return

        # Countdown
        self._countdown(COUNTDOWN_SECONDS, events)

    def _countdown(self, count, events):
        if count > 0:
            self.status_label.config(
                text=t("countdown", count=count), fg=colors["warning"]
            )
            self.after(1000, lambda: self._countdown(count - 1, events))
        else:
            self._begin_playback(events)

    def _begin_playback(self, events):
        self.play_btn.set_text("⏹")
        self.status_label.config(text=t("playing"), fg=colors["success"])

        def on_complete():
            self.play_btn.set_text("▶")
            self.status_label.config(text=t("completed"), fg=colors["success"])
            self._refresh_list()  # Update button states

            # Check if stop all was requested
            if self.stop_all_requested:
                self.stop_all_requested = False
                return

            # Auto advance
            if (
                self.playlist.repeat_mode != PlaylistService.REPEAT_NONE
                or self.playlist.has_next()
            ):
                song = self.playlist.next_song()
                if song:
                    self.after(1000, self._play_current)

        self.playback_engine.play_events(events, on_complete=on_complete)

    def _next_song(self):
        song = self.playlist.next_song()
        if song:
            self._play_current()

    def _prev_song(self):
        song = self.playlist.prev_song()
        if song:
            self._play_current()

    def _toggle_shuffle(self):
        self.playlist.toggle_shuffle()
        self._update_mode_buttons()

    def _toggle_repeat(self):
        self.playlist.cycle_repeat_mode()
        self._update_mode_buttons()

    # ==================== Script Preview ====================

    def _generate_script(self):
        song = self.playlist.get_current_song()
        if not song:
            messagebox.showinfo(t("info"), t("select_to_preview"))
            return

        path = song.get("path")
        if not path or not os.path.exists(path):
            messagebox.showerror("Lỗi", "File không tồn tại!")
            return

        # Reset events if switching to a different song
        if self.current_midi_path and path != self.current_midi_path:
            self.generated_events = None
            self.last_debug_info = None

        self.current_midi_path = path

        self.status_label.config(text=t("processing"), fg=colors["accent"])
        self.update()

        try:
            # Check if script viewer is already open
            if self.script_viewer_window and tk.Toplevel.winfo_exists(
                self.script_viewer_window
            ):
                self.script_viewer_window.lift()
                self.script_viewer_window.focus_force()
                self.status_label.config(text=t("preview"), fg=colors["success"])
                return

            # Use existing events if available, otherwise process
            if (
                self.generated_events
                and hasattr(self, "last_debug_info")
                and self.last_debug_info
            ):
                events = self.generated_events
                debug_info = self.last_debug_info
            else:
                events, _, debug_info = preprocess_midi(
                    path, auto_transpose=self.auto_transpose
                )
                self.generated_events = events
                self.last_debug_info = debug_info

            def save_events_and_debug(e, d=None):
                self.generated_events = e
                if d:
                    self.last_debug_info = d

            from .script_viewer import ScriptViewerWindow

            self.script_viewer_window = ScriptViewerWindow(
                self, events, path, debug_info=debug_info, on_save=save_events_and_debug
            )
            self.status_label.config(text=t("preview"), fg=colors["success"])
        except Exception as e:
            messagebox.showerror(t("error"), f"{t('error')}: {e}")
            self.status_label.config(text="❌ " + t("error") + "!", fg=colors["error"])

    # ==================== Save/Load ====================

    def _save_playlist(self):
        if self.playlist.is_empty():
            messagebox.showinfo(t("info"), t("playlist_empty_info"))
            return
        name = simpledialog.askstring(t("save_playlist"), t("enter_name"), parent=self)
        if name:
            if self.playlist.save_playlist(name):
                messagebox.showinfo("✓", t("saved", name=name))
            else:
                messagebox.showerror(t("error"), t("cannot_save"))

    def _load_playlist(self):
        playlists = self.playlist.get_saved_playlists()
        if not playlists:
            messagebox.showinfo(t("info"), t("no_playlist"))
            return

        dialog = tk.Toplevel(self)
        dialog.title(t("open_playlist"))
        dialog.geometry("280x350")
        dialog.configure(bg=colors["bg"])
        dialog.transient(self)
        dialog.grab_set()

        # Set icon
        from .theme import set_window_icon

        set_window_icon(dialog)

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 280) // 2
        y = (dialog.winfo_screenheight() - 350) // 2
        dialog.geometry(f"+{x}+{y}")

        tk.Label(
            dialog,
            text=t("choose_song"),
            font=("Segoe UI", 14, "bold"),
            bg=colors["bg"],
            fg=colors["fg"],
        ).pack(padx=15, pady=15, anchor="w")

        listbox = tk.Listbox(
            dialog,
            bg=colors["card"],
            fg=colors["fg"],
            font=("Segoe UI", 10),
            selectbackground=colors["accent"],
            highlightthickness=0,
        )
        listbox.pack(fill="both", expand=True, padx=15, pady=5)

        for name in playlists:
            listbox.insert(tk.END, name)

        btn_frame = tk.Frame(dialog, bg=colors["bg"])
        btn_frame.pack(fill="x", padx=15, pady=15)

        def load_selected():
            sel = listbox.curselection()
            if sel:
                self.playlist.load_playlist(listbox.get(sel[0]))
                dialog.destroy()

        ModernButton(
            btn_frame, text=t("open"), command=load_selected, kind="accent", width=8
        ).pack(side="left")
        ModernButton(
            btn_frame,
            text=t("cancel"),
            command=dialog.destroy,
            kind="secondary",
            width=8,
        ).pack(side="right")
        FadeEffect.fade_in(dialog, duration=150)

    def _clear_playlist(self):
        if self.playlist.is_empty():
            return
        if messagebox.askyesno(t("confirm"), t("delete_all")):
            self.playlist.clear()

    # ==================== Public ====================

    def refresh_preset_combo(self):
        """Compatibility method - not used in new UI"""
        pass
