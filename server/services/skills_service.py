"""
Skills Service for FourT Helper Admin
Handles all Skills/Weapons data operations - CRUD for skills.json
"""

import json
from pathlib import Path
from typing import Optional


class SkillsService:
    """Service for managing skills and weapons data"""
    
    def __init__(self, skills_file: Path):
        self.skills_file = skills_file
        self.data = {"weapons": [], "skills": []}
        
    def load_data(self) -> dict:
        """Load skills and weapons from JSON file"""
        self.data = {"weapons": [], "skills": []}
        
        if self.skills_file.exists():
            try:
                with open(self.skills_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception as e:
                raise RuntimeError(f"Không thể đọc skills.json: {e}")
        
        return self.data
    
    def save_data(self) -> bool:
        """Save skills data to JSON file"""
        try:
            with open(self.skills_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            raise RuntimeError(f"Không thể lưu: {e}")
    
    # ========== WEAPONS ==========
    
    def get_weapons(self) -> list:
        """Get all weapons"""
        return self.data.get('weapons', [])
    
    def get_weapon_ids(self) -> list:
        """Get list of weapon IDs"""
        return [w['id'] for w in self.get_weapons()]
    
    def get_weapon_by_id(self, weapon_id: str) -> Optional[dict]:
        """Get weapon by ID"""
        return next((w for w in self.get_weapons() if w['id'] == weapon_id), None)
    
    def get_weapon_by_index(self, idx: int) -> Optional[dict]:
        """Get weapon by index"""
        weapons = self.get_weapons()
        if 0 <= idx < len(weapons):
            return weapons[idx]
        return None
    
    def add_weapon(self, weapon: dict) -> bool:
        """Add a new weapon"""
        if not weapon.get('id'):
            raise ValueError("ID không được để trống")
        
        self.data.setdefault('weapons', []).append(weapon)
        return self.save_data()
    
    def update_weapon(self, idx: int, weapon: dict) -> bool:
        """Update weapon at index"""
        weapons = self.get_weapons()
        if 0 <= idx < len(weapons):
            self.data['weapons'][idx] = weapon
            return self.save_data()
        return False
    
    def delete_weapon(self, idx: int) -> bool:
        """Delete weapon at index"""
        weapons = self.get_weapons()
        if 0 <= idx < len(weapons):
            del self.data['weapons'][idx]
            return self.save_data()
        return False
    
    def reorder_weapons(self, from_idx: int, to_idx: int) -> bool:
        """Move weapon from one position to another"""
        weapons = self.get_weapons()
        if 0 <= from_idx < len(weapons) and 0 <= to_idx < len(weapons):
            weapon = weapons.pop(from_idx)
            weapons.insert(to_idx, weapon)
            return self.save_data()
        return False
    
    def get_skills_using_weapon(self, weapon_id: str) -> list:
        """Get all skills using a specific weapon"""
        return [s for s in self.get_skills() if s.get('weapon') == weapon_id]
    
    # ========== SKILLS ==========
    
    def get_skills(self, weapon_filter: str = "all") -> list:
        """Get skills, optionally filtered by weapon"""
        skills = self.data.get('skills', [])
        if weapon_filter == "all":
            return skills
        return [s for s in skills if s.get('weapon') == weapon_filter]
    
    def get_skill_by_id(self, skill_id: str) -> Optional[dict]:
        """Get skill by ID"""
        return next((s for s in self.get_skills() if s['id'] == skill_id), None)
    
    def add_skill(self, skill: dict) -> bool:
        """Add a new skill"""
        if not skill.get('id') or not skill.get('name'):
            raise ValueError("ID và Tên là bắt buộc")
        
        self.data.setdefault('skills', []).append(skill)
        return self.save_data()
    
    def update_skill(self, skill_id: str, skill: dict) -> bool:
        """Update existing skill by ID"""
        skills = self.data.get('skills', [])
        for i, s in enumerate(skills):
            if s['id'] == skill_id:
                self.data['skills'][i] = skill
                return self.save_data()
        return False
    
    def save_skill(self, skill: dict) -> bool:
        """Save skill - update if exists, add if new"""
        skill_id = skill.get('id')
        if not skill_id or not skill.get('name'):
            raise ValueError("ID và Tên là bắt buộc")
        
        skills = self.data.get('skills', [])
        existing_idx = next((i for i, s in enumerate(skills) if s['id'] == skill_id), None)
        
        if existing_idx is not None:
            skills[existing_idx] = skill
        else:
            skills.append(skill)
        
        self.data['skills'] = skills
        return self.save_data()
    
    def delete_skill(self, skill_id: str) -> bool:
        """Delete skill by ID"""
        skills = self.data.get('skills', [])
        self.data['skills'] = [s for s in skills if s['id'] != skill_id]
        return self.save_data()
    
    def generate_skill_id(self, weapon_id: str) -> str:
        """Generate next skill ID for a weapon"""
        weapon_skills = self.get_skills(weapon_id)
        next_num = len(weapon_skills) + 1
        return f"{weapon_id}_skill_{next_num}"
