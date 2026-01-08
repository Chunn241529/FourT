"""
Payment Window - Modern Payment UI
Features: Custom title bar, animations, modern glassmorphism design
Supports: VietQR (Bank Transfer) and PayPal
"""

import tkinter as tk
from tkinter import messagebox, Canvas
import urllib.request
import io
from PIL import Image, ImageTk
import threading
import time
import math
import webbrowser

from core.config import SEPAY_ENABLED, get_license_endpoints
from .theme import ModernButton, RoundedButton, colors, FONTS, COLORS
from .components import FramelessWindow
from .animations import interpolate_color, draw_rounded_rect


class AnimatedQRFrame(Canvas):
    """QR display with loading animation and glow effect"""

    def __init__(self, parent, size=240, **kwargs):
        super().__init__(
            parent,
            width=size + 20,
            height=size + 20,
            bg=COLORS["bg"],
            highlightthickness=0,
            **kwargs,
        )

        self.size = size
        self._loading = True
        self._pulse_phase = 0
        self._animation_id = None
        self._qr_image = None

        self._draw_frame()
        self._start_loading_animation()

    def _draw_frame(self):
        """Draw QR frame with optional glow"""
        try:
            if not self.winfo_exists():
                return
            self.delete("all")
        except tk.TclError:
            return

        cx, cy = (self.size + 20) / 2, (self.size + 20) / 2

        if self._loading:
            # Animated glow during loading
            glow_intensity = 0.3 + 0.2 * math.sin(self._pulse_phase)
            glow_color = interpolate_color(
                COLORS["bg"], COLORS["accent"], glow_intensity
            )

            # Outer glow
            draw_rounded_rect(
                self,
                5,
                5,
                self.size + 15,
                self.size + 15,
                radius=16,
                fill=glow_color,
                outline="",
            )

            # Inner frame
            draw_rounded_rect(
                self,
                10,
                10,
                self.size + 10,
                self.size + 10,
                radius=12,
                fill="white",
                outline=COLORS["accent"],
            )

            # Loading text
            self.create_text(
                cx,
                cy,
                text="⏳ Loading...",
                font=("Segoe UI", 12),
                fill=COLORS["fg_dim"],
            )
        else:
            # Static frame with subtle border
            draw_rounded_rect(
                self,
                8,
                8,
                self.size + 12,
                self.size + 12,
                radius=12,
                fill="white",
                outline=COLORS["success"],
                width=2,
            )

            # QR image
            if self._qr_image:
                self.create_image(cx, cy, image=self._qr_image, anchor="center")

    def _start_loading_animation(self):
        """Run loading pulse animation"""
        if not self._loading:
            return

        self._pulse_phase += 0.08  # Slower pulse
        self._draw_frame()

        self._animation_id = self.after(
            80, self._start_loading_animation
        )  # Slower animation

    def set_qr_image(self, photo):
        """Set QR image and stop loading animation"""
        self._loading = False
        self._qr_image = photo

        if self._animation_id:
            self.after_cancel(self._animation_id)
            self._animation_id = None

        self._draw_frame()

    def set_error(self, message="Lỗi"):
        """Show error state"""
        self._loading = False

        if self._animation_id:
            self.after_cancel(self._animation_id)

        self.delete("all")

        cx, cy = (self.size + 20) / 2, (self.size + 20) / 2

        draw_rounded_rect(
            self,
            10,
            10,
            self.size + 10,
            self.size + 10,
            radius=12,
            fill=COLORS["card"],
            outline=COLORS["error"],
        )

        self.create_text(
            cx, cy, text=f"❌ {message}", font=("Segoe UI", 12), fill=COLORS["error"]
        )


