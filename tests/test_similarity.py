import pytest
from backend.similarity.ast_normalizer import (
    extract_function_fingerprints_from_source,
    compute_structural_similarity,
    is_trivial_function,
)
from backend.similarity.baseline_text import compute_text_similarity

def test_ast_normalization_variable_renaming():
    code_original = """
def calculate_metrics(items, threshold):
    \"\"\"Docstring explaining metrics calculation.\"\"\"
    total = 0
    count = 0
    for item in items:
        if item > threshold:
            total += item
            count += 1
    if count == 0:
        return 0
    return total / count
"""

    code_renamed = """
def compute_scores(data_list, min_val):
    # Notice different docstring / comments and renamed identifiers
    sum_val = 0
    num_matches = 0
    for val in data_list:
        if val > min_val:
            sum_val += val
            num_matches += 1
    if num_matches == 0:
        return 0
    return sum_val / num_matches
"""

    fps1 = extract_function_fingerprints_from_source(code_original, "original.py")
    fps2 = extract_function_fingerprints_from_source(code_renamed, "renamed.py")

    assert len(fps1) == 1
    assert len(fps2) == 1

    # Exact structural twin test
    assert fps1[0].structural_hash == fps2[0].structural_hash
    score = compute_structural_similarity(fps1[0], fps2[0])
    assert score == 1.0

    # Whereas text diff should show significant discrepancy due to renamed variables
    text_score = compute_text_similarity(code_original, code_renamed)
    assert text_score < 0.65, f"Text score was {text_score}, expected < 0.65"

def test_trivial_boilerplate_exclusion():
    boilerplate_code = """
class DataModel:
    def __init__(self, val):
        self.val = val

    def get_val(self):
        return self.val

    def set_val(self, val):
        self.val = val

    def empty_hook(self):
        pass

    def real_business_logic(self, matrix, multiplier):
        output = []
        for row in matrix:
            new_row = [elem * multiplier for elem in row if elem > 0]
            output.append(new_row)
        return output
"""
    fps = extract_function_fingerprints_from_source(boilerplate_code, "model.py")
    # Only real_business_logic should be extracted; __init__, get_val, set_val, empty_hook should be ignored
    names = [f.function_name for f in fps]
    assert "real_business_logic" in names
    assert "__init__" not in names
    assert "get_val" not in names
    assert "set_val" not in names
    assert "empty_hook" not in names

def test_structural_similarity_dissimilar_functions():
    func1 = """
def binary_search(arr, target):
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
"""
    func2 = """
def read_and_parse_json(file_path):
    import json
    with open(file_path, 'r') as f:
        data = json.load(f)
    result = {}
    for k, v in data.items():
        result[str(k).upper()] = str(v)
    return result
"""
    fps1 = extract_function_fingerprints_from_source(func1, "search.py")
    fps2 = extract_function_fingerprints_from_source(func2, "parser.py")

    assert len(fps1) == 1
    assert len(fps2) == 1

    sim = compute_structural_similarity(fps1[0], fps2[0])
    assert sim < 0.35, f"Similarity between unrelated functions was {sim}, expected < 0.35"
