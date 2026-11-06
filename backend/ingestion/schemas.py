from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, HttpUrl

class GitUrlAnalysisRequest(BaseModel):
    repo_url: str
    access_token: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    starter_repo_url: Optional[str] = None

class AnalysisItemResponse(BaseModel):
    id: int
    user_id: int
    input_type: str
    source: str
    mode: str
    status: str
    error_message: Optional[str] = None
    options: Optional[dict[str, Any]] = None
    created_at: datetime
    finished_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
