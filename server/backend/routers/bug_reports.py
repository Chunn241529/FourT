"""
Bug Report API Router - CRUD operations for bug reports
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os
import json
import uuid
import shutil

router = APIRouter(prefix="/bug-reports", tags=["Bug Reports"])

# Storage paths
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
BUG_REPORTS_FILE = os.path.join(DATA_DIR, "bug_reports.json")
ATTACHMENTS_DIR = os.path.join(DATA_DIR, "bug_attachments")

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ATTACHMENTS_DIR, exist_ok=True)


class BugReport(BaseModel):
    id: str
    title: str
    description: str
    attachment_filename: Optional[str] = None
    attachment_path: Optional[str] = None
    status: str = "new"  # new, in_progress, resolved, closed
    created_at: str
    updated_at: Optional[str] = None
    notes: Optional[str] = None


class BugReportUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


def load_bug_reports() -> List[dict]:
    """Load bug reports from JSON file"""
    if os.path.exists(BUG_REPORTS_FILE):
        try:
            with open(BUG_REPORTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []


def save_bug_reports(reports: List[dict]):
    """Save bug reports to JSON file"""
    with open(BUG_REPORTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(reports, f, ensure_ascii=False, indent=2)


@router.post("")
async def create_bug_report(
    title: str = Form(...),
    description: str = Form(...),
    attachment: Optional[UploadFile] = File(None)
):
    """Create a new bug report with optional attachment"""
    report_id = str(uuid.uuid4())[:8]
    
    attachment_filename = None
    attachment_path = None
    
    # Handle file upload
    if attachment:
        # Validate file size (100MB max)
        content = await attachment.read()
        if len(content) > 100 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 100MB)")
        
        # Save file
        ext = os.path.splitext(attachment.filename)[1]
        safe_filename = f"{report_id}{ext}"
        attachment_path = os.path.join(ATTACHMENTS_DIR, safe_filename)
        
        with open(attachment_path, 'wb') as f:
            f.write(content)
        
        attachment_filename = attachment.filename
    
    # Create report
    report = {
        "id": report_id,
        "title": title,
        "description": description,
        "attachment_filename": attachment_filename,
        "attachment_path": attachment_path,
        "status": "new",
        "created_at": datetime.now().isoformat(),
        "updated_at": None,
        "notes": None
    }
    
    # Save
    reports = load_bug_reports()
    reports.insert(0, report)  # Add to beginning
    save_bug_reports(reports)
    
    print(f"[BugReport] Created: {report_id} - {title}")
    
    return {"success": True, "id": report_id, "message": "Bug report submitted successfully"}


@router.get("")
async def list_bug_reports(
    status: Optional[str] = None,
    limit: int = 50
):
    """List all bug reports, optionally filtered by status"""
    reports = load_bug_reports()
    
    if status:
        reports = [r for r in reports if r.get("status") == status]
    
    return {"reports": reports[:limit], "total": len(reports)}


@router.get("/{report_id}")
async def get_bug_report(report_id: str):
    """Get a specific bug report by ID"""
    reports = load_bug_reports()
    
    for report in reports:
        if report.get("id") == report_id:
            return report
    
    raise HTTPException(status_code=404, detail="Bug report not found")


@router.patch("/{report_id}")
async def update_bug_report(report_id: str, update: BugReportUpdate):
    """Update bug report status or notes"""
    reports = load_bug_reports()
    
    for i, report in enumerate(reports):
        if report.get("id") == report_id:
            if update.status:
                reports[i]["status"] = update.status
            if update.notes is not None:
                reports[i]["notes"] = update.notes
            reports[i]["updated_at"] = datetime.now().isoformat()
            
            save_bug_reports(reports)
            print(f"[BugReport] Updated: {report_id}")
            return reports[i]
    
    raise HTTPException(status_code=404, detail="Bug report not found")


@router.delete("/{report_id}")
async def delete_bug_report(report_id: str):
    """Delete a bug report"""
    reports = load_bug_reports()
    
    for i, report in enumerate(reports):
        if report.get("id") == report_id:
            # Delete attachment if exists
            if report.get("attachment_path") and os.path.exists(report["attachment_path"]):
                try:
                    os.remove(report["attachment_path"])
                except:
                    pass
            
            del reports[i]
            save_bug_reports(reports)
            print(f"[BugReport] Deleted: {report_id}")
            return {"success": True, "message": "Bug report deleted"}
    
    raise HTTPException(status_code=404, detail="Bug report not found")


@router.get("/{report_id}/attachment")
async def get_attachment(report_id: str):
    """Get attachment file for a bug report"""
    from fastapi.responses import FileResponse
    
    reports = load_bug_reports()
    
    for report in reports:
        if report.get("id") == report_id:
            if report.get("attachment_path") and os.path.exists(report["attachment_path"]):
                return FileResponse(
                    report["attachment_path"],
                    filename=report.get("attachment_filename", "attachment")
                )
            raise HTTPException(status_code=404, detail="No attachment found")
    
    raise HTTPException(status_code=404, detail="Bug report not found")


# Legacy endpoint for compatibility with existing client
@router.post("/submit")
async def submit_bug_report_legacy(
    title: str = Form(...),
    description: str = Form(...),
    attachment: Optional[UploadFile] = File(None)
):
    """Legacy endpoint - redirects to create_bug_report"""
    return await create_bug_report(title, description, attachment)
