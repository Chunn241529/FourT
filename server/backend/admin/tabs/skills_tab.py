"""
Skills Config Tab for Admin UI
"""

import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

from backend.admin.tabs.base_tab import BaseTab


class SkillsTab(BaseTab):
    """Skills Config tab - manage weapons and skills"""
    
    def setup(self):
        """Setup Skill Config tab UI"""
        COLORS = self.COLORS
        FONTS = self.FONTS
        ModernButton = self.ModernButton
        
        # Skills file path
        self.skills_file = self.backend_dir / "data" / "skills.json"
        self.selected_skill = None
        self.selected_weapon = None
        self.selected_weapon_idx = None
        self.skills_data = {"weapons": [], "skills": []}
        self.weapon_image_cache = {}
        self.weapon_item_rects = []
        self.weapon_hovered_idx = -1
        self.weapon_drag_data = {"idx": None, "start_y": 0, "dragging": False}
        
        # Preview photo references
        self.preview_photo_menu = None
        self.preview_photo_timeline = None
        
        # Main container - split into left (list) and right (preview/edit) using PanedWindow
        main_container = tk.PanedWindow(self.parent, orient=tk.HORIZONTAL, bg=COLORS['bg'], 
                                         sashwidth=6, sashrelief=tk.RAISED)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Skill list (resizable with PanedWindow)
        left_panel = tk.Frame(main_container, bg=COLORS['card'])
        main_container.add(left_panel, minsize=280, width=350)
        
        # === WEAPONS Section ===
        weapons_section = tk.Frame(left_panel, bg=COLORS['card'])
        weapons_section.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        weapons_header = tk.Frame(weapons_section, bg=COLORS['card'])
        weapons_header.pack(fill=tk.X)
        
        tk.Label(weapons_header, text="🗡️ Vũ khí", font=FONTS['bold'], 
                bg=COLORS['card'], fg=COLORS['fg']).pack(side=tk.LEFT)
        
        ModernButton(weapons_header, text="➕", command=self._add_weapon, 
                    kind='success', width=3).pack(side=tk.RIGHT, padx=2)
        ModernButton(weapons_header, text="✏️", command=self._edit_weapon, 
                    kind='primary', width=3).pack(side=tk.RIGHT, padx=2)
        ModernButton(weapons_header, text="❌", command=self._delete_weapon, 
                    kind='danger', width=3).pack(side=tk.RIGHT, padx=2)
        
        # Weapons Canvas (draggable list with hover effects)
        weapons_list_frame = tk.Frame(weapons_section, bg=COLORS['input_bg'])
        weapons_list_frame.pack(fill=tk.X, pady=5)
        
        self.weapons_canvas = tk.Canvas(
            weapons_list_frame, 
            height=120,
            bg=COLORS['input_bg'],
            highlightthickness=0
        )
        self.weapons_canvas.pack(fill=tk.X)
        
        # Bind weapon canvas events
        self.weapons_canvas.bind("<Button-1>", self._on_weapon_click)
        self.weapons_canvas.bind("<B1-Motion>", self._on_weapon_drag)
        self.weapons_canvas.bind("<ButtonRelease-1>", self._on_weapon_release)
        self.weapons_canvas.bind("<Motion>", self._on_weapon_hover)
        self.weapons_canvas.bind("<Leave>", self._on_weapon_leave)
        
        # Hidden scroll - scroll with mouse wheel
        def _on_weapon_scroll(event):
            bbox = self.weapons_canvas.bbox("all")
            if not bbox:
                return
            content_height = bbox[3] - bbox[1]
            visible_height = self.weapons_canvas.winfo_height()
            if content_height > visible_height:
                self.weapons_canvas.yview_scroll(-1 * (event.delta // 120), 'units')
        
        self.weapons_canvas.bind("<MouseWheel>", _on_weapon_scroll)
        
        # === SKILLS Section ===
        skills_section = tk.Frame(left_panel, bg=COLORS['card'])
        skills_section.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Weapon filter
        filter_frame = tk.Frame(skills_section, bg=COLORS['card'])
        filter_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(filter_frame, text="Lọc:", font=FONTS.get('small', ('Segoe UI', 9)), 
                bg=COLORS['card'], fg=COLORS['fg']).pack(side=tk.LEFT, padx=(0, 5))
        
        self.weapon_var = tk.StringVar(value="all")
        self.weapon_combo = ttk.Combobox(filter_frame, textvariable=self.weapon_var, 
                                         state='readonly', width=15)
        self.weapon_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.weapon_combo.bind('<<ComboboxSelected>>', self._on_weapon_filter_change)
        
        # Skills treeview
        tree_frame = tk.Frame(skills_section, bg=COLORS['bg'])
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        self.skills_tree = ttk.Treeview(
            tree_frame,
            columns=("name", "key", "weapon"),
            show="headings",
            yscrollcommand=vsb.set
        )
        vsb.config(command=self.skills_tree.yview)
        
        self.skills_tree.heading("name", text="Tên Skill")
        self.skills_tree.heading("key", text="Phím")
        self.skills_tree.heading("weapon", text="Vũ khí")
        
        self.skills_tree.column("name", width=130)
        self.skills_tree.column("key", width=60)
        self.skills_tree.column("weapon", width=70)
        
        self.skills_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.skills_tree.bind('<<TreeviewSelect>>', self._on_skill_select)
        
        # Skill Buttons
        btn_frame = tk.Frame(left_panel, bg=COLORS['card'])
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ModernButton(btn_frame, text="➕", command=self._add_skill, 
                    kind='success', width=3).pack(side=tk.LEFT, padx=(0, 5))
        ModernButton(btn_frame, text="❌", command=self._delete_skill, 
                    kind='danger', width=3).pack(side=tk.LEFT, padx=(0, 5))
        ModernButton(btn_frame, text="🔄", command=self._load_skills_data, 
                    kind='secondary', width=3).pack(side=tk.RIGHT)
        
        # Right panel - Edit/Preview (added to PanedWindow)
        right_panel = tk.Frame(main_container, bg=COLORS['card'])
        main_container.add(right_panel, minsize=400)
        
        tk.Label(right_panel, text="📝 Chi tiết Skill", font=FONTS['h2'], 
                bg=COLORS['card'], fg=COLORS['fg']).pack(anchor=tk.W, padx=15, pady=(15, 10))
        
        # Scrollable container for form (hidden scrollbar)
        scroll_container = tk.Frame(right_panel, bg=COLORS['card'])
        scroll_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Canvas for scrolling
        self.skill_detail_canvas = tk.Canvas(scroll_container, bg=COLORS['card'], 
                                              highlightthickness=0, bd=0)
        self.skill_detail_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Inner frame to hold all form content
        self.skill_detail_inner = tk.Frame(self.skill_detail_canvas, bg=COLORS['card'])
        self.skill_detail_window = self.skill_detail_canvas.create_window(
            (0, 0), window=self.skill_detail_inner, anchor='nw'
        )
        
        # Mouse wheel scroll (hidden scrollbar)
        def _on_skill_detail_scroll(event):
            if self.skill_detail_inner.winfo_reqheight() > self.skill_detail_canvas.winfo_height():
                self.skill_detail_canvas.yview_scroll(-1 * (event.delta // 120), 'units')
        
        self._skill_detail_scroll_handler = _on_skill_detail_scroll
        
        self.skill_detail_canvas.bind("<MouseWheel>", _on_skill_detail_scroll)
        self.skill_detail_inner.bind("<MouseWheel>", _on_skill_detail_scroll)
        
        # Update scroll region when inner frame changes size
        def _on_inner_configure(event):
            self.skill_detail_canvas.configure(scrollregion=self.skill_detail_canvas.bbox("all"))
            self._bind_scroll_to_children(self.skill_detail_inner)
        
        def _on_canvas_configure(event):
            self.skill_detail_canvas.itemconfig(self.skill_detail_window, width=event.width)
        
        self.skill_detail_inner.bind("<Configure>", _on_inner_configure)
        self.skill_detail_canvas.bind("<Configure>", _on_canvas_configure)
        
        # Form fields (now inside scrollable inner frame)
        form_frame = tk.Frame(self.skill_detail_inner, bg=COLORS['card'])
        form_frame.pack(fill=tk.X, padx=15, pady=5)
        
        # ID
        row = tk.Frame(form_frame, bg=COLORS['card'])
        row.pack(fill=tk.X, pady=5)
        tk.Label(row, text="ID:", width=10, anchor='w', font=FONTS['body'], 
                bg=COLORS['card'], fg=COLORS['fg']).pack(side=tk.LEFT)
        self.skill_id_entry = tk.Entry(row, font=FONTS['body'], bg=COLORS['input_bg'], 
                                       fg=COLORS['fg'], insertbackground=COLORS['fg'])
        self.skill_id_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Name
        row = tk.Frame(form_frame, bg=COLORS['card'])
        row.pack(fill=tk.X, pady=5)
        tk.Label(row, text="Tên:", width=10, anchor='w', font=FONTS['body'], 
                bg=COLORS['card'], fg=COLORS['fg']).pack(side=tk.LEFT)
        self.skill_name_entry = tk.Entry(row, font=FONTS['body'], bg=COLORS['input_bg'], 
                                         fg=COLORS['fg'], insertbackground=COLORS['fg'])
        self.skill_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Key
        row = tk.Frame(form_frame, bg=COLORS['card'])
        row.pack(fill=tk.X, pady=5)
        tk.Label(row, text="Phím:", width=10, anchor='w', font=FONTS['body'], 
                bg=COLORS['card'], fg=COLORS['fg']).pack(side=tk.LEFT)
        self.skill_key_entry = tk.Entry(row, font=FONTS['body'], bg=COLORS['input_bg'], 
                                        fg=COLORS['fg'], insertbackground=COLORS['fg'])
        self.skill_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(row, text="(lmb/rmb/mouse4/scroll_down...)", font=FONTS.get('small', ('Segoe UI', 9)), 
                bg=COLORS['card'], fg=COLORS.get('text_dim', COLORS['fg'])).pack(side=tk.LEFT, padx=5)
        
        # Modifiers (Alt, Ctrl, Shift)
        mod_row = tk.Frame(form_frame, bg=COLORS['card'])
        mod_row.pack(fill=tk.X, pady=5)
        tk.Label(mod_row, text="Modifiers:", width=10, anchor='w', font=FONTS['body'], 
                bg=COLORS['card'], fg=COLORS['fg']).pack(side=tk.LEFT)
        
        self.mod_alt_var = tk.BooleanVar(value=False)
        self.mod_ctrl_var = tk.BooleanVar(value=False)
        self.mod_shift_var = tk.BooleanVar(value=False)
        
        tk.Checkbutton(mod_row, text="Alt", variable=self.mod_alt_var,
                      bg=COLORS['card'], fg=COLORS['fg'], selectcolor=COLORS['input_bg'],
                      activebackground=COLORS['card'], activeforeground=COLORS['fg'],
                      font=FONTS['body']).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(mod_row, text="Ctrl", variable=self.mod_ctrl_var,
                      bg=COLORS['card'], fg=COLORS['fg'], selectcolor=COLORS['input_bg'],
                      activebackground=COLORS['card'], activeforeground=COLORS['fg'],
                      font=FONTS['body']).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(mod_row, text="Shift", variable=self.mod_shift_var,
                      bg=COLORS['card'], fg=COLORS['fg'], selectcolor=COLORS['input_bg'],
                      activebackground=COLORS['card'], activeforeground=COLORS['fg'],
                      font=FONTS['body']).pack(side=tk.LEFT, padx=5)
        
        # Hold time
        row = tk.Frame(form_frame, bg=COLORS['card'])
        row.pack(fill=tk.X, pady=5)
        tk.Label(row, text="Hold (s):", width=10, anchor='w', font=FONTS['body'], 
                bg=COLORS['card'], fg=COLORS['fg']).pack(side=tk.LEFT)
        self.skill_hold_entry = tk.Entry(row, font=FONTS['body'], bg=COLORS['input_bg'], 
                                         fg=COLORS['fg'], insertbackground=COLORS['fg'], width=10)
        self.skill_hold_entry.pack(side=tk.LEFT)
        
        tk.Label(row, text="Count:", font=FONTS['body'], 
                bg=COLORS['card'], fg=COLORS['fg']).pack(side=tk.LEFT, padx=(20, 5))
        self.skill_count_entry = tk.Entry(row, font=FONTS['body'], bg=COLORS['input_bg'], 
                                         fg=COLORS['fg'], insertbackground=COLORS['fg'], width=5)
        self.skill_count_entry.pack(side=tk.LEFT)
        
        tk.Label(row, text="CD (s):", font=FONTS['body'], 
                bg=COLORS['card'], fg=COLORS['fg']).pack(side=tk.LEFT, padx=(20, 5))
        self.skill_countdown_entry = tk.Entry(row, font=FONTS['body'], bg=COLORS['input_bg'], 
                                         fg=COLORS['fg'], insertbackground=COLORS['fg'], width=5)
        self.skill_countdown_entry.pack(side=tk.LEFT)
        
        # Weapon
        row = tk.Frame(form_frame, bg=COLORS['card'])
        row.pack(fill=tk.X, pady=5)
        tk.Label(row, text="Vũ khí:", width=10, anchor='w', font=FONTS['body'], 
                bg=COLORS['card'], fg=COLORS['fg']).pack(side=tk.LEFT)
        self.skill_weapon_var = tk.StringVar()
        self.skill_weapon_combo = ttk.Combobox(row, textvariable=self.skill_weapon_var, 
                                               state='readonly', width=15)
        self.skill_weapon_combo.pack(side=tk.LEFT)
        
        # Color
        row = tk.Frame(form_frame, bg=COLORS['card'])
        row.pack(fill=tk.X, pady=5)
        tk.Label(row, text="Màu:", width=10, anchor='w', font=FONTS['body'], 
                bg=COLORS['card'], fg=COLORS['fg']).pack(side=tk.LEFT)
        self.skill_color_entry = tk.Entry(row, font=FONTS['body'], bg=COLORS['input_bg'], 
                                          fg=COLORS['fg'], insertbackground=COLORS['fg'], width=10)
        self.skill_color_entry.pack(side=tk.LEFT)
        self.color_preview = tk.Label(row, text="  ██  ", bg=COLORS['accent'], width=5)
        self.color_preview.pack(side=tk.LEFT, padx=10)
        self.skill_color_entry.bind('<KeyRelease>', self._update_color_preview)
        
        # Image
        row = tk.Frame(form_frame, bg=COLORS['card'])
        row.pack(fill=tk.X, pady=5)
        tk.Label(row, text="Image:", width=10, anchor='w', font=FONTS['body'], 
                bg=COLORS['card'], fg=COLORS['fg']).pack(side=tk.LEFT)
        self.skill_image_entry = tk.Entry(row, font=FONTS['body'], bg=COLORS['input_bg'], 
                                          fg=COLORS['fg'], insertbackground=COLORS['fg'])
        self.skill_image_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ModernButton(row, text="📁", command=self._browse_image, 
                    kind='secondary', width=3).pack(side=tk.LEFT, padx=5)
        
        # Description
        row = tk.Frame(form_frame, bg=COLORS['card'])
        row.pack(fill=tk.BOTH, expand=True, pady=5)
        tk.Label(row, text="Mô tả:", width=10, anchor='w', font=FONTS['body'], 
                bg=COLORS['card'], fg=COLORS['fg']).pack(side=tk.TOP, anchor='w')
        tk.Label(row, text="Dùng [image: file.gif] chèn ảnh. *In đậm*, [#ff0000:Màu đỏ], [khaki:Màu Khaki]", 
                font=FONTS.get('small', ('Segoe UI', 9)), 
                bg=COLORS['card'], fg=COLORS.get('text_dim', COLORS['fg'])).pack(side=tk.TOP, anchor='w', pady=(0, 5))
        
        self.skill_desc_entry = tk.Text(row, font=FONTS['body'], bg=COLORS['input_bg'], 
                                       fg=COLORS['fg'], insertbackground=COLORS['fg'], height=4,
                                       undo=True)
        self.skill_desc_entry.pack(fill=tk.BOTH, expand=True)

        # Undo/Redo bindings
        def safe_undo(event):
            try:
                self.skill_desc_entry.edit_undo()
            except tk.TclError:
                pass
            return "break"

        def safe_redo(event):
            try:
                self.skill_desc_entry.edit_redo()
            except tk.TclError:
                pass
            return "break"

        self.skill_desc_entry.bind("<Control-z>", safe_undo)
        self.skill_desc_entry.bind("<Control-y>", safe_redo)
        
        # Preview section - Two previews side by side
        preview_frame = tk.Frame(self.skill_detail_inner, bg=COLORS['input_bg'], relief=tk.FLAT, bd=1)
        preview_frame.pack(fill=tk.X, padx=15, pady=15)
        
        tk.Label(preview_frame, text="Preview", font=FONTS['bold'], 
                bg=COLORS['input_bg'], fg=COLORS['fg']).pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        previews_container = tk.Frame(preview_frame, bg=COLORS['input_bg'], height=100)
        previews_container.pack(fill=tk.X, padx=10, pady=(0, 10))
        previews_container.pack_propagate(False)
        
        # === MENU Preview (left) ===
        menu_preview_frame = tk.Frame(previews_container, bg=COLORS['card'], relief=tk.RIDGE, bd=1)
        menu_preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        tk.Label(menu_preview_frame, text="📋 Menu Skill", font=FONTS.get('small', ('Segoe UI', 9)), 
                bg=COLORS['card'], fg=COLORS.get('fg_dim', COLORS['fg'])).pack(anchor=tk.W, padx=5, pady=5)
        
        menu_inner = tk.Frame(menu_preview_frame, bg=COLORS['bg'])
        menu_inner.pack(fill=tk.X, padx=5, pady=(0, 10))
        
        # Menu style: image + name + key
        self.menu_preview_image = tk.Label(menu_inner, text="", bg=COLORS['bg'], width=5, height=2)
        self.menu_preview_image.pack(side=tk.LEFT, padx=(5, 10))
        
        self.menu_preview_dot = tk.Label(menu_inner, text="●", font=("Arial", 12), bg=COLORS['bg'], fg=COLORS['accent'])
        self.menu_preview_dot.pack(side=tk.LEFT, padx=(0, 5))
        
        self.menu_preview_name = tk.Label(menu_inner, text="Skill Name", font=FONTS['body'], 
                                          bg=COLORS['bg'], fg=COLORS['fg'])
        self.menu_preview_name.pack(side=tk.LEFT)
        
        self.menu_preview_key = tk.Label(menu_inner, text="[KEY]", font=FONTS.get('small', ('Segoe UI', 9)), 
                                         bg=COLORS['bg'], fg=COLORS.get('fg_dim', COLORS['fg']))
        self.menu_preview_key.pack(side=tk.RIGHT, padx=5)
        
        # === TIMELINE Preview (right) ===
        timeline_preview_frame = tk.Frame(previews_container, bg=COLORS['card'], relief=tk.RIDGE, bd=1)
        timeline_preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        tk.Label(timeline_preview_frame, text="🕐 Timeline", font=FONTS.get('small', ('Segoe UI', 9)), 
                bg=COLORS['card'], fg=COLORS.get('fg_dim', COLORS['fg'])).pack(anchor=tk.W, padx=5, pady=5)
        
        timeline_inner = tk.Frame(timeline_preview_frame, bg=COLORS['bg'])
        timeline_inner.pack(fill=tk.X, padx=5, pady=(0, 10))
        
        # Timeline style: colored box with icon only
        self.timeline_preview_box = tk.Frame(timeline_inner, bg=COLORS['accent'], width=50, height=50)
        self.timeline_preview_box.pack(side=tk.LEFT, padx=10, pady=5)
        self.timeline_preview_box.pack_propagate(False)
        
        self.timeline_preview_image = tk.Label(self.timeline_preview_box, text="", bg=COLORS['accent'])
        self.timeline_preview_image.place(relx=0.5, rely=0.5, anchor='center')
        
        self.timeline_preview_key_fallback = tk.Label(self.timeline_preview_box, text="K", 
                                                      font=FONTS['h2'], bg=COLORS['accent'], fg='white')
        self.timeline_preview_key_fallback.place(relx=0.5, rely=0.5, anchor='center')
        
        # Save button
        save_frame = tk.Frame(self.skill_detail_inner, bg=COLORS['card'])
        save_frame.pack(fill=tk.X, padx=15, pady=10)
        
        ModernButton(save_frame, text="💾 Lưu Skill", command=self._save_skill, 
                    kind='primary', width=15).pack(side=tk.LEFT)
        
        # Load initial data
        self._load_skills_data()
    
    def _bind_scroll_to_children(self, widget):
        """Recursively bind mouse wheel scroll to all children widgets"""
        try:
            for child in widget.winfo_children():
                if not isinstance(child, tk.Text):
                    child.bind("<MouseWheel>", self._skill_detail_scroll_handler, add='+')
                self._bind_scroll_to_children(child)
        except:
            pass
    
    def _load_skills_data(self):
        """Load skills and weapons from JSON using SkillsService"""
        try:
            self.skills_data = self.admin.skills_service.load_data()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.skills_data = {"weapons": [], "skills": []}
        
        # Populate weapon filter
        weapons = ["all"] + self.admin.skills_service.get_weapon_ids()
        self.weapon_combo['values'] = weapons
        self.skill_weapon_combo['values'] = self.admin.skills_service.get_weapon_ids()
        
        # Refresh weapons listbox
        self._refresh_weapons_list()
        self._refresh_skills()
    
    def _refresh_weapons_list(self):
        """Refresh weapons canvas with draggable items"""
        COLORS = self.COLORS
        FONTS = self.FONTS
        
        self.weapons_canvas.delete("all")
        self.weapon_item_rects = []
        
        weapons = self.skills_data.get('weapons', [])
        row_height = 28
        y = 4
        
        for idx, weapon in enumerate(weapons):
            icon = weapon.get('icon', '')
            name = weapon.get('name', weapon['id'])
            color = weapon.get('color', '#95a5a6')
            image_path = weapon.get('image', '')
            
            # Determine if selected or hovered
            is_selected = (self.selected_weapon_idx == idx)
            is_hovered = (self.weapon_hovered_idx == idx)
            
            # Background
            if is_selected:
                bg_color = COLORS['accent']
            elif is_hovered:
                bg_color = COLORS.get('sidebar_hover', COLORS['card'])
            else:
                bg_color = COLORS['input_bg']
            
            x1, y1 = 4, y
            x2, y2 = self.weapons_canvas.winfo_width() - 4 or 320, y + row_height - 2
            
            # Draw rounded background
            self.weapons_canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=bg_color, outline=COLORS.get('border', '') if is_hovered else '',
                tags=(f"weapon_{idx}", "weapon_item")
            )
            
            # Try to load and display weapon image
            img_x = x1 + 14
            has_image = False
            
            if image_path:
                cache_key = f"{weapon['id']}_{image_path}"
                if cache_key not in self.weapon_image_cache:
                    try:
                        from PIL import Image, ImageTk
                        wwm_resources = self.backend_dir / "wwm_resources"
                        paths_to_try = [
                            wwm_resources / image_path,
                            wwm_resources / Path(image_path).name,
                            Path(image_path)
                        ]
                        for path in paths_to_try:
                            if path.exists():
                                img = Image.open(path)
                                img = img.resize((18, 18), Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
                                self.weapon_image_cache[cache_key] = ImageTk.PhotoImage(img)
                                break
                    except:
                        pass
                
                if cache_key in self.weapon_image_cache:
                    self.weapons_canvas.create_image(
                        img_x, (y1 + y2) / 2,
                        image=self.weapon_image_cache[cache_key],
                        tags=(f"weapon_{idx}", "weapon_item")
                    )
                    has_image = True
            
            if not has_image:
                # Fallback: Color box
                self.weapons_canvas.create_rectangle(
                    x1 + 6, y1 + 5, x1 + 22, y2 - 5,
                    fill=color, outline='',
                    tags=(f"weapon_{idx}", "weapon_item")
                )
            
            # Icon + Name
            display_text = f"{icon} {name}" if icon else name
            text_color = 'white' if is_selected else COLORS['fg']
            self.weapons_canvas.create_text(
                x1 + 30, (y1 + y2) / 2,
                text=display_text,
                anchor='w',
                fill=text_color,
                font=FONTS.get('small', ('Segoe UI', 9)),
                tags=(f"weapon_{idx}", "weapon_item")
            )
            
            # Drag handle indicator
            self.weapons_canvas.create_text(
                x2 - 15, (y1 + y2) / 2,
                text="⋮⋮",
                fill=COLORS.get('fg_dim', COLORS['fg']),
                font=("Arial", 9),
                tags=(f"weapon_{idx}", "weapon_item")
            )
            
            # Store rect for hit detection
            self.weapon_item_rects.append((x1, y1, x2, y2, idx))
            
            y += row_height
        
        # Update canvas scroll region
        self.weapons_canvas.configure(scrollregion=(0, 0, 320, y + 4))
    
    def _get_weapon_at_y(self, y):
        """Get weapon index at y position"""
        canvas_y = self.weapons_canvas.canvasy(y)
        for (x1, y1, x2, y2, idx) in self.weapon_item_rects:
            if y1 <= canvas_y <= y2:
                return idx
        return None
    
    def _on_weapon_click(self, event):
        """Handle weapon canvas click"""
        idx = self._get_weapon_at_y(event.y)
        if idx is not None:
            self.selected_weapon_idx = idx
            self.weapon_drag_data["idx"] = idx
            self.weapon_drag_data["start_y"] = event.y
            self.weapon_drag_data["dragging"] = False
            self._refresh_weapons_list()
    
    def _on_weapon_drag(self, event):
        """Handle weapon drag for reordering"""
        if self.weapon_drag_data["idx"] is None:
            return
        
        if abs(event.y - self.weapon_drag_data["start_y"]) > 10:
            self.weapon_drag_data["dragging"] = True
            self.weapons_canvas.config(cursor="fleur")
            
            target_idx = self._get_weapon_at_y(event.y)
            if target_idx is not None and target_idx != self.weapon_drag_data["idx"]:
                weapons = self.skills_data.get('weapons', [])
                src_idx = self.weapon_drag_data["idx"]
                
                if 0 <= src_idx < len(weapons) and 0 <= target_idx < len(weapons):
                    weapon = weapons.pop(src_idx)
                    weapons.insert(target_idx, weapon)
                    
                    self.weapon_drag_data["idx"] = target_idx
                    self.selected_weapon_idx = target_idx
                    self.weapon_drag_data["start_y"] = event.y
                    
                    self._refresh_weapons_list()
    
    def _on_weapon_release(self, event):
        """Handle weapon drag release"""
        was_dragging = self.weapon_drag_data.get("dragging", False)
        
        self.weapon_drag_data = {"idx": None, "start_y": 0, "dragging": False}
        self.weapons_canvas.config(cursor="")
        
        if was_dragging:
            self._save_skills_data()
            weapons = ["all"] + [w['id'] for w in self.skills_data.get('weapons', [])]
            self.weapon_combo['values'] = weapons
            self.skill_weapon_combo['values'] = [w['id'] for w in self.skills_data.get('weapons', [])]
    
    def _on_weapon_hover(self, event):
        """Handle weapon hover effect"""
        idx = self._get_weapon_at_y(event.y)
        if idx != self.weapon_hovered_idx:
            self.weapon_hovered_idx = idx
            if idx is not None:
                self.weapons_canvas.config(cursor="hand2")
            self._refresh_weapons_list()
    
    def _on_weapon_leave(self, event):
        """Handle mouse leave weapons canvas"""
        self.weapon_hovered_idx = -1
        self.weapons_canvas.config(cursor="")
        self._refresh_weapons_list()
    
    def _add_weapon(self):
        """Add new weapon"""
        COLORS = self.COLORS
        ModernButton = self.ModernButton
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Thêm Vũ Khí")
        dialog.geometry("400x300")
        dialog.configure(bg=COLORS['bg'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        form = tk.Frame(dialog, bg=COLORS['bg'])
        form.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(form, text="ID:", bg=COLORS['bg'], fg=COLORS['fg']).grid(row=0, column=0, sticky='w', pady=5)
        id_entry = tk.Entry(form, bg=COLORS['input_bg'], fg=COLORS['fg'])
        id_entry.grid(row=0, column=1, columnspan=2, sticky='ew', pady=5)
        
        tk.Label(form, text="Tên:", bg=COLORS['bg'], fg=COLORS['fg']).grid(row=1, column=0, sticky='w', pady=5)
        name_entry = tk.Entry(form, bg=COLORS['input_bg'], fg=COLORS['fg'])
        name_entry.grid(row=1, column=1, columnspan=2, sticky='ew', pady=5)
        
        tk.Label(form, text="Icon:", bg=COLORS['bg'], fg=COLORS['fg']).grid(row=2, column=0, sticky='w', pady=5)
        icon_entry = tk.Entry(form, bg=COLORS['input_bg'], fg=COLORS['fg'])
        icon_entry.grid(row=2, column=1, columnspan=2, sticky='ew', pady=5)
        
        tk.Label(form, text="Màu (#hex):", bg=COLORS['bg'], fg=COLORS['fg']).grid(row=3, column=0, sticky='w', pady=5)
        color_entry = tk.Entry(form, bg=COLORS['input_bg'], fg=COLORS['fg'])
        color_entry.insert(0, "#95a5a6")
        color_entry.grid(row=3, column=1, columnspan=2, sticky='ew', pady=5)
        
        tk.Label(form, text="Image:", bg=COLORS['bg'], fg=COLORS['fg']).grid(row=4, column=0, sticky='w', pady=5)
        image_entry = tk.Entry(form, bg=COLORS['input_bg'], fg=COLORS['fg'])
        image_entry.grid(row=4, column=1, sticky='ew', pady=5)
        
        def browse_image():
            filepath = filedialog.askopenfilename(
                initialdir=self.backend_dir / "wwm_resources",
                filetypes=[("Images", "*.png *.jpg *.webp")]
            )
            if filepath:
                image_entry.delete(0, tk.END)
                image_entry.insert(0, Path(filepath).name)
        
        ModernButton(form, text="📁", command=browse_image, kind='secondary', width=3).grid(row=4, column=2, padx=2)
        
        form.columnconfigure(1, weight=1)
        
        def save():
            weapon_id = id_entry.get().strip()
            name = name_entry.get().strip()
            if not weapon_id:
                messagebox.showwarning("Lỗi", "ID không được để trống")
                return
            
            new_weapon = {
                "id": weapon_id,
                "name": name or weapon_id,
                "icon": icon_entry.get().strip(),
                "color": color_entry.get().strip() or "#95a5a6",
                "image": image_entry.get().strip()
            }
            
            self.skills_data.setdefault('weapons', []).append(new_weapon)
            self._save_skills_data()
            self._load_skills_data()
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog, bg=COLORS['bg'])
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        ModernButton(btn_frame, text="Lưu", command=save, kind='primary', width=10).pack(side=tk.LEFT, padx=5)
        ModernButton(btn_frame, text="Hủy", command=dialog.destroy, kind='secondary', width=10).pack(side=tk.LEFT)
    
    def _edit_weapon(self):
        """Edit selected weapon"""
        COLORS = self.COLORS
        ModernButton = self.ModernButton
        
        if self.selected_weapon_idx is None:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn vũ khí để sửa")
            return
        
        idx = self.selected_weapon_idx
        weapon = self.skills_data.get('weapons', [])[idx]
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Sửa Vũ Khí")
        dialog.geometry("400x300")
        dialog.configure(bg=COLORS['bg'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        form = tk.Frame(dialog, bg=COLORS['bg'])
        form.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(form, text="ID:", bg=COLORS['bg'], fg=COLORS['fg']).grid(row=0, column=0, sticky='w', pady=5)
        id_entry = tk.Entry(form, bg=COLORS['input_bg'], fg=COLORS['fg'])
        id_entry.insert(0, weapon.get('id', ''))
        id_entry.config(state='disabled')
        id_entry.grid(row=0, column=1, columnspan=2, sticky='ew', pady=5)
        
        tk.Label(form, text="Tên:", bg=COLORS['bg'], fg=COLORS['fg']).grid(row=1, column=0, sticky='w', pady=5)
        name_entry = tk.Entry(form, bg=COLORS['input_bg'], fg=COLORS['fg'])
        name_entry.insert(0, weapon.get('name', ''))
        name_entry.grid(row=1, column=1, columnspan=2, sticky='ew', pady=5)
        
        tk.Label(form, text="Icon:", bg=COLORS['bg'], fg=COLORS['fg']).grid(row=2, column=0, sticky='w', pady=5)
        icon_entry = tk.Entry(form, bg=COLORS['input_bg'], fg=COLORS['fg'])
        icon_entry.insert(0, weapon.get('icon', ''))
        icon_entry.grid(row=2, column=1, columnspan=2, sticky='ew', pady=5)
        
        tk.Label(form, text="Màu (#hex):", bg=COLORS['bg'], fg=COLORS['fg']).grid(row=3, column=0, sticky='w', pady=5)
        color_entry = tk.Entry(form, bg=COLORS['input_bg'], fg=COLORS['fg'])
        color_entry.insert(0, weapon.get('color', '#95a5a6'))
        color_entry.grid(row=3, column=1, columnspan=2, sticky='ew', pady=5)
        
        tk.Label(form, text="Image:", bg=COLORS['bg'], fg=COLORS['fg']).grid(row=4, column=0, sticky='w', pady=5)
        image_entry = tk.Entry(form, bg=COLORS['input_bg'], fg=COLORS['fg'])
        image_entry.insert(0, weapon.get('image', ''))
        image_entry.grid(row=4, column=1, sticky='ew', pady=5)
        
        def browse_image():
            filepath = filedialog.askopenfilename(
                initialdir=self.backend_dir / "wwm_resources",
                filetypes=[("Images", "*.png *.jpg *.webp")]
            )
            if filepath:
                image_entry.delete(0, tk.END)
                image_entry.insert(0, Path(filepath).name)
        
        ModernButton(form, text="📁", command=browse_image, kind='secondary', width=3).grid(row=4, column=2, padx=2)
        
        form.columnconfigure(1, weight=1)
        
        def save():
            self.skills_data['weapons'][idx] = {
                "id": weapon['id'],
                "name": name_entry.get().strip() or weapon['id'],
                "icon": icon_entry.get().strip(),
                "color": color_entry.get().strip() or "#95a5a6",
                "image": image_entry.get().strip()
            }
            # Clear image cache for this weapon
            keys_to_delete = [k for k in self.weapon_image_cache if k.startswith(weapon['id'])]
            for k in keys_to_delete:
                del self.weapon_image_cache[k]
            
            self._save_skills_data()
            self._load_skills_data()
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog, bg=COLORS['bg'])
        btn_frame.pack(fill=tk.X, padx=20, pady=10)
        ModernButton(btn_frame, text="Lưu", command=save, kind='primary', width=10).pack(side=tk.LEFT, padx=5)
        ModernButton(btn_frame, text="Hủy", command=dialog.destroy, kind='secondary', width=10).pack(side=tk.LEFT)
    
    def _delete_weapon(self):
        """Delete selected weapon"""
        if self.selected_weapon_idx is None:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn vũ khí để xóa")
            return
        
        idx = self.selected_weapon_idx
        weapon = self.skills_data.get('weapons', [])[idx]
        
        # Check if any skills use this weapon
        skills_using = [s for s in self.skills_data.get('skills', []) if s.get('weapon') == weapon['id']]
        
        msg = f"Xóa vũ khí '{weapon['name']}'?"
        if skills_using:
            msg += f"\n⚠️ Có {len(skills_using)} skill đang dùng vũ khí này!"
        
        if messagebox.askyesno("Xác nhận", msg):
            del self.skills_data['weapons'][idx]
            self._save_skills_data()
            self._load_skills_data()
    
    def _save_skills_data(self):
        """Save skills data to JSON using SkillsService"""
        try:
            self.admin.skills_service.save_data()
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))
    
    def _refresh_skills(self):
        """Refresh skills list"""
        for item in self.skills_tree.get_children():
            self.skills_tree.delete(item)
        
        weapon_filter = self.weapon_var.get()
        skills = self.skills_data.get('skills', [])
        
        for skill in skills:
            if weapon_filter == "all" or skill.get('weapon') == weapon_filter:
                self.skills_tree.insert('', 'end', iid=skill['id'], values=(
                    skill.get('name', ''),
                    skill.get('key', ''),
                    skill.get('weapon', '')
                ))
    
    def _on_weapon_filter_change(self, event=None):
        """Handle weapon filter change"""
        self._refresh_skills()
    
    def _on_skill_select(self, event=None):
        """Handle skill selection"""
        selection = self.skills_tree.selection()
        if not selection:
            return
        
        skill_id = selection[0]
        skill = next((s for s in self.skills_data.get('skills', []) if s['id'] == skill_id), None)
        
        if skill:
            self.selected_skill = skill
            self._populate_skill_form(skill)
    
    def _populate_skill_form(self, skill):
        """Fill form with skill data"""
        self.skill_id_entry.delete(0, tk.END)
        self.skill_id_entry.insert(0, skill.get('id', ''))
        
        self.skill_name_entry.delete(0, tk.END)
        self.skill_name_entry.insert(0, skill.get('name', ''))
        
        self.skill_key_entry.delete(0, tk.END)
        self.skill_key_entry.insert(0, skill.get('key', ''))
        
        self.skill_hold_entry.delete(0, tk.END)
        self.skill_hold_entry.insert(0, str(skill.get('hold', 0.05)))
        
        self.skill_count_entry.delete(0, tk.END)
        self.skill_count_entry.insert(0, str(skill.get('click_count', 1)))
        
        self.skill_countdown_entry.delete(0, tk.END)
        countdown = skill.get('countdown', 0)
        self.skill_countdown_entry.insert(0, str(countdown) if countdown else "")
        
        self.skill_weapon_var.set(skill.get('weapon', 'common'))
        
        self.skill_color_entry.delete(0, tk.END)
        self.skill_color_entry.insert(0, skill.get('color', ''))
        
        self.skill_image_entry.delete(0, tk.END)
        self.skill_image_entry.insert(0, skill.get('image', ''))
        
        self.skill_desc_entry.delete("1.0", tk.END)
        self.skill_desc_entry.insert("1.0", skill.get('description', ''))
        
        # Load modifiers
        modifiers = skill.get('modifiers', [])
        self.mod_alt_var.set('alt' in modifiers)
        self.mod_ctrl_var.set('ctrl' in modifiers)
        self.mod_shift_var.set('shift' in modifiers)
        
        self._update_preview()
    
    def _update_color_preview(self, event=None):
        """Update color preview"""
        color = self.skill_color_entry.get()
        if color and (color.startswith('#') and len(color) in [4, 7]):
            try:
                self.color_preview.config(bg=color)
            except:
                pass
        self._update_preview()
    
    def _update_preview(self):
        """Update both Menu and Timeline skill previews"""
        COLORS = self.COLORS
        
        name = self.skill_name_entry.get() or "Skill Name"
        key = self.skill_key_entry.get() or "key"
        color = self.skill_color_entry.get()
        image_path = self.skill_image_entry.get()
        
        # Get weapon color if no skill color
        if not color:
            weapon_id = self.skill_weapon_var.get()
            weapon = next((w for w in self.skills_data.get('weapons', []) if w['id'] == weapon_id), None)
            if weapon:
                color = weapon.get('color', '#95a5a6')
            else:
                color = '#95a5a6'
        
        try:
            self.color_preview.config(bg=color)
        except:
            pass
        
        # Update Menu Preview
        self.menu_preview_name.config(text=name)
        self.menu_preview_key.config(text=f"[{key.upper()}]")
        self.menu_preview_dot.config(fg=color)
        
        # Update Timeline Preview
        try:
            self.timeline_preview_box.config(bg=color)
            self.timeline_preview_image.config(bg=color)
            self.timeline_preview_key_fallback.config(bg=color)
        except:
            pass
        
        # Build key display with modifiers for timeline
        modifiers = []
        if self.mod_alt_var.get():
            modifiers.append('alt')
        if self.mod_ctrl_var.get():
            modifiers.append('ctrl')
        if self.mod_shift_var.get():
            modifiers.append('shift')
        
        if modifiers:
            key_display = '+'.join(modifiers) + '+' + key
        else:
            key_display = key
        
        # Load and display images
        self._load_preview_images(image_path, color, key_display)
    
    def _load_preview_images(self, image_path, color, key_display):
        """Load and display images in both previews"""
        try:
            from PIL import Image, ImageTk
        except ImportError:
            self._show_preview_fallback(key_display)
            return
        
        if not image_path:
            self._show_preview_fallback(key_display)
            return
        
        try:
            wwm_resources = self.backend_dir / "wwm_resources"
            paths_to_try = [
                wwm_resources / image_path,
                wwm_resources / Path(image_path).name,
                Path(image_path)
            ]
            
            img = None
            for path in paths_to_try:
                if path.exists():
                    img = Image.open(path)
                    break
            
            if img:
                # Menu preview - 40x40
                img_menu = img.copy()
                img_menu = img_menu.resize((40, 40), Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
                self.preview_photo_menu = ImageTk.PhotoImage(img_menu)
                self.menu_preview_image.config(image=self.preview_photo_menu, text="", width=40, height=40)
                self.menu_preview_dot.config(text="")
                
                # Timeline preview - 40x40
                img_timeline = img.copy()
                img_timeline = img_timeline.resize((40, 40), Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
                self.preview_photo_timeline = ImageTk.PhotoImage(img_timeline)
                self.timeline_preview_image.config(image=self.preview_photo_timeline, text="")
                self.timeline_preview_key_fallback.config(text="")
            else:
                self._show_preview_fallback(key_display or "?")
                
        except Exception as e:
            self._show_preview_fallback("!")
    
    def _show_preview_fallback(self, key_text):
        """Show fallback preview when no image available"""
        try:
            self.menu_preview_image.config(image='', text="")
            self.preview_photo_menu = None
            self.menu_preview_dot.config(text="●")
            
            self.timeline_preview_image.config(image='', text="")
            self.preview_photo_timeline = None
            self.timeline_preview_key_fallback.config(text=key_text.upper() if key_text else "K")
        except:
            pass
    
    def _add_skill(self):
        """Add new skill"""
        self.selected_skill = None
        
        current_weapon = self.weapon_var.get()
        if current_weapon == "all":
            current_weapon = "common"
        
        skills = self.skills_data.get('skills', [])
        weapon_skills = [s for s in skills if s.get('weapon') == current_weapon]
        next_num = len(weapon_skills) + 1
        
        auto_id = f"{current_weapon}_skill_{next_num}"
        
        self.skill_id_entry.delete(0, tk.END)
        self.skill_id_entry.insert(0, auto_id)
        self.skill_name_entry.delete(0, tk.END)
        self.skill_key_entry.delete(0, tk.END)
        self.skill_hold_entry.delete(0, tk.END)
        self.skill_hold_entry.insert(0, "0.05")
        self.skill_count_entry.delete(0, tk.END)
        self.skill_count_entry.insert(0, "1")
        self.skill_countdown_entry.delete(0, tk.END)
        self.skill_weapon_var.set(current_weapon)
        self.skill_color_entry.delete(0, tk.END)
        self.skill_image_entry.delete(0, tk.END)
        self.skill_desc_entry.delete("1.0", tk.END)
        
        self.mod_alt_var.set(False)
        self.mod_ctrl_var.set(False)
        self.mod_shift_var.set(False)
        
        self._update_preview()
    
    def _save_skill(self):
        """Save skill to JSON"""
        skill_id = self.skill_id_entry.get().strip()
        name = self.skill_name_entry.get().strip()
        key = self.skill_key_entry.get().strip()
        
        if not skill_id or not name:
            messagebox.showwarning("Thiếu thông tin", "ID và Tên là bắt buộc")
            return
        
        try:
            hold = float(self.skill_hold_entry.get() or 0.05)
        except:
            hold = 0.05
            
        try:
            click_count = int(self.skill_count_entry.get() or 1)
            if click_count < 1: click_count = 1
        except:
            click_count = 1
        
        # Collect modifiers
        modifiers = []
        if self.mod_alt_var.get():
            modifiers.append('alt')
        if self.mod_ctrl_var.get():
            modifiers.append('ctrl')
        if self.mod_shift_var.get():
            modifiers.append('shift')
        
        new_skill = {
            "id": skill_id,
            "name": name,
            "key": key,
            "color": self.skill_color_entry.get().strip(),
            "hold": hold,
            "click_count": click_count,
            "weapon": self.skill_weapon_var.get(),
            "image": self.skill_image_entry.get().strip(),
            "description": self.skill_desc_entry.get("1.0", tk.END).strip()
        }
        
        # Add countdown if specified
        try:
            countdown = float(self.skill_countdown_entry.get() or 0)
            if countdown > 0:
                new_skill["countdown"] = countdown
        except:
            pass
        
        if modifiers:
            new_skill["modifiers"] = modifiers
        
        skills = self.skills_data.get('skills', [])
        existing_idx = next((i for i, s in enumerate(skills) if s['id'] == skill_id), None)
        
        if existing_idx is not None:
            skills[existing_idx] = new_skill
        else:
            skills.append(new_skill)
        
        self.skills_data['skills'] = skills
        
        try:
            with open(self.skills_file, 'w', encoding='utf-8') as f:
                json.dump(self.skills_data, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Thành công", f"Đã lưu skill: {name}")
            self._refresh_skills()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu: {e}")
    
    def _delete_skill(self):
        """Delete selected skill"""
        selection = self.skills_tree.selection()
        if not selection:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn skill để xóa")
            return
        
        skill_id = selection[0]
        
        if messagebox.askyesno("Xác nhận", f"Xóa skill '{skill_id}'?"):
            skills = self.skills_data.get('skills', [])
            self.skills_data['skills'] = [s for s in skills if s['id'] != skill_id]
            
            try:
                with open(self.skills_file, 'w', encoding='utf-8') as f:
                    json.dump(self.skills_data, f, indent=4, ensure_ascii=False)
                messagebox.showinfo("Thành công", "Đã xóa skill")
                self._refresh_skills()
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể xóa: {e}")
    
    def _browse_image(self):
        """Browse for image file"""
        filename = filedialog.askopenfilename(
            title="Chọn ảnh skill",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif"), ("All files", "*.*")]
        )
        if filename:
            import os
            basename = os.path.basename(filename)
            self.skill_image_entry.delete(0, tk.END)
            self.skill_image_entry.insert(0, basename)
            self._update_preview()
