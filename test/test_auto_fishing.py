# Cập nhật DEFAULT_CONFIG (thêm vào đầu file)
DEFAULT_CONFIG.update({
    "skills_data": {
        "Nameless Spear": [
            {"name": "Qiankun's Lock", "key_default": "q", "hold": 0.3, "desc": "Immobilize 2s + restore endurance"},
            {"name": "Legion Crusher", "key_default": "e", "hold": 0.4, "desc": "High dmg thrust (Unrivaled)"},
            {"name": "Storm Dance", "key_default": "rmb", "hold": 1.0, "desc": "Charged spin flurry"},
            {"name": "Light Attack", "key_default": "lmb", "hold": 0.15, "desc": "Chain x4"},
            {"name": "Spear Conversion", "key_default": "tab", "hold": 0.1, "desc": "Dual swap"}
        ],
        "Heavenquaker Spear": [
            {"name": "Sober Sorrow", "key_default": "q", "hold": 3.0, "desc": "Spin 6 sweeps + buffs"},
            {"name": "Sweep All", "key_default": "e", "hold": 0.5, "desc": "AoE enhanced by buffs"},
            {"name": "Drifting Thrust", "key_default": "rmb", "hold": 0.8, "desc": "Charged thrust flurry"},
            {"name": "Light Attack", "key_default": "lmb", "hold": 0.15, "desc": "Basic"},
            {"name": "Spear Conversion", "key_default": "tab", "hold": 0.1, "desc": "Dual swap"}
        ]
    },
    "current_pattern": []
})

# Thêm class mới (trước class WWMHelperGUI)
class ComboBuilder(tk.Frame):
    def __init__(self, parent, gui):
        super().__init__(parent)
        self.gui = gui
        self.skills_data = self.gui.config.get("skills_data", {})
        self.slots_data = [None] * 10  # [{'skill': dict, 'key_var': StringVar}]
        self.drag_data = None
        self.build_ui()

    def build_ui(self):
        # Left: Skills list
        left_frame = tk.LabelFrame(self, text="Skills (kéo thả)", bg="#2c3e50", fg="white")
        left_frame.pack(side="left", fill="y", padx=5, pady=5)

        self.skills_canvas = tk.Canvas(left_frame, width=200, height=400, bg="#34495e")
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.skills_canvas.yview)
        self.skills_scrollable = tk.Frame(self.skills_canvas)
        self.skills_scrollable.bind("<Configure>", lambda e: self.skills_canvas.configure(scrollregion=self.skills_canvas.bbox("all")))
        self.skills_canvas.create_window((0, 0), window=self.skills_scrollable, anchor="nw")
        self.skills_canvas.configure(yscrollcommand=scrollbar.set)
        self.skills_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.create_skills_list()

        # Middle: Slots timeline
        mid_frame = tk.LabelFrame(self, text="Combo Timeline (10 slots)", bg="#2c3e50", fg="white")
        mid_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        slots_container = tk.Frame(mid_frame)
        slots_container.pack(fill="x")
        self.slots = []
        for i in range(10):
            slot = tk.Frame(slots_container, bg="#ecf0f1", relief="ridge", width=80, height=60)
            slot.pack(side="left", padx=2, fill="both", expand=True)
            tk.Label(slot, text=str(i+1), font=("Arial", 12, "bold")).pack()
            slot.drop_tag = i  # for drop detect
            slot.bind("<Enter>", self.on_slot_enter)
            slot.bind("<Leave>", self.on_slot_leave)
            slot.bind("<ButtonRelease-1>", self.on_drop)
            self.slots.append(slot)

        # Buttons
        btn_frame = tk.Frame(mid_frame)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="Generate Pattern", command=self.generate).pack(side="left")
        ttk.Button(btn_frame, text="Clear All", command=self.clear_all).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Load to Spear Macro", command=self.load_to_macro).pack(side="left", padx=5)

        # Output
        tk.Label(mid_frame, text="Generated Pattern:", anchor="w").pack(anchor="w")
        self.output_text = tk.Text(mid_frame, height=8, font=("Consolas", 9))
        self.output_text.pack(fill="both", expand=True, pady=5)

    def create_skills_list(self):
        for weapon, skills in self.skills_data.items():
            w_lbl = tk.Label(self.skills_scrollable, text=weapon, font=("Arial", 10, "bold"), bg="#3498db", fg="white", pady=5)
            w_lbl.pack(fill="x", pady=2)
            for skill in skills:
                lbl = tk.Label(self.skills_scrollable, text=skill["name"][:12] + "...", bg="#27ae60", fg="white", relief="raised", pady=8, padx=5)
                lbl.pack(fill="x", pady=1)
                lbl.skill = skill
                lbl.bind("<Button-1>", lambda e, s=skill: self.drag_start(e, s))

    def drag_start(self, event, skill):
        self.drag_data = skill
        self.gui.log(f"🔄 Kéo: {skill['name']}")

    def on_slot_enter(self, event):
        if self.drag_data:
            event.widget.config(bg="#f39c12")  # highlight

    def on_slot_leave(self, event):
        if self.drag_data:
            event.widget.config(bg="#ecf0f1")

    def on_drop(self, event):
        slot = event.widget
        if self.drag_data and hasattr(slot, 'drop_tag'):
            idx = slot.drop_tag
            self.drop_to_slot(idx, self.drag_data)
        # reset highlight
        slot.config(bg="#ecf0f1")
        self.drag_data = None

    def drop_to_slot(self, idx, skill):
        slot = self.slots[idx]
        # clear
        for child in slot.winfo_children():
            child.destroy()
        # new
        s_frame = tk.Frame(slot, bg="white")
        s_frame.pack(fill="both", expand=True, padx=2, pady=2)
        tk.Label(s_frame, text=skill['name'][:10], font=("Arial", 9)).pack()
        key_var = tk.StringVar(value=skill.get('key_default', 'lmb'))
        ttk.Combobox(s_frame, textvariable=key_var, values=['lmb', 'rmb', '1','2','3','4','5','q','e','r','t','f','space','tab'], width=6, state="readonly").pack(pady=2)
        tk.Button(s_frame, text="X", command=lambda i=idx: self.clear_slot(i), bg="#e74c3c", fg="white").pack()
        self.slots_data[idx] = {'skill': skill, 'key_var': key_var}
        self.gui.log(f"✅ Drop slot {idx+1}: {skill['name']}")

    def clear_slot(self, idx):
        for child in self.slots[idx].winfo_children():
            child.destroy()
        self.slots_data[idx] = None

    def clear_all(self):
        for i in range(10):
            self.clear_slot(i)

    def generate(self):
        pattern = []
        for data in self.slots_data:
            if data:
                pat = {
                    "action": data['key_var'].get(),
                    "hold": data['skill'].get('hold', 0.2)
                }
                pattern.append(pat)
        json_str = json.dumps(pattern, indent=2)
        self.output_text.delete('1.0', 'end')
        self.output_text.insert('1.0', json_str)
        self.gui.log(f"📋 Generate: {len(pattern)} actions")

    def load_to_macro(self):
        pattern = []
        for data in self.slots_data:
            if data:
                pattern.append({
                    "action": data['key_var'].get(),
                    "hold": data['skill'].get('hold', 0.2)
                })
        self.gui.config['spear_pattern'] = pattern  # or current_pattern
        self.gui.save_config()
        # Reload to bot if running
        if hasattr(self.gui, 'spear_bot') and self.gui.spear_bot.running:
            self.gui.spear_bot.pattern = pattern
        self.gui.log("💾 Loaded to Spear Macro!")

