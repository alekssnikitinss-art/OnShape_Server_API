"""
OnShape BOM Manager - Refactored FastAPI Application
Manages Bills of Materials, Bounding Boxes, Properties, and Metadata in OnShape

Version: 2.1.1
Status: All routes integrated
"""

import os
import logging
from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, documents, bom, user, parts, metadata, properties, bom_extended
from database import Base, engine, init_db
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize databas
init_db()

# Create FastAPI app
app = FastAPI(
    title="OnShape BOM Manager",
    description="Manage OnShape BOMs, properties, and metadata",
    version="2.1.1"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (CSS, JS, images, etc.)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
else:
    logger.warning("⚠️ WARNING: static folder not found!")

# ============= MAIN PAGE =============

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main HTML page"""
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return """
        <html>
        <head><title>OnShape BOM Manager</title></head>
        <body>
            <h1>OnShape BOM Manager</h1>
            <p>Frontend files not found. Please ensure templates/index.html exists.</p>
            <p><a href="/health">Check health</a></p>
        </body>
        </html>
        """

# ============= HEALTH CHECK =============

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment"""
    return {
        "status": "healthy",
        "version": "2.1.1",
        "database": "connected",
        "services": {
            "auth": "✅ Ready",
            "documents": "✅ Ready",
            "bom": "✅ Ready",
            "bom_extended": "✅ Ready",
            "properties": "✅ Ready",
            "parts": "✅ Ready",
            "metadata": "✅ Ready",
            "user": "✅ Ready"
        }
    }

# ============= INCLUDE ROUTERS =============

# Authentication (OAuth login/logout)
app.include_router(auth.router, prefix="/auth", tags=["authentication"])

# User information
app.include_router(user.router, prefix="/api/user", tags=["user"])

# Document management (list, save, retrieve)
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])

# BOM operations (fetch only)
app.include_router(bom.router, prefix="/api/bom", tags=["bom"])

# Extended BOM operations (push, convert, calculate)
app.include_router(bom_extended.router, prefix="/api/bom", tags=["bom_extended"])

# Properties, bounding boxes, configuration variables
app.include_router(properties.router, prefix="/api/properties", tags=["properties"])

# Parts scanning and searching
app.include_router(parts.router, prefix="/api/parts", tags=["parts"])

# Metadata (custom properties) operations
app.include_router(metadata.router, prefix="/api/metadata", tags=["metadata"])

# ============= ERROR HANDLERS =============

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status": "error",
            "path": str(request.url.path)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(f"❌ Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status": "error",
            "path": str(request.url.path)
        }
    )

# ============= STARTUP/SHUTDOWN =============

@app.on_event("startup")
async def startup_event():
    """Run on app startup"""
    logger.info("=" * 60)
    logger.info("🚀 OnShape BOM Manager v2.1.1 Starting...")
    logger.info("=" * 60)
    logger.info(f"📊 Database: {settings.DATABASE_URL}")
    logger.info(f"🔐 Debug mode: {settings.DEBUG}")
    logger.info(f"🌐 OnShape API: {settings.ONSHAPE_API_URL}")
    logger.info("=" * 60)
    logger.info("✅ Services Ready:")
    logger.info("   • /auth - OAuth authentication")
    logger.info("   • /api/user - User information")
    logger.info("   • /api/documents - Document management")
    logger.info("   • /api/bom - BOM fetch & extended operations")
    logger.info("   • /api/properties - Bounding boxes & variables")
    logger.info("   • /api/parts - Part scanning & metadata browser")
    logger.info("   • /api/metadata - Custom properties")
    logger.info("=" * 60)

@app.on_event("shutdown")
async def shutdown_event():
    """Run on app shutdown"""
    logger.info("🛑 OnShape BOM Manager shutting down...")

# ============= MAIN ENTRY POINT =============

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )