from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import logging

from backend.db.database import SessionLocal
from backend.db.models import Analysis
from backend.ingestion.inspector import (
    get_analysis_workdir,
    cleanup_analysis_workdir,
    detect_git_mode,
    detect_languages,
)
from backend.ingestion.git_cloner import clone_repository

logger = logging.getLogger(__name__)

# In-process worker pool (No Celery, No Redis as requested)
executor = ThreadPoolExecutor(max_workers=3)

def run_pipeline(analysis_id: int):
    """Executes the full provenance and similarity pipeline in background worker."""
    db = SessionLocal()
    try:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            return

        workdir = get_analysis_workdir(analysis_id)

        # 1. Ingestion / Cloning if input is git_url
        if analysis.input_type == "git_url":
            analysis.status = "cloning"
            db.commit()

            options = analysis.options or {}
            access_token = options.get("access_token")
            clone_repository(
                repo_url=analysis.source,
                target_dir=workdir,
                access_token=access_token,
            )

        # 2. Inspect git mode & languages
        mode = detect_git_mode(workdir)
        analysis.mode = mode
        lang_info = detect_languages(workdir)

        opts = dict(analysis.options or {})
        opts["languages"] = lang_info
        analysis.options = opts
        analysis.status = "parsing"
        db.commit()

        # 3. Commit analysis (if full mode)
        if mode == "full":
            from backend.analysis.commits import analyze_commit_history
            analyze_commit_history(analysis_id=analysis.id, repo_dir=workdir, db=db, options=opts)

        # 4. Code similarity (Python AST)
        analysis.status = "comparing"
        db.commit()
        from backend.similarity.engine import run_similarity_analysis
        run_similarity_analysis(analysis_id=analysis.id, repo_dir=workdir, db=db, options=opts)

        # 5. Rule-based Flags & Triage
        from backend.flags.engine import generate_analysis_flags
        generate_analysis_flags(analysis_id=analysis.id, db=db)

        # 6. Complete
        analysis.status = "done"
        analysis.error_message = None
        analysis.finished_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        logger.exception(f"Pipeline failed for analysis {analysis_id}: {e}")
        db.rollback()
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if analysis:
            analysis.status = "failed"
            analysis.error_message = str(e)
            analysis.finished_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        # Cleanup temporary files
        try:
            cleanup_analysis_workdir(analysis_id)
        except Exception:
            pass
        db.close()

def enqueue_analysis(analysis_id: int):
    executor.submit(run_pipeline, analysis_id)