# Cập nhật WWMHelperGUI.build_ui() - thêm Notebook và tab
# Thay main_frame bằng notebook
# Trong build_ui(), sau header:

self.notebook = ttk.Notebook(main_frame)
self.notebook.pack(fill="both", expand=True, pady=10)

# Existing frames → tabs
fish_tab = tk.Frame(self.notebook)
self.notebook.add(fish_tab, text="🎣 Câu Cá")
# Move fish_frame content to fish_tab

daily_tab = tk.Frame(self.notebook)
self.notebook.add(daily_tab, text="📋 Daily")
# Move daily_frame to daily_tab

dodge_tab = tk.Frame(self.notebook)
self.notebook.add(dodge_tab, text="⚔️ Dodge")
# Move dodge_frame to dodge_tab

spear_tab = tk.Frame(self.notebook)
self.notebook.add(spear_tab, text="🔱 Spear Macro")
# Move spear_frame to spear_tab

combo_tab = tk.Frame(self.notebook)
self.notebook.add(combo_tab, text="🎮 Combo Builder")
self.combo_builder = ComboBuilder(combo_tab, self)

# Di chuyển control_frame, log_frame dưới notebook hoặc vào tab chung "Control"

# Log frame pack dưới notebook
log_frame.pack(fill="both", expand=True, pady=5)

# Trong __init__: self.root.bind('<ButtonRelease-1>', self.combo_builder.on_drop)  # if combo active, but since root binds work across tabs

# Thêm vào spear_bot: self.pattern = self.gui.config.get('spear_pattern', [])
# Trong spear_bot.loop: pattern = self.gui.config.get('spear_pattern', DEFAULT_CONFIG['pvp_pattern'])

# Update spear_bot __init__: self.pattern = []

# Trong loop: for act in self.pattern: ...

# Hoàn tất: Chạy tool → tab Combo Builder → kéo skill từ left → thả slot → chỉnh key → Generate → Load to Spear