from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional
import statistics
import git
from sqlalchemy.orm import Session

from backend.db.models import Analysis, Commit

def parse_git_datetime(git_dt) -> datetime:
    """Converts a git timestamp into a timezone-aware UTC datetime."""
    if isinstance(git_dt, (int, float)):
        return datetime.fromtimestamp(git_dt, timezone.utc)
    if isinstance(git_dt, datetime):
        if git_dt.tzinfo is None:
            return git_dt.replace(tzinfo=timezone.utc)
        return git_dt.astimezone(timezone.utc)
    return datetime.now(timezone.utc)

def extract_commit_stats(commit: git.Commit) -> tuple[int, int, int]:
    """Safely extracts (lines_added, lines_deleted, files_changed) from a git commit."""
    try:
        stats = commit.stats.total
        return stats.get("insertions", 0), stats.get("deletions", 0), stats.get("files", 0)
    except Exception:
        return 0, 0, 0

def analyze_commit_history(
    analysis_id: int,
    repo_dir: str | Path,
    db: Session,
    options: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Parses full git commit history, saves commits to DB, and computes:
    - Pacing metrics (commits/day, commits/week, gaps, rush)
    - Code growth & per-commit share
    - Burst changes ("large change in a short time")
    - Timestamp anomalies (author vs commit mismatch, out-of-order, regular intervals)
    - Author identities & consistency
    - Thin history threshold (<= 3 commits)
    """
    options = options or {}
    repo = git.Repo(repo_dir)

    # Topological & chronological order: oldest to newest
    raw_commits = list(repo.iter_commits("HEAD", reverse=True))
    total_commit_count = len(raw_commits)

    if total_commit_count == 0:
        return {"thin_history": True, "message": "insufficient history to analyze"}

    parsed_commits: list[dict[str, Any]] = []
    db_commits: list[Commit] = []
    
    running_net_lines = 0
    code_growth_timeline: list[dict[str, Any]] = []
    authors_map: dict[str, dict[str, Any]] = {}
    intervals_seconds: list[float] = []

    # Filter by start_date / end_date if requested in options
    start_filter = options.get("start_date")
    end_filter = options.get("end_date")
    start_dt = datetime.fromisoformat(start_filter) if start_filter else None
    end_dt = datetime.fromisoformat(end_filter) if end_filter else None

    # First pass: collect and store commits
    for idx, c in enumerate(raw_commits):
        c_author_dt = parse_git_datetime(c.authored_date)
        c_commit_dt = parse_git_datetime(c.committed_date)

        added, deleted, files = extract_commit_stats(c)
        running_net_lines = max(0, running_net_lines + added - deleted)

        c_author_name = str(c.author.name or "Unknown").strip()
        c_author_email = str(c.author.email or "").strip().lower()

        c_info = {
            "index": idx,
            "sha": c.hexsha,
            "author_name": c_author_name,
            "author_email": c_author_email,
            "author_date": c_author_dt,
            "commit_date": c_commit_dt,
            "lines_added": added,
            "lines_deleted": deleted,
            "files_changed": files,
            "net_lines": running_net_lines,
            "message": str(c.message or "").strip(),
        }
        parsed_commits.append(c_info)

        db_commit = Commit(
            analysis_id=analysis_id,
            sha=c.hexsha,
            author_name=c_author_name,
            author_email=c_author_email,
            author_date=c_author_dt,
            commit_date=c_commit_dt,
            lines_added=added,
            lines_deleted=deleted,
            files_changed=files,
            message=str(c.message or "").strip(),
        )
        db_commits.append(db_commit)

        # Track author distribution
        author_key = f"{c_author_name} <{c_author_email}>"
        if author_key not in authors_map:
            authors_map[author_key] = {"name": c_author_name, "email": c_author_email, "commits": 0, "lines_added": 0}
        authors_map[author_key]["commits"] += 1
        authors_map[author_key]["lines_added"] += added

        # Timeline for code growth chart
        code_growth_timeline.append({
            "sha": c.hexsha[:7],
            "date": c_commit_dt.isoformat(),
            "lines_added": added,
            "lines_deleted": deleted,
            "total_lines": running_net_lines,
        })

    # Save commits to database
    db.add_all(db_commits)
    db.commit()

    # Total net lines at end of history
    final_codebase_lines = running_net_lines if running_net_lines > 0 else sum(c["lines_added"] for c in parsed_commits)
    final_codebase_lines = max(1, final_codebase_lines)

    # 1. Thin-history check
    if total_commit_count <= 3:
        metrics = {
            "thin_history": True,
            "total_commits": total_commit_count,
            "final_codebase_lines": final_codebase_lines,
            "warning": "insufficient history to analyze",
            "growth_timeline": code_growth_timeline,
            "authors": list(authors_map.values()),
        }
        _update_analysis_options(db, analysis_id, "commit_metrics", metrics)
        return metrics

    # 2. Pacing, Gaps, and Bursts
    anomalies: list[dict[str, Any]] = []
    bursts: list[dict[str, Any]] = []
    timestamp_mismatches: list[dict[str, Any]] = []
    out_of_order_count = 0
    longest_gap_seconds = 0
    longest_gap_pair: Optional[tuple[str, str]] = None

    for i in range(1, len(parsed_commits)):
        prev_c = parsed_commits[i - 1]
        curr_c = parsed_commits[i]

        diff_seconds = (curr_c["commit_date"] - prev_c["commit_date"]).total_seconds()
        if diff_seconds < 0:
            out_of_order_count += 1
        else:
            intervals_seconds.append(diff_seconds)
            if diff_seconds > longest_gap_seconds:
                longest_gap_seconds = diff_seconds
                longest_gap_pair = (prev_c["sha"][:7], curr_c["sha"][:7])

        # Burst detection: large diff (> 500 lines or > 30% final lines) in a very short time (< 15 mins)
        share_of_final = curr_c["lines_added"] / final_codebase_lines
        if (curr_c["lines_added"] >= 500 or share_of_final >= 0.30) and 0 <= diff_seconds <= 900:
            bursts.append({
                "sha": curr_c["sha"][:7],
                "lines_added": curr_c["lines_added"],
                "share_percentage": round(share_of_final * 100, 1),
                "seconds_since_prev": int(diff_seconds),
                "description": f"large change in a short time ({curr_c['lines_added']} lines in {int(diff_seconds)}s)",
            })

    # Timestamp mismatch check (Author Date vs Commit Date)
    for c in parsed_commits:
        mismatch_seconds = abs((c["commit_date"] - c["author_date"]).total_seconds())
        if mismatch_seconds > 86400: # > 24 hours
            timestamp_mismatches.append({
                "sha": c["sha"][:7],
                "author_date": c["author_date"].isoformat(),
                "commit_date": c["commit_date"].isoformat(),
                "diff_hours": round(mismatch_seconds / 3600, 1),
            })

    # Suspiciously regular intervals (scripted / fake replay)
    regular_interval_flag = False
    std_dev_seconds = 0.0
    if len(intervals_seconds) >= 6:
        # Exclude extreme outliers when checking for scripted intervals
        filtered_intervals = [s for s in intervals_seconds if 5 <= s <= 7200]
        if len(filtered_intervals) >= 6:
            std_dev_seconds = statistics.stdev(filtered_intervals)
            # If standard deviation is extremely low (e.g. commits always 60s or 120s apart)
            if std_dev_seconds < 15.0 and statistics.mean(filtered_intervals) > 10:
                regular_interval_flag = True

    # 3. Share of final codebase added by each commit
    large_share_commits: list[dict[str, Any]] = []
    for c in parsed_commits:
        share = c["lines_added"] / final_codebase_lines
        if share >= 0.40 and c["lines_added"] > 150: # added > 40% of codebase in single commit
            large_share_commits.append({
                "sha": c["sha"][:7],
                "lines_added": c["lines_added"],
                "share_percentage": round(share * 100, 1),
                "message": c["message"][:80],
            })

    # 4. Last-minute rush indicator (commits within 48h of final commit or target end_date)
    final_dt = end_dt or parsed_commits[-1]["commit_date"]
    rush_threshold_dt = final_dt - timedelta(hours=48)
    rush_commits = [c for c in parsed_commits if c["commit_date"] >= rush_threshold_dt]
    rush_lines = sum(c["lines_added"] for c in rush_commits)
    rush_commit_percentage = round((len(rush_commits) / total_commit_count) * 100, 1)
    rush_lines_percentage = round((rush_lines / max(1, sum(c['lines_added'] for c in parsed_commits))) * 100, 1)

    # 5. Activity Heatmap matrix (Day of week 0..6 x Hour of day 0..23)
    # 0 = Monday, 6 = Sunday
    heatmap_matrix = [[0 for _ in range(24)] for _ in range(7)]
    for c in parsed_commits:
        w_day = c["commit_date"].weekday()
        hour = c["commit_date"].hour
        heatmap_matrix[w_day][hour] += 1

    # 6. Author analysis
    distinct_names = {c["author_name"] for c in parsed_commits}
    distinct_emails = {c["author_email"] for c in parsed_commits}
    generic_names = {"root", "admin", "user", "administrator", "ubuntu", "test", "demo"}
    has_generic_author = any(name.lower() in generic_names for name in distinct_names)

    commit_metrics = {
        "thin_history": False,
        "total_commits": total_commit_count,
        "final_codebase_lines": final_codebase_lines,
        "first_commit_date": parsed_commits[0]["commit_date"].isoformat(),
        "last_commit_date": parsed_commits[-1]["commit_date"].isoformat(),
        "longest_gap_days": round(longest_gap_seconds / 86400, 1),
        "longest_gap_pair": longest_gap_pair,
        "bursts": bursts,
        "large_share_commits": large_share_commits,
        "timestamp_mismatches": timestamp_mismatches,
        "out_of_order_count": out_of_order_count,
        "regular_interval_flag": regular_interval_flag,
        "regular_interval_std_dev": round(std_dev_seconds, 2),
        "rush": {
            "rush_commits_count": len(rush_commits),
            "rush_commit_percentage": rush_commit_percentage,
            "rush_lines_percentage": rush_lines_percentage,
        },
        "authors": list(authors_map.values()),
        "author_metrics": {
            "distinct_names_count": len(distinct_names),
            "distinct_emails_count": len(distinct_emails),
            "has_generic_author": has_generic_author,
        },
        "heatmap": heatmap_matrix,
        "growth_timeline": code_growth_timeline,
    }

    _update_analysis_options(db, analysis_id, "commit_metrics", commit_metrics)
    return commit_metrics

def _update_analysis_options(db: Session, analysis_id: int, key: str, value: Any):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if analysis:
        opts = dict(analysis.options or {})
        opts[key] = value
        analysis.options = opts
        db.commit()
