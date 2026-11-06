from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from backend.db.database import get_db
from backend.db.models import Analysis, SimilarityMatch, User
from backend.auth.dependencies import get_current_user

router = APIRouter(prefix="/analyses", tags=["similarity"])

class SimilarityMatchResponse(BaseModel):
    id: int
    analysis_id: int
    target_type: str
    target_ref: str
    score: float
    details: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

@router.get("/{analysis_id}/matches", response_model=List[SimilarityMatchResponse])
def get_analysis_similarity_matches(
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

    matches = db.query(SimilarityMatch).filter(
        SimilarityMatch.analysis_id == analysis_id
    ).order_by(SimilarityMatch.score.desc()).all()

    return matches

@router.get("/{analysis_id}/matches/{match_id}", response_model=SimilarityMatchResponse)
def get_single_match(
    analysis_id: int,
    match_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    match = db.query(SimilarityMatch).filter(
        SimilarityMatch.id == match_id,
        SimilarityMatch.analysis_id == analysis_id
    ).first()
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Similarity match not found")

    return match
