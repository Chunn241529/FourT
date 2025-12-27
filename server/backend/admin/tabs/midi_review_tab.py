"""
MIDI Review Tab for Admin UI - Approve/Reject pending MIDI uploads
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading

from backend.admin.tabs.base_tab import BaseTab


class MidiReviewTab(BaseTab):
    """MIDI Review/Approval tab for admin"""

    def setup(self):
        """Setup MIDI Review tab UI"""
        COLORS = self.COLORS
        FONTS = self.FONTS
        ModernButton = self.ModernButton

        # State
        self.midi_list = []
        self.filtered_midi = []
        self.selected_midi = None

        # === HEADER ===
        header = tk.Frame(self.parent, bg=COLORS["bg"])
        header.pack(fill=tk.X, padx=20, pady=(20, 15))

        tk.Label(
            header,
            text="🎵 MIDI Review",
            font=FONTS["h1"],
            bg=COLORS["bg"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)

        refresh_btn = ModernButton(
            header, text="Refresh", command=self._load_midi, kind="secondary"
        )
        refresh_btn.pack(side=tk.RIGHT)

        # === STATS ===
        stats_card = tk.Frame(self.parent, bg=COLORS["card"])
        stats_card.pack(fill=tk.X, padx=20, pady=(0, 15))

        self.stats_label = tk.Label(
            stats_card,
            text="Loading...",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
            padx=15,
            pady=12,
        )
        self.stats_label.pack(anchor="w")

        # === FILTER ===
        filter_frame = tk.Frame(self.parent, bg=COLORS["bg"])
        filter_frame.pack(fill=tk.X, padx=20, pady=(0, 15))

        tk.Label(
            filter_frame,
            text="Filter:",
            font=FONTS["body"],
            bg=COLORS["bg"],
            fg=COLORS["text_dim"],
        ).pack(side=tk.LEFT)

        self.filter_var = tk.StringVar(value="pending")
        filters = [
            ("Pending", "pending"),
            ("Approved", "approved"),
            ("Rejected", "rejected"),
            ("All", "all"),
        ]

        for text, value in filters:
            rb = tk.Radiobutton(
                filter_frame,
                text=text,
                variable=self.filter_var,
                value=value,
                font=FONTS["body"],
                bg=COLORS["bg"],
                fg=COLORS["fg"],
                selectcolor=COLORS["card"],
                activebackground=COLORS["bg"],
                activeforeground=COLORS["fg"],
                command=self._apply_filter,
            )
            rb.pack(side=tk.LEFT, padx=(15, 0))

        # === MIDI LIST ===
        list_card = tk.Frame(self.parent, bg=COLORS["card"])
        list_card.pack(fill=tk.X, padx=20, pady=(0, 15))

        tk.Label(
            list_card,
            text="MIDI Uploads",
            font=FONTS["h2"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(anchor="w", padx=15, pady=(15, 10))

        # Listbox container
        list_inner = tk.Frame(list_card, bg=COLORS["input_bg"])
        list_inner.pack(fill=tk.X, padx=15, pady=(0, 15))

        self.midi_listbox = tk.Listbox(
            list_inner,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            selectbackground=COLORS["accent"],
            selectforeground="white",
            highlightthickness=0,
            relief="flat",
            height=8,
            activestyle="none",
            cursor="hand2",
        )
        self.midi_listbox.pack(fill=tk.X, padx=2, pady=2)
        self.midi_listbox.bind("<<ListboxSelect>>", self._on_select_midi)

        # === DETAILS SECTION ===
        detail_card = tk.Frame(self.parent, bg=COLORS["card"])
        detail_card.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # Detail header with action buttons
        detail_header = tk.Frame(detail_card, bg=COLORS["card"])
        detail_header.pack(fill=tk.X, padx=15, pady=(15, 10))

        tk.Label(
            detail_header,
            text="Details",
            font=FONTS["h2"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side=tk.LEFT)

        # Action buttons
        btn_frame = tk.Frame(detail_header, bg=COLORS["card"])
        btn_frame.pack(side=tk.RIGHT)

        self.reject_btn = ModernButton(
            btn_frame, text="❌ Reject", command=self._reject_midi, kind="danger"
        )
        self.reject_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.approve_btn = ModernButton(
            btn_frame, text="✅ Approve", command=self._approve_midi, kind="success"
        )
        self.approve_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Detail content
        detail_container = tk.Frame(detail_card, bg=COLORS["card"])
        detail_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        # Build detail fields
        self._build_detail_fields(detail_container)

        # Initial load
        self._load_midi()

    def _build_detail_fields(self, container):
        """Build detail section fields"""
        COLORS = self.COLORS
        FONTS = self.FONTS

        # ID and Date row
        id_row = tk.Frame(container, bg=COLORS["card"])
        id_row.pack(fill=tk.X, pady=(0, 10))

        self.id_label = tk.Label(
            id_row,
            text="ID: -",
            font=FONTS["code"],
            bg=COLORS["card"],
            fg=COLORS["accent"],
        )
        self.id_label.pack(side=tk.LEFT)

        self.date_label = tk.Label(
            id_row,
            text="",
            font=FONTS["small"],
            bg=COLORS["card"],
            fg=COLORS["text_dim"],
        )
        self.date_label.pack(side=tk.RIGHT)

        # Title
        tk.Label(
            container,
            text="Title",
            font=FONTS["small"],
            bg=COLORS["card"],
            fg=COLORS["text_dim"],
        ).pack(anchor="w")

        self.title_label = tk.Label(
            container,
            text="-",
            font=FONTS["h2"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
            wraplength=500,
            justify="left",
            anchor="w",
        )
        self.title_label.pack(fill=tk.X, pady=(0, 10))

        # Uploader
        uploader_row = tk.Frame(container, bg=COLORS["card"])
        uploader_row.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            uploader_row,
            text="Uploader:",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["text_dim"],
        ).pack(side=tk.LEFT)

        self.uploader_label = tk.Label(
            uploader_row,
            text="-",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        )
        self.uploader_label.pack(side=tk.LEFT, padx=(10, 0))

        # Type and status
        type_row = tk.Frame(container, bg=COLORS["card"])
        type_row.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            type_row,
            text="Type:",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["text_dim"],
        ).pack(side=tk.LEFT)

        self.type_label = tk.Label(
            type_row,
            text="-",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        )
        self.type_label.pack(side=tk.LEFT, padx=(10, 20))

        tk.Label(
            type_row,
            text="Status:",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["text_dim"],
        ).pack(side=tk.LEFT)

        self.status_label = tk.Label(
            type_row,
            text="-",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["fg"],
        )
        self.status_label.pack(side=tk.LEFT, padx=(10, 0))

        # Description
        tk.Label(
            container,
            text="Description",
            font=FONTS["small"],
            bg=COLORS["card"],
            fg=COLORS["text_dim"],
        ).pack(anchor="w", pady=(5, 0))

        self.desc_text = tk.Text(
            container,
            font=FONTS["body"],
            bg=COLORS["input_bg"],
            fg=COLORS["fg"],
            height=3,
            wrap="word",
            relief="flat",
        )
        self.desc_text.pack(fill=tk.X, pady=(5, 10))
        self.desc_text.config(state="disabled")

        # Tags
        tags_row = tk.Frame(container, bg=COLORS["card"])
        tags_row.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            tags_row,
            text="Tags:",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["text_dim"],
        ).pack(side=tk.LEFT)

        self.tags_label = tk.Label(
            tags_row, text="-", font=FONTS["body"], bg=COLORS["card"], fg=COLORS["fg"]
        )
        self.tags_label.pack(side=tk.LEFT, padx=(10, 0))

        # File info
        file_row = tk.Frame(container, bg=COLORS["card"])
        file_row.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            file_row,
            text="File:",
            font=FONTS["body"],
            bg=COLORS["card"],
            fg=COLORS["text_dim"],
        ).pack(side=tk.LEFT)

        self.file_label = tk.Label(
            file_row, text="-", font=FONTS["body"], bg=COLORS["card"], fg=COLORS["fg"]
        )
        self.file_label.pack(side=tk.LEFT, padx=(10, 0))

    def _load_midi(self):
        """Load pending MIDI from server"""

        def fetch():
            try:
                import requests
                from core.config import get_license_server_url

                url = f"{get_license_server_url()}/api/community/midi/pending"
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    self.midi_list = (
                        data if isinstance(data, list) else data.get("items", [])
                    )
                    self.root.after(0, self._update_list)
                else:
                    self.root.after(
                        0, lambda: self.stats_label.config(text="Failed to load")
                    )
            except Exception as e:
                self.root.after(
                    0, lambda: self.stats_label.config(text=f"Error: {str(e)[:30]}")
                )

        threading.Thread(target=fetch, daemon=True).start()

    def _update_list(self):
        """Update the MIDI listbox"""
        self.midi_listbox.delete(0, tk.END)

        filter_status = self.filter_var.get()
        self.filtered_midi = self.midi_list

        if filter_status != "all":
            self.filtered_midi = [
                m for m in self.midi_list if m.get("status") == filter_status
            ]

        # Stats
        counts = {"pending": 0, "approved": 0, "rejected": 0}
        for m in self.midi_list:
            s = m.get("status", "pending")
            if s in counts:
                counts[s] += 1

        self.stats_label.config(
            text=f"Total: {len(self.midi_list)} | Pending: {counts['pending']} | Approved: {counts['approved']} | Rejected: {counts['rejected']}"
        )

        # List items
        for midi in self.filtered_midi:
            status = midi.get("status", "pending")
            icon = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(
                status, "❓"
            )
            title = midi.get("title", "Untitled")[:40]
            uploader = midi.get("uploader_username", "Unknown")[:15]
            self.midi_listbox.insert(tk.END, f"{icon} {title} - by {uploader}")

    def _apply_filter(self):
        """Apply status filter"""
        self._update_list()

    def _on_select_midi(self, event):
        """Handle MIDI selection"""
        selection = self.midi_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        if idx < len(self.filtered_midi):
            self.selected_midi = self.filtered_midi[idx]
            self._show_details()

    def _show_details(self):
        """Show selected MIDI details"""
        if not self.selected_midi:
            return

        m = self.selected_midi

        self.id_label.config(text=f"ID: {m.get('id', '-')}")

        created = m.get("created_at", "")[:19].replace("T", " ")
        self.date_label.config(text=f"Uploaded: {created}")

        self.title_label.config(text=m.get("title", "-"))
        self.uploader_label.config(text=m.get("uploader_username", "-"))
        self.type_label.config(text=m.get("midi_type", "normal").upper())

        status = m.get("status", "pending")
        status_color = {
            "pending": "#fbbf24",
            "approved": "#22c55e",
            "rejected": "#ef4444",
        }.get(status, self.COLORS["fg"])
        self.status_label.config(text=status.upper(), fg=status_color)

        self.desc_text.config(state="normal")
        self.desc_text.delete("1.0", tk.END)
        self.desc_text.insert("1.0", m.get("description", "") or "No description")
        self.desc_text.config(state="disabled")

        tags = m.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        self.tags_label.config(text=", ".join(tags) if tags else "None")

        file_size = m.get("file_size", 0)
        size_str = f"{file_size / 1024:.1f} KB" if file_size else "Unknown"
        self.file_label.config(text=f"{m.get('file_name', 'Unknown')} ({size_str})")

        # Enable/disable buttons based on status
        if status == "pending":
            self.approve_btn.pack(side=tk.RIGHT, padx=(5, 0))
            self.reject_btn.pack(side=tk.RIGHT, padx=(5, 0))
        else:
            # Already processed, hide buttons
            pass

    def _approve_midi(self):
        """Approve selected MIDI"""
        if not self.selected_midi:
            return

        if not messagebox.askyesno("Confirm", "Approve this MIDI?"):
            return

        self._update_midi_status("approved")

    def _reject_midi(self):
        """Reject selected MIDI"""
        if not self.selected_midi:
            return

        if not messagebox.askyesno("Confirm", "Reject this MIDI?"):
            return

        self._update_midi_status("rejected")

    def _update_midi_status(self, new_status):
        """Update MIDI status on server"""
        midi_id = self.selected_midi.get("id")

        # Update local immediately
        self.selected_midi["status"] = new_status
        for m in self.midi_list:
            if m.get("id") == midi_id:
                m["status"] = new_status
                break
        self._update_list()
        self._show_details()

        # Sync to server in background
        def update():
            try:
                import requests
                from core.config import get_license_server_url

                url = f"{get_license_server_url()}/api/community/midi/{midi_id}/review"
                requests.post(url, json={"status": new_status}, timeout=5)
            except Exception as e:
                print(f"[MidiReview] Failed to update status: {e}")

        threading.Thread(target=update, daemon=True).start()
