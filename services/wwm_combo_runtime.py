"""
WWM Combo Runtime - Singleton service for background combo execution

This service holds the combo player, combo manager, and trigger manager
so that active combos can continue running in the background even when
the WWM Combo UI is closed, as long as the launcher is still running.
"""

from typing import Callable, Optional, Dict, Any
from services.wwm_combo_service import ComboPlayer, ComboManager, TriggerManager, get_combos_dir


class WWMComboRuntime:
    """Singleton runtime for WWM Combo background execution"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'WWMComboRuntime':
        """Get or create the singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        if WWMComboRuntime._instance is not None:
            raise RuntimeError("Use get_instance() to get WWMComboRuntime")
        
        self.player = ComboPlayer()
        self.combo_manager = ComboManager(get_combos_dir())
        self.trigger_manager = TriggerManager()
        
        # Status callback for UI updates (optional)
        self.on_status_change: Optional[Callable[[str], None]] = None
        
        # UI callbacks for trigger events (set by UI when visible)
        self.ui_on_trigger_press: Optional[Callable] = None
        self.ui_on_trigger_release: Optional[Callable] = None
        self.ui_on_trigger_set: Optional[Callable] = None
        
        # Tk root for countdown overlay (set when UI is created)
        self.tk_root = None
        
        # Track if listeners are running
        self._listeners_started = False
        
        # === Session State (persists when UI is closed and reopened) ===
        # These values are saved by the UI when closing and restored when reopening
        self.session_combo_items: list = []  # Current timeline items being edited
        self.session_trigger_key: str = "Button.x1"  # Selected trigger button
        self.session_playback_mode: str = "once"  # once/loop/hold
        self.session_current_weapon: str = ""  # Selected weapon in palette
        
        # Setup trigger callbacks
        self._setup_trigger_callbacks()
        
        # Setup player callback for countdown overlay
        self.player.on_skill_executed = self._on_skill_executed
    
    def save_session_state(self, combo_items: list, trigger_key: str, 
                           playback_mode: str, current_weapon: str):
        """Save UI session state (called when UI is closing)"""
        self.session_combo_items = list(combo_items) if combo_items else []
        self.session_trigger_key = trigger_key or "Button.x1"
        self.session_playback_mode = playback_mode or "once"
        self.session_current_weapon = current_weapon or ""
    
    def get_session_state(self) -> Dict[str, Any]:
        """Get saved session state (called when UI is opening)"""
        return {
            'combo_items': self.session_combo_items,
            'trigger_key': self.session_trigger_key,
            'playback_mode': self.session_playback_mode,
            'current_weapon': self.session_current_weapon
        }
    
    def _setup_trigger_callbacks(self):
        """Setup callbacks for trigger manager"""
        self.trigger_manager.on_trigger_press = self._on_trigger_press
        self.trigger_manager.on_trigger_release = self._on_trigger_release
        self.trigger_manager.on_trigger_set = self._on_trigger_set
    
    def _on_trigger_press(self, key_or_button):
        """Callback when trigger pressed"""
        # Forward to UI if available
        if self.ui_on_trigger_press:
            self.ui_on_trigger_press(key_or_button)
            return  # UI handles playback
        
        # Background mode: handle playback directly
        combo_data = self.combo_manager.get_active(key_or_button)
        if combo_data:
            mode = combo_data['settings']['mode']
            if mode == "hold":
                if not self.player.running:
                    self._play_combo(combo_data)
            else:
                if self.player.running:
                    self.player.stop()
                else:
                    self._play_combo(combo_data)
    
    def _on_trigger_release(self, key_or_button):
        """Callback when trigger released"""
        # Forward to UI if available
        if self.ui_on_trigger_release:
            self.ui_on_trigger_release(key_or_button)
            return  # UI handles release
        
        # Background mode: handle release directly
        combo_data = self.combo_manager.get_active(key_or_button)
        if combo_data and combo_data['settings']['mode'] == 'hold' and self.player.running:
            self.player.stop()
    
    def _on_trigger_set(self, key_or_button):
        """Callback when trigger key/button is set"""
        # Forward to UI if available
        if self.ui_on_trigger_set:
            self.ui_on_trigger_set(key_or_button)
    
    def _on_skill_executed(self, skill_item: Dict):
        """Callback when a skill with countdown is executed"""
        countdown = skill_item.get('countdown', 0)
        if countdown <= 0 or not self.tk_root:
            return
        
        # Check if tk_root window still exists
        try:
            if not self.tk_root.winfo_exists():
                return
        except:
            return
        
        # Show countdown overlay on main thread
        try:
            from ui.wwm_combo.countdown_overlay import show_skill_countdown
            
            skill_name = skill_item.get('name', skill_item.get('key', 'Skill'))
            image_path = skill_item.get('image', '')
            
            self.tk_root.after(0, lambda: show_skill_countdown(
                self.tk_root,
                skill_name,
                image_path,
                countdown
            ))
        except Exception as e:
            print(f"[WWMComboRuntime] Error showing countdown: {e}")
    
    def _play_combo(self, combo_data):
        """Play a combo"""
        items = combo_data['items']
        mode = combo_data['settings']['mode']
        loop_count = 0 if mode in ('loop', 'hold') else 1
        
        if self.on_status_change:
            self.on_status_change(f"Playing: {combo_data['name']}")
        
        self.player.play(
            items, 
            on_finish=lambda: self._on_playback_finished(), 
            loop_count=loop_count
        )
    
    def _on_playback_finished(self):
        """Callback when playback finishes"""
        if self.on_status_change:
            self.on_status_change("Ready")
    
    def start_listeners(self):
        """Start global keyboard/mouse listeners if not already running"""
        if not self._listeners_started:
            self.trigger_manager.start()
            self._listeners_started = True
            print("[WWMComboRuntime] Listeners started")
    
    def stop_listeners(self):
        """Stop global listeners and player"""
        if self._listeners_started:
            self.trigger_manager.stop()
            self._listeners_started = False
        self.player.stop()
        print("[WWMComboRuntime] Listeners stopped")
    
    def has_active_combos(self) -> bool:
        """Check if there are any active combos"""
        return bool(self.combo_manager.active_combos)
    
    @property
    def active_combos(self) -> Dict[Any, Dict]:
        """Get active combos dict"""
        return self.combo_manager.active_combos


def get_wwm_combo_runtime() -> WWMComboRuntime:
    """Get the singleton WWM Combo Runtime instance"""
    return WWMComboRuntime.get_instance()
