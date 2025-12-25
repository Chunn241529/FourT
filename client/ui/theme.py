"""
UI Theme Configuration
"""

import tkinter as tk
from tkinter import ttk
from .animations import hex_to_rgb, rgb_to_hex

# Colors - Modern Dark Theme with Vibrant Accents (Splash Style)
COLORS = {
    # Backgrounds
    "bg": "#0d0d0d",  # Deep dark background (Splash match)
    "bg_secondary": "#141420",  # Slight purple tint
    "sidebar": "#161625",  # Sidebar background
    "sidebar_hover": "#1e1e30",  # Sidebar item hover
    "sidebar_active": "#252540",  # Sidebar item active
    "card": "#1a1a2e",  # Card background (Deep Blue/Purple - Splash match)
    "card_hover": "#222240",  # Card hover state
    "header": "#0d0d0d",  # Header background (Same as bg for seamless look)
    # Text
    "fg": "#e8e8e8",  # Primary text (brighter)
    "fg_dim": "#8888aa",  # Dimmed text (purple tint)
    "text_dim": "#6b6b8a",  # Even more dimmed
    # Accents
    "accent": "#667eea",  # Splash Blue/Purple Accent
    "accent_hover": "#768ff5",  # Lighter accent hover
    "primary": "#667eea",  # Primary is now same as accent
    "primary_hover": "#768ff5",  # Primary hover
    # Status Colors
    "success": "#00d9a0",  # Modern teal green
    "success_hover": "#00c090",  # Success hover
    "warning": "#ffc107",  # Amber warning
    "error": "#ff4757",  # Bright red error
    "danger": "#ff4757",  # Alias for error
    # UI Elements
    "border": "#1a1a2e",  # Subtle borders (Splash match)
    "input_bg": "#1e1e35",  # Input field background
    "button": "#252545",  # Button background
    "button_hover": "#303055",  # Button hover
    "secondary": "#2a2a45",  # Secondary elements
    # Gradients (for reference)
    "gradient_start": "#667eea",  # Purple
    "gradient_end": "#764ba2",  # Darker purple
}

# Fonts
FONTS = {
    "h1": ("Segoe UI", 16, "bold"),
    "h2": ("Segoe UI", 12, "bold"),
    "body": ("Segoe UI", 10),
    "small": ("Segoe UI", 9),
    "code": ("Consolas", 10),
    "bold": ("Segoe UI", 10, "bold"),
}


def apply_theme(root):
    """Apply theme to ttk styles"""
    style = ttk.Style(root)
    style.theme_use("clam")

    # Configure generic TFrame
    style.configure("TFrame", background=COLORS["bg"])

    # Configure TLabel
    style.configure(
        "TLabel", background=COLORS["bg"], foreground=COLORS["fg"], font=FONTS["body"]
    )

    # Configure TButton
    style.configure(
        "TButton",
        background=COLORS["input_bg"],
        foreground=COLORS["fg"],
        borderwidth=0,
        focuscolor=COLORS["accent"],
        font=FONTS["body"],
        padding=5,
    )
    style.map(
        "TButton",
        background=[("active", COLORS["accent"]), ("disabled", COLORS["sidebar"])],
        foreground=[("active", "white"), ("disabled", "#666666")],
    )

    # Configure Accent Button
    style.configure(
        "Accent.TButton",
        background=COLORS["accent"],
        foreground="white",
        font=("Segoe UI", 10, "bold"),
    )
    style.map("Accent.TButton", background=[("active", COLORS["accent_hover"])])

    # Configure Treeview
    style.configure(
        "Treeview",
        background=COLORS["input_bg"],
        foreground=COLORS["fg"],
        fieldbackground=COLORS["input_bg"],
        borderwidth=0,
        rowheight=28,
        font=FONTS["body"],
    )
    style.configure(
        "Treeview.Heading",
        background=COLORS["header"],
        foreground=COLORS["fg"],
        relief="flat",
        font=FONTS["h2"],
    )
    style.map(
        "Treeview",
        background=[("selected", COLORS["accent"])],
        foreground=[("selected", "white")],
    )

    # Configure TEntry
    style.configure(
        "TEntry",
        fieldbackground=COLORS["input_bg"],
        foreground=COLORS["fg"],
        insertcolor=COLORS["fg"],
        borderwidth=1,
        relief="flat",
    )

    # Configure TCombobox
    style.configure(
        "TCombobox",
        fieldbackground=COLORS["input_bg"],
        background=COLORS["input_bg"],
        foreground=COLORS["fg"],
        arrowcolor=COLORS["fg"],
        borderwidth=1,
        relief="flat",
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", COLORS["input_bg"])],
        selectbackground=[("readonly", COLORS["accent"])],
        selectforeground=[("readonly", "white")],
    )

    # Scrollbar
    style.configure(
        "Vertical.TScrollbar",
        background=COLORS["sidebar"],
        troughcolor=COLORS["bg"],
        bordercolor=COLORS["bg"],
        arrowcolor=COLORS["fg"],
    )


