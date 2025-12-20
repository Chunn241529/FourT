"""
WWM Combo Service - Business Logic Layer
Handles skill loading, image caching, combo playback, and save/load operations.
"""

import json
import os
import threading
import hashlib
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from typing import List, Dict, Any, Optional, Callable
from PIL import Image, ImageTk
from pynput import keyboard, mouse


class SkillLoader:
    """Handles loading skills and images from config with async loading and smart caching"""
    
    # Class-level cache to persist across reloads
    _skills_hash_cache: str = ""
    _pil_image_cache: Dict[str, Image.Image] = {}  # skill_id -> PIL Image (persistent)
    
    def __init__(self, resources_dir: str):
        self.resources_dir = resources_dir
        self.skills: List[Dict] = []
        self.weapons: List[Dict] = []
        self.image_cache: Dict[str, Any] = {}  # id -> PhotoImage (tk-specific)
        self._loading_images = False
        self._on_images_loaded: Optional[Callable] = None
        
        # Disk cache directory for persistent image storage
        self._cache_dir = os.path.join(resources_dir, ".image_cache")
        if not os.path.exists(self._cache_dir):
            try:
                os.makedirs(self._cache_dir)
            except Exception:
                pass
        
    def _get_skills_file_hash(self, filepath: str) -> str:
        """Calculate MD5 hash of skills.json for change detection"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    return hashlib.md5(f.read()).hexdigest()
        except Exception:
            pass
        return ""
        
    def load_skills(self, force: bool = False) -> List[Dict]:
        """Load skills from skills.json (local first, then server API)
        
        Args:
            force: If True, reload even if file hasn't changed
            
        Returns:
            List of skill dictionaries
        """
        # Look for skills.json in data folder (sibling to resources_dir's parent)
        data_dir = os.path.join(os.path.dirname(self.resources_dir), "data")
        skills_file = os.path.join(data_dir, "skills.json")
        
        # Smart caching: Skip if file hasn't changed
        current_hash = self._get_skills_file_hash(skills_file)
        if not force and current_hash and current_hash == SkillLoader._skills_hash_cache:
            # File unchanged, skip reload
            return self.skills
        
        data = None
        
        # Try local file first
        if os.path.exists(skills_file):
            try:
                with open(skills_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Update hash cache on successful load
                SkillLoader._skills_hash_cache = current_hash
            except Exception as e:
                print(f"Error loading local skills.json: {e}")
        
        # If no local file, try fetching from server (only if online)
        if data is None:
            try:
                from services.connection_manager import is_server_offline
                
                # Skip server fetch if offline
                if is_server_offline():
                    print("[SkillLoader] Offline - skipping server fetch")
                else:
                    from core.config import get_license_server_url
                    import requests
                    
                    api_url = f"{get_license_server_url()}/skills/data"
                    print(f"Fetching skills from server: {api_url}")
                    
                    response = requests.get(api_url, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        print(f"Loaded {len(data.get('skills', []))} skills from server")
            except Exception as e:
                print(f"Error fetching skills from server: {e}")
        
        # Parse data if available
        if data:
            if isinstance(data, dict):
                self.weapons = data.get('weapons', [])
                self.skills = data.get('skills', [])
            else:
                # Old format - list of skills
                self.skills = data
                self.weapons = [{"id": "common", "name": "Chung", "icon": "⭐", "color": "#95a5a6"}]
            return self.skills
        
        # Fallback default skills
        self.weapons = [{"id": "common", "name": "Chung", "icon": "⭐", "color": "#95a5a6"}]
        self.skills = [
            {"id": "light_attack", "name": "Công Thường", "key": "j", "color": "#e74c3c", "hold": 0.05, "weapon": "common"},
            {"id": "heavy_attack", "name": "Công Nặng", "key": "k", "color": "#8e44ad", "hold": 0.1, "weapon": "common"},
            {"id": "skill_1", "name": "Skill 1", "key": "u", "color": "#3498db", "hold": 0.05, "weapon": "common"},
            {"id": "skill_2", "name": "Skill 2", "key": "i", "color": "#2ecc71", "hold": 0.05, "weapon": "common"},
            {"id": "skill_3", "name": "Skill 3", "key": "o", "color": "#e67e22", "hold": 0.05, "weapon": "common"},
            {"id": "dodge", "name": "Né", "key": "shift", "color": "#f1c40f", "hold": 0.05, "weapon": "common"},
            {"id": "jump", "name": "Nhảy", "key": "space", "color": "#95a5a6", "hold": 0.05, "weapon": "common"},
        ]
        return self.skills
    
    def get_skills_by_weapon(self, weapon_id: str) -> List[Dict]:
        """Get skills filtered by weapon ID"""
        return [s for s in self.skills if s.get('weapon') == weapon_id]
    
    def get_skill_variants(self, weapon_id: str, key: str) -> List[Dict]:
        """Get all skill variants with same weapon and key, ordered by appearance in JSON"""
        variants = []
        for skill in self.skills:
            if skill.get('weapon') == weapon_id and skill.get('key') == key:
                variants.append(skill)
        return variants
    
    def get_weapon_by_id(self, weapon_id: str) -> Optional[Dict]:
        """Get weapon info by ID"""
        return next((w for w in self.weapons if w['id'] == weapon_id), None)
    
    def get_skill_color(self, skill: Dict) -> str:
        """Get skill color - inherits from weapon if not specified"""
        # If skill has its own color, use it
        if skill.get('color'):
            return skill['color']
        # Otherwise inherit from weapon
        weapon = self.get_weapon_by_id(skill.get('weapon', 'common'))
        if weapon and weapon.get('color'):
            return weapon['color']
        # Fallback
        return '#95a5a6'
    
    def load_images(self, size: tuple = (40, 40), on_complete: Callable = None) -> Dict[str, Any]:
        """Load images for all skills ASYNCHRONOUSLY (non-blocking)
        
        Args:
            size: Tuple of (width, height) for image resize
            on_complete: Optional callback when all images are loaded
            
        Returns:
            Current image cache (may be incomplete if still loading)
        """
        self._on_images_loaded = on_complete
        
        # Collect skills that need image loading
        skills_to_load = []
        for skill in self.skills:
            if 'image' not in skill:
                continue
            skill_id = skill['id']
            # Skip if already in PIL cache (persistent across reloads)
            if skill_id in SkillLoader._pil_image_cache:
                # Just convert to PhotoImage if not in tk cache
                if skill_id not in self.image_cache:
                    try:
                        pil_img = SkillLoader._pil_image_cache[skill_id]
                        self.image_cache[skill_id] = ImageTk.PhotoImage(pil_img)
                    except Exception:
                        pass
            else:
                skills_to_load.append(skill)
        
        # If all images already cached, call callback immediately
        if not skills_to_load:
            if on_complete:
                on_complete()
            return self.image_cache
        
        # Load remaining images in background thread
        self._loading_images = True
        thread = threading.Thread(
            target=self._load_images_async,
            args=(skills_to_load, size),
            daemon=True
        )
        thread.start()
        
        return self.image_cache
    
    def _load_images_async(self, skills: List[Dict], size: tuple):
        """Load images asynchronously using ThreadPoolExecutor"""
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.LANCZOS
        
        def load_single_image(skill: Dict) -> tuple:
            """Load a single image, returns (skill_id, pil_image or None)"""
            skill_id = skill['id']
            img_source = skill.get('image', '')
            
            # Try loading from disk cache first (fast path)
            cache_file = os.path.join(self._cache_dir, f"{skill_id}.png")
            if os.path.exists(cache_file):
                try:
                    pil_img = Image.open(cache_file)
                    return (skill_id, pil_img)
                except Exception:
                    pass
            
            # Load from source
            try:
                if img_source.startswith('http://') or img_source.startswith('https://'):
                    pil_img = self._load_from_url(img_source)
                else:
                    pil_img = self._load_from_file(img_source)
                    
                if pil_img:
                    pil_img = pil_img.resize(size, resample)
                    # Save to disk cache for next time
                    try:
                        pil_img.save(cache_file, "PNG")
                    except Exception:
                        pass
                    return (skill_id, pil_img)
            except Exception as e:
                print(f"Error loading image for {skill.get('name', skill_id)}: {e}")
            return (skill_id, None)
        
        # Use ThreadPoolExecutor for parallel loading
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(load_single_image, skills))
        
        # Store results in caches (must be done in main logic, not threads)
        for skill_id, pil_img in results:
            if pil_img:
                # Store in persistent PIL cache
                SkillLoader._pil_image_cache[skill_id] = pil_img
        
        # Notify completion - PhotoImage must be created in main thread
        self._loading_images = False
        if self._on_images_loaded:
            self._on_images_loaded()
    
    def finalize_images(self):
        """Convert PIL images to PhotoImages (must be called from main thread)"""
        for skill_id, pil_img in SkillLoader._pil_image_cache.items():
            if skill_id not in self.image_cache:
                try:
                    self.image_cache[skill_id] = ImageTk.PhotoImage(pil_img)
                except Exception as e:
                    print(f"Error creating PhotoImage for {skill_id}: {e}")
    
    def is_loading(self) -> bool:
        """Check if images are still loading"""
        return self._loading_images
    
    def _load_from_url(self, url: str) -> Optional[Image.Image]:
        """Load image from URL (skip if offline)"""
        try:
            from services.connection_manager import is_server_offline
            if is_server_offline():
                return None
            
            import requests
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                return Image.open(BytesIO(response.content))
        except Exception:
            pass
        return None
    
    def _load_from_file(self, filename: str) -> Optional[Image.Image]:
        """Load image from local file - supports multiple path formats"""
        # Try different path options
        paths_to_try = [
            filename,  # Absolute or relative from cwd
            os.path.join(self.resources_dir, filename),  # Relative to resources dir
            os.path.join(self.resources_dir, os.path.basename(filename)),  # Just filename in resources
        ]
        
        for img_path in paths_to_try:
            if os.path.exists(img_path):
                try:
                    return Image.open(img_path)
                except Exception:
                    continue
        return None


class ComboPlayer:
    """Handles combo playback with keyboard and mouse simulation"""
    
    def __init__(self):
        self.keyboard_controller = keyboard.Controller()
        self.mouse_controller = mouse.Controller()
        self.running = False
        self._thread: Optional[threading.Thread] = None
        # Callback for when a skill is executed (for countdown overlay)
        self.on_skill_executed: Optional[Callable[[Dict], None]] = None
        
    def play(self, combo_items: List[Dict], on_finish: Callable = None, loop_count: int = 1):
        """Play combo items in a separate thread"""
        self.running = True
        self._thread = threading.Thread(
            target=self._play_thread, 
            args=(combo_items, on_finish, loop_count), 
            daemon=True
        )
        self._thread.start()
        
    def stop(self):
        """Stop playback"""
        self.running = False
        
    def _play_thread(self, combo_items: List[Dict], on_finish: Callable, loop_count: int):
        import time
        iterations = 0
        
        while self.running:
            if loop_count > 0 and iterations >= loop_count:
                break
                
            for item in combo_items:
                if not self.running:
                    break
                    
                if item['type'] == 'delay':
                    time.sleep(item['value'])
                elif item['type'] == 'skill':
                    hold_duration = item.get('hold', 0.05)  # Default 50ms if not specified
                    click_count = item.get('click_count', 1)
                    
                    # Trigger countdown overlay if skill has countdown
                    if self.on_skill_executed and item.get('countdown', 0) > 0:
                        self.on_skill_executed(item)
                    
                    # Execute multiple times
                    for _ in range(max(1, int(click_count))):
                        if not self.running:
                            break
                        modifiers = item.get('modifiers', [])
                        self._execute_skill(item['key'], hold_duration, modifiers)
                    
            iterations += 1
            if loop_count == 0:
                continue
                
        self.running = False
        if on_finish:
            on_finish()
            
    def _execute_skill(self, key_str: str, hold_duration: float = 0.05, modifiers: list = None):
        """Press and release a key/perform action with specified hold duration and optional modifiers"""
        import time
        
        # Handle mouse scroll actions
        key_lower = key_str.lower()
        if key_lower == 'scroll_down':
            self.mouse_controller.scroll(0, -1)  # Scroll down
            time.sleep(hold_duration if hold_duration > 0 else 0.05)
            return
        elif key_lower == 'scroll_up':
            self.mouse_controller.scroll(0, 1)  # Scroll up
            time.sleep(hold_duration if hold_duration > 0 else 0.05)
            return
        elif key_lower in ('lmb', 'left_click', 'mouse1'):
            self.mouse_controller.press(mouse.Button.left)
            time.sleep(hold_duration if hold_duration > 0 else 0.05)
            self.mouse_controller.release(mouse.Button.left)
            return
        elif key_lower in ('rmb', 'right_click', 'mouse2'):
            self.mouse_controller.press(mouse.Button.right)
            time.sleep(hold_duration if hold_duration > 0 else 0.05)
            self.mouse_controller.release(mouse.Button.right)
            return
        elif key_lower in ('mmb', 'middle_click', 'mouse3'):
            self.mouse_controller.press(mouse.Button.middle)
            time.sleep(hold_duration if hold_duration > 0 else 0.05)
            self.mouse_controller.release(mouse.Button.middle)
            return
        elif key_lower in ('mouse4', 'x1', 'back'):
            self.mouse_controller.press(mouse.Button.x1)
            time.sleep(hold_duration if hold_duration > 0 else 0.05)
            self.mouse_controller.release(mouse.Button.x1)
            return
        elif key_lower in ('mouse5', 'x2', 'forward'):
            self.mouse_controller.press(mouse.Button.x2)
            time.sleep(hold_duration if hold_duration > 0 else 0.05)
            self.mouse_controller.release(mouse.Button.x2)
            return
        
        # Handle keyboard keys
        # Press modifiers first
        if modifiers:
            for mod in modifiers:
                mod_key = self._parse_key(mod)
                self.keyboard_controller.press(mod_key)
        
        key = self._parse_key(key_str)
        self.keyboard_controller.press(key)
        time.sleep(hold_duration if hold_duration > 0 else 0.05)
        self.keyboard_controller.release(key)
        
        # Release modifiers after
        if modifiers:
            for mod in reversed(modifiers):
                mod_key = self._parse_key(mod)
                self.keyboard_controller.release(mod_key)
        
    def _parse_key(self, key_str: str):
        """Parse key string to pynput key"""
        special_keys = {
            'space': keyboard.Key.space,
            'shift': keyboard.Key.shift,
            'ctrl': keyboard.Key.ctrl,
            'alt': keyboard.Key.alt,
            'tab': keyboard.Key.tab,
            'enter': keyboard.Key.enter,
            'esc': keyboard.Key.esc,
        }
        
        key_lower = key_str.lower()
        if key_lower in special_keys:
            return special_keys[key_lower]
        
        if len(key_str) == 1:
            return key_str.lower()
            
        return key_str


class ComboManager:
    """Manages combo creation, saving, and loading"""
    
    def __init__(self, combos_dir: str):
        self.combos_dir = combos_dir
        self.active_combos: Dict[Any, Dict] = {}  # trigger_code -> combo_data
        
        # Ensure combos directory exists
        if not os.path.exists(combos_dir):
            os.makedirs(combos_dir)
    
    def save_combo(self, filepath: str, items: List[Dict], settings: Dict) -> bool:
        """Save combo to JSON file"""
        try:
            data = {
                'items': items,
                'settings': settings
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving combo: {e}")
            return False
    
    def load_combo(self, filepath: str) -> Optional[Dict]:
        """Load combo from JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading combo: {e}")
            return None
    
    def add_active(self, trigger_code: Any, combo_data: Dict):
        """Add combo to active list"""
        normalized = self._normalize_trigger(trigger_code)
        self.active_combos[normalized] = combo_data
        
    def remove_active(self, trigger_code: Any):
        """Remove combo from active list"""
        normalized = self._normalize_trigger(trigger_code)
        if normalized in self.active_combos:
            del self.active_combos[normalized]
            
    def clear_active(self):
        """Clear all active combos"""
        self.active_combos = {}
        
    def get_active(self, trigger_code: Any) -> Optional[Dict]:
        """Get active combo by trigger"""
        normalized = self._normalize_trigger(trigger_code)
        return self.active_combos.get(normalized)
    
    @staticmethod
    def _normalize_trigger(key_or_button: Any) -> str:
        """Normalize trigger key/button to string for consistent comparison.
        
        This fixes the bug where pynput KeyCode objects are different instances 
        for the same key, causing dict lookups to fail.
        """
        if isinstance(key_or_button, mouse.Button):
            return f"Button.{key_or_button.name}"
        if hasattr(key_or_button, 'name'):
            # keyboard.Key like shift, ctrl, etc.
            return f"Key.{key_or_button.name}"
        if hasattr(key_or_button, 'char') and key_or_button.char:
            # keyboard.KeyCode with a character
            return f"char.{key_or_button.char.lower()}"
        # Fallback: use string representation
        return str(key_or_button)


