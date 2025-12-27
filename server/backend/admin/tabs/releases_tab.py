"""
Releases Tab - Admin UI for managing releases and download counts
"""

import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import threading
from pathlib import Path

from .base_tab import BaseTab
from backend import database as db


class ReleasesTab(BaseTab):
    """Tab for managing releases and download statistics"""

    def setup(self):
        """Setup the releases management UI"""
        # Main container
        container = tk.Frame(self.parent, bg=self.COLORS["bg"])
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        tk.Label(
            container,
            text="📦 Releases Management",
            font=self.FONTS["h1"],
            bg=self.COLORS["bg"],
            fg=self.COLORS["fg"],
        ).pack(anchor="w", pady=(0, 20))

        # Stats frame
        stats_frame = tk.Frame(container, bg=self.COLORS["card"])
        stats_frame.pack(fill="x", pady=(0, 20))

        # Total downloads display
        self.total_label = tk.Label(
            stats_frame,
            text="Total Downloads: Loading...",
            font=self.FONTS["h2"],
            bg=self.COLORS["card"],
            fg=self.COLORS["accent"],
        )
        self.total_label.pack(side="left", padx=20, pady=15)

        # Buttons frame (right side) - căn giữa vertical
        btn_frame = tk.Frame(stats_frame, bg=self.COLORS["card"])
        btn_frame.pack(side="right", padx=20, pady=15)

        # Refresh button (icon) - đặt trước để nằm bên phải
        refresh_btn = tk.Label(
            btn_frame,
            text="🔄",
            font=("Segoe UI Emoji", 12),
            bg=self.COLORS["card"],
            fg=self.COLORS["fg"],
            cursor="hand2",
        )
        refresh_btn.pack(side="right", padx=8)
        refresh_btn.bind("<Button-1>", lambda e: self._refresh_data())
        refresh_btn.bind(
            "<Enter>", lambda e: refresh_btn.config(fg=self.COLORS["accent"])
        )
        refresh_btn.bind("<Leave>", lambda e: refresh_btn.config(fg=self.COLORS["fg"]))

        # Releases list frame
        list_frame = tk.Frame(container, bg=self.COLORS["card"])
        list_frame.pack(fill="both", expand=True)

        # Header
        header = tk.Frame(list_frame, bg=self.COLORS["sidebar"])
        header.pack(fill="x")

        headers = [
            ("Version", 150),
            ("Name", 200),
            ("Downloads", 100),
            ("Published", 150),
            ("Actions", 150),
        ]
        for text, width in headers:
            tk.Label(
                header,
                text=text,
                font=self.FONTS["body"],
                bg=self.COLORS["sidebar"],
                fg=self.COLORS["fg"],
                width=width // 10,
            ).pack(side="left", padx=5, pady=10)

        # Scrollable releases list
        self.list_canvas = tk.Canvas(
            list_frame, bg=self.COLORS["card"], highlightthickness=0
        )
        self.list_canvas.pack(fill="both", expand=True)

        self.releases_frame = tk.Frame(self.list_canvas, bg=self.COLORS["card"])
        self.list_canvas.create_window((0, 0), window=self.releases_frame, anchor="nw")

        self.releases_frame.bind(
            "<Configure>",
            lambda e: self.list_canvas.configure(
                scrollregion=self.list_canvas.bbox("all")
            ),
        )

        # Mouse wheel scrolling
        self.list_canvas.bind(
            "<Enter>",
            lambda e: self.list_canvas.bind_all(
                "<MouseWheel>",
                lambda ev: self.list_canvas.yview_scroll(
                    -1 * (ev.delta // 120), "units"
                ),
            ),
        )
        self.list_canvas.bind(
            "<Leave>", lambda e: self.list_canvas.unbind_all("<MouseWheel>")
        )

        # Add release button at bottom
        add_frame = tk.Frame(container, bg=self.COLORS["bg"])
        add_frame.pack(fill="x", pady=(20, 0))

        add_btn = tk.Label(
            add_frame,
            text="➕ Add Release",
            font=self.FONTS["body"],
            bg=self.COLORS["bg"],
            fg=self.COLORS["accent"],
            cursor="hand2",
        )
        add_btn.pack(side="left")
        add_btn.bind("<Button-1>", lambda e: self._add_release_dialog())
        add_btn.bind("<Enter>", lambda e: add_btn.config(fg=self.COLORS["success"]))
        add_btn.bind("<Leave>", lambda e: add_btn.config(fg=self.COLORS["accent"]))

        sync_btn = tk.Label(
            add_frame,
            text="🔁 Sync Folder",
            font=self.FONTS["body"],
            bg=self.COLORS["bg"],
            fg=self.COLORS["fg"],
            cursor="hand2",
        )
        sync_btn.pack(side="left", padx=20)
        sync_btn.bind("<Button-1>", lambda e: self._sync_folder())
        sync_btn.bind("<Enter>", lambda e: sync_btn.config(fg=self.COLORS["accent"]))
        sync_btn.bind("<Leave>", lambda e: sync_btn.config(fg=self.COLORS["fg"]))

        # Load initial data
        self._refresh_data()

    def _run_async(self, coro, callback=None):
        """Run async function in background thread"""

        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(coro)
                if callback:
                    self.root.after(0, lambda: callback(result))
            except Exception as e:
                error_msg = str(e)  # Capture error message before lambda
                self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            finally:
                loop.close()

        threading.Thread(target=run, daemon=True).start()

    def _refresh_data(self):
        """Refresh releases data from database"""

        async def fetch():
            releases = await db.get_all_releases()
            stats = await db.get_download_stats()
            return {"releases": releases, "stats": stats}

        def update(data):
            # Update total
            total = data["stats"].get("total_downloads", 0)
            self.total_label.config(text=f"Total Downloads: {total:,}")

            # Clear old items
            for widget in self.releases_frame.winfo_children():
                widget.destroy()

            # Add releases
            for release in data["releases"]:
                self._add_release_row(release)

        self._run_async(fetch(), update)

    def _add_release_row(self, release):
        """Add a release row to the list"""
        row = tk.Frame(self.releases_frame, bg=self.COLORS["card"])
        row.pack(fill="x", pady=2)

        # Version
        tk.Label(
            row,
            text=release["version"],
            font=self.FONTS["body"],
            bg=self.COLORS["card"],
            fg=self.COLORS["accent"],
            width=15,
            anchor="w",
        ).pack(side="left", padx=5)

        # Name
        tk.Label(
            row,
            text=release.get("name", ""),
            font=self.FONTS["body"],
            bg=self.COLORS["card"],
            fg=self.COLORS["fg"],
            width=20,
            anchor="w",
        ).pack(side="left", padx=5)

        # Downloads (sum of all assets)
        total_downloads = sum(
            a.get("download_count", 0) for a in release.get("assets", [])
        )
        tk.Label(
            row,
            text=f"{total_downloads:,}",
            font=self.FONTS["body"],
            bg=self.COLORS["card"],
            fg=self.COLORS["success"],
            width=10,
        ).pack(side="left", padx=5)

        # Published date
        published = (
            release.get("published_at", "")[:10]
            if release.get("published_at")
            else "N/A"
        )
        tk.Label(
            row,
            text=published,
            font=self.FONTS["body"],
            bg=self.COLORS["card"],
            fg=self.COLORS["fg_dim"],
            width=15,
        ).pack(side="left", padx=5)

        # Actions (icon buttons)
        actions = tk.Frame(row, bg=self.COLORS["card"])
        actions.pack(side="left", padx=5)

        edit_btn = tk.Label(
            actions,
            text="✏️",
            font=("Segoe UI Emoji", 12),
            bg=self.COLORS["card"],
            fg=self.COLORS["fg"],
            cursor="hand2",
        )
        edit_btn.pack(side="left", padx=3)
        edit_btn.bind(
            "<Button-1>", lambda e, v=release["version"]: self._edit_release_dialog(v)
        )
        edit_btn.bind("<Enter>", lambda e: edit_btn.config(fg=self.COLORS["accent"]))
        edit_btn.bind("<Leave>", lambda e: edit_btn.config(fg=self.COLORS["fg"]))

        del_btn = tk.Label(
            actions,
            text="🗑️",
            font=("Segoe UI Emoji", 12),
            bg=self.COLORS["card"],
            fg=self.COLORS["fg"],
            cursor="hand2",
        )
        del_btn.pack(side="left", padx=3)
        del_btn.bind(
            "<Button-1>", lambda e, v=release["version"]: self._delete_release(v)
        )
        del_btn.bind("<Enter>", lambda e: del_btn.config(fg=self.COLORS["error"]))
        del_btn.bind("<Leave>", lambda e: del_btn.config(fg=self.COLORS["fg"]))

    def _add_release_dialog(self):
        """Show dialog to add new release"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Release")
        dialog.geometry("380x340")
        dialog.configure(bg=self.COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 380) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 340) // 2
        dialog.geometry(f"+{x}+{y}")

        # Content frame
        content = tk.Frame(dialog, bg=self.COLORS["bg"])
        content.pack(fill="both", expand=True, padx=25, pady=20)

        # Title
        tk.Label(
            content,
            text="📦 Add New Release",
            font=self.FONTS["h2"],
            bg=self.COLORS["bg"],
            fg=self.COLORS["fg"],
        ).pack(anchor="w", pady=(0, 15))

        # Version input
        tk.Label(
            content,
            text="Version",
            font=self.FONTS["small"],
            bg=self.COLORS["bg"],
            fg=self.COLORS["fg_dim"],
        ).pack(anchor="w")
        version_frame = tk.Frame(content, bg=self.COLORS["card"], bd=1, relief="solid")
        version_frame.pack(fill="x", pady=(2, 10))
        version_entry = tk.Entry(
            version_frame,
            font=self.FONTS["body"],
            width=30,
            bg=self.COLORS["input_bg"],
            fg=self.COLORS["fg"],
            insertbackground=self.COLORS["fg"],
            bd=0,
        )
        version_entry.pack(padx=10, pady=8)
        version_entry.focus()

        # Name input
        tk.Label(
            content,
            text="Name (optional)",
            font=self.FONTS["small"],
            bg=self.COLORS["bg"],
            fg=self.COLORS["fg_dim"],
        ).pack(anchor="w")
        name_frame = tk.Frame(content, bg=self.COLORS["card"], bd=1, relief="solid")
        name_frame.pack(fill="x", pady=(2, 10))
        name_entry = tk.Entry(
            name_frame,
            font=self.FONTS["body"],
            width=30,
            bg=self.COLORS["input_bg"],
            fg=self.COLORS["fg"],
            insertbackground=self.COLORS["fg"],
            bd=0,
        )
        name_entry.pack(padx=10, pady=8)

        # Prerelease toggle
        prerelease_var = tk.BooleanVar()
        pre_frame = tk.Frame(content, bg=self.COLORS["bg"])
        pre_frame.pack(fill="x", pady=5)

        pre_check = tk.Label(
            pre_frame,
            text="☐",
            font=("Segoe UI Emoji", 14),
            bg=self.COLORS["bg"],
            fg=self.COLORS["fg"],
            cursor="hand2",
        )
        pre_check.pack(side="left")
        tk.Label(
            pre_frame,
            text="Pre-release",
            font=self.FONTS["body"],
            bg=self.COLORS["bg"],
            fg=self.COLORS["fg"],
        ).pack(side="left", padx=5)

        def toggle_pre():
            prerelease_var.set(not prerelease_var.get())
            pre_check.config(
                text="☑" if prerelease_var.get() else "☐",
                fg=self.COLORS["accent"] if prerelease_var.get() else self.COLORS["fg"],
            )

        pre_check.bind("<Button-1>", lambda e: toggle_pre())

        # Buttons
        btn_frame = tk.Frame(content, bg=self.COLORS["bg"])
        btn_frame.pack(fill="x", pady=(15, 0))

        def save():
            version = version_entry.get().strip()
            if not version:
                messagebox.showerror("Error", "Version is required")
                return

            async def create():
                return await db.create_release(
                    version=version,
                    name=name_entry.get().strip() or None,
                    prerelease=prerelease_var.get(),
                )

            self._run_async(
                create(), lambda _: (dialog.destroy(), self._refresh_data())
            )

        save_btn = tk.Label(
            btn_frame,
            text="✓ Add Release",
            font=self.FONTS["body"],
            bg=self.COLORS["success"],
            fg="black",
            cursor="hand2",
            padx=15,
            pady=5,
        )
        save_btn.pack(side="right")
        save_btn.bind("<Button-1>", lambda e: save())

        cancel_btn = tk.Label(
            btn_frame,
            text="✗ Cancel",
            font=self.FONTS["body"],
            bg=self.COLORS["card"],
            fg=self.COLORS["fg"],
            cursor="hand2",
            padx=15,
            pady=5,
        )
        cancel_btn.pack(side="right", padx=(0, 10))
        cancel_btn.bind("<Button-1>", lambda e: dialog.destroy())

    def _edit_release_dialog(self, version):
        """Show dialog to edit release download count"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit {version}")
        dialog.geometry("380x350")
        dialog.configure(bg=self.COLORS["bg"])
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 380) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 340) // 2
        dialog.geometry(f"+{x}+{y}")

        # Content frame
        content = tk.Frame(dialog, bg=self.COLORS["bg"])
        content.pack(fill="both", expand=True, padx=25, pady=20)

        # Title
        tk.Label(
            content,
            text=f"✏️ Edit v{version}",
            font=self.FONTS["h2"],
            bg=self.COLORS["bg"],
            fg=self.COLORS["accent"],
        ).pack(anchor="w", pady=(0, 15))

        # Asset type selection (radio buttons)
        tk.Label(
            content,
            text="Asset Type",
            font=self.FONTS["small"],
            bg=self.COLORS["bg"],
            fg=self.COLORS["fg_dim"],
        ).pack(anchor="w")

        asset_type_var = tk.StringVar(value="zip")
        type_frame = tk.Frame(content, bg=self.COLORS["bg"])
        type_frame.pack(fill="x", pady=(2, 10))

        def update_asset_name():
            if asset_type_var.get() == "zip":
                asset_entry.delete(0, tk.END)
                asset_entry.insert(0, f"FourT_v{version}.zip")
            else:
                asset_entry.delete(0, tk.END)
                asset_entry.insert(0, f"FourT_Setup.exe")

        zip_radio = tk.Radiobutton(
            type_frame,
            text="ZIP (web download)",
            variable=asset_type_var,
            value="zip",
            bg=self.COLORS["bg"],
            fg=self.COLORS["fg"],
            selectcolor=self.COLORS["card"],
            command=update_asset_name,
        )
        zip_radio.pack(side="left", padx=(0, 15))

        exe_radio = tk.Radiobutton(
            type_frame,
            text="EXE (auto-update)",
            variable=asset_type_var,
            value="exe",
            bg=self.COLORS["bg"],
            fg=self.COLORS["fg"],
            selectcolor=self.COLORS["card"],
            command=update_asset_name,
        )
        exe_radio.pack(side="left")

        # Asset name input (auto-filled based on type)
        tk.Label(
            content,
            text="Asset Name",
            font=self.FONTS["small"],
            bg=self.COLORS["bg"],
            fg=self.COLORS["fg_dim"],
        ).pack(anchor="w")
        asset_frame = tk.Frame(content, bg=self.COLORS["card"], bd=1, relief="solid")
        asset_frame.pack(fill="x", pady=(2, 10))
        asset_entry = tk.Entry(
            asset_frame,
            font=self.FONTS["body"],
            width=30,
            bg=self.COLORS["input_bg"],
            fg=self.COLORS["fg"],
            insertbackground=self.COLORS["fg"],
            bd=0,
        )
        asset_entry.insert(0, f"FourT_v{version}.zip")  # Default to zip
        asset_entry.pack(padx=10, pady=8)

        # Download count input
        tk.Label(
            content,
            text="Download Count",
            font=self.FONTS["small"],
            bg=self.COLORS["bg"],
            fg=self.COLORS["fg_dim"],
        ).pack(anchor="w")
        count_frame = tk.Frame(content, bg=self.COLORS["card"], bd=1, relief="solid")
        count_frame.pack(fill="x", pady=(2, 10))
        count_entry = tk.Entry(
            count_frame,
            font=self.FONTS["body"],
            width=30,
            bg=self.COLORS["input_bg"],
            fg=self.COLORS["fg"],
            insertbackground=self.COLORS["fg"],
            bd=0,
        )
        count_entry.pack(padx=10, pady=8)
        count_entry.focus()

        # Buttons
        btn_frame = tk.Frame(content, bg=self.COLORS["bg"])
        btn_frame.pack(fill="x", pady=(15, 0))

        def save():
            try:
                count = int(count_entry.get())
                asset = asset_entry.get().strip()
                self._run_async(
                    db.set_asset_download_count(version, asset, count),
                    lambda _: (dialog.destroy(), self._refresh_data()),
                )
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number")

        save_btn = tk.Label(
            btn_frame,
            text="✓ Save",
            font=self.FONTS["body"],
            bg=self.COLORS["accent"],
            fg="white",
            cursor="hand2",
            padx=15,
            pady=5,
        )
        save_btn.pack(side="right")
        save_btn.bind("<Button-1>", lambda e: save())

        cancel_btn = tk.Label(
            btn_frame,
            text="✗ Cancel",
            font=self.FONTS["body"],
            bg=self.COLORS["card"],
            fg=self.COLORS["fg"],
            cursor="hand2",
            padx=15,
            pady=5,
        )
        cancel_btn.pack(side="right", padx=(0, 10))
        cancel_btn.bind("<Button-1>", lambda e: dialog.destroy())

        # Enter key to save
        count_entry.bind("<Return>", lambda e: save())

    def _delete_release(self, version):
        """Delete a release"""
        if messagebox.askyesno("Confirm", f"Delete release {version}?"):
            self._run_async(db.delete_release(version), lambda _: self._refresh_data())

    def _sync_folder(self):
        """Sync releases from folder"""
        from backend.routers.releases import sync_releases_from_folder

        self._run_async(
            sync_releases_from_folder(),
            lambda _: (
                messagebox.showinfo("Success", "Synced releases from folder"),
                self._refresh_data(),
            ),
        )