class ModernButton(tk.Button):
    """Custom Tkinter Button with modern styling and hover effects"""

    def __init__(self, parent, text, command=None, kind="secondary", **kwargs):
        self.kind = kind
        self._animation_id = None

        # Determine colors based on kind
        if kind == "primary":
            bg = COLORS["primary"]
            fg = "white"
            hover_bg = COLORS["primary_hover"]
        elif kind == "accent":
            bg = COLORS["accent"]
            fg = "white"
            hover_bg = COLORS["accent_hover"]
        elif kind == "danger":
            bg = COLORS["danger"]
            fg = "white"
            hover_bg = "#cc3344"
        elif kind == "success":
            bg = COLORS["success"]
            fg = "#0d0d0d"
            hover_bg = COLORS["success_hover"]
        else:  # secondary
            bg = COLORS["button"]
            fg = COLORS["fg"]
            hover_bg = COLORS["button_hover"]

        # Extract font from kwargs or use default
        font = kwargs.pop("font", FONTS["body"])

        # Allow overriding colors via kwargs
        if "bg" in kwargs:
            bg = kwargs.pop("bg")
        if "fg" in kwargs:
            fg = kwargs.pop("fg")

        super().__init__(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            relief="flat",
            bd=0,
            activebackground=hover_bg,
            activeforeground=fg,
            cursor="hand2",
            font=font,
            **kwargs,
        )

        self.default_bg = bg
        self.hover_bg = hover_bg
        self._current_bg = bg

        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def _animate_color(self, from_color, to_color, steps=4):
        """Animate color transition (optimized: 4 steps for faster response)"""
        if self._animation_id:
            self.after_cancel(self._animation_id)

        # Use cached color utilities from animations module
        r1, g1, b1 = hex_to_rgb(from_color)
        r2, g2, b2 = hex_to_rgb(to_color)

        def step(current):
            if current >= steps:
                try:
                    self._current_bg = to_color
                    super(ModernButton, self).configure(bg=to_color)
                except tk.TclError:
                    pass
                return

            t = current / steps
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)
            color = rgb_to_hex(r, g, b)

            try:
                self._current_bg = color
                super(ModernButton, self).configure(bg=color)
                self._animation_id = self.after(16, lambda: step(current + 1))
            except tk.TclError:
                pass

        step(0)

    def on_enter(self, e):
        if self["state"] != "disabled":
            self._animate_color(self._current_bg, self.hover_bg)

    def on_leave(self, e):
        if self["state"] != "disabled":
            self._animate_color(self._current_bg, self.default_bg)

    def configure(self, cnf=None, **kwargs):
        """Override configure to handle custom 'kind' option"""
        if cnf is None:
            cnf = {}

        # Merge kwargs into cnf
        cnf.update(kwargs)

        # Handle 'kind' option
        if "kind" in cnf:
            self.kind = cnf.pop("kind")

            # Update colors based on new kind
            if self.kind == "primary":
                bg = COLORS["accent"]
                fg = "white"
                hover_bg = COLORS["accent_hover"]
            elif self.kind == "accent":
                bg = COLORS["accent"]
                fg = "white"
                hover_bg = COLORS["accent_hover"]
            elif self.kind == "danger":
                bg = COLORS["error"]
                fg = "white"
                hover_bg = "#d65d45"
            elif self.kind == "success":
                bg = COLORS["success"]
                fg = "black"
                hover_bg = "#3db89f"
            else:  # secondary
                bg = COLORS["input_bg"]
                fg = COLORS["fg"]
                hover_bg = COLORS["border"]

            self.default_bg = bg
            self.hover_bg = hover_bg
            self._current_bg = bg

            # Apply new colors
            cnf["bg"] = bg
            cnf["fg"] = fg
            cnf["activebackground"] = hover_bg
            cnf["activeforeground"] = fg

        super().configure(cnf)

    # Alias config to configure
    config = configure


