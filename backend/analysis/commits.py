from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional
import fnmatch
import statistics
import git
from sqlalchemy.orm import Session

from backend.config import settings
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

def is_ignored_file(fpath: str, insertions: int) -> tuple[bool, str]:
    """
    Checks if a file path belongs to ignored directories, lockfiles, minified files,
    media/fonts/binaries, or large data files exceeding configured line threshold.
    Returns (is_ignored, reason).
    """
    normalized = fpath.replace("\\", "/").strip("/")
    parts = normalized.split("/")
    filename = parts[-1].lower()

    # Check directory components
    ignored_dirs = [d.lower() for d in getattr(settings, "IGNORED_DIRS", [])]
    for dir_part in parts[:-1]:
        if dir_part.lower() in ignored_dirs:
            return True, f"ignored directory: {dir_part}"

    # Check filename patterns (e.g. *.lock, package-lock.json, *.min.js, *.map)
    ignored_patterns = getattr(settings, "IGNORED_FILE_PATTERNS", [])
    for pat in ignored_patterns:
        if fnmatch.fnmatch(filename, pat.lower()):
            return True, f"pattern: {pat}"

    # Check extension for binaries / media / fonts
    ext = Path(filename).suffix.lower()
    ignored_exts = [e.lower() for e in getattr(settings, "IGNORED_EXTENSIONS", [])]
    if ext in ignored_exts:
        return True, f"media/font/binary asset ({ext})"

    # Check large data files
    large_data_exts = [e.lower() for e in getattr(settings, "LARGE_DATA_EXTENSIONS", [".json", ".csv", ".sql", ".tsv"])]
    large_threshold = getattr(settings, "LARGE_DATA_LINE_THRESHOLD", 300)
    if ext in large_data_exts and insertions > large_threshold:
        return True, f"large data file ({ext}, {insertions} lines > {large_threshold})"

    return False, ""

def extract_commit_stats(commit: git.Commit) -> tuple[int, int, int, list[dict[str, Any]]]:
    """
    Extracts clean source-code stats (lines_added, lines_deleted, files_changed, excluded_items)
    from a git commit by filtering out ignored directories, lockfiles, generated assets, and large data files.
    """
    clean_added = 0
    clean_deleted = 0
    clean_files = 0
    excluded_items: list[dict[str, Any]] = []

    try:
        files_stats = commit.stats.files
        if not files_stats:
            total = commit.stats.total
            return total.get("insertions", 0), total.get("deletions", 0), total.get("files", 0), []

        for fpath, fstat in files_stats.items():
            ins = fstat.get("insertions", 0)
            dels = fstat.get("deletions", 0)
            ignored, reason = is_ignored_file(fpath, ins)
            if ignored:
                excluded_items.append({
                    "file": fpath,
                    "lines": ins,
                    "reason": reason,
                    "commit": commit.hexsha[:7],
                })
            else:
                clean_added += ins
                clean_deleted += dels
                clean_files += 1

        return clean_added, clean_deleted, clean_files, excluded_items
    except Exception:
        return 0, 0, 0, []

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
    all_excluded_files: list[dict[str, Any]] = []
    
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

        added, deleted, files, excluded_items = extract_commit_stats(c)
        all_excluded_files.extend(excluded_items)
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

    # Excluded items summary
    total_excluded_lines = sum(item["lines"] for item in all_excluded_files)
    categories = {
        "Directories (node_modules, venv, build, etc.)": 0,
        "Lockfiles & Package Managers": 0,
        "Minified Assets & Source Maps": 0,
        "Images, Fonts & Media": 0,
        "Large Data Files (.json, .csv, .sql > threshold)": 0,
        "Other Non-Source": 0,
    }
    for item in all_excluded_files:
        r = item["reason"].lower()
        if "directory" in r:
            categories["Directories (node_modules, venv, build, etc.)"] += item["lines"]
        elif "lock" in r or "yarn" in r or "package-lock" in r:
            categories["Lockfiles & Package Managers"] += item["lines"]
        elif "min." in r or ".map" in r:
            categories["Minified Assets & Source Maps"] += item["lines"]
        elif "media" in r or "font" in r or "binary" in r:
            categories["Images, Fonts & Media"] += item["lines"]
        elif "large data" in r:
            categories["Large Data Files (.json, .csv, .sql > threshold)"] += item["lines"]
        else:
            categories["Other Non-Source"] += item["lines"]

    sample_excluded = sorted(all_excluded_files, key=lambda x: x["lines"], reverse=True)[:20]

    burst_min_lines = getattr(settings, "BURST_MIN_LINES", 500)
    burst_min_share = getattr(settings, "BURST_MIN_SHARE", 0.05)
    burst_window_s = getattr(settings, "BURST_WINDOW_SECONDS", 900)

    excluded_summary = {
        "total_excluded_files": len(all_excluded_files),
        "total_excluded_lines": total_excluded_lines,
        "categories_breakdown": {k: v for k, v in categories.items() if v > 0},
        "sample_excluded": [
            {"file": s["file"], "lines": s["lines"], "reason": s["reason"], "commit": s["commit"]}
            for s in sample_excluded
        ],
        "configured_rules": {
            "ignored_dirs": getattr(settings, "IGNORED_DIRS", []),
            "ignored_patterns": getattr(settings, "IGNORED_FILE_PATTERNS", []),
            "large_data_threshold": getattr(settings, "LARGE_DATA_LINE_THRESHOLD", 300),
            "burst_min_lines": burst_min_lines,
            "burst_min_share_pct": round(burst_min_share * 100, 1),
        }
    }

    # 1. Thin-history check
    if total_commit_count <= 3:
        metrics = {
            "thin_history": True,
            "total_commits": total_commit_count,
            "final_codebase_lines": final_codebase_lines,
            "warning": "insufficient history to analyze",
            "growth_timeline": code_growth_timeline,
            "authors": list(authors_map.values()),
            "excluded_summary": excluded_summary,
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

        # Scaled Burst detection: must exceed both absolute minimum and percentage of final codebase in a short window
        share_of_final = curr_c["lines_added"] / final_codebase_lines
        if (
            curr_c["lines_added"] >= burst_min_lines
            and share_of_final >= burst_min_share
            and 0 <= diff_seconds <= burst_window_s
        ):
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
        "excluded_summary": excluded_summary,
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
