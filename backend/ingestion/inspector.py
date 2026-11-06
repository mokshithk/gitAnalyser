import os
from pathlib import Path
from typing import Any
import git
from backend.config import settings
from backend.ingestion.safety import safe_rmtree

EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".html": "HTML",
    ".css": "CSS",
    ".json": "JSON",
    ".sql": "SQL",
}

def detect_git_mode(dir_path: str | Path) -> str:
    """
    Detects whether .git exists and is valid.
    Returns 'full' if valid git repository with at least one commit exists, else 'similarity_only'.
    """
    git_dir = Path(dir_path) / ".git"
    if not git_dir.exists():
        return "similarity_only"

    try:
        repo = git.Repo(dir_path)
        # Check if head commit exists
        _ = repo.head.commit
        return "full"
    except Exception:
        return "similarity_only"

def detect_languages(dir_path: str | Path) -> dict[str, Any]:
    """
    Scans files in directory and counts file count and lines per language.
    Ignores .git, .venv, node_modules, and cache folders.
    """
    ignored_dirs = {".git", ".venv", "node_modules", ".cache", "__pycache__", "dist", "build"}
    language_counts: dict[str, dict[str, int]] = {}

    for root, dirs, files in os.walk(dir_path):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for f in files:
            ext = Path(f).suffix.lower()
            lang = EXTENSION_LANGUAGE_MAP.get(ext)
            if not lang:
                continue

            fp = os.path.join(root, f)
            lines = 0
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fp_in:
                    lines = sum(1 for _ in fp_in)
            except Exception:
                pass

            if lang not in language_counts:
                language_counts[lang] = {"files": 0, "lines": 0}
            language_counts[lang]["files"] += 1
            language_counts[lang]["lines"] += lines

    if not language_counts:
        return {"primary": "Unknown", "breakdown": {}}

    primary_lang = max(language_counts.items(), key=lambda item: item[1]["lines"])[0]
    return {
        "primary": primary_lang,
        "breakdown": language_counts,
    }

def get_analysis_workdir(analysis_id: int) -> Path:
    base = Path(settings.WORKDIR)
    base.mkdir(parents=True, exist_ok=True)
    return base / str(analysis_id)

def cleanup_analysis_workdir(analysis_id: int) -> None:
    workdir = get_analysis_workdir(analysis_id)
    safe_rmtree(workdir)
