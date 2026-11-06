import os
import json
from pathlib import Path
from typing import Any, Optional
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.models import Analysis, SimilarityMatch, ReferenceCorpus
from backend.similarity.ast_normalizer import (
    FunctionFingerprint,
    extract_function_fingerprints_from_source,
    compute_structural_similarity,
)
from backend.similarity.baseline_text import (
    compute_text_similarity,
    compare_repositories_text_baseline,
)
from backend.ingestion.git_cloner import clone_repository
from backend.ingestion.safety import safe_rmtree

CORPUS_CACHE_FILE = Path(settings.WORKDIR) / "corpus_cache.json"

def scan_directory_for_python_files(dir_path: str | Path) -> dict[str, str]:
    """Scans directory and returns mapping of relative_path -> source_code for all .py files."""
    ignored = {".git", ".venv", "node_modules", ".cache", "__pycache__", "dist", "build"}
    py_files: dict[str, str] = {}
    base_dir = Path(dir_path).resolve()

    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in ignored]
        for f in files:
            if f.endswith(".py"):
                full_path = Path(root) / f
                try:
                    rel_path = str(full_path.relative_to(base_dir)).replace("\\", "/")
                    content = full_path.read_text(encoding="utf-8", errors="ignore")
                    py_files[rel_path] = content
                except Exception:
                    continue
    return py_files

def extract_repo_fingerprints(dir_path: str | Path) -> list[FunctionFingerprint]:
    """Extracts all non-trivial function fingerprints from a repository directory."""
    files = scan_directory_for_python_files(dir_path)
    all_fps: list[FunctionFingerprint] = []
    for rel_path, code in files.items():
        fps = extract_function_fingerprints_from_source(code, file_path=rel_path)
        all_fps.extend(fps)
    return all_fps

