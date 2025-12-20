"""
Playlist Frame - Modern UI with animations and hover effects
Uses theme components for consistent styling
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os

from .theme import colors, FONTS, ModernButton, GradientCard, COLORS
from .animations import FadeEffect, ColorTransition, hex_to_rgb, rgb_to_hex
from services.playlist_service import get_playlist_service, PlaylistService


class SongListItem(tk.Frame):
    """Individual song item with hover animation"""
    
    def __init__(self, parent, index, song, is_current=False, on_click=None, on_remove=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(bg=colors['card'], cursor='hand2')
        
        self.index = index
        self.song = song
        self.is_current = is_current
        self.on_click = on_click
        self.on_remove = on_remove
        self._hover = False
        
        # Highlight for current song
        self.indicator = tk.Frame(self, width=3, bg=colors['accent'] if is_current else colors['card'])
        self.indicator.pack(side='left', fill='y')
        
        # Content
        content = tk.Frame(self, bg=colors['card'])
        content.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        
        # Index
        self.index_label = tk.Label(
            content,
            text=f"{index + 1}.",
            font=('Segoe UI', 10),
            bg=colors['card'],
            fg=colors['accent'] if is_current else colors['fg_dim'],
            width=3,
            anchor='e'
        )
        self.index_label.pack(side='left')
        
        # Now playing indicator
        self.play_icon = tk.Label(
            content,
            text="▶" if is_current else "  ",
            font=('Segoe UI', 8),
            bg=colors['card'],
            fg=colors['accent'],
            width=2
        )
        self.play_icon.pack(side='left', padx=(5, 0))
        
        # Song name
        name = song.get('name', 'Unknown')
        if len(name) > 35:
            name = name[:32] + "..."
        
        self.name_label = tk.Label(
            content,
            text=name,
            font=('Segoe UI', 10, 'bold') if is_current else ('Segoe UI', 10),
            bg=colors['card'],
            fg=colors['fg'] if is_current else colors['fg_dim'],
            anchor='w'
        )
        self.name_label.pack(side='left', fill='x', expand=True, padx=(8, 0))
        
        # Remove button (hidden until hover)
        self.remove_btn = tk.Label(
            self,
            text="✕",
            font=('Segoe UI', 10),
            bg=colors['card'],
            fg=colors['card'],  # Hidden by default
            cursor='hand2',
            width=3
        )
        self.remove_btn.pack(side='right', padx=5)
        
        # Bind events
        for widget in [self, content, self.index_label, self.play_icon, self.name_label]:
            widget.bind('<Enter>', self._on_enter)
            widget.bind('<Leave>', self._on_leave)
            widget.bind('<Button-1>', self._on_click)
            widget.bind('<Double-Button-1>', self._on_double_click)
        
        self.remove_btn.bind('<Enter>', self._on_remove_enter)
        self.remove_btn.bind('<Leave>', self._on_remove_leave)
        self.remove_btn.bind('<Button-1>', self._on_remove_click)
    
    def _on_enter(self, e):
        self._hover = True
        self.configure(bg=colors['card_hover'])
        for widget in [self.indicator, self.index_label, self.play_icon, self.name_label]:
            try:
                widget.configure(bg=colors['card_hover'])
            except: pass
        # Show remove button
        self.remove_btn.configure(fg=colors['fg_dim'], bg=colors['card_hover'])
    
    def _on_leave(self, e):
        self._hover = False
        bg = colors['card']
        self.configure(bg=bg)
        for widget in [self.indicator, self.index_label, self.play_icon, self.name_label, self.remove_btn]:
            try:
                widget.configure(bg=bg)
            except: pass
        # Hide remove button
        self.remove_btn.configure(fg=bg)
        # Restore indicator color
        self.indicator.configure(bg=colors['accent'] if self.is_current else colors['card'])
    
    def _on_remove_enter(self, e):
        self.remove_btn.configure(fg=colors['error'])
    
    def _on_remove_leave(self, e):
        if self._hover:
            self.remove_btn.configure(fg=colors['fg_dim'])
    
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
    
    def __init__(self, parent, text, command=None, active=False, width=50, height=32, **kwargs):
        super().__init__(parent, width=width, height=height, bg=colors['bg'], 
                         highlightthickness=0, **kwargs)
        
        self.text = text
        self.command = command
        self._active = active
        self._width = width
        self._height = height
        self._hover = False
        
        self._draw()
        
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Button-1>', self._on_click)
    
    def _draw(self):
        self.delete('all')
        
        w, h = self._width, self._height
        r = 6  # corner radius
        
        # Background
        if self._active:
            fill = colors['accent']
            text_color = 'white'
        elif self._hover:
            fill = colors['card_hover']
            text_color = colors['fg']
        else:
            fill = colors['card']
            text_color = colors['fg_dim']
        
        # Draw rounded rect
        points = [
            r, 0, w-r, 0, w, 0, w, r, w, h-r, w, h, w-r, h, r, h, 0, h, 0, h-r, 0, r, 0, 0
        ]
        self.create_polygon(points, smooth=True, fill=fill, outline='')
        
        # Text
        self.create_text(w/2, h/2, text=self.text, fill=text_color, font=('Segoe UI Emoji', 12))
        
        self.config(cursor='hand2')
    
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


class PlaylistFrame(tk.Frame):
    """Modern UI component for playlist"""
    
    def __init__(self, parent, library_service, on_play_song=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(bg=colors['bg'])
        
        self.library_service = library_service
        self.on_play_song = on_play_song
        
        self.playlist = get_playlist_service()
        self.playlist.set_on_playlist_change(self._refresh_list)
        self.playlist.set_on_song_change(self._on_song_change)
        
        self._create_widgets()
        self._refresh_list()
    
    def _create_widgets(self):
        """Create modern UI"""
        
        # ===== HEADER =====
        header = tk.Frame(self, bg=colors['bg'])
        header.pack(fill='x', padx=15, pady=(15, 10))
        
        # Title with icon
        title_frame = tk.Frame(header, bg=colors['bg'])
        title_frame.pack(side='left')
        
        tk.Label(
            title_frame,
            text="🎵",
            font=('Segoe UI Emoji', 18),
            bg=colors['bg'],
            fg=colors['accent']
        ).pack(side='left')
        
        tk.Label(
            title_frame,
            text="Playlist",
            font=('Segoe UI', 16, 'bold'),
            bg=colors['bg'],
            fg=colors['fg']
        ).pack(side='left', padx=(8, 0))
        
        # Add button with animation
        self.add_btn = ModernButton(
            header,
            text="+ Thêm",
            command=self._show_add_menu,
            kind='accent',
            width=8
        )
        self.add_btn.pack(side='right')
        
        # ===== SONG LIST CONTAINER =====
        list_container = GradientCard(self)
        list_container.pack(fill='both', expand=True, padx=15, pady=5)
        
        # Scrollable frame
        self.canvas = tk.Canvas(
            list_container.content,
            bg=colors['card'],
            highlightthickness=0,
            bd=0
        )
        self.scrollbar = ttk.Scrollbar(list_container.content, orient='vertical', command=self.canvas.yview)
        
        self.songs_frame = tk.Frame(self.canvas, bg=colors['card'])
        
        self._songs_window_id = self.canvas.create_window((0, 0), window=self.songs_frame, anchor='nw')
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Bind canvas resize to update songs_frame width
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        self.canvas.pack(side='left', fill='both', expand=True)
        self.scrollbar.pack(side='right', fill='y')
        
        # Mouse wheel scrolling
        self.canvas.bind_all('<MouseWheel>', self._on_mousewheel)
        
        # Empty state
        self.empty_label = tk.Label(
            self.songs_frame,
            text="🎵\n\nPlaylist trống\n\nClick '+ Thêm' để thêm bài",
            font=('Segoe UI', 11),
            bg=colors['card'],
            fg=colors['fg_dim'],
            justify='center'
        )
        
        # ===== PLAYBACK CONTROLS =====
        controls_card = GradientCard(self)
        controls_card.pack(fill='x', padx=15, pady=12)
        
        # Main controls row
        controls_row = tk.Frame(controls_card.content, bg=colors['card'])
        controls_row.pack(fill='x')
        
        # Left: Playback buttons
        playback_frame = tk.Frame(controls_row, bg=colors['card'])
        playback_frame.pack(side='left')
        
        # Previous
        self.prev_btn = ToggleButton(playback_frame, "⏮", command=self._prev_song, width=42, height=36)
        self.prev_btn.pack(side='left', padx=2)
        
        # Play
        self.play_btn = ToggleButton(playback_frame, "▶", command=self._play_current, width=42, height=36)
        self.play_btn.pack(side='left', padx=2)
        
        # Next
        self.next_btn = ToggleButton(playback_frame, "⏭", command=self._next_song, width=42, height=36)
        self.next_btn.pack(side='left', padx=2)
        
        # Right: Mode toggles
        mode_frame = tk.Frame(controls_row, bg=colors['card'])
        mode_frame.pack(side='right')
        
        # Shuffle
        self.shuffle_btn = ToggleButton(
            mode_frame, "🔀", 
            command=self._toggle_shuffle,
            active=self.playlist.shuffle_enabled,
            width=42, height=36
        )
        self.shuffle_btn.pack(side='left', padx=2)
        
        # Repeat
        self.repeat_btn = ToggleButton(
            mode_frame, "🔁",
            command=self._toggle_repeat,
            active=self.playlist.repeat_mode != PlaylistService.REPEAT_NONE,
            width=42, height=36
        )
        self.repeat_btn.pack(side='left', padx=2)
        
        # ===== FOOTER: Save/Load =====
        footer = tk.Frame(self, bg=colors['bg'])
        footer.pack(fill='x', padx=15, pady=(0, 18))
        
        # Left: Song count
        self.count_label = tk.Label(
            footer,
            text="0 bài",
            font=('Segoe UI', 9),
            bg=colors['bg'],
            fg=colors['fg_dim']
        )
        self.count_label.pack(side='left')
        
        # Right: Actions
        actions = tk.Frame(footer, bg=colors['bg'])
        actions.pack(side='right')
        
        ModernButton(
            actions,
            text="💾",
            command=self._save_playlist,
            kind='secondary',
            width=4,
            font=('Segoe UI Emoji', 11)
        ).pack(side='left', padx=2)
        
        ModernButton(
            actions,
            text="📂",
            command=self._load_playlist,
            kind='secondary',
            width=4,
            font=('Segoe UI Emoji', 11)
        ).pack(side='left', padx=2)
        
        ModernButton(
            actions,
            text="🗑️",
            command=self._clear_playlist,
            kind='secondary',
            width=4,
            font=('Segoe UI Emoji', 11)
        ).pack(side='left', padx=2)
    
    def _on_mousewheel(self, event):
        # Only scroll if there's content to scroll
        if self.playlist.get_song_count() > 0:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')
    
    def _on_canvas_configure(self, event):
        """Handle canvas resize - update songs_frame width and center if empty"""
        canvas_width = event.width
        # Update songs_frame width to match canvas
        self.canvas.itemconfig(self._songs_window_id, width=canvas_width)
        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    # ==================== UI Updates ====================
    
    def _refresh_list(self):
        """Rebuild song list with animations"""
        # Clear existing
        for widget in self.songs_frame.winfo_children():
            widget.destroy()
        
        songs = self.playlist.get_all_songs()
        current_idx = self.playlist.get_current_index()
        
        if not songs:
            # Center the empty message
            self.empty_label = tk.Label(
                self.songs_frame,
                text="\n\n🎵\n\nPlaylist trống\n\nClick '+ Thêm' để thêm bài\n\n",
                font=('Segoe UI', 11),
                bg=colors['card'],
                fg=colors['fg_dim'],
                justify='center',
                anchor='center'
            )
            self.empty_label.pack(fill='both', expand=True)
        else:
            for i, song in enumerate(songs):
                item = SongListItem(
                    self.songs_frame,
                    index=i,
                    song=song,
                    is_current=(i == current_idx),
                    on_click=self._on_song_click,
                    on_remove=self._on_song_remove
                )
                item.pack(fill='x', pady=1)
        
        # Update count
        count = len(songs)
        self.count_label.config(text=f"{count} bài")
        
        # Update button states
        self._update_mode_buttons()
        
        # Update canvas scroll region
        self.songs_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def _on_song_change(self, song):
        self._refresh_list()
        # Scroll to current song
        current_idx = self.playlist.get_current_index()
        if current_idx >= 0:
            self.canvas.yview_moveto(current_idx / max(1, self.playlist.get_song_count()))
    
    def _update_mode_buttons(self):
        """Update shuffle/repeat button states"""
        self.shuffle_btn.set_active(self.playlist.shuffle_enabled)
        
        mode = self.playlist.repeat_mode
        if mode == PlaylistService.REPEAT_NONE:
            self.repeat_btn.set_active(False)
            self.repeat_btn.set_text("🔁")
        elif mode == PlaylistService.REPEAT_ALL:
            self.repeat_btn.set_active(True)
            self.repeat_btn.set_text("🔁")
        else:  # REPEAT_ONE
            self.repeat_btn.set_active(True)
            self.repeat_btn.set_text("🔂")
    
    # ==================== Add Songs ====================
    
    def _show_add_menu(self):
        """Show add menu with animation"""
        menu = tk.Menu(self, tearoff=0, bg=colors['card'], fg=colors['fg'],
                       activebackground=colors['accent'], activeforeground='white',
                       font=('Segoe UI', 10), bd=0)
        menu.add_command(label="📂  Từ thư viện...", command=self._add_from_library)
        menu.add_command(label="📁  Duyệt file...", command=self._add_from_file)
        
        try:
            x = self.add_btn.winfo_rootx()
            y = self.add_btn.winfo_rooty() + self.add_btn.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()
    
    def _add_from_library(self):
        """Modern library selection dialog"""
        dialog = tk.Toplevel(self)
        dialog.title("Chọn từ thư viện")
        dialog.geometry("320x450")
        dialog.configure(bg=colors['bg'])
        dialog.transient(self)
        dialog.grab_set()
        
        # Center
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 320) // 2
        y = (dialog.winfo_screenheight() - 450) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Header
        header = tk.Frame(dialog, bg=colors['bg'])
        header.pack(fill='x', padx=15, pady=15)
        
        tk.Label(
            header,
            text="📂 Chọn bài hát",
            font=('Segoe UI', 14, 'bold'),
            bg=colors['bg'],
            fg=colors['fg']
        ).pack(side='left')
        
        # List
        list_frame = tk.Frame(dialog, bg=colors['card'])
        list_frame.pack(fill='both', expand=True, padx=15, pady=5)
        
        listbox = tk.Listbox(
            list_frame,
            selectmode='extended',
            bg=colors['card'],
            fg=colors['fg'],
            font=('Segoe UI', 10),
            selectbackground=colors['accent'],
            selectforeground='white',
            highlightthickness=0,
            bd=0,
            activestyle='none'
        )
        
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side='right', fill='y')
        listbox.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        
        for midi in self.library_service.get_local_midi_files():
            listbox.insert(tk.END, midi)
        
        # Buttons
        btn_frame = tk.Frame(dialog, bg=colors['bg'])
        btn_frame.pack(fill='x', padx=15, pady=15)
        
        def add_selected():
            selections = listbox.curselection()
            count = 0
            for idx in selections:
                filename = listbox.get(idx)
                path = self.library_service.get_midi_path(filename)
                self.playlist.add_song(path, filename)
                count += 1
            dialog.destroy()
        
        ModernButton(
            btn_frame,
            text="Thêm",
            command=add_selected,
            kind='accent',
            width=10
        ).pack(side='left')
        
        ModernButton(
            btn_frame,
            text="Hủy",
            command=dialog.destroy,
            kind='secondary',
            width=8
        ).pack(side='right')
        
        # Fade in
        FadeEffect.fade_in(dialog, duration=150)
    
    def _add_from_file(self):
        from tkinter import filedialog
        paths = filedialog.askopenfilenames(
            filetypes=[("MIDI files", "*.mid *.midi")],
            title="Chọn file MIDI"
        )
        for path in paths:
            self.playlist.add_song(path)
    
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
        if song and self.on_play_song:
            self.on_play_song(song)
    
    def _next_song(self):
        song = self.playlist.next_song()
        if song and self.on_play_song:
            self.on_play_song(song)
    
    def _prev_song(self):
        song = self.playlist.prev_song()
        if song and self.on_play_song:
            self.on_play_song(song)
    
    def _toggle_shuffle(self):
        self.playlist.toggle_shuffle()
        self._update_mode_buttons()
    
    def _toggle_repeat(self):
        self.playlist.cycle_repeat_mode()
        self._update_mode_buttons()
    
    # ==================== Save/Load ====================
    
    def _save_playlist(self):
        if self.playlist.is_empty():
            messagebox.showinfo("Thông báo", "Playlist trống!")
            return
        
        name = simpledialog.askstring("Lưu Playlist", "Nhập tên playlist:", parent=self)
        if name:
            if self.playlist.save_playlist(name):
                messagebox.showinfo("✓", f"Đã lưu '{name}'")
            else:
                messagebox.showerror("Lỗi", "Không thể lưu")
    
    def _load_playlist(self):
        playlists = self.playlist.get_saved_playlists()
        if not playlists:
            messagebox.showinfo("Thông báo", "Chưa có playlist nào")
            return
        
        dialog = tk.Toplevel(self)
        dialog.title("Mở Playlist")
        dialog.geometry("280x350")
        dialog.configure(bg=colors['bg'])
        dialog.transient(self)
        dialog.grab_set()
        
        # Center
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 280) // 2
        y = (dialog.winfo_screenheight() - 350) // 2
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(
            dialog,
            text="📂 Chọn playlist",
            font=('Segoe UI', 14, 'bold'),
            bg=colors['bg'],
            fg=colors['fg']
        ).pack(padx=15, pady=15, anchor='w')
        
        listbox = tk.Listbox(
            dialog,
            bg=colors['card'],
            fg=colors['fg'],
            font=('Segoe UI', 10),
            selectbackground=colors['accent'],
            highlightthickness=0
        )
        listbox.pack(fill='both', expand=True, padx=15, pady=5)
        
        for name in playlists:
            listbox.insert(tk.END, name)
        
        btn_frame = tk.Frame(dialog, bg=colors['bg'])
        btn_frame.pack(fill='x', padx=15, pady=15)
        
        def load_selected():
            sel = listbox.curselection()
            if sel:
                name = listbox.get(sel[0])
                self.playlist.load_playlist(name)
                dialog.destroy()
        
        ModernButton(btn_frame, text="Mở", command=load_selected, kind='accent', width=8).pack(side='left')
        ModernButton(btn_frame, text="Hủy", command=dialog.destroy, kind='secondary', width=8).pack(side='right')
        
        FadeEffect.fade_in(dialog, duration=150)
    
    def _clear_playlist(self):
        if self.playlist.is_empty():
            return
        if messagebox.askyesno("Xác nhận", "Xóa tất cả bài?"):
            self.playlist.clear()
    
    # ==================== Public Methods ====================
    
    def on_playback_complete(self):
        """Called when a song finishes - auto advance"""
        song = self.playlist.next_song()
        if song and self.on_play_song:
            self.after(
                self.playlist.delay_between_songs * 1000,
                lambda: self.on_play_song(song)
            )
    
    def add_current_midi(self, path, name=None):
        """Add MIDI to playlist"""
        self.playlist.add_song(path, name)
