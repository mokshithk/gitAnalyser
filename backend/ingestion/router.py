import os
import shutil
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from sqlalchemy.orm import Session
from pathlib import Path

from backend.config import settings
from backend.db.database import get_db
from backend.db.models import User, Analysis
from backend.auth.dependencies import get_current_user, enforce_scan_rate_limit
from backend.ingestion.schemas import GitUrlAnalysisRequest, AnalysisItemResponse
from backend.ingestion.safety import validate_and_extract_zip, safe_rmtree
from backend.ingestion.inspector import get_analysis_workdir
from backend.ingestion.worker import enqueue_analysis

router = APIRouter(prefix="/analyses", tags=["analyses"])

@router.post("/git-url", response_model=AnalysisItemResponse, status_code=status.HTTP_201_CREATED)
def submit_git_url(
    req: GitUrlAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_scan_rate_limit(current_user, db)

    options = {}
    if req.start_date:
        options["start_date"] = req.start_date.isoformat()
    if req.end_date:
        options["end_date"] = req.end_date.isoformat()
    if req.starter_repo_url:
        options["starter_repo_url"] = req.starter_repo_url.strip()
    if req.access_token:
        # One-time use token, passed to worker in memory options, not stored in source
        options["access_token"] = req.access_token.strip()

    analysis = Analysis(
        user_id=current_user.id,
        input_type="git_url",
        source=req.repo_url.strip(),
        mode="full",
        status="queued",
        options=options,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    enqueue_analysis(analysis.id)
    return analysis

@router.post("/zip", response_model=AnalysisItemResponse, status_code=status.HTTP_201_CREATED)
async def submit_zip(
    file: UploadFile = File(...),
    starter_repo_url: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    enforce_scan_rate_limit(current_user, db)

    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a .zip archive"
        )

    # Initial Analysis record
    options = {}
    if starter_repo_url:
        options["starter_repo_url"] = starter_repo_url.strip()

    analysis = Analysis(
        user_id=current_user.id,
        input_type="zip",
        source=file.filename,
        mode="full", # will be verified after extraction
        status="queued",
        options=options,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Save to temp on D:
    tmp_dir = Path(settings.WORKDIR) / f"temp_{analysis.id}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    temp_zip = tmp_dir / "uploaded.zip"

    try:
        max_zip_bytes = settings.MAX_ZIP_SIZE_MB * 1024 * 1024
        bytes_read = 0
        with open(temp_zip, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                bytes_read += len(chunk)
                if bytes_read > max_zip_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Zip archive exceeds maximum size limit of {settings.MAX_ZIP_SIZE_MB} MB"
                    )
                buffer.write(chunk)

        # Extract safely into target workdir
        target_workdir = get_analysis_workdir(analysis.id)
        max_uncompressed_bytes = settings.MAX_REPO_SIZE_MB * 1024 * 1024
        validate_and_extract_zip(
            zip_path=temp_zip,
            target_dir=target_workdir,
            max_uncompressed_bytes=max_uncompressed_bytes,
        )

        enqueue_analysis(analysis.id)
        return analysis

    except HTTPException:
        safe_rmtree(tmp_dir)
        db.delete(analysis)
        db.commit()
        raise
    except Exception as e:
        safe_rmtree(tmp_dir)
        analysis.status = "failed"
        analysis.error_message = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process zip archive: {str(e)}"
        )
    finally:
        safe_rmtree(tmp_dir)

@router.get("", response_model=List[AnalysisItemResponse])
def list_analyses(
    status_filter: Optional[str] = Query(None, alias="status"),
    mode_filter: Optional[str] = Query(None, alias="mode"),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Analysis).filter(Analysis.user_id == current_user.id)
    if status_filter:
        query = query.filter(Analysis.status == status_filter)
    if mode_filter:
        query = query.filter(Analysis.mode == mode_filter)
    if search:
        query = query.filter(Analysis.source.ilike(f"%{search}%"))

    analyses = query.order_by(Analysis.created_at.desc()).all()
    return analyses

@router.get("/{analysis_id}", response_model=AnalysisItemResponse)
def get_analysis_status(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis

@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    
    db.delete(analysis)
    db.commit()
    return None
