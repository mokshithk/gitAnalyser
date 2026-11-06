import os
import time
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import git

EVAL_DIR = Path(__file__).resolve().parent
TEST_CASES_DIR = EVAL_DIR / "test_cases"
GROUND_TRUTH_FILE = EVAL_DIR / "ground_truth.json"

REFERENCE_CODE = """
def quicksort(arr):
    \"\"\"Standard recursive quicksort algorithm.\"\"\"
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)

def binary_search(arr, target):
    \"\"\"Iterative binary search.\"\"\"
    low = 0
    high = len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1

def matrix_multiply(matrix_a, matrix_b):
    \"\"\"Performs 2D matrix multiplication.\"\"\"
    rows_a = len(matrix_a)
    cols_a = len(matrix_a[0])
    rows_b = len(matrix_b)
    cols_b = len(matrix_b[0])
    if cols_a != rows_b:
        raise ValueError("Incompatible dimensions")
    result = [[0 for _ in range(cols_b)] for _ in range(rows_a)]
    for i in range(rows_a):
        for j in range(cols_b):
            for k in range(cols_a):
                result[i][j] += matrix_a[i][k] * matrix_b[k][j]
    return result
"""

RENAMED_CODE = """
def quicksort(elements):
    # Altered docstrings and variable names
    if len(elements) <= 1:
        return elements
    center = elements[len(elements) // 2]
    smaller = [val for val in elements if val < center]
    equal = [val for val in elements if val == center]
    greater = [val for val in elements if val > center]
    return quicksort(smaller) + equal + quicksort(greater)

def search_index(items, query):
    # Variable renaming to evade text diff
    start_pos = 0
    end_pos = len(items) - 1
    while start_pos <= end_pos:
        center_pos = (start_pos + end_pos) // 2
        if items[center_pos] == query:
            return center_pos
        elif items[center_pos] < query:
            start_pos = center_pos + 1
        else:
            end_pos = center_pos - 1
    return -1

def compute_product_matrix(mat_one, mat_two):
    # Restructured variable names
    dim_r1 = len(mat_one)
    dim_c1 = len(mat_one[0])
    dim_r2 = len(mat_two)
    dim_c2 = len(mat_two[0])
    if dim_c1 != dim_r2:
        raise ValueError("Invalid shapes for multiplication")
    res_grid = [[0 for _ in range(dim_c2)] for _ in range(dim_r1)]
    for r in range(dim_r1):
        for c in range(dim_c2):
            for inner in range(dim_c1):
                res_grid[r][c] += mat_one[r][inner] * mat_two[inner][c]
    return res_grid
"""

def create_git_repo(path: Path) -> git.Repo:
    if path.exists():
        import shutil
        from backend.ingestion.safety import remove_readonly
        shutil.rmtree(path, onerror=remove_readonly)
    path.mkdir(parents=True, exist_ok=True)
    repo = git.Repo.init(path)
    return repo

def make_commit(repo: git.Repo, filename: str, content: str, msg: str, dt: datetime, author="Mokshith <mokshith@example.com>"):
    file_path = Path(repo.working_dir) / filename
    file_path.write_text(content, encoding="utf-8")
    repo.index.add([filename])
    repo.index.commit(msg, commit_date=dt, author_date=dt)

