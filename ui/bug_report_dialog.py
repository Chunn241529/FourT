"""
Bug Report Dialog - Modern UI for reporting bugs
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import os
import threading

from .theme import colors, FONTS, ModernButton
from .components import FramelessWindow


class BugReportDialog:
    """Modern bug report dialog with title, description and file attachment"""
    
    MAX_FILE_SIZE_MB = 100
    ALLOWED_EXTENSIONS = {
        'images': ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'),
        'videos': ('.mp4', '.webm', '.mov', '.avi', '.mkv')
    }
    
    def __init__(self, parent):
        self.parent = parent
        self.attached_file = None
        self.submitting = False
        
        # Create dialog window
        self.dialog = FramelessWindow(
            parent,
            title="Báo cáo lỗi",
            icon_path=None
        )
        self.dialog.geometry("480x520")
        self.dialog.attributes('-topmost', True)
        
        # Center on screen
        self.dialog.update_idletasks()
        screen_w = self.dialog.winfo_screenwidth()
        screen_h = self.dialog.winfo_screenheight()
        x = (screen_w - 480) // 2
        y = (screen_h - 520) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Build the dialog UI"""
        content = self.dialog.content_frame
        content.configure(bg=colors['bg'])
        
        # Main container with padding
        container = tk.Frame(content, bg=colors['bg'])
        container.pack(fill='both', expand=True, padx=20, pady=15)
        
        # === Header ===
        header = tk.Frame(container, bg=colors['bg'])
        header.pack(fill='x', pady=(0, 15))
        
        tk.Label(
            header,
            text="🐞",
            font=('Segoe UI Emoji', 24),
            bg=colors['bg'],
            fg=colors['accent']
        ).pack(side='left')
        
        tk.Label(
            header,
            text="Báo cáo lỗi",
            font=FONTS['h1'],
            bg=colors['bg'],
            fg=colors['fg']
        ).pack(side='left', padx=(10, 0))
        
        # === Title input ===
        title_frame = tk.Frame(container, bg=colors['bg'])
        title_frame.pack(fill='x', pady=(0, 12))
        
        tk.Label(
            title_frame,
            text="Tiêu đề *",
            font=FONTS['body'],
            bg=colors['bg'],
            fg=colors['text_dim']
        ).pack(anchor='w', pady=(0, 5))
        
        self.title_entry = tk.Entry(
            title_frame,
            font=FONTS['body'],
            bg=colors['input_bg'],
            fg=colors['fg'],
            insertbackground=colors['fg'],
            relief='flat',
            highlightthickness=1,
            highlightbackground=colors['border'],
            highlightcolor=colors['accent']
        )
        self.title_entry.pack(fill='x', ipady=8)
        self.title_entry.insert(0, "")
        
        # === Description input ===
        desc_frame = tk.Frame(container, bg=colors['bg'])
        desc_frame.pack(fill='x', pady=(0, 12))
        
        tk.Label(
            desc_frame,
            text="Mô tả lỗi *",
            font=FONTS['body'],
            bg=colors['bg'],
            fg=colors['text_dim']
        ).pack(anchor='w', pady=(0, 5))
        
        self.desc_text = tk.Text(
            desc_frame,
            font=FONTS['body'],
            bg=colors['input_bg'],
            fg=colors['fg'],
            insertbackground=colors['fg'],
            relief='flat',
            highlightthickness=1,
            highlightbackground=colors['border'],
            highlightcolor=colors['accent'],
            height=6,
            wrap='word'
        )
        self.desc_text.pack(fill='x')
        
        # Placeholder text
        placeholder = "Mô tả chi tiết lỗi bạn gặp phải:\n- Lỗi xảy ra khi nào?\n- Các bước tái hiện lỗi?\n- Có thông báo lỗi gì không?"
        self.desc_text.insert('1.0', placeholder)
        self.desc_text.config(fg=colors['text_dim'])
        
        # Placeholder behavior
        def on_focus_in(e):
            if self.desc_text.get('1.0', 'end-1c') == placeholder:
                self.desc_text.delete('1.0', 'end')
                self.desc_text.config(fg=colors['fg'])
        
        def on_focus_out(e):
            if not self.desc_text.get('1.0', 'end-1c').strip():
                self.desc_text.insert('1.0', placeholder)
                self.desc_text.config(fg=colors['text_dim'])
        
        self.desc_text.bind('<FocusIn>', on_focus_in)
        self.desc_text.bind('<FocusOut>', on_focus_out)
        
        # === File attachment ===
        file_frame = tk.Frame(container, bg=colors['bg'])
        file_frame.pack(fill='x', pady=(0, 12))
        
        tk.Label(
            file_frame,
            text="Đính kèm hình ảnh/video (tối đa 100MB)",
            font=FONTS['body'],
            bg=colors['bg'],
            fg=colors['text_dim']
        ).pack(anchor='w', pady=(0, 5))
        
        # File selection row
        file_row = tk.Frame(file_frame, bg=colors['bg'])
        file_row.pack(fill='x')
        
        self.file_label = tk.Label(
            file_row,
            text="Chưa chọn file",
            font=FONTS['small'],
            bg=colors['input_bg'],
            fg=colors['text_dim'],
            anchor='w',
            padx=10,
            pady=8
        )
        self.file_label.pack(side='left', fill='x', expand=True)
        
        self.browse_btn = ModernButton(
            file_row,
            text="📁 Chọn file",
            command=self._browse_file,
            kind='secondary'
        )
        self.browse_btn.pack(side='right', padx=(10, 0), ipady=4)
        
        # Clear file button (hidden initially)
        self.clear_btn = ModernButton(
            file_row,
            text="✕",
            command=self._clear_file,
            kind='danger',
            width=3
        )
        # Will show when file is selected
        
        # === File info ===
        self.file_info_label = tk.Label(
            file_frame,
            text="",
            font=FONTS['small'],
            bg=colors['bg'],
            fg=colors['success']
        )
        self.file_info_label.pack(anchor='w', pady=(5, 0))
        
        # === Buttons ===
        btn_frame = tk.Frame(container, bg=colors['bg'])
        btn_frame.pack(fill='x', pady=(10, 0))
        
        # Submit button (full width)
        self.submit_btn = ModernButton(
            btn_frame,
            text="📤 Gửi báo cáo",
            command=self._submit,
            kind='success'
        )
        self.submit_btn.pack(fill='x', ipady=8)
        
        # === Status label ===
        self.status_label = tk.Label(
            container,
            text="",
            font=FONTS['small'],
            bg=colors['bg'],
            fg=colors['warning']
        )
        self.status_label.pack(fill='x', pady=(10, 0))
    
    def _browse_file(self):
        """Open file browser for image/video selection"""
        filetypes = [
            ("Hình ảnh & Video", "*.png *.jpg *.jpeg *.gif *.bmp *.webp *.mp4 *.webm *.mov *.avi *.mkv"),
            ("Hình ảnh", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
            ("Video", "*.mp4 *.webm *.mov *.avi *.mkv"),
            ("Tất cả files", "*.*")
        ]
        
        filepath = filedialog.askopenfilename(
            parent=self.dialog,
            title="Chọn hình ảnh hoặc video",
            filetypes=filetypes
        )
        
        if filepath:
            self._validate_and_set_file(filepath)
    
    def _validate_and_set_file(self, filepath):
        """Validate file size and type"""
        try:
            file_size = os.path.getsize(filepath)
            file_size_mb = file_size / (1024 * 1024)
            
            # Check size
            if file_size_mb > self.MAX_FILE_SIZE_MB:
                messagebox.showwarning(
                    "File quá lớn",
                    f"File có dung lượng {file_size_mb:.1f}MB, vượt quá giới hạn {self.MAX_FILE_SIZE_MB}MB.\n\nVui lòng chọn file nhỏ hơn.",
                    parent=self.dialog
                )
                return
            
            # Check extension
            ext = os.path.splitext(filepath)[1].lower()
            all_allowed = self.ALLOWED_EXTENSIONS['images'] + self.ALLOWED_EXTENSIONS['videos']
            
            if ext not in all_allowed:
                messagebox.showwarning(
                    "Định dạng không hỗ trợ",
                    f"Chỉ hỗ trợ các định dạng:\n• Hình ảnh: PNG, JPG, GIF, BMP, WebP\n• Video: MP4, WebM, MOV, AVI, MKV",
                    parent=self.dialog
                )
                return
            
            # Set file
            self.attached_file = filepath
            filename = os.path.basename(filepath)
            
            # Update UI
            self.file_label.config(
                text=filename,
                fg=colors['fg']
            )
            self.file_info_label.config(
                text=f"✓ {file_size_mb:.1f}MB - Đã chọn",
                fg=colors['success']
            )
            
            # Show clear button
            self.clear_btn.pack(side='right', padx=(5, 0))
            
        except Exception as e:
            messagebox.showerror(
                "Lỗi",
                f"Không thể đọc file: {e}",
                parent=self.dialog
            )
    
    def _clear_file(self):
        """Clear attached file"""
        self.attached_file = None
        self.file_label.config(
            text="Chưa chọn file",
            fg=colors['text_dim']
        )
        self.file_info_label.config(text="")
        self.clear_btn.pack_forget()
    
    def _submit(self):
        """Submit bug report"""
        if self.submitting:
            return
        
        # Validate
        title = self.title_entry.get().strip()
        desc = self.desc_text.get('1.0', 'end-1c').strip()
        
        # Check placeholder
        placeholder = "Mô tả chi tiết lỗi bạn gặp phải:"
        if desc.startswith(placeholder):
            desc = ""
        
        if not title:
            self.status_label.config(text="⚠ Vui lòng nhập tiêu đề", fg=colors['warning'])
            self.title_entry.focus_set()
            return
        
        if not desc:
            self.status_label.config(text="⚠ Vui lòng mô tả lỗi", fg=colors['warning'])
            self.desc_text.focus_set()
            return
        
        # Start submission
        self.submitting = True
        self.submit_btn.config(state='disabled', text="Đang gửi...")
        self.status_label.config(text="📤 Đang gửi báo cáo...", fg=colors['accent'])
        
        # Submit in background
        threading.Thread(
            target=self._do_submit,
            args=(title, desc, self.attached_file),
            daemon=True
        ).start()
    
    def _do_submit(self, title, desc, filepath):
        """Actually submit the bug report"""
        try:
            import requests
            from core.config import get_license_server_url
            
            url = f"{get_license_server_url()}/bug-reports"
            
            # Prepare data
            data = {
                'title': title,
                'description': desc
            }
            
            files = None
            if filepath:
                filename = os.path.basename(filepath)
                files = {'attachment': (filename, open(filepath, 'rb'))}
            
            # Send request
            response = requests.post(url, data=data, files=files, timeout=60)
            
            if files:
                files['attachment'][1].close()
            
            if response.status_code == 200:
                self._on_submit_success()
            else:
                error_msg = response.json().get('detail', 'Unknown error')
                self._on_submit_error(f"Server error: {error_msg}")
                
        except requests.exceptions.ConnectionError:
            # Fallback to email
            self._fallback_to_email(title, desc, filepath)
        except Exception as e:
            self._on_submit_error(str(e))
    
    def _fallback_to_email(self, title, desc, filepath):
        """Fallback to email when server unavailable"""
        import webbrowser
        
        email = "support@4thelper.com"
        subject = f"[Bug Report] {title}"
        body = f"{desc}"
        
        if filepath:
            body += f"\n\n[Attachment: {os.path.basename(filepath)}]\n(Vui lòng đính kèm file vào email)"
        
        mailto_url = f"mailto:{email}?subject={subject}&body={body}".replace(' ', '%20').replace('\n', '%0A')
        
        def open_email():
            webbrowser.open(mailto_url)
            self.dialog.after(100, lambda: self._on_submit_success(via_email=True))
        
        self.dialog.after(0, open_email)
    
    def _on_submit_success(self, via_email=False):
        """Handle successful submission"""
        def update():
            if via_email:
                self.status_label.config(
                    text="✓ Đã mở email client. Vui lòng gửi email.",
                    fg=colors['success']
                )
            else:
                self.status_label.config(
                    text="✓ Đã gửi báo cáo thành công! Cảm ơn bạn.",
                    fg=colors['success']
                )
            
            # Close after delay
            self.dialog.after(2000, self._close)
        
        self.dialog.after(0, update)
    
    def _on_submit_error(self, error):
        """Handle submission error"""
        def update():
            self.submitting = False
            self.submit_btn.config(state='normal', text="📤 Gửi báo cáo")
            self.status_label.config(
                text=f"❌ Lỗi: {error[:50]}...",
                fg=colors['error']
            )
        
        self.dialog.after(0, update)
    
    def _close(self):
        """Close the dialog"""
        try:
            self.dialog.destroy()
        except:
            pass


def show_bug_report_dialog(parent):
    """Show the bug report dialog"""
    BugReportDialog(parent)