class RoundedButton(tk.Canvas):
    """Modern button with true rounded corners using Canvas"""

    def __init__(
        self,
        parent,
        text,
        command=None,
        kind="secondary",
        width=100,
        height=32,
        radius=8,
        **kwargs,
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=kwargs.pop("canvas_bg", COLORS["bg"]),
            highlightthickness=0,
            **kwargs,
        )

        self.text = text
        self.command = command
        self.kind = kind
        self.btn_width = width
        self.btn_height = height
        self.radius = radius
        self._animation_id = None

        # Determine colors
        self._set_colors_for_kind(kind)

        # Draw initial state
        self._draw_button(hover=False)

        # Bindings
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _set_colors_for_kind(self, kind):
        """Set colors based on button kind"""
        if kind == "primary":
            self.bg_color = COLORS["primary"]
            self.fg_color = "white"
            self.hover_color = COLORS["primary_hover"]
        elif kind == "accent":
            self.bg_color = COLORS["accent"]
            self.fg_color = "white"
            self.hover_color = COLORS["accent_hover"]
        elif kind == "danger":
            self.bg_color = COLORS["danger"]
            self.fg_color = "white"
            self.hover_color = "#cc3344"
        elif kind == "success":
            self.bg_color = COLORS["success"]
            self.fg_color = "#0d0d0d"
            self.hover_color = COLORS["success_hover"]
        else:  # secondary
            self.bg_color = COLORS["button"]
            self.fg_color = COLORS["fg"]
            self.hover_color = COLORS["button_hover"]

        self._current_color = self.bg_color

    def _draw_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        """Draw a rounded rectangle"""
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _draw_button(self, hover=False, pressed=False):
        """Draw the button"""
        self.delete("all")

        w, h, r = self.btn_width, self.btn_height, self.radius

        # Current color
        if pressed:
            fill = self.hover_color
        elif hover:
            fill = self.hover_color
        else:
            fill = self._current_color

        # Draw rounded rectangle
        self._draw_rounded_rect(1, 1, w - 1, h - 1, r, fill=fill, outline="")

        # Subtle border
        self._draw_rounded_rect(
            1,
            1,
            w - 1,
            h - 1,
            r,
            fill="",
            outline=COLORS["border"] if not hover else fill,
        )

        # Text
        self.create_text(
            w / 2, h / 2, text=self.text, fill=self.fg_color, font=FONTS["body"]
        )

        self.config(cursor="hand2")

    def _on_enter(self, event):
        self._animate_to(self.hover_color)

    def _on_leave(self, event):
        self._animate_to(self.bg_color)

    def _on_click(self, event):
        self._draw_button(pressed=True)

    def _on_release(self, event):
        self._draw_button(hover=True)
        if self.command:
            self.command()

    def _animate_to(self, target_color, steps=4):
        """Animate color transition (optimized: 4 steps for faster response)"""
        if self._animation_id:
            self.after_cancel(self._animation_id)

        from_color = self._current_color

        # Use cached color utilities from animations module
        r1, g1, b1 = hex_to_rgb(from_color)
        r2, g2, b2 = hex_to_rgb(target_color)

        def step(current):
            if current >= steps:
                self._current_color = target_color
                self._draw_button(hover=(target_color == self.hover_color))
                return

            t = current / steps
            r = int(r1 + (r2 - r1) * t)
            g = int(g1 + (g2 - g1) * t)
            b = int(b1 + (b2 - b1) * t)

            self._current_color = rgb_to_hex(r, g, b)
            self._draw_button(hover=False)
            self._animation_id = self.after(16, lambda: step(current + 1))

        step(0)


# Alias for backward compatibility (or user preference)
colors = COLORS


class GradientCard(tk.Frame):
    """Card-style container with gradient effect and subtle shadow"""

    def __init__(self, parent, title=None, **kwargs):
        # Extract custom params
        card_bg = kwargs.pop("card_bg", COLORS["card"])

        super().__init__(parent, bg=card_bg, **kwargs)

        # Subtle border effect
        self.configure(
            relief="flat",
            bd=1,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["border"],
            highlightthickness=1,
        )

        # Add padding frame
        self.content = tk.Frame(self, bg=card_bg)
        self.content.pack(fill="both", expand=True, padx=15, pady=15)

        # Optional title
        if title:
            title_label = tk.Label(
                self.content, text=title, font=FONTS["h2"], bg=card_bg, fg=COLORS["fg"]
            )
            title_label.pack(anchor="w", pady=(0, 10))