class TriggerManager:
    """Manages global keyboard/mouse listeners for triggers"""
    
    def __init__(self):
        self.key_listener: Optional[keyboard.Listener] = None
        self.mouse_listener: Optional[mouse.Listener] = None
        
        self.is_setting_trigger = False
        self.trigger_key_code: Any = mouse.Button.x1
        
        # Callbacks
        self.on_trigger_press: Optional[Callable] = None
        self.on_trigger_release: Optional[Callable] = None
        self.on_trigger_set: Optional[Callable] = None
        
    def start(self):
        """Start global listeners"""
        self.stop()  # Stop existing listeners first
        
        self.key_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self.key_listener.start()
        
        self.mouse_listener = mouse.Listener(on_click=self._on_mouse_click)
        self.mouse_listener.start()
        
    def stop(self):
        """Stop global listeners"""
        if self.key_listener:
            self.key_listener.stop()
            self.key_listener = None
        if self.mouse_listener:
            self.mouse_listener.stop()
            self.mouse_listener = None
            
    def start_setting_trigger(self):
        """Enter trigger setting mode"""
        self.is_setting_trigger = True
        
    def _on_key_press(self, key):
        if self.is_setting_trigger:
            self._set_trigger(key)
            return
        if self.on_trigger_press:
            self.on_trigger_press(key)
            
    def _on_key_release(self, key):
        if self.on_trigger_release:
            self.on_trigger_release(key)
            
    def _on_mouse_click(self, x, y, button, pressed):
        if self.is_setting_trigger:
            if pressed:
                self._set_trigger(button)
            return
        
        if pressed:
            if self.on_trigger_press:
                self.on_trigger_press(button)
        else:
            if self.on_trigger_release:
                self.on_trigger_release(button)
                
    def _set_trigger(self, key_or_button):
        """Set the trigger key/button"""
        self.trigger_key_code = key_or_button
        self.is_setting_trigger = False
        if self.on_trigger_set:
            self.on_trigger_set(key_or_button)
            
    @staticmethod
    def get_key_name(key) -> str:
        """Get display name for key/button"""
        if isinstance(key, mouse.Button):
            return str(key)
        if hasattr(key, 'name'):
            return key.name.upper()
        elif hasattr(key, 'char'):
            return key.char.upper() if key.char else "UNKNOWN"
        return str(key)
    
    @staticmethod
    def parse_trigger_string(trigger_str: str):
        """Parse trigger string back to key/button object"""
        try:
            if trigger_str.startswith("Button."):
                button_name = trigger_str.split('.')[-1]
                return getattr(mouse.Button, button_name, mouse.Button.x1)
            
            if hasattr(keyboard.Key, trigger_str.lower()):
                return getattr(keyboard.Key, trigger_str.lower())
            
            if len(trigger_str) == 1:
                return trigger_str.lower()
            
            return mouse.Button.x1
        except Exception:
            return mouse.Button.x1


