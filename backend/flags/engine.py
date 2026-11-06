from typing import Any, List, Dict
from sqlalchemy.orm import Session

from backend.db.models import Analysis, Flag, SimilarityMatch, Commit

MANDATORY_DISCLAIMER = (
    "CodeProvenance produces evidentiary signals and triage metrics intended exclusively for human review. "
    "These findings do NOT prove cheating, plagiarism, or malicious intent. Authentic development workflows "
    "(such as squashed commits, external prototyping, or offline coding) can trigger similar anomalies."
)

SYSTEM_LIMITATIONS = [
    {
        "title": "Thin or Squashed Git History",
        "description": "Repositories with few commits or squashed feature branches lack temporal resolution, obscuring iterative pace."
    },
    {
        "title": "No Git Metadata in Zip Uploads",
        "description": "Source code archives without a .git directory operate strictly in similarity-only mode with zero commit telemetry."
    },
    {
        "title": "Reference Corpus Boundedness",
        "description": "Code similarity detection reflects only the indexed reference corpus and previously analyzed peer projects in the database."
    },
    {
        "title": "Timestamp Forgeability",
        "description": "Git commit timestamps and author dates can be altered via environment variables (GIT_COMMITTER_DATE) or rebase scripting."
    },
    {
        "title": "Language Support Scope",
        "description": "Structural AST fingerprinting currently normalizes Python syntax. Non-Python files receive line-level triage."
    }
]