class AnimatedProgressBar(tk.Canvas):
    """Custom progress bar with smooth animation and gradient"""

    def __init__(self, parent, width=300, height=20, **kwargs):
        super().__init__(
            parent, height=height, bg=COLORS["bg"], highlightthickness=0, **kwargs
        )

        self.bar_width = width
        self.bar_height = height
        self.progress = 0
        self._animation_id = None

        # Draw background
        self.bg_rect = self.create_rectangle(
            0,
            0,
            width,
            height,
            fill=COLORS["input_bg"],
            outline=COLORS["border"],
            width=1,
        )

        # Progress fill
        self.progress_rect = self.create_rectangle(
            0, 0, 0, height, fill=COLORS["success"], outline=""
        )

        # Percentage text
        self.text = self.create_text(
            width / 2, height / 2, text="0%", fill=COLORS["fg"], font=FONTS["small"]
        )

        # Bind to resize event for responsive width
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        """Handle resize - update bar width to match container"""
        if event.width > 10:  # Ignore tiny resize events
            self.bar_width = event.width
            # Update background rect
            self.coords(self.bg_rect, 0, 0, self.bar_width, self.bar_height)
            # Update text position
            self.coords(self.text, self.bar_width / 2, self.bar_height / 2)
            # Update progress display
            self._update_display()

    def set_progress(self, value, animate=True):
        """Set progress value (0-100)"""
        value = max(0, min(100, value))  # Clamp between 0-100

        if animate:
            self._animate_to(value)
        else:
            self.progress = value
            self._update_display()

    def _animate_to(self, target_value):
        """Animate progress to target value"""
        if self._animation_id:
            self.after_cancel(self._animation_id)

        start_value = self.progress
        steps = 20
        step_size = (target_value - start_value) / steps

        def step(current_step):
            if current_step >= steps:
                self.progress = target_value
                self._update_display()
                return

            self.progress = start_value + (step_size * current_step)
            self._update_display()
            self._animation_id = self.after(16, lambda: step(current_step + 1))

        step(0)

    def _update_display(self):
        """Update visual display"""
        # Calculate fill width
        fill_width = (self.bar_width * self.progress) / 100

        # Update rectangle
        self.coords(self.progress_rect, 0, 0, fill_width, self.bar_height)

        # Update text
        self.itemconfig(self.text, text=f"{int(self.progress)}%")

        # Gradient effect by changing color based on progress
        if self.progress < 30:
            color = COLORS["error"]
        elif self.progress < 70:
            color = COLORS["warning"]
        else:
            color = COLORS["success"]

        self.itemconfig(self.progress_rect, fill=color)


