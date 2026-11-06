import ast
import builtins
import hashlib
import textwrap
from dataclasses import dataclass, asdict
from typing import Optional, List, Set, Tuple

BUILTIN_NAMES = set(dir(builtins))

TRIVIAL_METHOD_NAMES = {
    "__init__",
    "__str__",
    "__repr__",
    "__eq__",
    "__ne__",
    "__hash__",
    "__len__",
    "__getitem__",
    "__setitem__",
    "__delitem__",
}

@dataclass
class FunctionFingerprint:
    file_path: str
    function_name: str
    start_line: int
    end_line: int
    statement_count: int
    raw_code: str
    structural_hash: str
    node_types: list[str]

    def to_dict(self):
        return asdict(self)

class ASTNormalizer(ast.NodeTransformer):
    """
    Transforms an AST to normalize identifiers while preserving syntax structure.
    - Strips docstrings
    - Renames user-defined arguments and local variables to canonical placeholders
    - Preserves built-in names and language keywords
    """
    def __init__(self):
        self.var_map: dict[str, str] = {}
        self.var_counter = 0

    def get_canonical_name(self, original: str) -> str:
        if original in BUILTIN_NAMES or original.startswith("__"):
            return original
        if original not in self.var_map:
            self.var_map[original] = f"id_{self.var_counter}"
            self.var_counter += 1
        return self.var_map[original]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        # Strip docstring if present
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:]

        # Rename arguments
        for arg in node.args.args:
            if arg.arg != "self" and arg.arg != "cls":
                arg.arg = self.get_canonical_name(arg.arg)

        # Rename function name
        if not node.name.startswith("__"):
            node.name = self.get_canonical_name(node.name)

        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:]

        for arg in node.args.args:
            if arg.arg != "self" and arg.arg != "cls":
                arg.arg = self.get_canonical_name(arg.arg)

        if not node.name.startswith("__"):
            node.name = self.get_canonical_name(node.name)

        self.generic_visit(node)
        return node

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if node.id not in ("self", "cls") and node.id not in BUILTIN_NAMES:
            node.id = self.get_canonical_name(node.id)
        return node

def is_trivial_function(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Checks whether a function is trivial boilerplate (very short, getters, pass, init)."""
    if func_node.name in TRIVIAL_METHOD_NAMES:
        return True

    # Check non-docstring statements
    body = func_node.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]

    # Empty or single pass
    if not body or (len(body) == 1 and isinstance(body[0], ast.Pass)):
        return True

    # Simple getter: return self._x or return 0
    if len(body) == 1 and isinstance(body[0], ast.Return):
        ret_val = body[0].value
        if isinstance(ret_val, (ast.Constant, ast.Attribute, ast.Name)):
            return True

    # Simple setter: self._x = val
    if len(body) == 1 and isinstance(body[0], ast.Assign):
        if len(body[0].targets) == 1 and isinstance(body[0].targets[0], ast.Attribute):
            return True

    # Very short function with <= 2 simple statements
    if len(body) <= 2:
        # Check total AST nodes
        node_count = sum(1 for _ in ast.walk(func_node))
        if node_count < 12:
            return True

    return False

def extract_node_type_sequence(node: ast.AST) -> list[str]:
    """Flattens AST into node type labels for fuzzy/structural n-gram comparisons."""
    types = []
    for n in ast.walk(node):
        types.append(type(n).__name__)
    return types

def extract_function_fingerprints_from_source(source_code: str, file_path: str = "") -> list[FunctionFingerprint]:
    """
    Parses Python source code, extracts non-trivial functions, normalizes ASTs,
    and returns FunctionFingerprint objects.
    """
    try:
        tree = ast.parse(source_code)
    except (SyntaxError, ValueError):
        return []

    lines = source_code.splitlines()
    fingerprints: list[FunctionFingerprint] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if is_trivial_function(node):
                continue

            start_line = getattr(node, "lineno", 1)
            end_line = getattr(node, "end_lineno", start_line)
            
            raw_snippet = "\n".join(lines[start_line - 1 : end_line]) if lines else ""
            dedented_snippet = textwrap.dedent(raw_snippet)
            statement_count = len(node.body)

            # Deep copy / normalize node
            normalized_tree = ast.parse(dedented_snippet)
            normalizer = ASTNormalizer()
            normalizer.visit(normalized_tree)
            ast.fix_missing_locations(normalized_tree)

            structural_dump = ast.dump(normalized_tree, annotate_fields=False)
            structural_hash = hashlib.sha256(structural_dump.encode("utf-8")).hexdigest()
            node_types = extract_node_type_sequence(normalized_tree)

            fp = FunctionFingerprint(
                file_path=file_path,
                function_name=node.name,
                start_line=start_line,
                end_line=end_line,
                statement_count=statement_count,
                raw_code=raw_snippet,
                structural_hash=structural_hash,
                node_types=node_types,
            )
            fingerprints.append(fp)

    return fingerprints

def compute_structural_similarity(fp1: FunctionFingerprint, fp2: FunctionFingerprint) -> float:
    """
    Computes structural similarity score [0.0 .. 1.0] between two function fingerprints.
    - If exact normalized structural hash matches: 1.0 (exact structural twin)
    - Otherwise: compute Jaccard similarity of 3-grams of AST node types.
    """
    if fp1.structural_hash == fp2.structural_hash:
        return 1.0

    # N-gram Jaccard on node types
    def get_ngrams(seq: list[str], n: int = 3) -> set[tuple[str, ...]]:
        if len(seq) < n:
            return {tuple(seq)}
        return {tuple(seq[i : i + n]) for i in range(len(seq) - n + 1)}

    ngrams1 = get_ngrams(fp1.node_types, 3)
    ngrams2 = get_ngrams(fp2.node_types, 3)

    if not ngrams1 or not ngrams2:
        return 0.0

    intersection = len(ngrams1 & ngrams2)
    union = len(ngrams1 | ngrams2)
    return intersection / union if union > 0 else 0.0
