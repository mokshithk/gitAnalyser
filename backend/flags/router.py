from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import Analysis, Flag, SimilarityMatch, User
from backend.auth.dependencies import get_current_user
from backend.flags.engine import MANDATORY_DISCLAIMER, SYSTEM_LIMITATIONS
from backend.flags.pdf_export import generate_pdf_report

router = APIRouter(prefix="/analyses", tags=["flags_and_reports"])

class FlagUpdate(BaseModel):
    review_status: str # 'open', 'reviewed', 'dismissed'
    note: Optional[str] = None

class FlagResponse(BaseModel):
    id: int
    analysis_id: int
    type: str
    severity: str
    confidence: float
    title: str
    evidence: Optional[dict[str, Any]] = None
    review_status: str
    note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ReportResponse(BaseModel):
    analysis_id: int
    source: str
    input_type: str
    mode: str
    status: str
    review_priority: str
    disclaimer: str
    limitations: list[dict[str, str]]
    flags: List[FlagResponse]
    matches_count: int
    commit_metrics: Optional[dict[str, Any]] = None

@router.get("/{analysis_id}/flags", response_model=List[FlagResponse])
def get_analysis_flags(
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

    flags = db.query(Flag).filter(Flag.analysis_id == analysis_id).order_by(
        Flag.severity.desc(), Flag.id.asc()
    ).all()
    return flags

@router.patch("/{analysis_id}/flags/{flag_id}", response_model=FlagResponse)
def update_flag_review(
    analysis_id: int,
    flag_id: int,
    payload: FlagUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    flag = db.query(Flag).filter(
        Flag.id == flag_id,
        Flag.analysis_id == analysis_id
    ).first()
    if not flag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")

    if payload.review_status not in ("open", "reviewed", "dismissed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid review status")

    flag.review_status = payload.review_status
    if payload.note is not None:
        flag.note = payload.note
    db.commit()
    db.refresh(flag)
    return flag

@router.get("/{analysis_id}/report", response_model=ReportResponse)
def get_full_report(
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

    flags = db.query(Flag).filter(Flag.analysis_id == analysis_id).all()
    matches_count = db.query(SimilarityMatch).filter(SimilarityMatch.analysis_id == analysis_id).count()

    opts = analysis.options or {}
    priority = opts.get("review_priority", "CLEAN")

    return ReportResponse(
        analysis_id=analysis.id,
        source=analysis.source,
        input_type=analysis.input_type,
        mode=analysis.mode,
        status=analysis.status,
        review_priority=priority,
        disclaimer=MANDATORY_DISCLAIMER,
        limitations=SYSTEM_LIMITATIONS,
        flags=[FlagResponse.model_validate(f) for f in flags],
        matches_count=matches_count,
        commit_metrics=opts.get("commit_metrics"),
    )

@router.get("/{analysis_id}/report/pdf")
def download_pdf_report(
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

    flags = db.query(Flag).filter(Flag.analysis_id == analysis_id).all()
    matches = db.query(SimilarityMatch).filter(SimilarityMatch.analysis_id == analysis_id).all()
    opts = analysis.options or {}
    commit_metrics = opts.get("commit_metrics") or {}

    pdf_bytes = generate_pdf_report(analysis, flags, matches, commit_metrics)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=CodeProvenance_Report_{analysis.id}.pdf"
        }
    )
