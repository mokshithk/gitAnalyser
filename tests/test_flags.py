import pytest
from backend.db.database import SessionLocal
from backend.db.models import User, Analysis, Flag, SimilarityMatch
from backend.flags.engine import generate_analysis_flags, MANDATORY_DISCLAIMER, SYSTEM_LIMITATIONS
from backend.flags.pdf_export import generate_pdf_report

@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()

@pytest.fixture
def test_user(db_session):
    import uuid
    user = User(
        email=f"flag_tester_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="hashed_dummy",
        role="user"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

def test_flag_generation_and_priority(db_session, test_user):
    analysis = Analysis(
        user_id=test_user.id,
        input_type="git_url",
        source="https://github.com/example/demo.git",
        mode="full",
        status="done",
        options={
            "commit_metrics": {
                "thin_history": False,
                "total_commits": 12,
                "final_codebase_lines": 1000,
                "large_share_commits": [
                    {
                        "sha": "a1b2c3d",
                        "lines_added": 750,
                        "share_percentage": 75.0,
                        "message": "Initial code dump"
                    }
                ],
                "bursts": [
                    {
                        "sha": "e4f5a6b",
                        "lines_added": 600,
                        "seconds_since_prev": 120,
                        "description": "large change in a short time (600 lines in 120s)"
                    }
                ],
            }
        }
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    flags = generate_analysis_flags(analysis.id, db_session)
    assert len(flags) >= 2

    # Check bulk add flag
    bulk_flag = next(f for f in flags if f.type == "SINGLE_COMMIT_BULK_ADD")
    assert bulk_flag.severity == "high"
    assert "75.0%" in bulk_flag.title
    assert "questions" in bulk_flag.evidence
    assert len(bulk_flag.evidence["questions"]) >= 1

    # Check burst flag
    burst_flag = next(f for f in flags if f.type == "BURST_PACE_ANOMALY")
    assert burst_flag.severity == "high"
    assert "large change in a short time" in burst_flag.evidence["description"]

    # Check Review Priority in analysis options
    db_session.refresh(analysis)
    assert analysis.options["review_priority"] == "HIGH"

def test_pdf_report_generation(db_session, test_user):
    analysis = Analysis(
        user_id=test_user.id,
        input_type="git_url",
        source="https://github.com/example/pdf-test.git",
        mode="full",
        status="done",
        options={"review_priority": "MEDIUM", "commit_metrics": {"total_commits": 15, "final_codebase_lines": 800}}
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    flag1 = Flag(
        analysis_id=analysis.id,
        type="LAST_MINUTE_RUSH",
        severity="medium",
        confidence=0.85,
        title="70% of code added in final 24h",
        evidence={"description": "70% code rush", "questions": ["What caused the rush?"]},
        review_status="open",
    )
    db_session.add(flag1)
    db_session.commit()

    pdf_bytes = generate_pdf_report(
        analysis=analysis,
        flags=[flag1],
        matches=[],
        commit_metrics={"total_commits": 15, "final_codebase_lines": 800}
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    # PDF magic bytes
    assert pdf_bytes.startswith(b"%PDF-")

def test_multiple_bursts_collapse_to_one_flag(db_session, test_user):
    analysis = Analysis(
        user_id=test_user.id,
        input_type="git_url",
        source="https://github.com/example/multi-burst.git",
        mode="full",
        status="done",
        options={
            "commit_metrics": {
                "thin_history": False,
                "total_commits": 25,
                "final_codebase_lines": 5000,
                "bursts": [
                    {"sha": "c111111", "lines_added": 600, "seconds_since_prev": 60, "share_percentage": 12.0},
                    {"sha": "c222222", "lines_added": 750, "seconds_since_prev": 120, "share_percentage": 15.0},
                    {"sha": "c333333", "lines_added": 900, "seconds_since_prev": 300, "share_percentage": 18.0},
                ],
                "large_share_commits": [],
                "regular_interval_flag": False,
            }
        }
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    flags = generate_analysis_flags(analysis.id, db_session)
    burst_flags = [f for f in flags if f.type == "BURST_PACE_ANOMALY"]
    # All 3 bursts must collapse into exactly 1 flag
    assert len(burst_flags) == 1
    bf = burst_flags[0]
    assert "3 large changes in short windows" in bf.title
    assert bf.evidence["burst_count"] == 3
    assert len(bf.evidence["commits"]) == 3
    # Burst alone must be medium
    assert bf.severity == "medium"

def test_burst_alone_never_reaches_high(db_session, test_user):
    # Case 1: Burst alone
    analysis = Analysis(
        user_id=test_user.id,
        input_type="git_url",
        source="https://github.com/example/burst-alone.git",
        mode="full",
        status="done",
        options={
            "commit_metrics": {
                "thin_history": False,
                "total_commits": 10,
                "final_codebase_lines": 2000,
                "bursts": [
                    {"sha": "b123456", "lines_added": 600, "seconds_since_prev": 180, "share_percentage": 30.0}
                ],
                "large_share_commits": [],
                "regular_interval_flag": False,
            }
        }
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    flags = generate_analysis_flags(analysis.id, db_session)
    bf = next(f for f in flags if f.type == "BURST_PACE_ANOMALY")
    assert bf.severity == "medium"
    assert bf.severity != "high"

    # Case 2: Burst + secondary corroboration (e.g. regular scripted intervals)
    analysis.options = {
        "commit_metrics": {
            "thin_history": False,
            "total_commits": 10,
            "final_codebase_lines": 2000,
            "bursts": [
                {"sha": "b123456", "lines_added": 600, "seconds_since_prev": 180, "share_percentage": 30.0}
            ],
            "large_share_commits": [],
            "regular_interval_flag": True, # Secondary signal agrees
        }
    }
    db_session.commit()

    flags2 = generate_analysis_flags(analysis.id, db_session)
    bf2 = next(f for f in flags2 if f.type == "BURST_PACE_ANOMALY")
    assert bf2.severity == "high"
