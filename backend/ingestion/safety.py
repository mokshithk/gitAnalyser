import os
import stat
import shutil
import zipfile
from pathlib import Path

class ZipValidationError(ValueError):
    pass

def remove_readonly(func, path, exc_info):
    """Windows-compatible onerror callback for shutil.rmtree to remove read-only git files."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

def safe_rmtree(path: str | Path) -> None:
    """Safely removes a directory tree, handling Windows read-only files."""
    p = Path(path)
    if p.exists():
        shutil.rmtree(p, onerror=remove_readonly)

def check_directory_size(dir_path: str | Path, max_bytes: int) -> int:
    """Walks directory, calculates total bytes, and ensures it does not exceed max_bytes."""
    total_bytes = 0
    for root, _, files in os.walk(dir_path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total_bytes += os.path.getsize(fp)
            except OSError:
                continue
            if total_bytes > max_bytes:
                raise ValueError(f"Directory size exceeds maximum limit of {max_bytes / (1024 * 1024):.1f} MB")
    return total_bytes

def validate_and_extract_zip(
    zip_path: str | Path,
    target_dir: str | Path,
    max_uncompressed_bytes: int,
    max_ratio: float = 100.0,
    max_file_count: int = 20000,
) -> None:
    """
    Validates a zip file against zip-bomb, ratio, entry count, and path traversal vulnerabilities.
    Extracts safely into target_dir only if all checks pass.
    """
    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    if not zipfile.is_zipfile(zip_path):
        raise ZipValidationError("Uploaded file is not a valid zip archive")

    compressed_size = os.path.getsize(zip_path)
    total_uncompressed = 0
    entry_count = 0

    with zipfile.ZipFile(zip_path, "r") as zf:
        infolist = zf.infolist()
        if len(infolist) > max_file_count:
            raise ZipValidationError(f"Archive contains {len(infolist)} files, exceeding limit of {max_file_count}")

        for member in infolist:
            entry_count += 1
            filename = member.filename
            
            # Check for path traversal attempts
            if filename.startswith("/") or filename.startswith("\\") or ":" in filename:
                raise ZipValidationError(f"Suspicious path detected in archive: {filename}")
            
            parts = Path(filename).parts
            if ".." in parts:
                raise ZipValidationError(f"Path traversal detected in archive: {filename}")

            total_uncompressed += member.file_size
            if total_uncompressed > max_uncompressed_bytes:
                raise ZipValidationError(
                    f"Total uncompressed size exceeds limit of {max_uncompressed_bytes / (1024 * 1024):.1f} MB"
                )

        if compressed_size > 0:
            ratio = total_uncompressed / compressed_size
            if ratio > max_ratio and total_uncompressed > 10 * 1024 * 1024:
                raise ZipValidationError(
                    f"Suspicious compression ratio ({ratio:.1f}:1). Potential zip bomb rejected."
                )

        # Extract safely checking each resolved path
        for member in infolist:
            dest_path = (target_dir / member.filename).resolve()
            # Ensure dest_path is strictly inside target_dir
            if not str(dest_path).startswith(str(target_dir)):
                raise ZipValidationError(f"Path traversal escape detected: {member.filename}")
            
            zf.extract(member, target_dir)
