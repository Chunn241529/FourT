"""
Modern Menu Component with Rounded Corners and Animations
"""
import tkinter as tk
from .theme import colors, FONTS
from .animations import FadeEffect, SlideEffect, draw_rounded_rect, interpolate_color


class ModernMenu(tk.Toplevel):
    """Custom modern popup menu with rounded corners and animations"""
    
    CORNER_RADIUS = 12
    ITEM_HEIGHT = 44
    MENU_PADDING = 8
    HEADER_HEIGHT = 28  # Height for header icons row
    
    def __init__(self, parent, x, y, items, on_close=None, animate=True, on_bug_report=None):
        super().__init__(parent)
        self.items = items
        self.on_close_callback = on_close
        self.on_bug_report = on_bug_report
        self.animate = animate
        self.item_widgets = []
        self.hovered_index = -1
        
        # Window setup - transparent background for rounded effect
        self.overrideredirect(True)
        self.attributes('-topmost', True)
        self.configure(bg='black')
        self.attributes('-transparentcolor', 'black')
        
        # Calculate menu dimensions
        self.menu_width = 240
        self.menu_height = self._calculate_height()
        
        # Target position
        self.target_x = x
        self.target_y = y
        
        # Create canvas for rounded rectangle
        self.canvas = tk.Canvas(
            self,
            width=self.menu_width + 10,
            height=self.menu_height + 10,
            bg='black',
            highlightthickness=0
        )
        self.canvas.pack()
        
        # Draw menu background
        self._draw_background()
        
        # Draw header icons (bug report, etc.)
        self._draw_header_icons()
        
        # Build menu items
        self._build_menu()
        
        # Bind events
        self.bind('<FocusOut>', lambda e: self._close())
        self.bind('<Escape>', lambda e: self._close())
        
        # Position and animate
        if animate:
            self.attributes('-alpha', 0)
            self.geometry(f"+{x}+{y}")
            self.focus_force()
            FadeEffect.fade_in(self, duration=120, end_alpha=0.98)
            SlideEffect.slide_in(self, x, y, direction='left', distance=15, duration=120)
        else:
            self.geometry(f"+{x}+{y}")
            self.attributes('-alpha', 0.98)
            self.focus_force()
    
    def _calculate_height(self) -> int:
        """Calculate total menu height based on items"""
        height = self.MENU_PADDING * 2 + self.HEADER_HEIGHT  # Include header icons row
        for item in self.items:
            if item.get('type') == 'separator':
                height += 9  # Separator height
            else:
                height += self.ITEM_HEIGHT
        return height
    
    def _draw_background(self):
        """Draw rounded rectangle background with shadow"""
        pad = 5  # Shadow offset
        
        # Shadow layers for soft shadow effect
        for i in range(3, 0, -1):
            shadow_color = f'#{"0" * (6 - i)}{"1" * i * 2}{"0" * (6 - i * 2)}'[:7]
            draw_rounded_rect(
                self.canvas,
                pad + i, pad + i,
                self.menu_width + pad + i, self.menu_height + pad + i,
                radius=self.CORNER_RADIUS,
                fill='#111118', outline=''
            )
        
        # Main background
        draw_rounded_rect(
            self.canvas,
            pad, pad,
            self.menu_width + pad, self.menu_height + pad,
            radius=self.CORNER_RADIUS,
            fill=colors['bg'], outline=colors['border']
        )
        
        # Subtle inner glow/border
        draw_rounded_rect(
            self.canvas,
            pad + 1, pad + 1,
            self.menu_width + pad - 1, self.menu_height + pad - 1,
            radius=self.CORNER_RADIUS - 1,
            fill='', outline='#252540'
        )
    
    def _draw_header_icons(self):
        """Draw header icons row (bug report aligned right)"""
        pad = 5
        
        # Bug report icon - positioned at top right
        bug_x = self.menu_width + pad - 22
        bug_y = pad + self.MENU_PADDING + 6
        
        # Bug icon with hover effect
        self.canvas.create_text(
            bug_x, bug_y,
            text='🐞',
            font=('Segoe UI Emoji', 12),
            fill='#6c7086',  # Dim color by default
            tags=('bug_icon', 'bug_clickable')
        )
        
        # Bind hover and click events
        self.canvas.tag_bind('bug_clickable', '<Enter>', self._on_bug_enter)
        self.canvas.tag_bind('bug_clickable', '<Leave>', self._on_bug_leave)
        self.canvas.tag_bind('bug_clickable', '<Button-1>', self._on_bug_click)
    
    def _on_bug_enter(self, event):
        """Bug icon hover enter"""
        self.canvas.itemconfig('bug_icon', fill='#f38ba8')  # Red-ish for bug
        self.canvas.config(cursor='hand2')
    
    def _on_bug_leave(self, event):
        """Bug icon hover leave"""
        self.canvas.itemconfig('bug_icon', fill='#6c7086')
        self.canvas.config(cursor='')
    
    def _on_bug_click(self, event):
        """Bug icon click - trigger bug report"""
        if self.on_bug_report:
            self._do_destroy()
            self.on_bug_report()
    
    def _build_menu(self):
        """Create menu items as canvas elements"""
        y_offset = self.MENU_PADDING + 5 + self.HEADER_HEIGHT  # Start after header
        pad = 5
        widget_idx = 0  # Separate counter for actual menu items
        
        for item in self.items:
            if item.get('type') == 'separator':
                # Draw separator line
                self.canvas.create_line(
                    pad + 15, y_offset + 4,
                    self.menu_width + pad - 15, y_offset + 4,
                    fill=colors['border'], width=1
                )
                y_offset += 9
            else:
                # Create item with widget_idx (not loop idx)
                self._create_menu_item(widget_idx, item, pad, y_offset)
                y_offset += self.ITEM_HEIGHT
                widget_idx += 1  # Only increment for actual items
    
    def _create_menu_item(self, idx: int, item: dict, pad: int, y: int):
        """Create a single menu item with hover effects"""
        is_disabled = item.get('in_develop', False) or item.get('command') is None
        text_color = item.get('fg', colors['fg'])
        
        if is_disabled and item.get('command') is None and 'TRIAL' not in item.get('label', ''):
            text_color = colors['text_dim']
        
        x1, y1 = pad + 6, y
        x2, y2 = self.menu_width + pad - 6, y + self.ITEM_HEIGHT - 4
        
        # Hover background (initially hidden)
        hover_rect = draw_rounded_rect(
            self.canvas, x1, y1, x2, y2,
            radius=8,
            fill=colors['bg'], outline='',
            tags=(f'hover_{idx}', 'hover_bg')
        )
        
        # Icon
        icon_x = pad + 25
        if 'icon' in item:
            self.canvas.create_text(
                icon_x, y + self.ITEM_HEIGHT // 2 - 2,
                text=item['icon'],
                font=('Segoe UI Emoji', 13),
                fill=text_color,
                tags=(f'item_{idx}', 'clickable')
            )
        
        # Label text
        label = item['label']
        if item.get('in_develop'):
            label += " (Dev)"
            
        self.canvas.create_text(
            icon_x + 25, y + self.ITEM_HEIGHT // 2 - 2,
            text=label,
            font=FONTS['body'],
            fill=text_color,
            anchor='w',
            tags=(f'item_{idx}', 'clickable')
        )
        
        # Store item data for events
        self.item_widgets.append({
            'idx': idx,
            'item': item,
            'bounds': (x1, y1, x2, y2),
            'hover_rect': hover_rect,
            'disabled': is_disabled and item.get('command') is None
        })
        
        # Bind hover and click events to canvas
        self.canvas.tag_bind(f'item_{idx}', '<Enter>', lambda e, i=idx: self._on_item_enter(i))
        self.canvas.tag_bind(f'item_{idx}', '<Leave>', lambda e, i=idx: self._on_item_leave(i))
        self.canvas.tag_bind(f'item_{idx}', '<Button-1>', lambda e, i=idx: self._on_item_click(i))
        
        # Also bind to hover rect
        self.canvas.tag_bind(f'hover_{idx}', '<Enter>', lambda e, i=idx: self._on_item_enter(i))
        self.canvas.tag_bind(f'hover_{idx}', '<Leave>', lambda e, i=idx: self._on_item_leave(i))
        self.canvas.tag_bind(f'hover_{idx}', '<Button-1>', lambda e, i=idx: self._on_item_click(i))
    
    def _on_item_enter(self, idx: int):
        """Handle mouse enter on menu item"""
        widget_data = self.item_widgets[idx]
        if widget_data['disabled']:
            return
            
        self.hovered_index = idx
        self.canvas.config(cursor='hand2')
        
        # Animate hover background
        self.canvas.itemconfig(widget_data['hover_rect'], fill=colors['sidebar_active'])
    
    def _on_item_leave(self, idx: int):
        """Handle mouse leave from menu item"""
        widget_data = self.item_widgets[idx]
        self.hovered_index = -1
        self.canvas.config(cursor='')
        
        # Reset hover background
        self.canvas.itemconfig(widget_data['hover_rect'], fill=colors['bg'])
    
    def _on_item_click(self, idx: int):
        """Handle click on menu item"""
        widget_data = self.item_widgets[idx]
        if widget_data['disabled']:
            return
            
        item = widget_data['item']
        command = item.get('command')
        
        # Destroy menu immediately (no animation - fixes exit double-click)
        self._do_destroy()
        
        # Execute command after menu is destroyed
        if command:
            try:
                command()
            except Exception as e:
                print(f"[Menu] Command error: {e}")
    
    def _close(self):
        """Close the menu with animation"""
        if self.animate:
            FadeEffect.fade_out(self, duration=80, on_complete=self._do_destroy)
        else:
            self._do_destroy()
    
    def _do_destroy(self):
        """Actually destroy the window"""
        if self.on_close_callback:
            self.on_close_callback()
        try:
            self.destroy()
        except tk.TclError:
            pass

