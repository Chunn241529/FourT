from .routers import web_home
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import (
    license,
    features,
    payment,
    sepay,
    trial,
    update,
    midi,
    skills,
    combos,
    download,
    security,
    bug_reports,
    stats,
    releases,
    youtube,
    auth,  # Community Auth
    community,  # Community MIDI Platform
    community_web,  # Community Web Pages
)
from backend.middleware.rate_limiter import RateLimitMiddleware

app = FastAPI(
    title="FourT Helper Backend",
    description="Backend API for FourT Helper application",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Rate Limiting middleware
app.add_middleware(RateLimitMiddleware)

# Mount static files for updates (dist folder)
from fastapi.staticfiles import StaticFiles
import os

# Get absolute path to dist directory
# backend/main.py -> backend -> root
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
dist_dir = os.path.join(root_dir, "dist")

# Ensure dist directory exists
if not os.path.exists(dist_dir):
    os.makedirs(dist_dir)

print(f"[Server] Static files directory: {dist_dir}")
print(f"[Server] dist.zip exists: {os.path.exists(os.path.join(dist_dir, 'dist.zip'))}")


@app.middleware("http")
async def log_requests(request, call_next):
    print(f"[Server] Request: {request.method} {request.url}")
    response = await call_next(request)
    print(f"[Server] Response status: {response.status_code}")
    return response


# Mount static files AFTER middleware to ensure proper logging
app.mount("/static", StaticFiles(directory=dist_dir), name="static")

# Mount addons directory for serving addon files (tesseract-portable.zip, etc.)
addons_dir = os.path.join(root_dir, "addons")
if not os.path.exists(addons_dir):
    os.makedirs(addons_dir)
print(f"[Server] Addons directory: {addons_dir}")

app.mount("/addons", StaticFiles(directory=addons_dir), name="addons")

# Include routers
app.include_router(license.router)
app.include_router(features.router)
app.include_router(payment.router)
app.include_router(sepay.router)
app.include_router(trial.router)
app.include_router(update.router)
app.include_router(midi.router)
app.include_router(skills.router)
app.include_router(combos.router)
app.include_router(download.router, prefix="/download", tags=["download"])
app.include_router(security.router)
app.include_router(bug_reports.router)
app.include_router(stats.router)
app.include_router(releases.router)
app.include_router(youtube.router)
app.include_router(auth.router)  # Community Auth
app.include_router(community.router)  # Community MIDI Platform

# Community Web Pages - accessible at /community/* or midi.fourt.io.vn/*
app.include_router(community_web.router, prefix="/community", tags=["community-web"])


# REMOVED OLD ROOT ROUTE: @app.get("/")
# async def root():
#     return {"message": "FourT Helper Backend is running"}
#
@app.get("/health")
async def health_check():
    """Health check endpoint for URL discovery"""
    return {"status": "ok", "service": "FourT Helper Backend"}


# Added by FourT Helper
app.include_router(web_home.router)


# Global 404 Handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import FileResponse


@app.exception_handler(404)
async def custom_404_handler(request, exc):
    """Serve custom 404 page"""
    # Try to serve from development web directory first
    web_404 = os.path.join(root_dir, "web", "community", "404.html")
    if os.path.exists(web_404):
        return FileResponse(web_404)

    # Fallback to dist directory
    dist_404 = os.path.join(dist_dir, "community", "404.html")
    if os.path.exists(dist_404):
        return FileResponse(dist_404)

    return {"detail": "Not Found"}