def load_or_update_corpus_cache(db: Session) -> dict[str, list[dict[str, Any]]]:
    """Loads cached fingerprints of reference corpus repos."""
    cache: dict[str, list[dict[str, Any]]] = {}
    if CORPUS_CACHE_FILE.exists():
        try:
            cache = json.loads(CORPUS_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    corpus_repos = db.query(ReferenceCorpus).all()
    updated = False

    for c in corpus_repos:
        if c.repo_url not in cache:
            tmp_clone = Path(settings.WORKDIR) / f"corpus_tmp_{c.id}"
            try:
                clone_repository(c.repo_url, tmp_clone)
                fps = extract_repo_fingerprints(tmp_clone)
                cache[c.repo_url] = [fp.to_dict() for fp in fps]
                updated = True
            except Exception:
                cache[c.repo_url] = []
            finally:
                safe_rmtree(tmp_clone)

    if updated:
        try:
            CORPUS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CORPUS_CACHE_FILE.write_text(json.dumps(cache), encoding="utf-8")
        except Exception:
            pass

    return cache

def dict_to_fingerprint(d: dict[str, Any]) -> FunctionFingerprint:
    return FunctionFingerprint(
        file_path=d["file_path"],
        function_name=d["function_name"],
        start_line=d["start_line"],
        end_line=d["end_line"],
        statement_count=d["statement_count"],
        raw_code=d["raw_code"],
        structural_hash=d["structural_hash"],
        node_types=d["node_types"],
    )

def compare_fingerprint_sets(
    source_fps: list[FunctionFingerprint],
    target_fps: list[FunctionFingerprint],
    target_label: str,
    target_type: str,
    analysis_id: int,
    db: Session,
    min_similarity_threshold: float = 0.70,
) -> Optional[SimilarityMatch]:
    """
    Compares two lists of function fingerprints.
    Finds exact AST matches and structural similarity matches.
    Stores match into DB if significant resemblance is found.
    """
    if not source_fps or not target_fps:
        return None

    matched_pairs: list[dict[str, Any]] = []
    total_score = 0.0

    # Build target hash index for fast exact matching
    target_by_hash: dict[str, list[FunctionFingerprint]] = {}
    for tfp in target_fps:
        target_by_hash.setdefault(tfp.structural_hash, []).append(tfp)

    for sfp in source_fps:
        # Check exact structural hash first
        if sfp.structural_hash in target_by_hash:
            best_target = target_by_hash[sfp.structural_hash][0]
            score = 1.0
            matched_pairs.append({
                "source_function": sfp.function_name,
                "source_file": sfp.file_path,
                "source_lines": [sfp.start_line, sfp.end_line],
                "source_code": sfp.raw_code,
                "target_function": best_target.function_name,
                "target_file": best_target.file_path,
                "target_code": best_target.raw_code,
                "similarity_score": score,
                "match_type": "exact_ast",
            })
            total_score += 1.0
            continue

        # If no exact match, search for high structural similarity
        best_partial_score = 0.0
        best_partial_target = None
        for tfp in target_fps:
            sim = compute_structural_similarity(sfp, tfp)
            if sim > best_partial_score:
                best_partial_score = sim
                best_partial_target = tfp
                if best_partial_score >= 0.95:
                    break

        if best_partial_score >= min_similarity_threshold and best_partial_target:
            matched_pairs.append({
                "source_function": sfp.function_name,
                "source_file": sfp.file_path,
                "source_lines": [sfp.start_line, sfp.end_line],
                "source_code": sfp.raw_code,
                "target_function": best_partial_target.function_name,
                "target_file": best_partial_target.file_path,
                "target_code": best_partial_target.raw_code,
                "similarity_score": round(best_partial_score, 3),
                "match_type": "structural_similarity",
            })
            total_score += best_partial_score

    if not matched_pairs:
        return None

    overall_similarity = min(1.0, total_score / max(1, len(source_fps)))

    match_record = SimilarityMatch(
        analysis_id=analysis_id,
        target_type=target_type,
        target_ref=target_label,
        score=round(overall_similarity, 3),
        details={
            "matched_functions_count": len(matched_pairs),
            "total_source_functions": len(source_fps),
            "total_target_functions": len(target_fps),
            "overall_score": round(overall_similarity, 3),
            "matched_pairs": matched_pairs,
        }
    )
    db.add(match_record)
    db.commit()
    return match_record

def run_similarity_analysis(
    analysis_id: int,
    repo_dir: str | Path,
    db: Session,
    options: Optional[dict[str, Any]] = None,
) -> list[SimilarityMatch]:
    """
    Main entry point for Module M4:
    1. Extracts function fingerprints from repo_dir
    2. Excludes template/starter repo functions if specified in options
    3. Compares against reference corpus
    4. Compares against previously analyzed projects in DB
    5. Saves similarity matches to DB
    """
    options = options or {}
    source_fps = extract_repo_fingerprints(repo_dir)

    if not source_fps:
        return []

    # Exclude starter/template repo functions if provided
    starter_url = options.get("starter_repo_url")
    if starter_url:
        tmp_starter = Path(settings.WORKDIR) / f"starter_{analysis_id}"
        try:
            clone_repository(starter_url, tmp_starter)
            starter_fps = extract_repo_fingerprints(tmp_starter)
            starter_hashes = {fp.structural_hash for fp in starter_fps}
            # Exclude functions present in starter
            source_fps = [fp for fp in source_fps if fp.structural_hash not in starter_hashes]
        except Exception:
            pass
        finally:
            safe_rmtree(tmp_starter)

    if not source_fps:
        return []

    created_matches: list[SimilarityMatch] = []

    # 1. Compare against Reference Corpus
    corpus_cache = load_or_update_corpus_cache(db)
    for repo_url, target_fp_dicts in corpus_cache.items():
        target_fps = [dict_to_fingerprint(d) for d in target_fp_dicts]
        m = compare_fingerprint_sets(
            source_fps=source_fps,
            target_fps=target_fps,
            target_label=repo_url,
            target_type="corpus",
            analysis_id=analysis_id,
            db=db,
        )
        if m:
            created_matches.append(m)

    # 2. Compare against previous analyses in DB
    prev_analyses = db.query(Analysis).filter(
        Analysis.id != analysis_id,
        Analysis.status == "done"
    ).all()

    for prev in prev_analyses:
        opts = prev.options or {}
        prev_fp_dicts = opts.get("fingerprints", [])
        if prev_fp_dicts:
            target_fps = [dict_to_fingerprint(d) for d in prev_fp_dicts]
            m = compare_fingerprint_sets(
                source_fps=source_fps,
                target_fps=target_fps,
                target_label=f"Analysis #{prev.id} ({prev.source})",
                target_type="previous_analysis",
                analysis_id=analysis_id,
                db=db,
            )
            if m:
                created_matches.append(m)

    # Save current fingerprints in options for future comparisons
    curr_analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if curr_analysis:
        curr_opts = dict(curr_analysis.options or {})
        curr_opts["fingerprints"] = [fp.to_dict() for fp in source_fps]
        curr_analysis.options = curr_opts
        db.commit()

    return created_matches
