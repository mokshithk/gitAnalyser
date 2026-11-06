from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="user")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    analyses = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")

class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    input_type = Column(String(50), nullable=False) # 'git_url', 'zip', 'batch'
    source = Column(String(512), nullable=False)
    mode = Column(String(50), nullable=False, default="full") # 'full', 'similarity_only'
    status = Column(String(50), nullable=False, default="queued") # 'queued', 'cloning', 'parsing', 'comparing', 'done', 'failed'
    error_message = Column(Text, nullable=True)
    options = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="analyses")
    commits = relationship("Commit", back_populates="analysis", cascade="all, delete-orphan")
    matches = relationship("SimilarityMatch", back_populates="analysis", cascade="all, delete-orphan")
    flags = relationship("Flag", back_populates="analysis", cascade="all, delete-orphan")

class Commit(Base):
    __tablename__ = "commits"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    sha = Column(String(64), nullable=False)
    author_name = Column(String(255), nullable=False)
    author_email = Column(String(255), nullable=False)
    author_date = Column(DateTime, nullable=False)
    commit_date = Column(DateTime, nullable=False)
    lines_added = Column(Integer, nullable=False, default=0)
    lines_deleted = Column(Integer, nullable=False, default=0)
    files_changed = Column(Integer, nullable=False, default=0)
    message = Column(Text, nullable=False)

    analysis = relationship("Analysis", back_populates="commits")

class SimilarityMatch(Base):
    __tablename__ = "similarity_matches"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type = Column(String(50), nullable=False) # 'corpus', 'previous_analysis', 'batch_peer'
    target_ref = Column(String(512), nullable=False)
    score = Column(Float, nullable=False)
    details = Column(JSON, nullable=True)

    analysis = relationship("Analysis", back_populates="matches")

class Flag(Base):
    __tablename__ = "flags"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=False) # 'low', 'medium', 'high'
    confidence = Column(Float, nullable=False, default=1.0)
    title = Column(String(255), nullable=False)
    evidence = Column(JSON, nullable=True)
    review_status = Column(String(50), nullable=False, default="open") # 'open', 'reviewed', 'dismissed'
    note = Column(Text, nullable=True)

    analysis = relationship("Analysis", back_populates="flags")

class ReferenceCorpus(Base):
    __tablename__ = "reference_corpus"

    id = Column(Integer, primary_key=True, index=True)
    repo_url = Column(String(512), unique=True, nullable=False)
    language = Column(String(50), nullable=False, default="python")
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
