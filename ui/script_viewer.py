"""
Script Viewer & Editor Window
Allows viewing and editing MIDI script events
"""

import tkinter as tk
import os
from tkinter import ttk, simpledialog, messagebox
from .theme import COLORS, FONTS, ModernButton, colors
from .components import FramelessWindow

class ScriptViewerWindow(FramelessWindow):
    """Window to view and edit generated key script"""
    
    def __init__(self, parent, events, midi_path, debug_info=None, on_play=None, on_save=None):
        # Extract filename for title
        filename = os.path.basename(midi_path) if midi_path else "MIDI"
        title = f"📋 Script: {filename}"
        
        super().__init__(parent.winfo_toplevel(), title=title)
        self.geometry("520x550")
        
        self.events = list(events)  # Make a mutable copy
        self.original_events = list(events)  # Keep original for reset
        self.midi_path = midi_path
        self.debug_info = debug_info or {}
        self.on_play = on_play
        self.on_save = on_save
        self.modified = False
        self.parent_frame = parent  # Store parent for re-processing
        
        self._create_widgets()
        self._populate_script()
        
    def _create_widgets(self):
        # Header (inside content_frame from FramelessWindow)
        header = tk.Frame(self.content_frame, bg=COLORS['bg'])
        header.pack(fill='x', padx=15, pady=(10, 5))
        
        self.event_count_label = tk.Label(
            header, 
            text=f"📋 Tổng: {len(self.events)} events", 
            font=FONTS['h2'], 
            bg=COLORS['bg'], 
            fg=COLORS['fg']
        )
        self.event_count_label.pack(side='left')
        
        # Buttons row
        btn_frame = tk.Frame(header, bg=COLORS['bg'])
        btn_frame.pack(side='right')
        
        ModernButton(
            btn_frame, 
            text="▶ Phát", 
            command=self._on_play_click, 
            kind='success',
            width=8
        ).pack(side='left', padx=2)
        
        ModernButton(
            btn_frame, 
            text="↩ Reset", 
            command=self._reset_script, 
            kind='secondary',
            width=8
        ).pack(side='left', padx=2)
        
        # Instructions
        hint_frame = tk.Frame(self.content_frame, bg=COLORS['bg'])
        hint_frame.pack(fill='x', padx=15, pady=(0, 5))
        
        tk.Label(
            hint_frame, 
            text="💡 Double-click để chỉnh sửa | Del để xóa event", 
            font=('Segoe UI', 9), 
            bg=COLORS['bg'], 
            fg=colors['fg_dim']
        ).pack(side='left')
        
        # ===== DEBUG INFO PANEL =====
        if self.debug_info:
            debug_frame = tk.Frame(self.content_frame, bg=colors['card'])
            debug_frame.pack(fill='x', padx=15, pady=(0, 10))
            
            inner_debug = tk.Frame(debug_frame, bg=colors['card'])
            inner_debug.pack(fill='x', padx=10, pady=10)
            
            # Row 1: Key detection info
            info_row1 = tk.Frame(inner_debug, bg=colors['card'])
            info_row1.pack(fill='x')
            
            tk.Label(info_row1, text="🎵 Detected Key:", font=('Segoe UI', 10),
                     bg=colors['card'], fg=colors['fg_dim']).pack(side='left')
            tk.Label(info_row1, text=self.debug_info.get('estimated_key', 'N/A'),
                     font=('Segoe UI', 10, 'bold'), bg=colors['card'], 
                     fg=colors['accent']).pack(side='left', padx=(5, 20))
            
            tk.Label(info_row1, text="Transpose:", font=('Segoe UI', 10),
                     bg=colors['card'], fg=colors['fg_dim']).pack(side='left')
            tk.Label(info_row1, text=f"{self.debug_info.get('transpose', 0):+d} semitones",
                     font=('Segoe UI', 10, 'bold'), bg=colors['card'], 
                     fg=colors['fg']).pack(side='left', padx=(5, 0))
            
            # Row 2: Out of range stats + Manual transpose
            info_row2 = tk.Frame(inner_debug, bg=colors['card'])
            info_row2.pack(fill='x', pady=(8, 0))
            
            out_range = self.debug_info.get('out_range', 0)
            total = self.debug_info.get('total_notes', 1)
            out_pct = 100 * out_range / total if total > 0 else 0
            
            out_color = colors['success'] if out_pct < 5 else (colors['warning'] if out_pct < 20 else colors['error'])
            tk.Label(info_row2, text="📊 Out of range:", font=('Segoe UI', 10),
                     bg=colors['card'], fg=colors['fg_dim']).pack(side='left')
            tk.Label(info_row2, text=f"{out_range}/{total} ({out_pct:.1f}%)",
                     font=('Segoe UI', 10, 'bold'), bg=colors['card'], 
                     fg=out_color).pack(side='left', padx=(5, 15))
            
            # Row 3: Auto transpose toggle + Manual transpose
            info_row3 = tk.Frame(inner_debug, bg=colors['card'])
            info_row3.pack(fill='x', pady=(8, 0))
            
            # Auto-transpose toggle
            self.auto_transpose_var = tk.BooleanVar(value=True)
            auto_check = tk.Checkbutton(
                info_row3, text="Auto Transpose", 
                variable=self.auto_transpose_var,
                font=('Segoe UI', 9),
                bg=colors['card'], fg=colors['fg'],
                selectcolor=colors['card'],
                activebackground=colors['card'],
                command=self._on_auto_transpose_toggle
            )
            auto_check.pack(side='left')
            
            # Manual transpose control
            tk.Label(info_row3, text="| Manual:", font=('Segoe UI', 10),
                     bg=colors['card'], fg=colors['fg_dim']).pack(side='left', padx=(10, 5))
            
            self.transpose_var = tk.StringVar(value=str(self.debug_info.get('transpose', 0)))
            self.transpose_entry = tk.Entry(info_row3, textvariable=self.transpose_var, width=5,
                                        font=('Segoe UI', 10), bg=colors['input_bg'], fg=COLORS['fg'])
            self.transpose_entry.pack(side='left', padx=5)
            
            ModernButton(info_row3, text="Reprocess", command=self._reprocess_with_transpose,
                         kind='accent', width=10).pack(side='left', padx=5)
        
        # Script List
        list_frame = tk.Frame(self.content_frame, bg=COLORS['bg'])
        list_frame.pack(fill='both', expand=True, padx=15, pady=(0, 10))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side='right', fill='y')
        
        # Treeview with editable appearance
        columns = ('idx', 'time', 'action', 'key', 'modifier')
        self.tree = ttk.Treeview(
            list_frame, 
            columns=columns, 
            show='headings', 
            yscrollcommand=scrollbar.set,
            selectmode='browse'
        )
        
        self.tree.heading('idx', text='#')
        self.tree.heading('time', text='Time (s)')
        self.tree.heading('action', text='Action')
        self.tree.heading('key', text='Key')
        self.tree.heading('modifier', text='Modifier')
        
        self.tree.column('idx', width=40, anchor='center')
        self.tree.column('time', width=80, anchor='center')
        self.tree.column('action', width=80, anchor='center')
        self.tree.column('key', width=60, anchor='center')
        self.tree.column('modifier', width=100, anchor='center')
        
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.tree.yview)
        
        # Bind events
        self.tree.bind('<Double-1>', self._on_double_click)
        self.tree.bind('<Delete>', self._on_delete)
        
    def _populate_script(self):
        """Populate the treeview with events"""
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for idx, event in enumerate(self.events):
            time, action, key, modifier = event
            mod_str = modifier if modifier else "-"
            action_emoji = "⬇" if action == "press" else "⬆"
            self.tree.insert('', 'end', values=(
                idx + 1,
                f"{time:.3f}",
                f"{action_emoji} {action}",
                key.upper(),
                mod_str
            ))
        
        self.event_count_label.config(text=f"📋 Tổng: {len(self.events)} events")
        
    def _on_double_click(self, event):
        """Handle double-click to edit"""
        item = self.tree.selection()
        if not item:
            return
            
        item = item[0]
        col = self.tree.identify_column(event.x)
        row_idx = int(self.tree.item(item)['values'][0]) - 1
        
        if row_idx < 0 or row_idx >= len(self.events):
            return
            
        current_event = self.events[row_idx]
        time, action, key, modifier = current_event
        
        # Determine which column was clicked
        if col == '#2':  # Time column
            new_val = simpledialog.askfloat(
                "Chỉnh Time", 
                f"Nhập thời gian mới (giây):",
                initialvalue=time,
                minvalue=0.0,
                parent=self
            )
            if new_val is not None:
                self.events[row_idx] = (new_val, action, key, modifier)
                self._mark_modified()
                
        elif col == '#4':  # Key column
            new_val = simpledialog.askstring(
                "Chỉnh Key", 
                f"Nhập phím mới (ví dụ: a, s, d, f):",
                initialvalue=key,
                parent=self
            )
            if new_val and len(new_val) == 1:
                self.events[row_idx] = (time, action, new_val.lower(), modifier)
                self._mark_modified()
                
        elif col == '#5':  # Modifier column
            # Show options
            mod_window = tk.Toplevel(self)
            mod_window.title("Chọn Modifier")
            mod_window.geometry("200x150")
            mod_window.configure(bg=COLORS['bg'])
            mod_window.transient(self)
            mod_window.grab_set()
            
            tk.Label(mod_window, text="Chọn modifier:", font=FONTS['body'],
                    bg=COLORS['bg'], fg=COLORS['fg']).pack(pady=10)
            
            def set_mod(mod):
                self.events[row_idx] = (time, action, key, mod)
                self._mark_modified()
                mod_window.destroy()
            
            for mod_text, mod_val in [("Không có", None), ("Shift (♯)", "shift"), ("Ctrl (♭)", "ctrl")]:
                btn = ModernButton(mod_window, text=mod_text, command=lambda m=mod_val: set_mod(m),
                                  kind='secondary' if mod_val != modifier else 'accent', width=15)
                btn.pack(pady=3)
        
        self._populate_script()
            
    def _on_delete(self, event):
        """Delete selected event"""
        item = self.tree.selection()
        if not item:
            return
            
        row_idx = int(self.tree.item(item[0])['values'][0]) - 1
        
        if row_idx < 0 or row_idx >= len(self.events):
            return
            
        # Find and delete paired event (press/release)
        deleted = self.events[row_idx]
        time, action, key, modifier = deleted
        
        # Find paired event
        paired_action = "release" if action == "press" else "press"
        paired_idx = None
        for i, ev in enumerate(self.events):
            if ev[1] == paired_action and ev[2] == key and ev[3] == modifier:
                # Found a potential pair
                if action == "press" and ev[0] >= time:
                    paired_idx = i
                    break
                elif action == "release" and ev[0] <= time:
                    paired_idx = i
                    break
        
        if paired_idx is not None:
            if messagebox.askyesno("Xóa Event", f"Xóa cả cặp press/release cho phím '{key}'?"):
                # Delete both (higher index first)
                if paired_idx > row_idx:
                    del self.events[paired_idx]
                    del self.events[row_idx]
                else:
                    del self.events[row_idx]
                    del self.events[paired_idx]
                self._mark_modified()
        else:
            if messagebox.askyesno("Xóa Event", f"Xóa event này?"):
                del self.events[row_idx]
                self._mark_modified()
        
        self._populate_script()
        
    def _reset_script(self):
        """Reset to original"""
        if self.modified:
            if not messagebox.askyesno("Reset", "Bỏ tất cả thay đổi?"):
                return
        
        self.events = list(self.original_events)
        self.modified = False
        # Update title (FramelessWindow uses set_title)
        filename = os.path.basename(self.midi_path) if self.midi_path else "MIDI"
        self.set_title(f"📋 Script: {filename}")
        self._populate_script()
        
    def _mark_modified(self):
        """Mark script as modified"""
        self.modified = True
        # Update title with modified indicator
        filename = os.path.basename(self.midi_path) if self.midi_path else "MIDI"
        self.set_title(f"📋 Script: {filename} *")
        # Sort by time after any modification
        self.events.sort(key=lambda x: x[0])
        
    def _reprocess_with_transpose(self):
        """Re-process MIDI with current settings"""
        # Import here to avoid circular import
        from core.midi_processor import preprocess_midi
        
        use_auto = hasattr(self, 'auto_transpose_var') and self.auto_transpose_var.get()
        
        if use_auto:
            # Auto transpose
            manual_transpose = None
        else:
            # Manual transpose
            try:
                manual_transpose = int(self.transpose_var.get())
            except ValueError:
                messagebox.showerror("Lỗi", "Transpose phải là số nguyên (VD: -2, 0, 3)")
                return
            
            if manual_transpose < -24 or manual_transpose > 24:
                messagebox.showerror("Lỗi", "Transpose phải trong khoảng -24 đến +24")  
                return
        
        try:
            events, _, new_debug_info = preprocess_midi(
                self.midi_path, 
                auto_transpose=use_auto,
                manual_transpose=manual_transpose
            )
            
            self.events = list(events)
            self.original_events = list(events)
            self.debug_info = new_debug_info
            self._populate_script()
            
            # Update parent's events AND debug_info
            if self.on_save:
                self.on_save(events, new_debug_info)
            
            if use_auto:
                messagebox.showinfo("✓", f"Đã reprocess với Auto Transpose (= {new_debug_info.get('transpose', 0):+d})")
            else:
                messagebox.showinfo("✓", f"Đã reprocess với transpose = {manual_transpose:+d}")
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi reprocess: {e}")
    
    def _on_auto_transpose_toggle(self):
        """Handle auto transpose toggle"""
        if hasattr(self, 'transpose_entry'):
            if self.auto_transpose_var.get():
                self.transpose_entry.config(state='disabled')
            else:
                self.transpose_entry.config(state='normal')
        
    def _on_play_click(self):
        """Handle play button click"""
        # Save events to parent first
        if self.on_save:
            self.on_save(self.events)
        
        # Try to play via parent_frame if it has _play_current method
        if hasattr(self.parent_frame, '_play_current'):
            self.destroy()  # Close script viewer
            self.parent_frame._play_current()
        elif self.on_play:
            self.on_play()
        
    def get_events(self):
        """Return current events (for parent to retrieve)"""
        return self.events
