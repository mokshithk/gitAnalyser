# CodeProvenance Evaluation & Benchmark Results

**Date of Execution:** 2026-11-06 17:09:24 UTC  
**Evaluation Target:** CodeProvenance (AST Structural Normalization + Commit History Telemetry) vs Plain Text-Diff Baseline (`difflib.SequenceMatcher`).

---

## 1. Executive Summary Table

| Metric | CodeProvenance (Proposed) | Plain Text-Diff Baseline | Difference / Improvement |
| :--- | :---: | :---: | :---: |
| **Precision** | **100.0%** | 100.0% | +0.0% |
| **Recall (Sensitivity)** | **100.0%** | 33.3% | **+66.7%** |
| **False Positive Rate (FPR)** | **0.0%** | 0.0% | 0.0% |
| **F1-Score** | **1.0000** | 0.5000 | **+0.5** |
| **True Positives (TP)** | 9 / 9 | 3 / 9 | +6 |
| **False Negatives (FN)** | **0** | 6 | -6 |
| **False Positives (FP)** | **0** | 0 | 0 |
| **True Negatives (TN)** | 3 / 3 | 3 / 3 | 0 |

---

## 2. Granular Test Case Breakdown (12 Repositories)

| Test Case | Ground Truth Class | Expected Status | AST Score | Text Score | Commit Anomaly Flags | CodeProvenance Verdict | Text-Diff Verdict | Result Notes |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `genuine_1` | `genuine_history` | Genuine | 0.0 | 0.0 | None | **Clean** | Clean | Correctly recognized natural incremental development cadence. |
| `genuine_2` | `genuine_history` | Genuine | 0.0 | 0.0 | None | **Clean** | Clean | Correctly recognized natural incremental development cadence. |
| `genuine_3` | `genuine_history` | Genuine | 0.0 | 0.0 | None | **Clean** | Clean | Correctly recognized natural incremental development cadence. |
| `direct_copy_1` | `direct_copy` | Anomalous | 1.0 | 1.0 | None | **Flagged** | Flagged | Both engines detected verbatim copy. |
| `direct_copy_2` | `direct_copy` | Anomalous | 1.0 | 1.0 | None | **Flagged** | Flagged | Both engines detected verbatim copy. |
| `direct_copy_3` | `direct_copy` | Anomalous | 1.0 | 1.0 | None | **Flagged** | Flagged | Both engines detected verbatim copy. |
| `renamed_copy_1` | `renamed_restructured_copy` | Anomalous | 1.0 | 0.029 | None | **Flagged** | Clean | AST matched identical subtree despite renamed variables; text diff failed. |
| `renamed_copy_2` | `renamed_restructured_copy` | Anomalous | 1.0 | 0.029 | None | **Flagged** | Clean | AST matched identical subtree despite renamed variables; text diff failed. |
| `renamed_copy_3` | `renamed_restructured_copy` | Anomalous | 1.0 | 0.029 | None | **Flagged** | Clean | AST matched identical subtree despite renamed variables; text diff failed. |
| `fake_history_1` | `fake_history` | Anomalous | 0.0 | 0.0 | RegularIntervals | **Flagged** | Clean | Flagged by commit interval std-dev; text diff completely missed due to lack of temporal analysis. |
| `fake_history_2` | `fake_history` | Anomalous | 0.0 | 0.0 | RegularIntervals | **Flagged** | Clean | Flagged by commit interval std-dev; text diff completely missed due to lack of temporal analysis. |
| `fake_history_3` | `fake_history` | Anomalous | 0.0 | 0.0 | RegularIntervals | **Flagged** | Clean | Flagged by commit interval std-dev; text diff completely missed due to lack of temporal analysis. |

---

## 3. Error Analysis & Key Viva Findings

### Why AST Normalization Outperformed Text-Diff
1. **Renamed-Variable Invariance:** In the `renamed_restructured_copy` class, identifiers (`arr` &rarr; `elements`, `target` &rarr; `query`) and docstrings were altered to evade simple string matching. Naive text diff collapsed to a similarity score of ~0.029 (below the 0.65 threshold), producing a **False Negative**. CodeProvenance's AST identifier normalization mapped all custom parameters to canonical syntax trees, producing a **1.00 AST match**.
2. **Temporal Dimension (Fake History Detection):** The text-diff baseline has zero awareness of git commit timestamps or developmental pace. When a student uses an automated script to generate commits every 60 seconds (`fake_history`), text diff considers the code independent. CodeProvenance's interval standard deviation metric caught the artificial uniformity immediately.
3. **Genuine Work Protection:** On authentic incremental histories (`genuine_1`, `genuine_2`, `genuine_3`), CodeProvenance achieved **0% False Positive Rate (FPR)**, correctly recognizing that small commits over multiple days with natural gaps indicate authentic progress.

---

## 4. Academic Limitations of this Evaluation (Viva Talking Points)

- **Dataset Size:** The evaluation was performed on a focused labeled dataset of 12 test repositories (3 per category). While sufficient to empirically demonstrate algorithmic superiority on core failure modes, testing on hundreds of real student repositories across different programming languages remains future work.
- **Syntactic Restructuring Limits:** If code is radically restructured (e.g. converting a recursive quicksort into an iterative stack implementation), AST subtrees diverge, which would require program dependency graphs (PDG) or execution trace analysis.
- **Multi-Language Support:** AST normalization is currently implemented for Python; other languages in this version rely on text and commit telemetry.
