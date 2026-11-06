import os
import subprocess
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
    Clones full git repository into target_dir using subprocess.run with Git CLI.
    Enforces Windows-safe timeout, GIT_TERMINAL_PROMPT=0, and directory size limit.
    """
    timeout = timeout_seconds or getattr(settings, "CLONE_TIMEOUT", settings.CLONE_TIMEOUT_SECONDS)
    max_bytes = (max_size_mb or settings.MAX_REPO_SIZE_MB) * 1024 * 1024
    target_dir = Path(target_dir).resolve()

    if target_dir.exists():
        safe_rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    auth_url = build_authenticated_url(repo_url, access_token)

    cmd = ["git", "clone", auth_url, str(target_dir)]
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"

    try:
        proc = subprocess.run(
            cmd,
            timeout=timeout,
            capture_output=True,
            text=True,
            env=env,
        )

        if proc.returncode != 0:
            safe_rmtree(target_dir)
            err_msg = (proc.stderr or proc.stdout or f"git clone exited with code {proc.returncode}").strip()
            if access_token and access_token in err_msg:
                err_msg = err_msg.replace(access_token, "******")
            raise GitCloneError(f"Git clone failed: {err_msg}")

        # Enforce size limit after clone
        check_directory_size(target_dir, max_bytes)
        return git.Repo(target_dir)

    except subprocess.TimeoutExpired as e:
        # Kill the process tree on Windows
        pid = getattr(e, "pid", None)
        try:
            if pid:
                subprocess.run(f"taskkill /T /F /PID {pid}", shell=True, capture_output=True)
            else:
                subprocess.run("taskkill /T /F /IM git.exe", shell=True, capture_output=True)
                subprocess.run("taskkill /T /F /IM git-remote-https.exe", shell=True, capture_output=True)
        except Exception:
            pass
        safe_rmtree(target_dir)
        raise GitCloneError(f"Clone timed out after {timeout} seconds") from None
    except ValueError as e:
        safe_rmtree(target_dir)
        raise GitCloneError(str(e)) from None
    except GitCloneError:
        raise
    except Exception as e:
        safe_rmtree(target_dir)
        raise GitCloneError(f"Unexpected error while cloning: {str(e)}") from None
