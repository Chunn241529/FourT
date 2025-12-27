"""
Skills API Router
Serves skills.json data to clients
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
import json

router = APIRouter(
    prefix="/skills",
    tags=["skills"]
)


@router.get("/data")
async def get_skills_data():
    """Get skills.json data for WWM Combo"""
    try:
        # Find wwm_resources directory
        # backend/routers/skills.py -> backend/routers -> backend -> root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(current_dir))
        skills_file = os.path.join(root_dir, "data", "skills.json")
        
        if not os.path.exists(skills_file):
            # Try current working directory
            skills_file = os.path.join("data", "skills.json")
        
        if os.path.exists(skills_file):
            with open(skills_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            raise HTTPException(status_code=404, detail="skills.json not found")
            
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/image/{filename}")
async def get_skill_image(filename: str):
    """Serve skill image from wwm_resources"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(os.path.dirname(current_dir))
        
        # Try multiple paths
        paths_to_try = [
            os.path.join(root_dir, "wwm_resources", filename),
            os.path.join("wwm_resources", filename),
        ]
        
        for img_path in paths_to_try:
            if os.path.exists(img_path):
                return FileResponse(img_path)
        
        raise HTTPException(status_code=404, detail="Image not found")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
