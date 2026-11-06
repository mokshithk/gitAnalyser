import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import git
import pytest

from backend.db.database import SessionLocal
from backend.db.models import User, Analysis, Commit
from backend.analysis.commits import analyze_commit_history

@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()

@pytest.fixture
def test_user(db_session):
    import uuid
    user = User(
        email=f"tester_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="hashed_dummy",
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

def test_thin_history_warning(tmp_path, db_session, test_user):
    repo_dir = tmp_path / "thin_repo"
    repo = git.Repo.init(repo_dir)
    
    # 2 commits only
    f1 = repo_dir / "app.py"
    f1.write_text("print('hello')\n")
    repo.index.add(["app.py"])
    repo.index.commit("First commit")

    f1.write_text("print('hello world')\n")
    repo.index.add(["app.py"])
    repo.index.commit("Second commit")

    analysis = Analysis(
        user_id=test_user.id,
        input_type="zip",
        source="thin.zip",
        mode="full",
        status="parsing",
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    res = analyze_commit_history(analysis.id, repo_dir, db_session)
    assert res["thin_history"] is True
    assert "insufficient history to analyze" in res["warning"]

def test_burst_and_large_share_detection(tmp_path, db_session, test_user):
    repo_dir = tmp_path / "burst_repo"
    repo = git.Repo.init(repo_dir)

    base_time = int(time.time()) - 10000

    def dt_obj(s):
        return datetime.fromtimestamp(s, timezone.utc)

    # 4 commits to exceed thin history limit (<= 3)
    # Commit 1
    f = repo_dir / "main.py"
    f.write_text("x = 1\n")
    repo.index.add(["main.py"])
    repo.index.commit("Init", commit_date=dt_obj(base_time), author_date=dt_obj(base_time))

    # Commit 2
    f.write_text("x = 2\n")
    repo.index.add(["main.py"])
    repo.index.commit("Update", commit_date=dt_obj(base_time + 3600), author_date=dt_obj(base_time + 3600))

    # Commit 3 (Burst: 600 lines added 10 seconds later)
    bulk_code = "\n".join([f"def func_{i}(): return {i}" for i in range(600)])
    f.write_text(bulk_code)
    repo.index.add(["main.py"])
    repo.index.commit("Massive dump", commit_date=dt_obj(base_time + 3610), author_date=dt_obj(base_time + 3610))

    # Commit 4
    f2 = repo_dir / "util.py"
    f2.write_text("y = 10\n")
    repo.index.add(["util.py"])
    repo.index.commit("Finish", commit_date=dt_obj(base_time + 7200), author_date=dt_obj(base_time + 7200))

    analysis = Analysis(
        user_id=test_user.id,
        input_type="git_url",
        source="https://example.com/burst.git",
        mode="full",
        status="parsing",
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    res = analyze_commit_history(analysis.id, repo_dir, db_session)
    assert res["thin_history"] is False
    assert len(res["bursts"]) >= 1
    assert "large change in a short time" in res["bursts"][0]["description"]
    assert len(res["large_share_commits"]) >= 1
    assert res["large_share_commits"][0]["share_percentage"] >= 50.0

def test_regular_interval_detection(tmp_path, db_session, test_user):
    repo_dir = tmp_path / "scripted_repo"
    repo = git.Repo.init(repo_dir)

    base_time = int(time.time()) - 20000

    def dt_obj(s):
        return datetime.fromtimestamp(s, timezone.utc)

    # Create 8 commits exactly 60 seconds apart
    f = repo_dir / "code.py"
    for i in range(8):
        f.write_text(f"# line {i}\nx_{i} = {i}\n")
        repo.index.add(["code.py"])
        t = dt_obj(base_time + (i * 60))
        repo.index.commit(f"Scripted commit {i}", commit_date=t, author_date=t)

    analysis = Analysis(
        user_id=test_user.id,
        input_type="git_url",
        source="https://example.com/scripted.git",
        mode="full",
        status="parsing",
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    res = analyze_commit_history(analysis.id, repo_dir, db_session)
    assert res["regular_interval_flag"] is True
    assert res["regular_interval_std_dev"] < 5.0