class ModernCheckbox(tk.Canvas):
    """Modern custom checkbox with animation"""

    def __init__(self, parent, text="", variable=None, command=None, **kwargs):
        self.size = kwargs.pop("size", 20)
        self.text = text
        self.variable = variable or tk.BooleanVar(value=False)
        self.command = command

        # Calculate width based on text length
        text_width = len(text) * 7 + 10
        total_width = self.size + 8 + text_width

        super().__init__(
            parent,
            width=total_width,
            height=self.size + 4,
            bg=kwargs.pop("bg", COLORS["bg"]),
            highlightthickness=0,
            **kwargs,
        )

        self._checked = self.variable.get()
        self._hover = False
        self._animation_id = None
        self._check_scale = 1.0 if self._checked else 0.0

        # Colors
        self.box_color = COLORS["input_bg"]
        self.check_color = COLORS["accent"]
        self.border_color = COLORS["border"]
        self.hover_border = COLORS["accent"]

        self._draw()

        # Bindings
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

        # Watch variable changes
        self.variable.trace_add("write", self._on_var_change)

    def _draw(self):
        """Draw the checkbox"""
        self.delete("all")

        s = self.size
        x, y = 2, 2
        r = 4  # Corner radius

        # Box background
        border = self.hover_border if self._hover else self.border_color
        fill = self.check_color if self._checked else self.box_color

        # Draw rounded rectangle for box
        points = [
            x + r,
            y,
            x + s - r,
            y,
            x + s,
            y,
            x + s,
            y + r,
            x + s,
            y + s - r,
            x + s,
            y + s,
            x + s - r,
            y + s,
            x + r,
            y + s,
            x,
            y + s,
            x,
            y + s - r,
            x,
            y + r,
            x,
            y,
        ]
        self.create_polygon(points, fill=fill, outline=border, width=2, smooth=True)

        # Draw checkmark with animation scale
        if self._check_scale > 0:
            cx, cy = x + s / 2, y + s / 2
            scale = self._check_scale

            # Checkmark path (scaled)
            check_points = [
                cx - 5 * scale,
                cy,
                cx - 2 * scale,
                cy + 4 * scale,
                cx + 5 * scale,
                cy - 4 * scale,
            ]
            self.create_line(
                check_points, fill="white", width=2, capstyle="round", joinstyle="round"
            )

        # Text label
        self.create_text(
            s + 10,
            s / 2 + 2,
            text=self.text,
            anchor="w",
            fill=COLORS["fg"],
            font=FONTS["body"],
        )

    def _on_click(self, event):
        """Toggle checkbox"""
        self._checked = not self._checked
        self.variable.set(self._checked)
        self._animate_check()
        if self.command:
            self.command()

    def _on_enter(self, event):
        self._hover = True
        self._draw()
        self.config(cursor="hand2")

    def _on_leave(self, event):
        self._hover = False
        self._draw()

    def _on_var_change(self, *args):
        """Handle variable changes from outside"""
        new_val = self.variable.get()
        if new_val != self._checked:
            self._checked = new_val
            self._animate_check()

    def _animate_check(self):
        """Animate checkmark appearance"""
        if self._animation_id:
            self.after_cancel(self._animation_id)

        target = 1.0 if self._checked else 0.0
        steps = 6
        step_size = (target - self._check_scale) / steps

        def step(current):
            if current >= steps:
                self._check_scale = target
                self._draw()
                return

            self._check_scale += step_size
            self._draw()
            self._animation_id = self.after(16, lambda: step(current + 1))

        step(0)


class ModernRadioButton(tk.Canvas):
    """Modern custom radio button with animation"""

    def __init__(
        self, parent, text="", variable=None, value=None, command=None, **kwargs
    ):
        self.size = kwargs.pop("size", 20)
        self.text = text
        self.variable = variable
        self.value = value
        self.command = command

        # Calculate width
        text_width = len(text) * 7 + 10
        total_width = self.size + 8 + text_width

        super().__init__(
            parent,
            width=total_width,
            height=self.size + 4,
            bg=kwargs.pop("bg", COLORS["bg"]),
            highlightthickness=0,
            **kwargs,
        )

        self._selected = (self.variable.get() == self.value) if self.variable else False
        self._hover = False
        self._animation_id = None
        self._dot_scale = 1.0 if self._selected else 0.0

        # Colors
        self.circle_color = COLORS["input_bg"]
        self.dot_color = COLORS["accent"]
        self.border_color = COLORS["border"]
        self.hover_border = COLORS["accent"]

        self._draw()

        # Bindings
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

        # Watch variable changes
        if self.variable:
            self.variable.trace_add("write", self._on_var_change)

    def _draw(self):
        """Draw the radio button"""
        self.delete("all")

        s = self.size
        cx, cy = s / 2 + 2, s / 2 + 2
        r = s / 2 - 1

        # Outer circle
        border = self.hover_border if self._hover else self.border_color
        fill = self.circle_color
        self.create_oval(
            cx - r, cy - r, cx + r, cy + r, fill=fill, outline=border, width=2
        )

        # Inner dot with animation scale
        if self._dot_scale > 0:
            dot_r = (r - 4) * self._dot_scale
            self.create_oval(
                cx - dot_r,
                cy - dot_r,
                cx + dot_r,
                cy + dot_r,
                fill=self.dot_color,
                outline="",
            )

        # Text label
        self.create_text(
            s + 10,
            s / 2 + 2,
            text=self.text,
            anchor="w",
            fill=COLORS["fg"],
            font=FONTS["body"],
        )

    def _on_click(self, event):
        """Select this radio button"""
        if self.variable:
            self.variable.set(self.value)
        self._selected = True
        self._animate_dot()
        if self.command:
            self.command()

    def _on_enter(self, event):
        self._hover = True
        self._draw()
        self.config(cursor="hand2")

    def _on_leave(self, event):
        self._hover = False
        self._draw()

    def _on_var_change(self, *args):
        """Handle variable changes"""
        new_selected = self.variable.get() == self.value
        if new_selected != self._selected:
            self._selected = new_selected
            self._animate_dot()

    def _animate_dot(self):
        """Animate dot appearance"""
        if self._animation_id:
            self.after_cancel(self._animation_id)

        target = 1.0 if self._selected else 0.0
        steps = 6
        step_size = (target - self._dot_scale) / steps

        def step(current):
            if current >= steps:
                self._dot_scale = target
                self._draw()
                return

            self._dot_scale += step_size
            self._draw()
            self._animation_id = self.after(16, lambda: step(current + 1))

        step(0)


