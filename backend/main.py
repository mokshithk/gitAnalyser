from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from backend.config import settings
from backend.db.database import engine
from backend.auth.router import router as auth_router
from backend.ingestion.router import router as ingestion_router
from backend.analysis.router import router as analysis_router

app = FastAPI(
    title="CodeProvenance API",
    description="Evidence-based code provenance, commit pace triage, and structural similarity analysis.",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router, prefix="/api")
app.include_router(ingestion_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")

@app.get("/api/health")
def healthcheck():
    db_status = "healthy"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "online",
        "app": "CodeProvenance",
        "database": db_status,
        "limits": {
            "max_repo_size_mb": settings.MAX_REPO_SIZE_MB,
            "max_zip_size_mb": settings.MAX_ZIP_SIZE_MB,
            "clone_timeout_seconds": settings.CLONE_TIMEOUT_SECONDS,
            "scans_per_user_per_hour": settings.SCANS_PER_USER_PER_HOUR,
        }
    }
