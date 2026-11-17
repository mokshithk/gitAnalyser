import os
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.database import SessionLocal
from backend.db.models import Analysis
from backend.ingestion.safety import safe_rmtree

def cleanup_expired_analyses(
    db: Session,
    retention_days: int | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """
    Purges analyses older than retention_days (defaults to settings.RETENTION_DAYS).
    Cascades deletions in the database and cleans up any residual workdir artifacts.
    """
    days = retention_days if retention_days is not None else settings.RETENTION_DAYS
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    expired_analyses = db.query(Analysis).filter(Analysis.created_at < cutoff).all()
    count = len(expired_analyses)
    cleaned_workdirs = 0

    workdir_base = Path(settings.WORKDIR)

    for a in expired_analyses:
        workdir_path = workdir_base / str(a.id)
        if workdir_path.exists():
            if not dry_run:
                safe_rmtree(workdir_path)
            cleaned_workdirs += 1

        if not dry_run:
            db.delete(a)

    if not dry_run and count > 0:
        db.commit()

    return {
        "expired_analyses_found": count,
        "analyses_deleted": 0 if dry_run else count,
        "workdirs_cleaned": cleaned_workdirs,
        "retention_days": days,
        "dry_run": dry_run,
    }

def main():
    parser = argparse.ArgumentParser(description="CodeProvenance retention cleanup utility")
    parser.add_argument("--days", type=int, default=None, help="Retention period in days (defaults to config)")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be purged without deleting")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        results = cleanup_expired_analyses(db, retention_days=args.days, dry_run=args.dry_run)
        mode_str = "[DRY RUN] " if results["dry_run"] else ""
        print(f"{mode_str}Retention Cleanup (>{results['retention_days']} days):")
        print(f" - Analyses purged: {results['analyses_deleted']} (found: {results['expired_analyses_found']})")
        print(f" - Residual workdirs cleaned: {results['workdirs_cleaned']}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