class TemplateManager:
    """Manages combo templates - save, load, delete, and fetch from server"""
    
    def __init__(self, combos_dir: str):
        self.combos_dir = combos_dir
        self.templates_file = os.path.join(combos_dir, "templates.json")
        self.templates: List[Dict] = []  # Local templates
        self.server_templates: List[Dict] = []  # Server templates (cached)
        self.load_templates()
    
    def load_templates(self) -> List[Dict]:
        """Load local templates from JSON file"""
        if os.path.exists(self.templates_file):
            try:
                with open(self.templates_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.templates = data.get('templates', [])
            except Exception as e:
                print(f"Error loading templates: {e}")
                self.templates = []
        return self.templates
    
    def fetch_server_templates(self, timeout: int = 8) -> List[Dict]:
        """Fetch templates from server API and sync to local storage"""
        try:
            from services.connection_manager import is_server_offline
            
            # Skip if offline
            if is_server_offline():
                print("[TemplateManager] Offline - using cached templates")
                return self.server_templates
            
            from core.config import get_license_server_url
            import requests
            
            api_url = f"{get_license_server_url()}/combos/list"
            response = requests.get(api_url, timeout=timeout)
            
            if response.status_code == 200:
                data = response.json()
                new_server_templates = data.get('templates', [])
                
                # Mark as server templates
                for t in new_server_templates:
                    t['is_server'] = True
                    t['synced_from_server'] = True
                
                # Sync: add new server templates to local storage
                synced_count = 0
                local_names = {t['name'] for t in self.templates}
                
                for server_t in new_server_templates:
                    if server_t['name'] not in local_names:
                        # Add new server template to local
                        self.templates.append({
                            'name': server_t['name'],
                            'items': server_t.get('items', []),
                            'synced_from_server': True
                        })
                        synced_count += 1
                
                if synced_count > 0:
                    self.save_templates()
                    print(f"[TemplateManager] Synced {synced_count} new templates from server")
                
                self.server_templates = new_server_templates
                print(f"[TemplateManager] Fetched {len(new_server_templates)} templates from server")
            else:
                print(f"[TemplateManager] Server returned {response.status_code}")
                
        except Exception as e:
            print(f"Error fetching server templates: {e}")
        
        return self.server_templates
    
    def save_templates(self) -> bool:
        """Save local templates to JSON file"""
        try:
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump({'templates': self.templates}, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving templates: {e}")
            return False
    
    def add_template(self, name: str, items: List[Dict]) -> bool:
        """Add a new local template"""
        # Check for duplicate name
        if any(t['name'] == name for t in self.templates):
            return False
        
        self.templates.append({
            'name': name,
            'items': items
        })
        return self.save_templates()
    
    def delete_template(self, name: str) -> bool:
        """Delete a local template by name"""
        self.templates = [t for t in self.templates if t['name'] != name]
        return self.save_templates()
    
    def get_template(self, name: str) -> Optional[Dict]:
        """Get template by name (local first, then server)"""
        local = next((t for t in self.templates if t['name'] == name), None)
        if local:
            return local
        return next((t for t in self.server_templates if t['name'] == name), None)
    
    def get_all_templates(self) -> List[Dict]:
        """Get all templates - includes synced server templates"""
        # Since server templates are now synced to local, just return local templates
        # Mark synced templates with 'is_server' flag for UI distinction
        result = []
        for t in self.templates:
            template_copy = dict(t)
            if t.get('synced_from_server'):
                template_copy['is_server'] = True
            result.append(template_copy)
        return result


# Factory function to get resources directory
def get_resources_dir() -> str:
    """Get the wwm_resources directory path"""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "wwm_resources")


def get_combos_dir() -> str:
    """Get the wwm_combos directory path"""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "wwm_combos")
