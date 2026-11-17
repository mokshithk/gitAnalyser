import io
import csv
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
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

class PairwiseMatrixRequest(BaseModel):
    analysis_ids: Optional[List[int]] = None

class PairwiseMatrixResponse(BaseModel):
    items: List[dict[str, Any]]
    matrix: List[List[float]]
    labels: List[str]

@router.post("/pairwise-matrix", response_model=PairwiseMatrixResponse)
def get_pairwise_similarity_matrix(
    payload: Optional[PairwiseMatrixRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Analysis).filter(Analysis.user_id == current_user.id, Analysis.status == "done")
    if payload and payload.analysis_ids:
        query = query.filter(Analysis.id.in_(payload.analysis_ids))

    analyses = query.order_by(Analysis.id.asc()).limit(50).all()
    if not analyses:
        return PairwiseMatrixResponse(items=[], matrix=[], labels=[])

    ids = [a.id for a in analyses]
    labels = [f"#{a.id} {a.source.split('/')[-1] or a.source}" for a in analyses]

    # Query all matches between these analyses
    matches = db.query(SimilarityMatch).filter(
        SimilarityMatch.analysis_id.in_(ids)
    ).all()

    # Build symmetric score lookup
    score_lookup: dict[tuple[int, int], float] = {}
    for m in matches:
        src_id = m.analysis_id
        for other in analyses:
            if other.id == src_id:
                continue
            if other.source == m.target_ref or str(other.id) == str(m.target_ref):
                prev = score_lookup.get((src_id, other.id), 0.0)
                highest = max(prev, m.score)
                score_lookup[(src_id, other.id)] = highest
                score_lookup[(other.id, src_id)] = highest

    n = len(analyses)
    matrix = [[1.0 if i == j else score_lookup.get((ids[i], ids[j]), 0.0) for j in range(n)] for i in range(n)]

    items = [
        {
            "id": a.id,
            "source": a.source,
            "mode": a.mode,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in analyses
    ]

    return PairwiseMatrixResponse(items=items, matrix=matrix, labels=labels)

@router.get("/pairwise-matrix/export.csv")
def export_pairwise_similarity_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    res = get_pairwise_similarity_matrix(None, current_user, db)
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow(["Analysis"] + res.labels)
    for i, label in enumerate(res.labels):
        row = [label] + [f"{round(score * 100, 1)}%" for score in res.matrix[i]]
        writer.writerow(row)

    csv_bytes = output.getvalue().encode("utf-8")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pairwise_similarity_matrix.csv"}
    )

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