class ScrollableFrame(tk.Frame):
    """Frame with hidden scrollbar that appears on hover/scroll"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=kwargs.pop("bg", COLORS["bg"]), **kwargs)

        # Create canvas and scrollbar
        self.canvas = tk.Canvas(
            self, bg=COLORS["bg"], highlightthickness=0, borderwidth=0
        )
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )

        # Inner frame for content
        self.inner_frame = tk.Frame(self.canvas, bg=COLORS["bg"])

        # Create window
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.inner_frame, anchor="nw"
        )

        # Pack canvas (scrollbar initially hidden)
        self.canvas.pack(side="left", fill="both", expand=True)

        # State
        self._scrollbar_visible = False
        self._hide_id = None

        # Bindings
        self.inner_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.inner_frame.bind("<MouseWheel>", self._on_mousewheel)

        # Bind mousewheel to all children
        self.inner_frame.bind_all("<MouseWheel>", self._on_mousewheel_global, add="+")

    def _on_frame_configure(self, event):
        """Update scroll region when inner frame changes"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """Match inner frame width to canvas"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        # Mark as initialized after first configure
        self._initialized = True

    def _on_scroll(self, *args):
        """Called when scrollbar moves - show scrollbar briefly (but not on initial setup)"""
        self.scrollbar.set(*args)
        # Skip showing scrollbar during initialization
        if not getattr(self, "_initialized", False):
            return
        self._show_scrollbar()
        self._schedule_hide()

    def _on_mousewheel(self, event):
        """Handle mouse wheel scroll"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        # Scrollbar stays hidden, only scroll works

    def _on_mousewheel_global(self, event):
        """Handle global mousewheel - only if mouse is over this frame"""
        # Check if mouse is within our widget
        try:
            x = self.winfo_pointerx() - self.winfo_rootx()
            y = self.winfo_pointery() - self.winfo_rooty()
            if 0 <= x <= self.winfo_width() and 0 <= y <= self.winfo_height():
                self._on_mousewheel(event)
        except:
            pass

    def _on_enter(self, event):
        """Mouse enter - scrollbar stays hidden"""
        pass

    def _on_leave(self, event):
        """Mouse leave - scrollbar stays hidden"""
        pass

    def _show_scrollbar(self):
        """Show the scrollbar - disabled, scrollbar always hidden"""
        pass

    def _hide_scrollbar(self):
        """Hide the scrollbar"""
        if self._scrollbar_visible:
            self._scrollbar_visible = False
            self.scrollbar.pack_forget()

    def _schedule_hide(self):
        """Schedule hiding scrollbar after delay"""
        if self._hide_id:
            self.after_cancel(self._hide_id)
        self._hide_id = self.after(1500, self._hide_scrollbar)


def set_window_icon(window):
    """
    Set the application icon for any Tk/Toplevel window.
    Works with both frozen exe and development environment.

    Args:
        window: tk.Tk or tk.Toplevel instance
    """
    try:
        import os
        import sys

        # Get icon path
        if getattr(sys, "frozen", False):
            # Running as frozen exe
            base_path = os.path.dirname(sys.executable)
        else:
            # Running as script
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        icon_path = os.path.join(base_path, "favicon.ico")

        if os.path.exists(icon_path):
            window.iconbitmap(icon_path)
        else:
            # Try alternative paths
            alt_paths = [
                os.path.join(base_path, "assets", "favicon.ico"),
                os.path.join(os.path.dirname(base_path), "favicon.ico"),
            ]
            for path in alt_paths:
                if os.path.exists(path):
                    window.iconbitmap(path)
                    break
    except Exception as e:
        # Silent fail - icon is not critical
        pass
