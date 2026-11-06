# CodeProvenance &mdash; Ingestion & Triage Pipeline Workflow

This document illustrates the end-to-end ingestion pipeline, safety boundaries, and analytical state machine implemented in `backend/ingestion/worker.py`.

---

## 1. End-to-End Pipeline Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as Instructor / Reviewer
    participant Frontend as React + Vite SPA
    participant API as FastAPI Gateway
    participant Worker as Background ThreadPool
    participant FS as D:\gitAnalyserProject\workdir
    participant Git as Git CLI
    participant Engine as AST & Telemetry Engines
    participant DB as MariaDB `codeprovenance`

    User->>Frontend: Submit Git URL / Upload Zip
    Frontend->>API: POST /api/analyses/git-url (or /zip)
    API->>DB: Check hourly scan rate limit
    API->>DB: INSERT analyses (status='queued')
    API->>Worker: enqueue_analysis(analysis_id)
    API-->>Frontend: 201 Created (Analysis object)

    Worker->>DB: UPDATE status='cloning'
    alt Git URL Input
        Worker->>Git: git clone --kill-after-timeout (workdir/{id})
        Git->>FS: Full commit history written
    else Zip Upload Input
        Worker->>FS: validate_and_extract_zip (zip bomb + traversal checks)
        FS->>FS: Extracted safely into workdir/{id}
    end

    Worker->>FS: detect_git_mode (Check for .git)
    alt .git directory found
        Worker->>DB: UPDATE mode='full'
    else No .git directory
        Worker->>DB: UPDATE mode='similarity_only'
    end

    Worker->>DB: UPDATE status='parsing'
    opt Mode is 'full'
        Worker->>Engine: analyze_commit_history()
        Engine->>FS: Iterate commits, compute gaps, bursts, codebase share
        Engine->>DB: INSERT INTO commits
    end

    Worker->>DB: UPDATE status='comparing'
    Worker->>Engine: run_similarity_analysis()
    Engine->>FS: Walk .py files, extract AST functions
    Engine->>Engine: Normalize AST, strip docstrings, canonicalize identifiers
    Engine->>DB: Query reference_corpus & previous fingerprints
    Engine->>DB: INSERT INTO similarity_matches

    Worker->>Engine: generate_analysis_flags()
    Engine->>DB: INSERT INTO flags
    Engine->>DB: UPDATE review_priority ('HIGH' | 'MEDIUM' | 'LOW' | 'CLEAN')

    Worker->>FS: cleanup_analysis_workdir (Safe delete)
    Worker->>DB: UPDATE status='done', finished_at=NOW()

    Frontend->>API: GET /api/analyses/{id} (Poll progress)
    API-->>Frontend: Status 'done' with telemetry & flags
    User->>Frontend: View Charts, Viva Questions, Download PDF
```

---

## 2. Ingestion Safety & Threat Mitigation Rules

```mermaid
flowchart TD
    Start["User Submits Archive or URL"] --> CheckRate{"Scan Rate Limit Exceeded?<br/>(Max 20/hr/user)"}
    CheckRate -- Yes --> ErrRate["HTTP 429 Too Many Requests"]
    CheckRate -- No --> CheckType{"Input Type"}

    CheckType -- "Git URL" --> CheckAuth["Build URL with Single-Use Token"]
    CheckAuth --> CloneProc["git clone with timeout (60s)"]
    CloneProc --> CheckSize{"Repo Size <= 250 MB?"}
    CheckSize -- No --> ErrSize["Abort: Exceeds Size Limit (Cleanup)"]
    CheckSize -- Yes --> InspectDir["Inspect Mode (.git present?)"]

    CheckType -- "Zip Upload" --> CheckZipSize{"Zip File <= 50 MB?"}
    CheckZipSize -- No --> ErrZipSize["HTTP 413 Payload Too Large"]
    CheckZipSize -- Yes --> CheckBomb{"Zip-Bomb Ratio Check<br/>(Uncompressed <= 250 MB, Ratio <= 100:1)"}
    CheckBomb -- Suspicious --> ErrBomb["Reject: Potential Zip Bomb"]
    CheckBomb -- Safe --> CheckTraversal{"Path Traversal Check<br/>(No '..', no absolute paths, no escaping)"}
    CheckTraversal -- Dangerous --> ErrTraversal["Reject: Malicious Path Detected"]
    CheckTraversal -- Safe --> SafeExtract["Extract to workdir/{id}"]
    SafeExtract --> InspectDir

    InspectDir --> ModeChoice{"Valid .git exists?"}
    ModeChoice -- Yes --> FullMode["Set mode = 'full'<br/>(Commit Telemetry + AST Engine)"]
    ModeChoice -- No --> SimMode["Set mode = 'similarity_only'<br/>(AST Engine Only)"]

    FullMode --> RunEngines["Execute Analytical Pipeline"]
    SimMode --> RunEngines
    RunEngines --> CleanTemp["Cleanup Ephemeral workdir/{id}"]
    CleanTemp --> Done["Analysis Status = 'done'"]
```
