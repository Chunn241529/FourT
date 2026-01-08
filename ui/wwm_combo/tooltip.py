"""
RichTooltip - Advanced tooltip with title, description, and image/GIF support.
Dark theme styling with markdown-like text formatting.
"""

import tkinter as tk
import re
import math
from pathlib import Path


class RichTooltip:
    """
    Advanced tooltip that supports Title, Description (multiline), and Image/GIF.
    Renders with a dark theme and custom styling.
    """
    def __init__(self, widget, get_data_func, resources_dir, auto_bind=True):
        self.widget = widget
        self.get_data_func = get_data_func  # Function returning dict: {name, description, image_path}
        self.resources_dir = resources_dir
        self.tipwindow = None
        self.id = None
        
        if auto_bind:
            self.widget.bind("<Enter>", self.enter)
            self.widget.bind("<Leave>", self.leave)
            self.widget.bind("<ButtonPress>", self.leave)
        
    def enter(self, event=None):
        self.schedule()
        
    def leave(self, event=None):
        self.unschedule()
        self.hidetip()
        
    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)  # 500ms delay
        
    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)
            
    def showtip(self, event=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
        self.show_at_manual(x, y)

    def show_at_manual(self, x, y):
        data = self.get_data_func()
        if not data or not data.get('description'):
            return
            
        # Create toplevel
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry(f"+{x}+{y}")
        tw.wm_attributes("-topmost", 1)
        tw.wm_attributes("-alpha", 0.95)  # Slight transparency
        
        # Main container with border
        bg_color = "#1e1e1e"
        border_color = "#3498db"
        text_color = "#ecf0f1"
        dim_color = "#bdc3c7"
        
        frame = tk.Frame(tw, bg=bg_color, relief='solid', bd=1)
        frame.config(highlightbackground=border_color, highlightthickness=1)
        frame.pack()
        
        # Title (Skill Name)
        if data.get('name'):
            tk.Label(frame, text=data['name'], justify=tk.LEFT,
                    bg=bg_color, fg=border_color,
                    font=("Segoe UI", 10, "bold")).pack(anchor='w', padx=10, pady=(8, 2))
                    
        # Separator
        tk.Frame(frame, bg="#333", height=1).pack(fill='x', padx=10, pady=2)
        
        # Image Parsing [image: filename.png]
        img_path = None
        desc = data.get('description', '')
        img_match = re.search(r'\[image:\s*(.*?)\]', desc)
        if img_match:
            img_filename = img_match.group(1)
            # Remove the tag from description for display
            desc = re.sub(r'\[image:\s*.*?\]', '', desc).strip()
            
            # Try to find file
            possible_paths = [
                self.resources_dir / img_filename,
                Path(img_filename)
            ]
            for p in possible_paths:
                if p.exists():
                    img_path = p
                    break

        # Description (Text with Markdown support)
        if desc:
            text_widget = self._create_description_widget(frame, desc, bg_color, text_color)
            text_widget.pack(anchor='w', fill='x', pady=(0, 5))
        
        # Image/GIF display
        if img_path:
            self._display_image(frame, img_path, bg_color)

    def _create_description_widget(self, parent, desc, bg_color, text_color):
        """Create text widget with markdown-like formatting"""
        text_widget = tk.Text(parent, bg=bg_color, fg=text_color,
                            font=("Segoe UI", 9),
                            wrap=tk.WORD, width=40, height=1,
                            bd=0, highlightthickness=0,
                            padx=10, pady=5)
        
        # Configure markdown tags
        text_widget.tag_configure("highlight", font=("Segoe UI", 9, "bold"))
        text_widget.tag_configure("bold", font=("Segoe UI", 9, "bold"))
        
        # Parse and insert formatted text
        parts = re.split(r'(\*.*?\*|\[[^\]]+:[^\]]+\])', desc)
        
        for part in parts:
            if not part:
                continue
            
            if part.startswith('*') and part.endswith('*') and len(part) > 1:
                # Bold text
                content = part[1:-1]
                text_widget.insert(tk.END, content, "highlight")
                
            elif part.startswith('[') and part.endswith(']') and ':' in part:
                # Custom color [color:content]
                try:
                    inner = part[1:-1]
                    color_code, content = inner.split(':', 1)
                    color_code = color_code.strip()
                    
                    tag_name = f"color_{color_code}"
                    text_widget.tag_configure(tag_name, foreground=color_code)
                    
                    if content.startswith('*') and content.endswith('*') and len(content) > 1:
                        bold_content = content[1:-1]
                        text_widget.insert(tk.END, bold_content, (tag_name, "bold"))
                    else:
                        text_widget.insert(tk.END, content, tag_name)
                except Exception:
                    text_widget.insert(tk.END, part)
            else:
                text_widget.insert(tk.END, part)
        
        # Auto-adjust height
        clean_text = re.sub(r'\[[^\]]+:(.*?)\]', r'\1', desc)
        clean_text = re.sub(r'\*(.*?)\*', r'\1', clean_text)
        
        num_lines = 0
        char_width = 38
        
        for line in clean_text.split('\n'):
            if len(line) == 0:
                num_lines += 1
            else:
                num_lines += math.ceil(len(line) / char_width)
        
        final_height = min(num_lines, 20)
        text_widget.configure(height=final_height)
        text_widget.configure(state=tk.DISABLED, cursor="arrow")
        
        return text_widget
    
    def _display_image(self, frame, img_path, bg_color):
        """Display static image or animated GIF"""
        try:
            from PIL import Image, ImageTk, ImageSequence
            
            pil_img = Image.open(str(img_path))
            
            # Check if animated
            self.is_animated = getattr(pil_img, "is_animated", False)
            self.frames = []
            self.delay = 100
            
            loaded_anim = False
            if self.is_animated:
                try:
                    max_w = 280
                    for img_frame in ImageSequence.Iterator(pil_img):
                        frame_rgba = img_frame.copy().convert('RGBA')
                        ratio = max_w / frame_rgba.width
                        new_h = int(frame_rgba.height * ratio)
                        frame_resized = frame_rgba.resize((max_w, new_h), Image.Resampling.LANCZOS)
                        self.frames.append(ImageTk.PhotoImage(frame_resized))
                    
                    self.delay = pil_img.info.get('duration', 100)
                    self.current_frame = 0
                    
                    self.img_label = tk.Label(frame, image=self.frames[0], bg=bg_color)
                    self.img_label.pack(padx=10, pady=(0, 10))
                    
                    self._animate()
                    loaded_anim = True
                except Exception as e:
                    print(f"Animation load failed, falling back to static: {e}")
                    self.frames = []
            
            if not loaded_anim:
                # Static image
                if pil_img.mode != 'RGBA':
                    pil_img = pil_img.convert('RGBA')
                
                max_w = 280
                if pil_img.width > max_w:
                    ratio = max_w / pil_img.width
                    new_h = int(pil_img.height * ratio)
                    pil_img = pil_img.resize((max_w, new_h), Image.Resampling.LANCZOS)
                
                photo = ImageTk.PhotoImage(pil_img)
                self.img_label = tk.Label(frame, image=photo, bg=bg_color)
                self.img_label.image = photo
                self.img_label.pack(padx=10, pady=(0, 10))
                
        except Exception as e:
            print(f"Tooltip image error: {e}")

    def _animate(self):
        """Loop animation frames"""
        if not self.tipwindow:
            return
            
        self.current_frame = (self.current_frame + 1) % len(self.frames)
        self.img_label.configure(image=self.frames[self.current_frame])
        
        self.tipwindow.after(self.delay, self._animate)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()
