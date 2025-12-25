"""
OCR Setup Window
Window to help users select and install OCR engines for Quest Video Helper
Supports: Windows OCR (built-in), Tesseract (portable download)
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from services.ocr_addon_manager import OCRAddonManager
from .theme import colors, FONTS, ModernButton
from .components import FramelessWindow

class OCRSetupWindow:
    """
    Window to manage OCR engine selection and installation
    """
    
    def __init__(self, parent: tk.Tk, on_ready: Optional[Callable[[], None]] = None,
                 selected_engine: str = None):
        """
        Initialize OCR setup window
        
        Args:
            parent: Parent Tk window
            on_ready: Callback when OCR is ready to use
            selected_engine: Pre-selected engine ID
        """
        self.parent = parent
        self.on_ready = on_ready
        self.ocr_manager = OCRAddonManager()
        self.selected_engine = selected_engine
        
        # Use FramelessWindow with custom title bar
        import os
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "favicon.ico")
        if not os.path.exists(icon_path):
            icon_path = None
        
        self.root = FramelessWindow(
            parent,
            title="OCR Engine Setup",
            icon_path=icon_path
        )
        self.root.geometry("450x420")
        
        self._is_installing = False
        self._setup_ui()
        
        # Override close to handle install check
        self.root._original_close = self.root.close
        self.root.close = self._on_close
    
    def _setup_ui(self) -> None:
        """Setup UI elements with modern styling and hidden scroll"""
        # Main container with hidden scroll - use FramelessWindow's content_frame
        container = self.root.content_frame
        
        # Canvas for scrolling (hidden scrollbar)
        self.canvas = tk.Canvas(container, bg=colors['bg'], highlightthickness=0)
        self.scrollable_frame = tk.Frame(self.canvas, bg=colors['bg'])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.pack(fill="both", expand=True)
        
        # Auto-resize scroll window
        def on_canvas_resize(event):
            self.canvas.itemconfig(window_id, width=event.width)
        self.canvas.bind("<Configure>", on_canvas_resize)
        
        # Mouse wheel scroll
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", _on_mousewheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))
        
        content = self.scrollable_frame
        
        # Header
        header_frame = tk.Frame(content, bg=colors['bg'])
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        tk.Label(
            header_frame,
            text="🔧 Chọn OCR Engine",
            font=FONTS['h1'],
            bg=colors['bg'],
            fg=colors['accent']
        ).pack(side="left")
        
        # Description
        desc_frame = tk.Frame(content, bg=colors['bg'])
        desc_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        tk.Label(
            desc_frame,
            text="Chọn engine OCR để đọc text từ màn hình.",
            font=FONTS['body'],
            bg=colors['bg'],
            fg=colors['fg_dim'],
            justify="left"
        ).pack(anchor="w")
        
        # Engine options
        self.engine_var = tk.StringVar(value=self.selected_engine or "windows")
        
        engines_frame = tk.Frame(content, bg=colors['bg'])
        engines_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        for engine_id in self.ocr_manager.get_available_engines():
            info = self.ocr_manager.get_engine_info(engine_id)
            self._create_engine_option(engines_frame, engine_id, info)
        
        # Progress section
        self.progress_frame = tk.Frame(content, bg=colors['bg'])
        self.progress_frame.pack(fill="x", padx=20, pady=10)
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(fill="x")
        self.progress_bar.pack_forget()  # Hide initially
        
        self.progress_label = tk.Label(
            self.progress_frame,
            text="",
            font=FONTS['small'],
            bg=colors['bg'],
            fg=colors['fg_dim']
        )
        self.progress_label.pack(anchor="w")
        self.progress_label.pack_forget()  # Hide initially
        
        # Buttons - modern styled
        btn_frame = tk.Frame(content, bg=colors['bg'])
        btn_frame.pack(fill="x", padx=20, pady=(10, 20))
        
        # Install button
        self.install_btn = tk.Label(
            btn_frame,
            text="📥  Cài đặt Engine",
            font=("Segoe UI", 10, "bold"),
            bg=colors['accent'],
            fg="white",
            cursor="hand2",
            padx=15,
            pady=8
        )
        self.install_btn.pack(side="left")
        self.install_btn.bind("<Button-1>", lambda e: self._install() if self.install_btn['state'] != 'disabled' else None)
        self.install_btn.bind("<Enter>", lambda e: self.install_btn.config(bg="#5a9cf8") if self.install_btn.cget('cursor') == 'hand2' else None)
        self.install_btn.bind("<Leave>", lambda e: self.install_btn.config(bg=colors['accent']) if self.install_btn.cget('cursor') == 'hand2' else None)
        
        # Continue button
        self.continue_btn = tk.Label(
            btn_frame,
            text="✓  Tiếp tục",
            font=("Segoe UI", 10, "bold"),
            bg=colors['success'],
            fg="white",
            cursor="hand2",
            padx=15,
            pady=8
        )
        self.continue_btn.pack(side="left", padx=(10, 0))
        self.continue_btn.bind("<Button-1>", lambda e: self._continue() if self.continue_btn.cget('cursor') == 'hand2' else None)
        self.continue_btn.bind("<Enter>", lambda e: self.continue_btn.config(bg="#27ae60") if self.continue_btn.cget('cursor') == 'hand2' else None)
        self.continue_btn.bind("<Leave>", lambda e: self.continue_btn.config(bg=colors['success']) if self.continue_btn.cget('cursor') == 'hand2' else None)
        
        # Update button states
        self._update_buttons()
    
    def _create_engine_option(self, parent: tk.Frame, engine_id: str, info: dict) -> None:
        """Create a radio button option for an engine"""
        frame = tk.Frame(parent, bg=colors['card'], padx=15, pady=10)
        frame.pack(fill="x", pady=5)
        
        # Radio button
        rb = tk.Radiobutton(
            frame,
            text=info.get('name', engine_id),
            variable=self.engine_var,
            value=engine_id,
            font=FONTS['bold'],
            bg=colors['card'],
            fg=colors['fg'],
            selectcolor=colors['input_bg'],
            activebackground=colors['card'],
            activeforeground=colors['fg'],
            command=self._update_buttons
        )
        rb.pack(anchor="w")
        
        # Description
        desc_text = info.get('description', '')
        size_text = info.get('size', '')
        status_text = "✓ Sẵn sàng" if info.get('is_ready') else "⚠ Cần cài đặt"
        status_color = colors['success'] if info.get('is_ready') else colors['warning']
        
        info_text = f"{desc_text}\nDung lượng: {size_text}"
        
        tk.Label(
            frame,
            text=info_text,
            font=FONTS['small'],
            bg=colors['card'],
            fg=colors['text_dim'],
            justify="left"
        ).pack(anchor="w", padx=(20, 0))
        
        tk.Label(
            frame,
            text=status_text,
            font=FONTS['small'],
            bg=colors['card'],
            fg=status_color
        ).pack(anchor="w", padx=(20, 0))
    
    def _update_buttons(self) -> None:
        """Update button states based on selected engine"""
        engine_id = self.engine_var.get()
        is_ready = self.ocr_manager.is_engine_ready(engine_id)
        
        if is_ready:
            # Disable install button
            self.install_btn.config(
                text="✓  Đã cài đặt",
                bg=colors['card'],
                fg=colors['fg_dim'],
                cursor=""
            )
            # Enable continue button
            self.continue_btn.config(
                bg=colors['success'],
                cursor="hand2"
            )
        else:
            info = self.ocr_manager.ENGINES.get(engine_id, {})
            if info.get('requires_download'):
                self.install_btn.config(text="📥  Tải và cài đặt")
            else:
                self.install_btn.config(text="📥  Kích hoạt")
            # Enable install button
            self.install_btn.config(
                bg=colors['accent'],
                fg="white",
                cursor="hand2"
            )
            # Disable continue button
            self.continue_btn.config(
                bg=colors['card'],
                fg=colors['fg_dim'],
                cursor=""
            )
    
    def _install(self) -> None:
        """Install selected engine"""
        if self._is_installing:
            return
        
        # Check if button is disabled (no cursor)
        if self.install_btn.cget('cursor') == '':
            return
        
        engine_id = self.engine_var.get()
        
        self._is_installing = True
        # Disable install button visually
        self.install_btn.config(bg=colors['card'], fg=colors['fg_dim'], cursor="")
        
        # Show progress
        self.progress_bar.pack(fill="x")
        self.progress_label.pack(anchor="w", pady=(5, 0))
        self.progress_bar['value'] = 0
        
        def on_progress(status: str, percent: int):
            try:
                self.progress_label.config(text=status)
                self.progress_bar['value'] = percent
                self.root.update_idletasks()
            except tk.TclError:
                pass
        
        def on_complete(success: bool):
            self._is_installing = False
            
            try:
                if success:
                    self.progress_label.config(text="Hoàn tất!")
                    self._update_buttons()
                    # Refresh UI
                    self._refresh_engine_status()
                else:
                    self.progress_label.config(text="Cài đặt thất bại")
                    # Re-enable install button
                    self.install_btn.config(bg=colors['accent'], fg="white", cursor="hand2")
            except tk.TclError:
                pass
        
        self.ocr_manager.install_engine_async(engine_id, on_progress, on_complete)
    
    def _refresh_engine_status(self) -> None:
        """Refresh the engine status display"""
        # Simply update button states
        self._update_buttons()
    
    def _continue(self) -> None:
        """Continue with selected engine"""
        self.selected_engine = self.engine_var.get()
        self.root.destroy()
        
        if self.on_ready:
            self.on_ready()
    
    def _on_close(self) -> None:
        """Handle window close"""
        if self._is_installing:
            import tkinter.messagebox as messagebox
            if not messagebox.askyesno(
                "Đang cài đặt",
                "Đang cài đặt OCR Engine. Bạn có chắc muốn hủy?"
            ):
                return
        
        # Use FramelessWindow's original close
        if hasattr(self.root, '_original_close'):
            self.root._original_close()
        else:
            self.root.destroy()
    
    def get_selected_engine(self) -> Optional[str]:
        """Get the selected engine ID"""
        return self.selected_engine
