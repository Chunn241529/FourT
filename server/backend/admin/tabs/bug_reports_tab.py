"""
Bug Reports Tab for Admin UI - Clean Vertical Design
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading

from backend.admin.tabs.base_tab import BaseTab


class BugReportsTab(BaseTab):
    """Bug Reports management tab - Simple vertical layout"""
    
    def setup(self):
        """Setup Bug Reports tab UI"""
        COLORS = self.COLORS
        FONTS = self.FONTS
        ModernButton = self.ModernButton
        
        # State
        self.reports = []
        self.filtered_reports = []
        self.selected_report = None
        
        # === HEADER ===
        header = tk.Frame(self.parent, bg=COLORS['bg'])
        header.pack(fill=tk.X, padx=20, pady=(20, 15))
        
        tk.Label(
            header,
            text="Bug Reports",
            font=FONTS['h1'],
            bg=COLORS['bg'],
            fg=COLORS['fg']
        ).pack(side=tk.LEFT)
        
        refresh_btn = ModernButton(
            header,
            text="Refresh",
            command=self._load_reports,
            kind='secondary'
        )
        refresh_btn.pack(side=tk.RIGHT)
        
        # === STATS ===
        stats_card = tk.Frame(self.parent, bg=COLORS['card'])
        stats_card.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        self.stats_label = tk.Label(
            stats_card,
            text="Loading...",
            font=FONTS['body'],
            bg=COLORS['card'],
            fg=COLORS['fg'],
            padx=15,
            pady=12
        )
        self.stats_label.pack(anchor='w')
        
        # === FILTER ===
        filter_frame = tk.Frame(self.parent, bg=COLORS['bg'])
        filter_frame.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        tk.Label(
            filter_frame,
            text="Filter:",
            font=FONTS['body'],
            bg=COLORS['bg'],
            fg=COLORS['text_dim']
        ).pack(side=tk.LEFT)
        
        self.filter_var = tk.StringVar(value="all")
        filters = [("All", "all"), ("New", "new"), ("In Progress", "in_progress"), ("Resolved", "resolved")]
        
        for text, value in filters:
            rb = tk.Radiobutton(
                filter_frame,
                text=text,
                variable=self.filter_var,
                value=value,
                font=FONTS['body'],
                bg=COLORS['bg'],
                fg=COLORS['fg'],
                selectcolor=COLORS['card'],
                activebackground=COLORS['bg'],
                activeforeground=COLORS['fg'],
                command=self._apply_filter
            )
            rb.pack(side=tk.LEFT, padx=(15, 0))
        
        # === REPORTS LIST ===
        list_card = tk.Frame(self.parent, bg=COLORS['card'])
        list_card.pack(fill=tk.X, padx=20, pady=(0, 15))
        
        tk.Label(
            list_card,
            text="Reports",
            font=FONTS['h2'],
            bg=COLORS['card'],
            fg=COLORS['fg']
        ).pack(anchor='w', padx=15, pady=(15, 10))
        
        # Listbox container
        list_inner = tk.Frame(list_card, bg=COLORS['input_bg'])
        list_inner.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        self.reports_listbox = tk.Listbox(
            list_inner,
            font=FONTS['body'],
            bg=COLORS['input_bg'],
            fg=COLORS['fg'],
            selectbackground=COLORS['accent'],
            selectforeground='white',
            highlightthickness=0,
            relief='flat',
            height=8,
            activestyle='none',
            cursor='hand2'
        )
        self.reports_listbox.pack(fill=tk.X, padx=2, pady=2)
        self.reports_listbox.bind('<<ListboxSelect>>', self._on_select_report)
        
        # === DETAILS SECTION ===
        detail_card = tk.Frame(self.parent, bg=COLORS['card'])
        detail_card.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # Detail header
        detail_header = tk.Frame(detail_card, bg=COLORS['card'])
        detail_header.pack(fill=tk.X, padx=15, pady=(15, 10))
        
        tk.Label(
            detail_header,
            text="Details",
            font=FONTS['h2'],
            bg=COLORS['card'],
            fg=COLORS['fg']
        ).pack(side=tk.LEFT)
        
        self.delete_btn = ModernButton(
            detail_header,
            text="Delete",
            command=self._delete_report,
            kind='danger'
        )
        self.delete_btn.pack(side=tk.RIGHT)
        
        # Detail content - with hidden scroll
        detail_container = tk.Frame(detail_card, bg=COLORS['card'])
        detail_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # Canvas for scroll (hidden scrollbar)
        self.detail_canvas = tk.Canvas(
            detail_container,
            bg=COLORS['card'],
            highlightthickness=0,
            bd=0
        )
        self.detail_canvas.pack(fill=tk.BOTH, expand=True)
        
        self.detail_inner = tk.Frame(self.detail_canvas, bg=COLORS['card'])
        self.detail_canvas_window = self.detail_canvas.create_window(
            (0, 0), window=self.detail_inner, anchor='nw'
        )
        
        self.detail_inner.bind('<Configure>', self._on_detail_configure)
        self.detail_canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Mouse wheel
        self.detail_canvas.bind('<Enter>', lambda e: self.detail_canvas.bind_all('<MouseWheel>', self._on_mousewheel))
        self.detail_canvas.bind('<Leave>', lambda e: self.detail_canvas.unbind_all('<MouseWheel>'))
        
        # === BUILD DETAIL FIELDS ===
        self._build_detail_fields()
        
        # Initial load
        self._load_reports()
    
    def _build_detail_fields(self):
        """Build detail section fields"""
        COLORS = self.COLORS
        FONTS = self.FONTS
        ModernButton = self.ModernButton
        
        inner = self.detail_inner
        
        # ID row
        id_row = tk.Frame(inner, bg=COLORS['card'])
        id_row.pack(fill=tk.X, pady=(0, 10))
        
        self.id_label = tk.Label(
            id_row,
            text="ID: -",
            font=FONTS['code'],
            bg=COLORS['card'],
            fg=COLORS['accent']
        )
        self.id_label.pack(side=tk.LEFT)
        
        self.time_label = tk.Label(
            id_row,
            text="",
            font=FONTS['small'],
            bg=COLORS['card'],
            fg=COLORS['text_dim']
        )
        self.time_label.pack(side=tk.RIGHT)
        
        # Title
        tk.Label(
            inner,
            text="Title",
            font=FONTS['small'],
            bg=COLORS['card'],
            fg=COLORS['text_dim']
        ).pack(anchor='w')
        
        self.title_label = tk.Label(
            inner,
            text="-",
            font=FONTS['h2'],
            bg=COLORS['card'],
            fg=COLORS['fg'],
            wraplength=500,
            justify='left',
            anchor='w'
        )
        self.title_label.pack(fill=tk.X, pady=(0, 10))
        
        # Status row
        status_row = tk.Frame(inner, bg=COLORS['card'])
        status_row.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            status_row,
            text="Status:",
            font=FONTS['body'],
            bg=COLORS['card'],
            fg=COLORS['text_dim']
        ).pack(side=tk.LEFT)
        
        self.status_var = tk.StringVar(value="new")
        self.status_combo = ttk.Combobox(
            status_row,
            textvariable=self.status_var,
            values=["new", "in_progress", "resolved", "closed"],
            state="readonly",
            width=12
        )
        self.status_combo.pack(side=tk.LEFT, padx=(10, 10))
        
        ModernButton(
            status_row,
            text="Update",
            command=self._update_status,
            kind='primary'
        ).pack(side=tk.LEFT)
        
        # Description
        tk.Label(
            inner,
            text="Description",
            font=FONTS['small'],
            bg=COLORS['card'],
            fg=COLORS['text_dim']
        ).pack(anchor='w', pady=(5, 0))
        
        self.desc_text = tk.Text(
            inner,
            font=FONTS['body'],
            bg=COLORS['input_bg'],
            fg=COLORS['fg'],
            height=4,
            wrap='word',
            relief='flat'
        )
        self.desc_text.pack(fill=tk.X, pady=(5, 10))
        self.desc_text.config(state='disabled')
        
        # Attachment
        attach_row = tk.Frame(inner, bg=COLORS['card'])
        attach_row.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(
            attach_row,
            text="Attachment:",
            font=FONTS['body'],
            bg=COLORS['card'],
            fg=COLORS['text_dim']
        ).pack(side=tk.LEFT)
        
        self.attach_label = tk.Label(
            attach_row,
            text="None",
            font=FONTS['body'],
            bg=COLORS['card'],
            fg=COLORS['fg']
        )
        self.attach_label.pack(side=tk.LEFT, padx=(10, 0))
        
        self.download_btn = ModernButton(
            attach_row,
            text="Download",
            command=self._download_attachment,
            kind='secondary'
        )
        
        # Notes
        tk.Label(
            inner,
            text="Admin Notes",
            font=FONTS['small'],
            bg=COLORS['card'],
            fg=COLORS['text_dim']
        ).pack(anchor='w', pady=(10, 0))
        
        self.notes_text = tk.Text(
            inner,
            font=FONTS['body'],
            bg=COLORS['input_bg'],
            fg=COLORS['fg'],
            height=3,
            wrap='word',
            relief='flat'
        )
        self.notes_text.pack(fill=tk.X, pady=(5, 10))
        
        ModernButton(
            inner,
            text="Save Notes",
            command=self._save_notes,
            kind='success'
        ).pack(anchor='w')
    
    def _on_detail_configure(self, event):
        self.detail_canvas.configure(scrollregion=self.detail_canvas.bbox('all'))
    
    def _on_canvas_configure(self, event):
        self.detail_canvas.itemconfig(self.detail_canvas_window, width=event.width)
    
    def _on_mousewheel(self, event):
        self.detail_canvas.yview_scroll(-1 * (event.delta // 120), 'units')
    
    def _load_reports(self):
        """Load bug reports from server"""
        def fetch():
            try:
                import requests
                from core.config import get_license_server_url
                
                url = f"{get_license_server_url()}/bug-reports"
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    self.reports = data.get("reports", [])
                    self.root.after(0, self._update_list)
                else:
                    self.root.after(0, lambda: self.stats_label.config(text="Failed to load"))
            except Exception as e:
                self.root.after(0, lambda: self.stats_label.config(text=f"Error: {str(e)[:30]}"))
        
        threading.Thread(target=fetch, daemon=True).start()
    
    def _update_list(self):
        """Update the reports listbox"""
        self.reports_listbox.delete(0, tk.END)
        
        filter_status = self.filter_var.get()
        self.filtered_reports = self.reports
        
        if filter_status != "all":
            self.filtered_reports = [r for r in self.reports if r.get("status") == filter_status]
        
        # Stats
        counts = {"new": 0, "in_progress": 0, "resolved": 0, "closed": 0}
        for r in self.reports:
            s = r.get("status", "new")
            if s in counts:
                counts[s] += 1
        
        self.stats_label.config(
            text=f"Total: {len(self.reports)} | New: {counts['new']} | In Progress: {counts['in_progress']} | Resolved: {counts['resolved']}"
        )
        
        # List items
        for report in self.filtered_reports:
            status = report.get("status", "new")
            icon = {"new": "[NEW]", "in_progress": "[WIP]", "resolved": "[OK]", "closed": "[X]"}.get(status, "[ ]")
            title = report.get("title", "Untitled")[:40]
            self.reports_listbox.insert(tk.END, f"{icon} {title}")
    
    def _apply_filter(self):
        """Apply status filter"""
        self._update_list()
    
    def _on_select_report(self, event):
        """Handle report selection"""
        selection = self.reports_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        if idx < len(self.filtered_reports):
            self.selected_report = self.filtered_reports[idx]
            self._show_details()
    
    def _show_details(self):
        """Show selected report details"""
        if not self.selected_report:
            return
        
        r = self.selected_report
        
        self.id_label.config(text=f"ID: {r.get('id', '-')}")
        
        created = r.get("created_at", "")[:19].replace("T", " ")
        self.time_label.config(text=created)
        
        self.title_label.config(text=r.get("title", "-"))
        self.status_var.set(r.get("status", "new"))
        
        self.desc_text.config(state='normal')
        self.desc_text.delete('1.0', tk.END)
        self.desc_text.insert('1.0', r.get("description", ""))
        self.desc_text.config(state='disabled')
        
        if r.get("attachment_filename"):
            self.attach_label.config(text=r["attachment_filename"])
            self.download_btn.pack(side=tk.LEFT, padx=(10, 0))
        else:
            self.attach_label.config(text="None")
            self.download_btn.pack_forget()
        
        self.notes_text.delete('1.0', tk.END)
        self.notes_text.insert('1.0', r.get("notes", "") or "")
    
    def _update_status(self):
        """Update report status"""
        if not self.selected_report:
            return
        
        report_id = self.selected_report.get("id")
        new_status = self.status_var.get()
        
        # Update local immediately
        self.selected_report["status"] = new_status
        for r in self.reports:
            if r.get("id") == report_id:
                r["status"] = new_status
                break
        self._update_list()
        
        # Sync to server in background (fire and forget)
        def update():
            try:
                import requests
                from core.config import get_license_server_url
                
                url = f"{get_license_server_url()}/bug-reports/{report_id}"
                requests.patch(url, json={"status": new_status}, timeout=5)
            except:
                pass
        
        threading.Thread(target=update, daemon=True).start()
    
    def _save_notes(self):
        """Save admin notes"""
        if not self.selected_report:
            return
        
        report_id = self.selected_report.get("id")
        notes = self.notes_text.get('1.0', 'end-1c')
        
        # Update local
        self.selected_report["notes"] = notes
        
        # Sync to server (fire and forget)
        def save():
            try:
                import requests
                from core.config import get_license_server_url
                
                url = f"{get_license_server_url()}/bug-reports/{report_id}"
                requests.patch(url, json={"notes": notes}, timeout=5)
            except:
                pass
        
        threading.Thread(target=save, daemon=True).start()
    
    def _download_attachment(self):
        """Download attachment"""
        if not self.selected_report:
            return
        
        report_id = self.selected_report.get("id")
        filename = self.selected_report.get("attachment_filename", "file")
        
        from tkinter import filedialog
        save_path = filedialog.asksaveasfilename(initialfile=filename)
        if not save_path:
            return
        
        def download():
            try:
                import requests
                from core.config import get_license_server_url
                
                url = f"{get_license_server_url()}/bug-reports/{report_id}/attachment"
                response = requests.get(url, timeout=60)
                
                if response.status_code == 200:
                    with open(save_path, 'wb') as f:
                        f.write(response.content)
            except:
                pass
        
        threading.Thread(target=download, daemon=True).start()
    
    def _delete_report(self):
        """Delete report"""
        if not self.selected_report:
            return
        
        if not messagebox.askyesno("Confirm", "Delete this report?"):
            return
        
        report_id = self.selected_report.get("id")
        
        def delete():
            try:
                import requests
                from core.config import get_license_server_url
                
                url = f"{get_license_server_url()}/bug-reports/{report_id}"
                response = requests.delete(url, timeout=10)
                
                if response.status_code == 200:
                    self.selected_report = None
                    self.root.after(0, self._load_reports)
            except:
                pass
        
        threading.Thread(target=delete, daemon=True).start()
