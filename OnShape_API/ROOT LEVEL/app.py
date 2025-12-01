"""
OnShape BOM Manager - Refactored FastAPI Application
Manages Bills of Materials, Bounding Boxes, and Properties in OnShape
"""

from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import RedirectResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from routes import auth, documents, bom, properties, user
from database import Base, engine, init_db
from config import settings

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="OnShape BOM Manager",
    description="Manage OnShape BOMs and bounding boxes",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# ============= MAIN PAGE =============

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve main HTML page"""
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Frontend files not found</h1>"

# ============= HEALTH CHECK =============

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment"""
    return {"status": "healthy", "version": "2.0.0"}

# ============= INCLUDE ROUTERS =============

app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(bom.router, prefix="/api/bom", tags=["bom"])
app.include_router(properties.router, prefix="/api/properties", tags=["properties"])

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)