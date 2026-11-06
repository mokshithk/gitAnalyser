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
