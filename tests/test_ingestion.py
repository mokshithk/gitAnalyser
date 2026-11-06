import io
import zipfile
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch

from backend.db.database import SessionLocal
from backend.db.models import User, Analysis
from backend.ingestion.safety import validate_and_extract_zip, ZipValidationError
from backend.ingestion.inspector import detect_git_mode, detect_languages
from backend.ingestion.git_cloner import build_authenticated_url, clone_repository, GitCloneError
from backend.ingestion.worker import run_pipeline
from backend.flags.router import get_full_report

@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()

@pytest.fixture
def test_user(db_session):
    import uuid
    user = User(
        email=f"clone_tester_{uuid.uuid4().hex[:6]}@example.com",
        password_hash="hashed_dummy",
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

def test_authenticated_url_building():
    url = "https://github.com/testuser/myrepo.git"
    token = "ghp_1234567890abcdef"
    authed = build_authenticated_url(url, token)
    assert authed == "https://ghp_1234567890abcdef@github.com/testuser/myrepo.git"

    # No token
    assert build_authenticated_url(url, None) == url

def test_safe_zip_extraction(tmp_path):
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        zf.writestr("hello.py", "print('hello world')\n")
        zf.writestr("sub/module.py", "def add(a, b):\n    return a + b\n")

    zip_bytes.seek(0)
    zip_path = tmp_path / "valid.zip"
    zip_path.write_bytes(zip_bytes.getvalue())

    dest_dir = tmp_path / "extracted"
    validate_and_extract_zip(
        zip_path=zip_path,
        target_dir=dest_dir,
        max_uncompressed_bytes=10 * 1024 * 1024,
    )

    assert (dest_dir / "hello.py").exists()
    assert (dest_dir / "sub" / "module.py").exists()
    assert (dest_dir / "hello.py").read_text().strip() == "print('hello world')"

def test_zip_path_traversal_rejection(tmp_path):
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        zf.writestr("../traversal.txt", "evil content")

    zip_bytes.seek(0)
    zip_path = tmp_path / "evil.zip"
    zip_path.write_bytes(zip_bytes.getvalue())

    dest_dir = tmp_path / "extracted_evil"
    with pytest.raises(ZipValidationError, match="Path traversal"):
        validate_and_extract_zip(
            zip_path=zip_path,
            target_dir=dest_dir,
            max_uncompressed_bytes=10 * 1024 * 1024,
        )

def test_zip_absolute_path_rejection(tmp_path):
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        zf.writestr("/root/pwn.txt", "evil content")

    zip_bytes.seek(0)
    zip_path = tmp_path / "evil_abs.zip"
    zip_path.write_bytes(zip_bytes.getvalue())

    dest_dir = tmp_path / "extracted_abs"
    with pytest.raises(ZipValidationError, match="Suspicious path"):
        validate_and_extract_zip(
            zip_path=zip_path,
            target_dir=dest_dir,
            max_uncompressed_bytes=10 * 1024 * 1024,
        )

def test_git_mode_detection(tmp_path):
    plain_dir = tmp_path / "plain"
    plain_dir.mkdir()
    (plain_dir / "test.py").write_text("x = 1")
    assert detect_git_mode(plain_dir) == "similarity_only"

    git_dir = tmp_path / "repo"
    import git
    repo = git.Repo.init(git_dir)
    test_file = git_dir / "main.py"
    test_file.write_text("print('version 1')")
    repo.index.add(["main.py"])
    repo.index.commit("Initial commit")

    assert detect_git_mode(git_dir) == "full"

def test_detect_languages(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "app.py").write_text("import sys\nprint('app')\n")
    (proj / "script.py").write_text("for i in range(5):\n    print(i)\n")
    (proj / "index.js").write_text("console.log('hi');\n")

    info = detect_languages(proj)
    assert info["primary"] == "Python"
    assert "Python" in info["breakdown"]
    assert info["breakdown"]["Python"]["files"] == 2
    assert "JavaScript" in info["breakdown"]
    assert info["breakdown"]["JavaScript"]["files"] == 1

def test_clone_timeout_handling(tmp_path, db_session, test_user):
    target = tmp_path / "timeout_repo"
    
    # 1. Test direct clone_repository timeout
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["git", "clone"], timeout=45)):
        with pytest.raises(GitCloneError) as exc_info:
            clone_repository("https://github.com/example/slow.git", target, timeout_seconds=45)
        assert "Clone timed out after 45 seconds" in str(exc_info.value)
        assert not target.exists()

    # 2. Test worker pipeline handling on timeout
    analysis = Analysis(
        user_id=test_user.id,
        input_type="git_url",
        source="https://github.com/example/slow.git",
        mode="full",
        status="queued",
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    with patch("backend.ingestion.git_cloner.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["git", "clone"], timeout=60)):
        run_pipeline(analysis.id)

    fresh_db = SessionLocal()
    try:
        reloaded = fresh_db.query(Analysis).filter(Analysis.id == analysis.id).first()
        assert reloaded.status == "failed"
        assert "Clone timed out after 60 seconds" in reloaded.error_message
        assert reloaded.options.get("review_priority") == "NOT ANALYZED"
    finally:
        fresh_db.close()

def test_failed_analysis_never_clean_priority(db_session, test_user):
    analysis = Analysis(
        user_id=test_user.id,
        input_type="git_url",
        source="https://github.com/example/broken.git",
        mode="full",
        status="failed",
        error_message="Clone timed out after 60 seconds",
        options={"review_priority": "NOT ANALYZED"}
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    report = get_full_report(analysis.id, test_user, db_session)
    assert report.status == "failed"
    assert report.review_priority == "NOT ANALYZED"
    assert report.review_priority != "CLEAN"
    assert report.review_priority != "LOW"
