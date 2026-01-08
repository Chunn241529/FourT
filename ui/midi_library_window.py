"""
Midi Library Window - Redesigned
Modern selection UI with custom title bar, animations, and table view
"""

import tkinter as tk
from tkinter import ttk
import os

from .components import FramelessWindow
from .theme import colors, FONTS, ModernButton, GradientCard
from .animations import FadeEffect, ColorTransition
from feature_manager import get_feature_manager
from core.config import Features


class LibraryItem(tk.Frame):
    """Individual library item with cheat-like selection style"""

    def __init__(
        self, parent, filename, is_selected=False, on_click=None, index=0, **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.configure(bg=colors["card"], cursor="hand2")
        self.filename = filename
        self.is_selected = is_selected
        self.on_click = on_click
        self.index = index
        self._hover = False

        # Visual selection indicator (Left colored bar)
        self.indicator = tk.Frame(
            self, width=3, bg=colors["accent"] if is_selected else colors["card"]
        )
        self.indicator.pack(side="left", fill="y")

        # Content container
        content = tk.Frame(self, bg=colors["card"])
        content.pack(side="left", fill="both", expand=True, padx=10, pady=8)

        # Icon
        self.icon_label = tk.Label(
            content,
            text="🎵",
            font=("Segoe UI Emoji", 10),
            bg=colors["card"],
            fg=colors["accent"] if is_selected else colors["fg_dim"],
        )
        self.icon_label.pack(side="left")

        # Filename
        self.name_label = tk.Label(
            content,
            text=filename,
            font=("Segoe UI", 10, "bold") if is_selected else ("Segoe UI", 10),
            bg=colors["card"],
            fg=colors["fg"] if is_selected else colors["fg_dim"],
            anchor="w",
        )
        self.name_label.pack(side="left", fill="x", expand=True, padx=(10, 0))

        # Checkbox/Status (fake)
        self.status_label = tk.Label(
            self,
            text="✓" if is_selected else "",
            font=("Segoe UI", 10, "bold"),
            bg=colors["card"],
            fg=colors["success"],
            width=3,
        )
        self.status_label.pack(side="right", padx=5)

        # Bindings
        for w in [self, content, self.icon_label, self.name_label, self.status_label]:
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
            w.bind("<Button-1>", self._on_click)

    def _on_enter(self, e):
        self._hover = True
        self._update_colors()

    def _on_leave(self, e):
        self._hover = False
        self._update_colors()

    def _on_click(self, e):
        if self.on_click:
            self.on_click(self.index)

    def set_selected(self, selected):
        self.is_selected = selected
        self._update_colors()
        self.indicator.configure(
            bg=(
                colors["accent"]
                if selected
                else ("#2a2a3d" if self._hover else colors["card"])
            )
        )
        self.status_label.configure(text="✓" if selected else "")
        self.name_label.configure(
            font=("Segoe UI", 10, "bold") if selected else ("Segoe UI", 10),
            fg=colors["fg"] if selected else colors["fg_dim"],
        )
        self.icon_label.configure(fg=colors["accent"] if selected else colors["fg_dim"])

    def _update_colors(self):
        # Determine background color
        if self.is_selected:
            bg = "#252535"  # Slightly highlighted for selected
        elif self._hover:
            bg = colors["card_hover"]
        else:
            bg = colors["card"]

        self.configure(bg=bg)
        for w in [self.name_label, self.icon_label, self.status_label]:
            try:
                w.configure(bg=bg)
            except:
                pass
        self.winfo_children()[1].configure(bg=bg)  # Content frame


class MidiLibraryWindow:
    """Modern MIDI Library Selection Window"""

    def __init__(self, parent, library_service, playlist_service):
        self.parent = parent
        self.library_service = library_service
        self.playlist_service = playlist_service

        # Determine icon path
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "favicon.ico")
        if not os.path.exists(icon_path):
            # Fallback
            icon_path = None

        self.window = FramelessWindow(
            parent, title="Thư viện MIDI", width=600, height=400, icon_path=icon_path
        )

        self.selected_indices = set()
        self.items = []

        self.setup_ui()
        self.load_files()

        # Center window relative to parent
        self.window.center_relative(parent)

        # Fade in
        FadeEffect.fade_in(self.window, duration=200)

    def setup_ui(self):
        content = self.window.content_frame

        # Footer Actions (Pack FIRST at BOTTOM to reserve space)
        footer = tk.Frame(content, bg=colors["bg"])
        footer.pack(side="bottom", fill="x", padx=20, pady=20)

        self.count_label = tk.Label(
            footer,
            text="Đã chọn: 0",
            font=("Segoe UI", 10),
            bg=colors["bg"],
            fg=colors["fg_dim"],
        )
        self.count_label.pack(side="left")

        action_btns = tk.Frame(footer, bg=colors["bg"])
        action_btns.pack(side="right")

        ModernButton(
            action_btns,
            text="Thêm vào Playlist",
            command=self._confirm_add,
            kind="accent",
            width=14,
        ).pack(side="left", padx=5)

        ModernButton(
            action_btns,
            text="Hủy",
            command=self.window.destroy,
            kind="secondary",
            width=8,
        ).pack(side="left")

        # Header Area (Pack TOP)
        header = tk.Frame(content, bg=colors["bg"])
        header.pack(side="top", fill="x", padx=20, pady=(20, 10))

        tk.Label(
            header,
            text="📂 Chọn bài hát",
            font=("Segoe UI", 16, "bold"),
            bg=colors["bg"],
            fg=colors["fg"],
        ).pack(side="left")

        # Search Bar
        search_frame = tk.Frame(header, bg=colors["bg"])
        search_frame.pack(side="left", padx=20, fill="x", expand=True)

        fm = get_feature_manager()
        has_search = fm.has_feature(Features.MIDI_LIBRARY_SEARCH)

        self.search_var = tk.StringVar()
        if has_search:
            search_entry = tk.Entry(
                search_frame,
                textvariable=self.search_var,
                font=("Segoe UI", 10),
                bg=colors["card"],
                fg=colors["fg"],
                insertbackground=colors["fg"],
                relief="flat",
                bd=0,
            )
            search_entry.pack(side="left", fill="x", expand=True, ipady=4)
            # Add bottom border
            tk.Frame(search_frame, height=2, bg=colors["accent"]).pack(
                side="bottom", fill="x"
            )

            search_entry.bind("<KeyRelease>", self._on_search)
            # Placeholder logic could be added here
        else:
            # Locked search
            entry_mock = tk.Label(
                search_frame,
                text="🔍 Tìm kiếm (Yêu cầu gói Plus)",
                font=("Segoe UI", 10, "italic"),
                bg=colors["bg_secondary"],
                fg=colors["fg_dim"],
                anchor="w",
                padx=5,
            )
            entry_mock.pack(side="left", fill="x", expand=True, ipady=4)

            lock_btn = tk.Label(
                search_frame,
                text="🔒",
                font=("Segoe UI Emoji", 12),
                bg=colors["bg"],
                fg=colors["warning"],
                cursor="hand2",
            )
            lock_btn.pack(side="right", padx=5)
            lock_btn.bind("<Button-1>", lambda e: self._show_upgrade_hint())

        # "Select All" button (small text)
        self.select_all_btn = tk.Label(
            header,
            text="Chọn tất cả",
            font=("Segoe UI", 9),
            bg=colors["bg"],
            fg=colors["accent"],
            cursor="hand2",
        )
        self.select_all_btn.pack(side="right", pady=5)
        self.select_all_btn.bind("<Button-1>", self._toggle_select_all)

        # List Container (Card style) - Pack LAST to fill remaining space
        list_container = GradientCard(content)
        list_container.pack(side="top", fill="both", expand=True, padx=20, pady=5)

        # Header for Table
        table_header = tk.Frame(
            list_container.content, bg=colors["bg_secondary"], height=30
        )
        table_header.pack(fill="x")
        table_header.pack_propagate(False)

        tk.Label(
            table_header,
            text="Tên file",
            font=("Segoe UI", 9, "bold"),
            bg=colors["bg_secondary"],
            fg=colors["fg_dim"],
        ).pack(
            side="left", padx=40
        )  # Padding to skip icon/indicator

        # Scrollable Area
        self.canvas = tk.Canvas(
            list_container.content, bg=colors["card"], highlightthickness=0, bd=0
        )
        # Hidden scrollbar logic: We mapped yview but don't pack the scrollbar
        self.scrollbar = ttk.Scrollbar(
            list_container.content, orient="vertical", command=self.canvas.yview
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.items_frame = tk.Frame(self.canvas, bg=colors["card"])
        self._window_id = self.canvas.create_window(
            (0, 0), window=self.items_frame, anchor="nw"
        )

        self.items_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Bind mousewheel only when hovering
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

        self.canvas.pack(side="left", fill="both", expand=True)

    def load_files(self):
        files = self.library_service.get_local_midi_files()

        for idx, filename in enumerate(files):
            item = LibraryItem(
                self.items_frame,
                filename=filename,
                index=idx,
                on_click=self._on_item_click,
            )
            item.pack(fill="x", pady=1)
            self.items.append(item)

        if not files:
            tk.Label(
                self.items_frame,
                text="\nThư viện trống\nHãy copy file .mid vào thư mục midi_files",
                font=("Segoe UI", 10),
                bg=colors["card"],
                fg=colors["fg_dim"],
                justify="center",
            ).pack(fill="both", expand=True, pady=20)

    def _on_item_click(self, index):
        if index in self.selected_indices:
            self.selected_indices.remove(index)
            self.items[index].set_selected(False)
        else:
            self.selected_indices.add(index)
            self.items[index].set_selected(True)
        self._update_count()

    def _toggle_select_all(self, e):
        if len(self.selected_indices) == len(self.items):
            # Deselect all
            self.selected_indices.clear()
            for item in self.items:
                item.set_selected(False)
            self.select_all_btn.config(text="Chọn tất cả")
        else:
            # Select all
            self.selected_indices = set(range(len(self.items)))
            for item in self.items:
                item.set_selected(True)
            self.select_all_btn.config(text="Bỏ chọn tất cả")
        self._update_count()

    def _update_count(self):
        count = len(self.selected_indices)
        self.count_label.config(text=f"Đã chọn: {count}")

    def _confirm_add(self):
        if not self.selected_indices:
            self.window.destroy()
            return

        count = 0
        full = False
        for idx in self.selected_indices:
            filename = self.items[idx].filename
            path = self.library_service.get_midi_path(filename)
            result = self.playlist_service.add_song(path, filename)
            if result == -1:
                full = True
                break
            count += 1

        print(f"[Library] Added {count} songs")
        if full:
            from tkinter import messagebox

            messagebox.showwarning(
                "Giới hạn",
                "Đã đạt giới hạn số bài hát của gói cước hiện tại!\nVui lòng nâng cấp để thêm nhiều hơn.",
            )

        self.window.destroy()

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._window_id, width=event.width)

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        try:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    def _on_search(self, event=None):
        query = self.search_var.get().lower()

        # Hide all first
        for item in self.items:
            item.pack_forget()

        # Show matching
        visible_count = 0
        for item in self.items:
            if query in item.filename.lower():
                item.pack(fill="x", pady=1)
                visible_count += 1

        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _show_upgrade_hint(self):
        from tkinter import messagebox

        messagebox.showinfo(
            "Nâng cấp",
            "Tính năng tìm kiếm nâng cao chỉ có trong gói Plus, Pro và Premium.\n\nHãy nâng cấp để mở khóa!",
        )
