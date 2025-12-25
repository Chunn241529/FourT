"""
Payment Window - Modern VietQR Payment UI
Features: Custom title bar, animations, modern glassmorphism design
"""

import tkinter as tk
from tkinter import messagebox, Canvas
import urllib.request
import io
from PIL import Image, ImageTk
import threading
import time
import math

from core.config import SEPAY_ENABLED, get_license_endpoints
from .theme import ModernButton, colors, FONTS, COLORS
from .components import FramelessWindow
from .animations import interpolate_color, draw_rounded_rect


class AnimatedQRFrame(Canvas):
    """QR display with loading animation and glow effect"""

    def __init__(self, parent, size=280, **kwargs):
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
        self.delete("all")

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
                font=("Segoe UI", 14),
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
    """Modern Payment Window with custom title bar and animations"""

    def __init__(self, parent, feature_manager, package_info, on_success=None):
        self.feature_manager = feature_manager
        self.package_info = package_info
        self.on_success = on_success
        self.order_data = None
        self.polling = False
        self.poll_count = 0
        self.max_poll_count = 120  # 10 minutes

        # Create frameless window
        self.window = FramelessWindow(
            parent, title=f"Thanh toán - {package_info['name']}"
        )
        self.window.geometry("420x590")

        # Center on screen
        self.window.update_idletasks()
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - 420) // 2
        y = (screen_height - 480) // 2
        self.window.geometry(f"+{x}+{y}")

        self._create_widgets()
        self._init_payment()

    def _create_widgets(self):
        """Create modern UI widgets"""
        content = self.window.content_frame
        content.configure(bg=COLORS["bg"])

        # Package badge
        badge_frame = tk.Frame(content, bg=COLORS["bg"])
        badge_frame.pack(pady=(20, 10))

        pkg_color = self.package_info.get("color", COLORS["accent"])
        badge = tk.Label(
            badge_frame,
            text=f"✨ {self.package_info['name'].upper()}",
            font=("Segoe UI", 14, "bold"),
            bg=COLORS["card"],
            fg=pkg_color,
            padx=20,
            pady=8,
        )
        badge.pack()

        # Price display with animation placeholder
        self.price_frame = tk.Frame(content, bg=COLORS["bg"])
        self.price_frame.pack(pady=(5, 15))

        self.price_label = tk.Label(
            self.price_frame,
            text="Đang tạo đơn...",
            font=("Segoe UI", 24, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["fg"],
        )
        self.price_label.pack()

        self.status_label = tk.Label(
            self.price_frame,
            text="",
            font=("Segoe UI", 10),
            bg=COLORS["bg"],
            fg=COLORS["fg_dim"],
        )
        self.status_label.pack()

        # QR Frame with animation
        qr_container = tk.Frame(content, bg=COLORS["bg"])
        qr_container.pack(pady=10)

        self.qr_frame = AnimatedQRFrame(qr_container, size=260)
        self.qr_frame.pack()

        # Auto-check status (smaller, below QR)
        self.auto_check_label = tk.Label(
            content,
            text="🔄 Tự động xác nhận khi thanh toán...",
            font=("Segoe UI", 10),
            bg=COLORS["bg"],
            fg=COLORS["fg_dim"],
        )
        self.auto_check_label.pack(pady=(15, 20))

    def _animate_price(self, target_price):
        """Animate price counter"""
        current = 0
        step = max(1, target_price // 30)  # Slower steps

        def animate():
            nonlocal current
            if current < target_price:
                current = min(current + step, target_price)
                self.price_label.config(text=f"{current:,} VND")
                self.window.after(50, animate)  # Slower frame rate
            else:
                self.price_label.config(text=f"{target_price:,} VND")

        animate()

    def _init_payment(self):
        """Create order and load QR"""

        def task():
            # Pass price from package_info (fetched from server config) to ensure consistency
            self.order_data = self.feature_manager.create_payment_order(
                self.package_info["id"],
                amount=self.package_info.get(
                    "price", 0
                ),  # Use price from server config
            )

            if not self.order_data:
                self.window.after(
                    0, lambda: messagebox.showerror("Lỗi", "Không thể tạo đơn hàng")
                )
                self.window.after(0, self.window.destroy)
                return

            is_offline = self.order_data.get("created_offline", False)
            # Use price from package_info (server config) for display consistency
            amount = self.package_info.get("price", self.order_data.get("amount", 0))

            # Animate price
            self.window.after(0, lambda: self._animate_price(amount))

            # Update status
            if is_offline:
                self.window.after(
                    0,
                    lambda: self.status_label.config(
                        text="⚠️ Chế độ offline - Liên hệ admin sau khi thanh toán",
                        fg=COLORS["warning"],
                    ),
                )
            else:
                self.window.after(
                    0,
                    lambda: self.status_label.config(
                        text="🔄 Tự động xác nhận khi thanh toán thành công",
                        fg=COLORS["success"],
                    ),
                )

            # (transfer_info removed from UI - QR auto-fills all info)

            # Load QR Image
            try:
                qr_url = self.order_data["qr_url"]
                with urllib.request.urlopen(qr_url, timeout=10) as u:
                    raw_data = u.read()

                image = Image.open(io.BytesIO(raw_data))
                image = image.resize((240, 240), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)

                self.window.after(0, lambda: self.qr_frame.set_qr_image(photo))
                # Keep reference
                self.qr_photo = photo

            except Exception as e:
                print(f"Error loading QR: {e}")
                self.window.after(0, lambda: self.qr_frame.set_error("Lỗi tải QR"))

            # Start polling
            if SEPAY_ENABLED and not is_offline:
                self.window.after(
                    0,
                    lambda: self.auto_check_label.config(
                        text="🔍 Tự động kiểm tra thanh toán..."
                    ),
                )
                self.window.after(5000, self._start_polling)

        threading.Thread(target=task, daemon=True).start()

    def _manual_check_payment(self):
        """Manually check payment status"""
        if not self.order_data:
            return

        self.auto_check_label.config(text="🔍 Đang kiểm tra...", fg=COLORS["accent"])

        def check():
            try:
                import requests

                order_id = self.order_data["order_id"]
                url = f"{get_license_endpoints()['check_payment']}/{order_id}"

                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()

                    if data.get("payment_verified"):
                        license_key = data.get("license_key")
                        if license_key:
                            self.window.after(
                                0, lambda: self._handle_payment_success(license_key)
                            )
                        return
                    else:
                        self.window.after(
                            0,
                            lambda: self.auto_check_label.config(
                                text="⏳ Chưa nhận được thanh toán",
                                fg=COLORS["warning"],
                            ),
                        )
                else:
                    self.window.after(
                        0,
                        lambda: self.auto_check_label.config(
                            text="❌ Không thể kiểm tra", fg=COLORS["error"]
                        ),
                    )

            except Exception as e:
                self.window.after(
                    0,
                    lambda: self.auto_check_label.config(
                        text=f"❌ Lỗi: {e}", fg=COLORS["error"]
                    ),
                )

        threading.Thread(target=check, daemon=True).start()

    def _start_polling(self):
        """Start auto-polling for payment"""
        if not self.order_data or self.polling:
            return

        self.polling = True
        self._poll_payment_status()

    def _poll_payment_status(self):
        """Poll for payment verification"""
        if not self.polling or not self.order_data:
            return

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

                order_id = self.order_data["order_id"]
                url = f"{get_license_endpoints()['check_payment']}/{order_id}"

                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()

                    if data.get("payment_verified"):
                        license_key = data.get("license_key")
                        if license_key:
                            try:
                                self.window.after(
                                    0, lambda: self._handle_payment_success(license_key)
                                )
                            except:
                                pass
                        return

                # Continue polling
                self.poll_count += 1
                if self.poll_count < self.max_poll_count:
                    try:
                        if not self.window.winfo_exists():
                            self.polling = False
                            return
                        self.window.after(5000, self._poll_payment_status)

                        # Update status - check widget exists
                        def update_label():
                            try:
                                if (
                                    self.window.winfo_exists()
                                    and self.auto_check_label.winfo_exists()
                                ):
                                    self.auto_check_label.config(
                                        text=f"🔍 Đang chờ thanh toán... ({self.poll_count})",
                                        fg=COLORS["fg_dim"],
                                    )
                            except:
                                pass

                        self.window.after(0, update_label)
                    except:
                        self.polling = False
                else:
                    self.polling = False

            except:
                self.poll_count += 1
                if self.poll_count < self.max_poll_count:
                    try:
                        if self.window.winfo_exists():
                            self.window.after(5000, self._poll_payment_status)
                        else:
                            self.polling = False
                    except:
                        self.polling = False

        threading.Thread(target=check_status, daemon=True).start()

    def _handle_payment_success(self, license_key):
        """Handle successful payment"""
        self.polling = False

        self.auto_check_label.config(
            text="✅ Thanh toán thành công!", fg=COLORS["success"]
        )

        success = self.feature_manager.activate_license(license_key)

        if success:
            messagebox.showinfo(
                "Thành công",
                "🎉 Thanh toán đã được xác nhận!\nLicense đã được kích hoạt.",
            )
            self.window.destroy()

            if self.on_success:
                self.on_success()
        else:
            messagebox.showerror("Lỗi", "Không thể kích hoạt license")
