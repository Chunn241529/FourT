"""
WWM Combo Settings Dialog - Keybinding configuration UI
"""

import tkinter as tk
from .tooltip import RichTooltip

# Import theme
try:
    from ..theme import colors, FONTS, ModernButton
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from ui.theme import colors, FONTS, ModernButton


class SettingsDialog(tk.Toplevel):
    """Settings dialog for WWM Combo keybindings"""
    
    def __init__(self, parent, on_save=None):
        super().__init__(parent)
        self.parent = parent
        self.on_save = on_save
        
        self.title("⚙ WWM Combo Settings")
        self.geometry("580x520")
        self.configure(bg=colors['bg'])
        self.transient(parent)
        self.grab_set()
        
        # Center relative to parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 580) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 480) // 2
        self.geometry(f"+{x}+{y}")
        
        # Get settings service
        from services.user_settings_service import get_user_settings_service
        self.settings_service = get_user_settings_service()
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup dialog UI"""
        # Header
        header = tk.Frame(self, bg=colors['header'], height=45)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="⚙ Keybinding Settings", font=FONTS['h2'],
                bg=colors['header'], fg=colors['fg']).pack(side='left', padx=15, pady=10)
        
        # Content - two column layout
        content = tk.Frame(self, bg=colors['bg'])
        content.pack(fill='both', expand=True, padx=15, pady=10)
        
        # Left column
        left_col = tk.Frame(content, bg=colors['bg'])
        left_col.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # Right column
        right_col = tk.Frame(content, bg=colors['bg'])
        right_col.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        # Keybinding entries
        keybindings = self.settings_service.get_all_keybindings()
        self.entry_vars = {}
        
        # Left column skills
        left_skills = [
            ("skill_1", "Skill 1"),
            ("skill_2", "Skill 2"),
            ("light_attack", "Light Attack"),
            ("heavy_attack", "Heavy Attack"),
            ("charge_attack", "Charge Attack"),
            ("deflect", "Deflect"),
            ("defend", "Defend"),
            ("dodge", "Dodge"),
            ("jump", "Jump"),
            ("tab", "Tab"),
            ("switch_weapon", "Switch Weapon"),
        ]
        
        # Right column skills (Mystic)
        right_skills = [
            ("mystic_skill_skill_1", "Mystic 1"),
            ("mystic_skill_skill_2", "Mystic 2"),
            ("mystic_skill_skill_3", "Mystic 3"),
            ("mystic_skill_skill_4", "Mystic 4"),
            ("mystic_skill_skill_5", "Mystic Alt 1"),
            ("mystic_skill_skill_6", "Mystic Alt 2"),
            ("mystic_skill_skill_7", "Mystic Alt 3"),
            ("mystic_skill_skill_8", "Mystic Alt 4"),
        ]
        
        # Build left column
        tk.Label(left_col, text="⚔ Combat Skills", font=FONTS['bold'],
                bg=colors['bg'], fg=colors['accent']).pack(anchor='w', pady=(0, 8))
        
        for skill_id, label in left_skills:
            self._create_entry_row(left_col, skill_id, label, keybindings)
        
        # Build right column
        tk.Label(right_col, text="✨ Mystic Skills", font=FONTS['bold'],
                bg=colors['bg'], fg=colors['accent']).pack(anchor='w', pady=(0, 8))
        
        for skill_id, label in right_skills:
            self._create_entry_row(right_col, skill_id, label, keybindings)
        
        # Special keys reference (outside content frame)
        ref_frame = tk.Frame(self, bg=colors['card'])
        ref_frame.pack(fill='x', padx=15, pady=(5, 0))
        
        tk.Label(ref_frame, text="Special Keys: lmb, rmb, mouse4, x1, x2, scroll_up, scroll_down, shift, ctrl, alt, space, tab", 
                font=FONTS['small'], bg=colors['card'], fg=colors['fg_dim']).pack(padx=10, pady=6)
        
        # Buttons
        btn_frame = tk.Frame(self, bg=colors['bg'])
        btn_frame.pack(fill='x', padx=15, pady=12)
        
        ModernButton(btn_frame, text="Reset to Default", command=self._reset_defaults,
                    kind='secondary', width=14).pack(side='left')
        
        ModernButton(btn_frame, text="Cancel", command=self.destroy,
                    kind='secondary', width=10).pack(side='right', padx=(5, 0))
        
        ModernButton(btn_frame, text="Save", command=self._save_settings,
                    kind='primary', width=10).pack(side='right')
    
    def _create_entry_row(self, parent, skill_id, label, keybindings):
        """Create a keybinding entry row"""
        row = tk.Frame(parent, bg=colors['bg'])
        row.pack(fill='x', pady=3)
        
        tk.Label(row, text=label + ":", font=FONTS['body'], width=12, anchor='w',
                bg=colors['bg'], fg=colors['fg']).pack(side='left')
        
        var = tk.StringVar(value=keybindings.get(skill_id, ""))
        entry = tk.Entry(row, textvariable=var, font=FONTS['body'],
                       bg=colors['input_bg'], fg=colors['fg'],
                       insertbackground=colors['fg'], width=12)
        entry.pack(side='left', padx=5)
        self.entry_vars[skill_id] = var
    
    def _save_settings(self):
        """Save settings and close"""
        for skill_id, var in self.entry_vars.items():
            self.settings_service.set_keybind(skill_id, var.get().strip())
        self.settings_service.save_settings()
        
        if self.on_save:
            self.on_save()
        self.destroy()
    
    def _reset_defaults(self):
        """Reset to default keybindings"""
        self.settings_service.reset_to_defaults()
        keybindings = self.settings_service.get_all_keybindings()
        for skill_id, var in self.entry_vars.items():
            var.set(keybindings.get(skill_id, ""))