def generate_analysis_flags(analysis_id: int, db: Session) -> list[Flag]:
    """
    Evaluates rule-based signals from commit telemetry and similarity matches.
    Creates Flag records with explainable evidence and interview follow-up questions.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        return []

    # Clear any previous flags if re-running
    db.query(Flag).filter(Flag.analysis_id == analysis_id).delete()

    opts = analysis.options or {}
    commit_metrics = opts.get("commit_metrics") or {}
    matches = db.query(SimilarityMatch).filter(SimilarityMatch.analysis_id == analysis_id).all()

    new_flags: list[Flag] = []

    # 1. Thin history signal
    if commit_metrics.get("thin_history"):
        f = Flag(
            analysis_id=analysis_id,
            type="THIN_HISTORY",
            severity="low",
            confidence=1.0,
            title="Insufficient Commit History",
            evidence={
                "message": "insufficient history to analyze",
                "commits_count": commit_metrics.get("total_commits", 0),
                "questions": [
                    "How was this repository populated? Was work conducted in a separate branch, local directory, or another version control system?"
                ]
            },
            review_status="open",
        )
        new_flags.append(f)

    # 2. Large share in a single commit
    large_share_commits = commit_metrics.get("large_share_commits") or []
    for lsc in large_share_commits:
        pct = lsc.get("share_percentage", 0)
        sev = "high" if pct >= 65.0 else "medium"
        f = Flag(
            analysis_id=analysis_id,
            type="SINGLE_COMMIT_BULK_ADD",
            severity=sev,
            confidence=0.95,
            title=f"{pct}% of codebase added in single commit",
            evidence={
                "sha": lsc.get("sha"),
                "lines_added": lsc.get("lines_added"),
                "share_percentage": pct,
                "commit_message": lsc.get("message"),
                "questions": [
                    f"Explain the design and implementation steps for commit {lsc.get('sha')}. Why was such a substantial proportion committed in a single transaction?",
                    "Can you demonstrate how this specific module connects with the rest of your application architecture?"
                ]
            },
            review_status="open",
        )
        new_flags.append(f)

    # 3. Burst pace anomaly ("large change in a short time")
    bursts = commit_metrics.get("bursts") or []
    for b in bursts:
        f = Flag(
            analysis_id=analysis_id,
            type="BURST_PACE_ANOMALY",
            severity="high",
            confidence=0.90,
            title="Large change in a short time",
            evidence={
                "sha": b.get("sha"),
                "lines_added": b.get("lines_added"),
                "seconds_since_prev": b.get("seconds_since_prev"),
                "description": b.get("description"),
                "questions": [
                    f"Commit {b.get('sha')} introduced {b.get('lines_added')} lines within {b.get('seconds_since_prev')}s of previous commit. Was this code copied or ported from an external reference or drafted offline?",
                    "Walk us through the logic of this function or class line by line."
                ]
            },
            review_status="open",
        )
        new_flags.append(f)

    # 4. Scripted / Regular intervals
    if commit_metrics.get("regular_interval_flag"):
        std_dev = commit_metrics.get("regular_interval_std_dev", 0.0)
        f = Flag(
            analysis_id=analysis_id,
            type="SCRIPTED_REGULAR_PACE",
            severity="high",
            confidence=0.88,
            title="Suspiciously regular commit pace",
            evidence={
                "interval_std_dev_seconds": std_dev,
                "description": f"Commit intervals have an unnaturally low standard deviation ({std_dev}s), characteristic of automated scripts.",
                "questions": [
                    "Were these commits staged or committed using an automation script or batch replay tool?"
                ]
            },
            review_status="open",
        )
        new_flags.append(f)

    # 5. Timestamp anomalies (Author vs Committer date mismatch)
    ts_mismatches = commit_metrics.get("timestamp_mismatches") or []
    if len(ts_mismatches) >= 1:
        worst_mismatch = max(ts_mismatches, key=lambda x: x.get("diff_hours", 0))
        f = Flag(
            analysis_id=analysis_id,
            type="TIMESTAMP_MISMATCH",
            severity="medium",
            confidence=0.85,
            title="Author and commit timestamp discrepancy",
            evidence={
                "mismatch_count": len(ts_mismatches),
                "worst_mismatch_sha": worst_mismatch.get("sha"),
                "diff_hours": worst_mismatch.get("diff_hours"),
                "questions": [
                    "Was git rebase, cherry-pick, git commit --amend, or git format-patch applied during development?"
                ]
            },
            review_status="open",
        )
        new_flags.append(f)

    # 6. Last-minute rush
    rush = commit_metrics.get("rush") or {}
    if rush.get("rush_commit_percentage", 0) >= 60.0 and commit_metrics.get("total_commits", 0) > 4:
        f = Flag(
            analysis_id=analysis_id,
            type="LAST_MINUTE_RUSH",
            severity="medium",
            confidence=0.80,
            title="Last-minute commit rush",
            evidence={
                "rush_commit_percentage": rush.get("rush_commit_percentage"),
                "rush_lines_percentage": rush.get("rush_lines_percentage"),
                "questions": [
                    "What caused the heavy clustering of commits immediately prior to completion?"
                ]
            },
            review_status="open",
        )
        new_flags.append(f)

    # 7. Generic or mismatched author identity
    author_metrics = commit_metrics.get("author_metrics") or {}
    if author_metrics.get("has_generic_author"):
        f = Flag(
            analysis_id=analysis_id,
            type="GENERIC_AUTHOR_NAME",
            severity="low",
            confidence=0.95,
            title="Generic author identity detected",
            evidence={
                "authors": commit_metrics.get("authors"),
                "questions": [
                    "Why was git configured with a generic username (e.g. root, admin, user) on the development machine?"
                ]
            },
            review_status="open",
        )
        new_flags.append(f)

    # 8. High AST similarity matches
    for m in matches:
        if m.score >= 0.70:
            sev = "high" if m.score >= 0.85 else "medium"
            details = m.details or {}
            matched_count = details.get("matched_functions_count", 0)
            f = Flag(
                analysis_id=analysis_id,
                type="HIGH_AST_SIMILARITY",
                severity=sev,
                confidence=0.92,
                title=f"Structural AST match ({int(m.score * 100)}%) with {m.target_type}",
                evidence={
                    "target_ref": m.target_ref,
                    "target_type": m.target_type,
                    "score": m.score,
                    "matched_functions_count": matched_count,
                    "questions": [
                        f"Target reference '{m.target_ref}' shares {matched_count} structurally identical or near-identical functions. Did you consult or base your code on this repository?",
                        "Describe the algorithm used in these matched functions without referencing external resources."
                    ]
                },
                review_status="open",
            )
            new_flags.append(f)

    db.add_all(new_flags)
    db.commit()

    # Determine Review Priority (Strict rule: NO single authenticity score!)
    high_count = sum(1 for f in new_flags if f.severity == "high")
    med_count = sum(1 for f in new_flags if f.severity == "medium")
    
    if high_count >= 1 or med_count >= 3:
        priority = "HIGH"
    elif med_count >= 1:
        priority = "MEDIUM"
    elif len(new_flags) >= 1:
        priority = "LOW"
    else:
        priority = "CLEAN"

    opts["review_priority"] = priority
    analysis.options = opts
    db.commit()

    return new_flags
