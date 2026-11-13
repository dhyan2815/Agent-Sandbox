"""Codebase pack ingestion: one document per file, with a heading per function or class.

The engine's chunker splits on headings. Giving every top-level function and class
its own heading means chunks follow the code's structure without the engine knowing
anything about Python.
"""

import ast
import subprocess
from pathlib import Path

from hyper_rag.types import Document


def _python_as_markdown(source: str) -> str:
    """Rewrite a Python file as markdown: module docstring, then one section per symbol."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source
    lines = source.splitlines()
    sections = []
    docstring = ast.get_docstring(tree)
    if docstring:
        sections.append(f"## Module overview\n\n{docstring}")
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            first = min([node.lineno, *(d.lineno for d in node.decorator_list)])
            code = "\n".join(lines[first - 1 : node.end_lineno])
            # Blank lines inside code would be read as paragraph breaks; keep each
            # symbol as one paragraph so it is only split if it exceeds the chunk size.
            code = "\n".join(line for line in code.splitlines() if line.strip())
            sections.append(f"## {kind} {node.name}\n\n{code}")
    constants = [
        "\n".join(lines[node.lineno - 1 : node.end_lineno])
        for node in tree.body
        if isinstance(node, ast.Assign | ast.AnnAssign)
    ]
    if constants:
        sections.append("## Module constants\n\n" + "\n".join(constants))
    return "\n\n".join(sections)


def _repository_root(source: dict, pack, raw_dir: Path) -> Path:
    if source.get("git_url"):
        checkout = raw_dir / "repo"
        if not checkout.exists():
            subprocess.run(
                ["git", "clone", "--depth", "1", source["git_url"], str(checkout)], check=True
            )
        return checkout
    # A relative path is resolved from the project root (the folder that holds packs/).
    return (pack.path.parent.parent / source.get("path", ".")).resolve()


def fetch(pack, raw_dir: Path):
    for source in pack.config.sources:
        root = _repository_root(source, pack, raw_dir)
        files = sorted({path for pattern in source["include"] for path in root.glob(pattern)})
        for path in files:
            text = path.read_text(encoding="utf-8", errors="replace")
            if not text.strip():
                continue
            relative = path.relative_to(root).as_posix()
            if path.suffix == ".py":
                text = _python_as_markdown(text)
            yield Document(id=relative, title=relative, url=relative, text=text)
