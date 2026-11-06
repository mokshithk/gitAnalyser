import os
import urllib.parse
from pathlib import Path
import git
from backend.config import settings
from backend.ingestion.safety import check_directory_size, safe_rmtree

class GitCloneError(Exception):
    pass

def build_authenticated_url(raw_url: str, token: str | None) -> str:
    """Inserts access token into git HTTP/HTTPS URL for single-use cloning without persisting."""
    if not token:
        return raw_url
    
    parsed = urllib.parse.urlsplit(raw_url)
    if parsed.scheme in ("http", "https"):
        netloc = f"{token}@{parsed.netloc}"
        return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
    return raw_url

def clone_repository(
    repo_url: str,
    target_dir: str | Path,
    access_token: str | None = None,
    timeout_seconds: int | None = None,
    max_size_mb: int | None = None,
) -> git.Repo:
    """
    Clones full git repository into target_dir using Git CLI through GitPython.
    Applies timeout and enforces maximum directory size limit.
    """
    timeout = timeout_seconds or settings.CLONE_TIMEOUT_SECONDS
    max_bytes = (max_size_mb or settings.MAX_REPO_SIZE_MB) * 1024 * 1024
    target_dir = Path(target_dir).resolve()

    if target_dir.exists():
        safe_rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    auth_url = build_authenticated_url(repo_url, access_token)

    try:
        # Clone with timeout via git CLI
        repo = git.Repo.clone_from(
            auth_url,
            target_dir,
            kill_after_timeout=timeout,
        )

        # Enforce size limit after clone
        check_directory_size(target_dir, max_bytes)
        return repo
    except git.GitCommandError as e:
        safe_rmtree(target_dir)
        # Sanitize any token from error messages
        err_msg = str(e)
        if access_token and access_token in err_msg:
            err_msg = err_msg.replace(access_token, "******")
        raise GitCloneError(f"Git clone failed: {err_msg}") from None
    except ValueError as e:
        safe_rmtree(target_dir)
        raise GitCloneError(str(e)) from None
    except Exception as e:
        safe_rmtree(target_dir)
        raise GitCloneError(f"Unexpected error while cloning: {str(e)}") from None
