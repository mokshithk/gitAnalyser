import difflib
from pathlib import Path

def normalize_text_lines(text: str) -> list[str]:
    """Cleans text into non-empty, stripped lines for text-diff baseline."""
    lines = []
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned and not cleaned.startswith("#"):
            lines.append(cleaned)
    return lines

def compute_text_similarity(text1: str, text2: str) -> float:
    """
    Computes text similarity using standard difflib SequenceMatcher on normalized lines.
    Returns float score between 0.0 and 1.0.
    """
    lines1 = normalize_text_lines(text1)
    lines2 = normalize_text_lines(text2)

    if not lines1 and not lines2:
        return 1.0
    if not lines1 or not lines2:
        return 0.0

    matcher = difflib.SequenceMatcher(None, lines1, lines2)
    return matcher.ratio()

def compare_repositories_text_baseline(repo1_files: dict[str, str], repo2_files: dict[str, str]) -> float:
    """
    Compares two repositories using text-diff baseline.
    Computes average of maximum similarity for each source file against any target file.
    """
    if not repo1_files or not repo2_files:
        return 0.0

    scores = []
    for path1, content1 in repo1_files.items():
        best_file_score = 0.0
        for path2, content2 in repo2_files.items():
            s = compute_text_similarity(content1, content2)
            if s > best_file_score:
                best_file_score = s
            if best_file_score >= 0.98:
                break
        scores.append(best_file_score)

    return sum(scores) / len(scores) if scores else 0.0
