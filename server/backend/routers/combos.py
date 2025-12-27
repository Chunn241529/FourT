"""
Combos API Router
Serves combo templates from wwm_combos folder to clients
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
import json
import glob

router = APIRouter(
    prefix="/combos",
    tags=["combos"]
)


def get_combos_dir():
    """Get wwm_combos directory path"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir))
    combos_dir = os.path.join(root_dir, "wwm_combos")
    
    if not os.path.exists(combos_dir):
        # Try current working directory
        combos_dir = "wwm_combos"
    
    return combos_dir


@router.get("/list")
async def list_combo_templates():
    """List all combo template files from wwm_combos folder"""
    try:
        combos_dir = get_combos_dir()
        
        if not os.path.exists(combos_dir):
            return {"templates": []}
        
        templates = []
        
        for filepath in glob.glob(os.path.join(combos_dir, "*.json")):
            filename = os.path.basename(filepath)
            
            # Skip templates.json (local templates file)
            if filename == "templates.json":
                continue
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    name = os.path.splitext(filename)[0]
                    items = data.get('items', [])
                    
                    templates.append({
                        "name": name,
                        "filename": filename,
                        "items": items,
                        "skill_count": sum(1 for i in items if i.get('type') == 'skill'),
                        "delay_count": sum(1 for i in items if i.get('type') == 'delay')
                    })
            except Exception as e:
                print(f"Error loading combo {filename}: {e}")
                continue
        
        return {"templates": templates}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{filename}")
async def download_combo(filename: str):
    """Download a specific combo file"""
    try:
        combos_dir = get_combos_dir()
        filepath = os.path.join(combos_dir, filename)
        
        # Security: ensure filename is just a filename, not a path
        if os.path.basename(filename) != filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        if os.path.exists(filepath):
            return FileResponse(filepath, filename=filename)
        
        raise HTTPException(status_code=404, detail="Combo file not found")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