def generate_dataset():
    print("Generating evaluation test dataset in eval/test_cases/ ...")
    base_time = datetime.now(timezone.utc) - timedelta(days=30)
    ground_truth = {}

    # 0. Reference Corpus Repo
    ref_dir = TEST_CASES_DIR / "corpus_reference"
    ref_repo = create_git_repo(ref_dir)
    make_commit(ref_repo, "algorithms.py", REFERENCE_CODE, "Add core standard algorithms", base_time)
    print("  Created reference corpus repo.")

    # 1. Genuine History (3 repos)
    # Natural cadence: irregular intervals (hours/days apart), small incremental commits
    for i in range(1, 4):
        case_id = f"genuine_{i}"
        repo_dir = TEST_CASES_DIR / case_id
        repo = create_git_repo(repo_dir)

        t = base_time + timedelta(days=i*2)
        make_commit(repo, "app.py", "# Project setup\nVERSION = '0.1.0'\n", "Initial project scaffold", t)
        
        t += timedelta(hours=14)
        make_commit(repo, "models.py", "class Record:\n    def __init__(self, key, val):\n        self.key = key\n        self.val = val\n", "Add data model", t)
        
        t += timedelta(days=1, hours=3)
        make_commit(repo, "utils.py", f"def format_record_{i}(r):\n    return f'KEY: {{r.key}} = {{r.val}}'\n", "Add string formatting utility", t)
        
        t += timedelta(days=2, hours=5)
        make_commit(repo, "processor.py", f"def process_batch_{i}(items):\n    cleaned = [x.strip() for x in items if x]\n    return sorted(cleaned)\n", "Add custom batch cleaner", t)
        
        t += timedelta(hours=6)
        make_commit(repo, "tests.py", f"def test_processor_{i}():\n    assert len(process_batch_{i}(['a', 'b'])) == 2\n", "Add unit tests", t)

        ground_truth[case_id] = {
            "class": "genuine_history",
            "is_anomalous": False,
            "expected_flags": [],
            "description": "Authentic incremental development with natural time gaps"
        }
    print("  Created 3 Genuine History test cases.")

    # 2. Direct Verbatim Copy (3 repos)
    # Single massive commit or 2 commits containing exact copy of reference code
    for i in range(1, 4):
        case_id = f"direct_copy_{i}"
        repo_dir = TEST_CASES_DIR / case_id
        repo = create_git_repo(repo_dir)

        t = base_time + timedelta(days=10 + i)
        make_commit(repo, "readme.txt", "My project implementation", "Initial readme", t)
        
        t += timedelta(minutes=5)
        # Direct dump of reference code
        make_commit(repo, "solution.py", REFERENCE_CODE, "Finished all algorithms", t)

        ground_truth[case_id] = {
            "class": "direct_copy",
            "is_anomalous": True,
            "expected_flags": ["HIGH_AST_SIMILARITY", "SINGLE_COMMIT_BULK_ADD"],
            "description": "Verbatim copy of reference algorithms added in a bulk commit"
        }
    print("  Created 3 Direct Copy test cases.")

    # 3. Renamed Variable / Restructured Copy (3 repos)
    # Identifier names changed, docstrings stripped/modified. AST identical, text-diff degraded.
    for i in range(1, 4):
        case_id = f"renamed_copy_{i}"
        repo_dir = TEST_CASES_DIR / case_id
        repo = create_git_repo(repo_dir)

        t = base_time + timedelta(days=15 + i)
        make_commit(repo, "config.py", "DEBUG = False\n", "Setup configuration", t)
        
        t += timedelta(minutes=15)
        make_commit(repo, "my_algorithms.py", RENAMED_CODE, "Implement searching and sorting", t)

        ground_truth[case_id] = {
            "class": "renamed_restructured_copy",
            "is_anomalous": True,
            "expected_flags": ["HIGH_AST_SIMILARITY"],
            "description": "Restructured twin with renamed identifiers to evade naive text grep"
        }
    print("  Created 3 Renamed Restructured Copy test cases.")

    # 4. Fake History / Scripted Replay (3 repos)
    # 8 commits created exactly 60 seconds apart by an automated script loop
    for i in range(1, 4):
        case_id = f"fake_history_{i}"
        repo_dir = TEST_CASES_DIR / case_id
        repo = create_git_repo(repo_dir)

        t = base_time + timedelta(days=20 + i)
        for commit_idx in range(8):
            make_commit(
                repo,
                "scripted_file.py",
                f"# Generated code chunk {commit_idx}\ndef function_step_{commit_idx}():\n    return {commit_idx * 10}\n",
                f"Automated commit step {commit_idx}",
                t + timedelta(seconds=commit_idx * 60)
            )

        ground_truth[case_id] = {
            "class": "fake_history",
            "is_anomalous": True,
            "expected_flags": ["SCRIPTED_REGULAR_PACE"],
            "description": "Scripted replay with perfectly uniform 60-second commit intervals"
        }
    print("  Created 3 Fake History (Scripted Replay) test cases.")

    # Write ground truth JSON
    GROUND_TRUTH_FILE.write_text(json.dumps(ground_truth, indent=2), encoding="utf-8")
    print(f"Ground truth metadata written to: {GROUND_TRUTH_FILE}")

if __name__ == "__main__":
    generate_dataset()
