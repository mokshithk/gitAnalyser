from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from datetime import datetime

from backend.db.database import get_db
from backend.db.models import Analysis, Commit, User
from backend.auth.dependencies import get_current_user

router = APIRouter(prefix="/analyses", tags=["commits"])

class CommitResponse(BaseModel):
    id: int
    sha: str
    author_name: str
    author_email: str
    author_date: datetime
    commit_date: datetime
    lines_added: int
    lines_deleted: int
    files_changed: int
    message: str

    model_config = ConfigDict(from_attributes=True)

@router.get("/{analysis_id}/commits", response_model=List[CommitResponse])
def get_analysis_commits(
    analysis_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    commits = db.query(Commit).filter(
        Commit.analysis_id == analysis_id
    ).order_by(Commit.commit_date.asc()).offset(offset).limit(limit).all()
    
    return commits

@router.get("/{analysis_id}/commit-metrics")
def get_analysis_commit_metrics(
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

    opts = analysis.options or {}
    metrics = opts.get("commit_metrics")
    if not metrics:
        return {"status": analysis.status, "mode": analysis.mode, "metrics": None}

    return {
        "status": analysis.status,
        "mode": analysis.mode,
        "metrics": metrics
    }
