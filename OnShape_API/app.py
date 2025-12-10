"""
OnShape BOM Manager - Refactored FastAPI Application
Manages Bills of Materials, Bounding Boxes, Properties, and Metadata in OnShape
"""


import os
from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, documents, bom, user, parts, metadata
from database import Base, engine, init_db
from config import settings

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="OnShape BOM Manager",
    description="Manage OnShape BOMs, properties, and metadata",
    version="2.1.0"
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
    print("WARNING: static folder not found!")

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
        "version": "2.1.0",
        "database": "connected"
    }

# ============= INCLUDE ROUTERS =============

app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(bom.router, prefix="/api/bom", tags=["bom"])
app.include_router(parts.router, prefix="/api/parts", tags=["parts"])
app.include_router(metadata.router, prefix="/api/metadata", tags=["metadata"])

# ============= ERROR HANDLERS =============

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status": "error"}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    print(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status": "error"}
    )

# ============= STARTUP/SHUTDOWN =============

@app.on_event("startup")
async def startup_event():
    """Run on app startup"""
    print("🚀 OnShape BOM Manager starting...")
    print(f"📊 Database: {settings.DATABASE_URL}")
    print(f"🔐 Debug mode: {settings.DEBUG}")
    print(f"✅ Metadata service available at /api/metadata")

@app.on_event("shutdown")
async def shutdown_event():
    """Run on app shutdown"""
    print("🛑 OnShape BOM Manager shutting down...")

# ============= MAIN ENTRY POINT =============

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)