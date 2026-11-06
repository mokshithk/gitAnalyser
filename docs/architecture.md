# CodeProvenance &mdash; Architectural Design & Knowledge Graph

This document details the layered architecture, module relationships, and data flow of **CodeProvenance** (GitHub: `gitAnalyser`).

---

## 1. High-Level Architecture Diagram

```mermaid
flowchart TD
    subgraph ClientTier["Client Tier (React + Vite)"]
        UI["SPA Interface<br/>(UI/UX Pro Max Dark OLED)"]
        Pages["Auth | Dashboard | New Analysis | Analysis Detail"]
        Components["CommitTimeline | ActivityHeatmap | CodeGrowthChart | MatchViewer | FlagsList"]
    end

    subgraph APITier["FastAPI Service Tier (Port 8000)"]
        API["FastAPI Application"]
        AuthRouter["/api/auth<br/>(JWT, Bcrypt, Rate Limiter)"]
        IngestRouter["/api/analyses<br/>(Git Clone & Safe Zip Ingest)"]
        CommitRouter["/api/analyses/commits<br/>(Pacing, Bursts, Timeline)"]
        SimRouter["/api/analyses/matches<br/>(AST Similarity, Diff Viewer)"]
        FlagRouter["/api/analyses/flags & /report<br/>(Triage, PDF Export)"]
    end

    subgraph WorkerTier["In-Process Worker Tier"]
        Pool["ThreadPoolExecutor Pool<br/>(Max 3 Background Workers)"]
        Pipeline["run_pipeline(analysis_id)<br/>(Queued &rarr; Cloning &rarr; Parsing &rarr; Comparing &rarr; Done)"]
    end

    subgraph Engines["Core Analytical Engines"]
        GitEngine["Commit History Analyzer<br/>(GitPython CLI, Gaps, Rush, Bursts, Intervals)"]
        ASTEngine["Structural AST Normalizer<br/>(Builtin `ast`, Identifier Renaming, Subtree Hashes)"]
        FlagEngine["Rule-Based Triage Engine<br/>(Explainable Evidence, Viva Questions, Review Priority)"]
        PDFGen["Pure-Python PDF Generator<br/>(ReportLab Flowables & Tables)"]
    end

    subgraph DataStorage["Data & State Tier (D: Drive & XAMPP MariaDB)"]
        DB[("MariaDB `codeprovenance`<br/>(Port 3306)")]
        Workdir["D:\\gitAnalyserProject\\workdir<br/>(Ephemeral Sandboxed Analysis Dirs)"]
        Cache["D:\\gitAnalyserProject\\.cache<br/>(Pip, Npm, Playwright, PyCache)"]
    end

    UI --> API
    API --> AuthRouter
    API --> IngestRouter
    API --> CommitRouter
    API --> SimRouter
    API --> FlagRouter

    IngestRouter --> Pool
    Pool --> Pipeline
    Pipeline --> GitEngine
    Pipeline --> ASTEngine
    Pipeline --> FlagEngine
    FlagRouter --> PDFGen

    GitEngine --> Workdir
    ASTEngine --> Workdir
    Pipeline --> DB
    AuthRouter --> DB
    FlagRouter --> DB
```

---

## 2. Core Modules & Responsibilities

| Module | Location | Primary Responsibility |
| :--- | :--- | :--- |
| **Authentication & Security** | `backend/auth/` | Bcrypt password hashing, JWT bearer token issuance/validation, and scan rate limiting per user. |
| **Ingestion & Safety** | `backend/ingestion/` | Git CLI shallow/full history cloning, access token isolation, zip bomb prevention, path traversal defense, and workdir cleanup. |
| **Commit Telemetry** | `backend/analysis/` | Topological git commit graph parsing, lines added/deleted, codebase share calculation, burst pace anomaly detection, and activity heatmap. |
| **Structural AST Similarity** | `backend/similarity/` | Python AST parsing, docstring stripping, variable/argument normalization to canonical placeholders, exact subtree hashing, and text-diff baseline. |
| **Explainable Flags & Triage** | `backend/flags/` | Evaluates rule-based signals, produces concrete evidence summaries, generates suggested interview questions, and exports pure-Python PDF reports. |
| **Frontend UI/UX** | `frontend/` | React 18 + Vite SPA styled with UI/UX Pro Max technical dark palette, Chart.js visualizations, and side-by-side match viewer. |

---

## 3. Database Entity Relationship Diagram

```mermaid
erDiagram
    users ||--o{ analyses : owns
    analyses ||--o{ commits : contains
    analyses ||--o{ similarity_matches : has
    analyses ||--o{ flags : triggers

    users {
        int id PK
        string email
        string password_hash
        string role
        datetime created_at
    }

    analyses {
        int id PK
        int user_id FK
        string input_type
        string source
        string mode
        string status
        text error_message
        json options
        datetime created_at
        datetime finished_at
    }

    commits {
        int id PK
        int analysis_id FK
        string sha
        string author_name
        string author_email
        datetime author_date
        datetime commit_date
        int lines_added
        int lines_deleted
        int files_changed
        text message
    }

    similarity_matches {
        int id PK
        int analysis_id FK
        string target_type
        string target_ref
        float score
        json details
    }

    flags {
        int id PK
        int analysis_id FK
        string type
        string severity
        float confidence
        string title
        json evidence
        string review_status
        text note
    }

    reference_corpus {
        int id PK
        string repo_url
        string language
        datetime added_at
    }
```