class PaymentWindow:
    """
    Modern Payment Window with custom title bar and animations
    Supports VietQR and PayPal
    """

    def __init__(self, parent, feature_manager, package_info, on_success=None):
        self.feature_manager = feature_manager
        self.package_info = package_info
        self.on_success = on_success
        self.order_data = None
        self.polling = False
        self.poll_count = 0
        self.max_poll_count = 120  # 10 minutes
        self.current_method = "vietqr"  # vietqr | paypal
        self.usd_price = 0.0

        # Create frameless window
        self.window = FramelessWindow(parent, title=f"Nâng cấp {package_info['name']}")
        self.window.geometry("400x600")

        # Center on screen
        self.window.update_idletasks()
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 600) // 2
        self.window.geometry(f"+{x}+{y}")

        self._create_widgets()

        # Start with default method
        self._switch_method("vietqr")

    def _create_widgets(self):
        """Create modern UI widgets"""
        content = self.window.content_frame
        content.configure(bg=COLORS["bg"])

        # --- Header Section ---
        header_frame = tk.Frame(content, bg=COLORS["bg"])
        header_frame.pack(pady=(20, 10), fill="x")

        # Package Badge (Pill shape)
        pkg_color = self.package_info.get("color", COLORS["accent"])

        # Draw a custom canvas for the badge
        badge_canvas = Canvas(
            header_frame, width=200, height=40, bg=COLORS["bg"], highlightthickness=0
        )
        badge_canvas.pack()

        # Pill shape
        draw_rounded_rect(
            badge_canvas,
            50,
            2,
            150,
            38,
            radius=18,
            fill=COLORS["card"],
            outline=pkg_color,
            width=1,
        )

        # Text
        badge_canvas.create_text(
            100,
            20,
            text=self.package_info["name"].upper(),
            font=("Segoe UI", 12, "bold"),
            fill=pkg_color,
        )
        badge_canvas.create_text(
            80, 20, text="✨", font=("Segoe UI", 10), fill="gold"
        )  # Icon

        # --- Tab Selector (Segmented Control style) ---
        self.method_frame = tk.Frame(content, bg=COLORS["card"], padx=3, pady=3)
        self.method_frame.pack(pady=20, padx=40, fill="x")

        # We will use two frames inside a container to simulate a pill selector
        # But for Tkinter, simpler is better: A generic frame with 2 buttons

        self.btn_vietqr = self._create_tab_button("VietQR", "vietqr")
        self.btn_vietqr.pack(side="left", fill="x", expand=True, padx=1)

        self.btn_paypal = self._create_tab_button("PayPal", "paypal")
        self.btn_paypal.pack(side="right", fill="x", expand=True, padx=1)

        # --- Dynamic Content Area ---
        self.content_area = tk.Frame(content, bg=COLORS["bg"])
        self.content_area.pack(fill="both", expand=True, padx=20)

    def _create_tab_button(self, text, method):
        return tk.Button(
            self.method_frame,
            text=text,
            font=("Segoe UI", 10),
            bd=0,
            relief="flat",
            cursor="hand2",
            command=lambda: self._switch_method(method),
        )

    def _update_selector_ui(self):
        """Update selector buttons style"""
        active_bg = COLORS["accent"]
        active_fg = "white"
        inactive_bg = COLORS["bg"]
        inactive_fg = COLORS["fg_dim"]

        if self.current_method == "vietqr":
            self.btn_vietqr.config(
                bg=active_bg, fg=active_fg, font=("Segoe UI", 10, "bold")
            )
            self.btn_paypal.config(
                bg=inactive_bg, fg=inactive_fg, font=("Segoe UI", 10)
            )
        else:
            self.btn_vietqr.config(
                bg=inactive_bg, fg=inactive_fg, font=("Segoe UI", 10)
            )
            self.btn_paypal.config(
                bg=active_bg, fg=active_fg, font=("Segoe UI", 10, "bold")
            )

    def _switch_method(self, method):
        """Switch payment method"""
        self.current_method = method
        self._update_selector_ui()

        self.polling = False  # Stop any existing polling
        self.order_data = None

        # Clear content
        for widget in self.content_area.winfo_children():
            widget.destroy()

        if method == "vietqr":
            self._show_vietqr_ui()
        else:
            self._show_paypal_ui()

    # ================= VIETQR LOGIC =================

    def _show_vietqr_ui(self):
        """Show VietQR UI elements"""
        # Price
        self.price_label = tk.Label(
            self.content_area,
            text=f"{self.package_info.get('price', 0):,} đ",
            font=("Segoe UI", 24, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["fg"],
        )
        self.price_label.pack(pady=(10, 5))

        self.status_label = tk.Label(
            self.content_area,
            text="Đang tạo mã QR...",
            font=("Segoe UI", 10),
            bg=COLORS["bg"],
            fg=COLORS["fg_dim"],
        )
        self.status_label.pack()

        # QR Frame with animation
        qr_container = tk.Frame(self.content_area, bg=COLORS["bg"])
        qr_container.pack(pady=20)

        self.qr_frame = AnimatedQRFrame(qr_container, size=220)
        self.qr_frame.pack()

        # Tip
        tk.Label(
            self.content_area,
            text="Mở App Ngân hàng quét mã để thanh toán",
            font=("Segoe UI", 9),
            bg=COLORS["bg"],
            fg=COLORS["fg_dim"],
        ).pack(pady=10)

        # Start logic
        self._init_vietqr_payment()

    def _init_vietqr_payment(self):
        """Create order and load QR"""

        def task():
            self.order_data = self.feature_manager.create_payment_order(
                self.package_info["id"],
                amount=self.package_info.get("price", 0),
            )

            if not self.order_data:
                self.window.after(
                    0,
                    lambda: self.status_label.config(
                        text="Lỗi tạo đơn hàng", fg=COLORS["error"]
                    ),
                )
                return

            is_offline = self.order_data.get("created_offline", False)

            # Update status
            if is_offline:
                status_text = "⚠️ Chế độ offline (Liên hệ Admin)"
                status_color = COLORS["warning"]
            else:
                status_text = "✅ Đang chờ thanh toán..."
                status_color = COLORS["accent"]

            self.window.after(
                0, lambda: self.status_label.config(text=status_text, fg=status_color)
            )

            # Load QR Image
            try:
                qr_url = self.order_data["qr_url"]
                with urllib.request.urlopen(qr_url, timeout=10) as u:
                    raw_data = u.read()

                image = Image.open(io.BytesIO(raw_data))
                image = image.resize((220, 220), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)

                def safe_update_qr():
                    # Check if qr_frame still exists (user might have switched tabs)
                    if hasattr(self, "qr_frame") and self.qr_frame.winfo_exists():
                        self.qr_frame.set_qr_image(photo)
                        self.qr_photo = photo  # Keep reference

                self.window.after(0, safe_update_qr)

            except Exception as e:
                print(f"Error loading QR: {e}")
                self.window.after(0, lambda: self.qr_frame.set_error("Lỗi tải QR"))

            # Start polling
            if SEPAY_ENABLED and not is_offline:
                self.window.after(5000, lambda: self._start_polling("check_payment"))

        threading.Thread(target=task, daemon=True).start()

    # ================= PAYPAL LOGIC =================

    def _show_paypal_ui(self):
        """Show PayPal UI elements"""

        # --- Card Container ---
        card = tk.Frame(self.content_area, bg=COLORS["card"], padx=20, pady=20)
        card.pack(fill="x", pady=20)

        # PayPal Logo (Styled Text)
        logo_frame = tk.Frame(card, bg=COLORS["card"])
        logo_frame.pack(pady=(0, 15))

        # Pay (Dark Blue)
        tk.Label(
            logo_frame,
            text="Pay",
            font=("Segoe UI", 28, "bold italic"),
            bg=COLORS["card"],
            fg="#003087",
        ).pack(side="left")

        # Pal (Light Blue)
        tk.Label(
            logo_frame,
            text="Pal",
            font=("Segoe UI", 28, "bold italic"),
            bg=COLORS["card"],
            fg="#009cde",
        ).pack(side="left")

        # Separator
        tk.Frame(card, bg=COLORS["fg_dim"], height=1).pack(fill="x", pady=10)

        # Price Info
        row1 = tk.Frame(card, bg=COLORS["card"])
        row1.pack(fill="x", pady=2)
        tk.Label(
            row1,
            text="Gói:",
            font=("Segoe UI", 10),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
        ).pack(side="left")
        tk.Label(
            row1,
            text=self.package_info["name"],
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side="right")

        row2 = tk.Frame(card, bg=COLORS["card"])
        row2.pack(fill="x", pady=2)
        tk.Label(
            row2,
            text="Giá gốc:",
            font=("Segoe UI", 10),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
        ).pack(side="left")
        tk.Label(
            row2,
            text=f"{self.package_info.get('price', 0):,} VND",
            font=("Segoe UI", 10),
            bg=COLORS["card"],
            fg=COLORS["fg"],
        ).pack(side="right")

        # Total Price in USD
        self.usd_label = tk.Label(
            card,
            text="...",
            font=("Segoe UI", 20, "bold"),
            bg=COLORS["card"],
            fg="#003087",
        )
        self.usd_label.pack(pady=(15, 5))

        tk.Label(
            card,
            text="(Quy đổi tham khảo)",
            font=("Segoe UI", 8),
            bg=COLORS["card"],
            fg=COLORS["fg_dim"],
        ).pack()

        # --- Action Button ---
        self.paypal_btn_container = tk.Frame(self.content_area, bg=COLORS["bg"])
        self.paypal_btn_container.pack(pady=20)

        self.btn_pay = ModernButton(
            self.paypal_btn_container,
            text="Thanh toán bằng PayPal",
            command=self._init_paypal_payment,
            kind="primary",  # Will override color below
            width=30,
            height=45,
        )
        self.btn_pay.configure(bg="#FFC439", fg="black")  # PayPal Gold
        self.btn_pay.pack()

        # Status
        self.paypal_status = tk.Label(
            self.content_area,
            text="",
            font=("Segoe UI", 9),
            bg=COLORS["bg"],
            fg=COLORS["fg_dim"],
        )
        self.paypal_status.pack(pady=5)

        # Calculate USD immediately (rough estimate)
        vnd = self.package_info.get("price", 0)
        self.usd_price = round(vnd / 25000, 2)
        self.usd_label.config(text=f"${self.usd_price:.2f}")

    def _init_paypal_payment(self):
        """Create PayPal order and open browser"""
        self.paypal_status.config(text="Đang kết nối đến server...", fg=COLORS["fg"])
        self.btn_pay.config(state="disabled", text="Đang xử lý...")

        def task():
            self.order_data = self.feature_manager.create_paypal_order(
                self.package_info["id"]
            )

            # Reset button state in main thread
            self.window.after(
                0,
                lambda: self.btn_pay.config(
                    state="normal", text="Thanh toán lại (nếu lỗi)"
                ),
            )

            if not self.order_data or "approve_url" not in self.order_data:
                err = "Lỗi kết nối Server"
                if self.order_data and "detail" in self.order_data:
                    err = self.order_data["detail"]

                self.window.after(
                    0,
                    lambda: self.paypal_status.config(
                        text=f"❌ {err}", fg=COLORS["error"]
                    ),
                )
                return

            approve_url = self.order_data["approve_url"]

            # Open Browser
            webbrowser.open(approve_url)

            # Update UI to Waiting State
            def update_ui():
                # Remove button, show loader
                for widget in self.paypal_btn_container.winfo_children():
                    widget.destroy()

                # Loader
                tk.Label(
                    self.paypal_btn_container,
                    text="⏳",
                    font=("Segoe UI", 24),
                    bg=COLORS["bg"],
                ).pack()

                tk.Label(
                    self.paypal_btn_container,
                    text="Đang chờ xác nhận từ PayPal...",
                    font=("Segoe UI", 10, "bold"),
                    bg=COLORS["bg"],
                    fg=COLORS["accent"],
                ).pack(pady=5)

                self.paypal_status.config(
                    text="Vui lòng hoàn tất thanh toán trên trình duyệt web",
                    fg=COLORS["fg_dim"],
                )

                # Start polling
                self.window.after(2000, lambda: self._start_polling("check_paypal"))

            self.window.after(0, update_ui)

        threading.Thread(target=task, daemon=True).start()

    # ================= COMMON LOGIC =================

    def _start_polling(self, check_type):
        """Start auto-polling for payment"""
        if not self.order_data or self.polling:
            return

        self.polling = True
        self._poll_payment_status(check_type)

    def _poll_payment_status(self, check_type):
        """Poll for payment verification"""
        if not self.polling or not self.order_data:
            return

        # Stop if window closed
        try:
            if not self.window.winfo_exists():
                self.polling = False
                return
        except:
            self.polling = False
            return

        def check_status():
            try:
                import requests

                endpoint_key = (
                    "check_payment" if check_type == "check_payment" else "check_paypal"
                )

                # PayPal might use 'order_id' as the key from create_order response
                # VietQR might use 'order_id' (internal UUID)
                order_id = self.order_data.get("order_id")

                url = f"{get_license_endpoints()[endpoint_key]}/{order_id}"

                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()

                    if (
                        data.get("verified")
                        or data.get("payment_verified")
                        or data.get("status") == "completed"
                    ):
                        license_key = data.get("license_key")
                        if license_key:
                            self.window.after(
                                0, lambda: self._handle_payment_success(license_key)
                            )
                        return

                # Continue polling
                self.poll_count += 1
                if self.poll_count < self.max_poll_count:
                    if self.polling and self.window.winfo_exists():
                        self.window.after(
                            3000, lambda: self._poll_payment_status(check_type)
                        )
                else:
                    self.polling = False  # Timeout

            except Exception as e:
                print(f"Polling error: {e}")
                self.poll_count += 1
                if self.poll_count < self.max_poll_count:
                    if self.polling and self.window.winfo_exists():
                        self.window.after(
                            3000, lambda: self._poll_payment_status(check_type)
                        )

        threading.Thread(target=check_status, daemon=True).start()

    def _handle_payment_success(self, license_key):
        """Handle successful payment"""
        self.polling = False

        # Clear content and show success
        for widget in self.content_area.winfo_children():
            widget.destroy()

        tk.Label(
            self.content_area, text="🎉", font=("Segoe UI", 48), bg=COLORS["bg"]
        ).pack(pady=(40, 10))

        tk.Label(
            self.content_area,
            text="Thanh toán thành công!",
            font=("Segoe UI", 16, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["success"],
        ).pack()

        success = self.feature_manager.activate_license(license_key)

        if success:
            tk.Label(
                self.content_area,
                text="License đã được kích hoạt.\nVui lòng khởi động lại ứng dụng.",
                font=("Segoe UI", 10),
                bg=COLORS["bg"],
                fg=COLORS["fg_dim"],
            ).pack(pady=10)

            ModernButton(
                self.content_area,
                text="Đóng",
                command=self.window.destroy,
                kind="secondary",
            ).pack(pady=20)

            if self.on_success:
                self.on_success()
        else:
            messagebox.showerror("Lỗi", "Không thể kích hoạt license")
