"""Outils déterministes d'analyse de code (AST) — pas de LLM ici.

Le LLM ne fait QUE résumer/interpréter la sortie structurée : on évite de lui
faire "halluciner" une structure de code, l'analyse elle-même est 100% Python.
"""
import ast

from langchain_core.tools import tool
from radon.complexity import cc_visit


@tool
def analyze_code_structure(code: str) -> dict:
    """Analyse la structure statique d'un code source Python.

    Retourne : fonctions, classes, imports, nombre de lignes, complexité
    cyclomatique moyenne et une liste d'anomalies détectées (docstrings
    manquantes, fonctions trop longues, etc.).
    """
    issues: list[str] = []

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return {
            "functions": [],
            "classes": [],
            "imports": [],
            "loc": len(code.splitlines()),
            "cyclomatic_complexity": 0.0,
            "issues": [f"Erreur de syntaxe: {exc}"],
            "summary": "Le code fourni n'est pas un Python valide.",
        }

    functions = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.extend(f"{module}.{alias.name}" for alias in node.names)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            if not ast.get_docstring(node):
                issues.append(f"Fonction '{node.name}' sans docstring")
            body_len = len(node.body)
            if body_len > 40:
                issues.append(f"Fonction '{node.name}' trop longue ({body_len} lignes)")

    try:
        blocks = cc_visit(code)
        avg_complexity = (
            sum(b.complexity for b in blocks) / len(blocks) if blocks else 0.0
        )
    except Exception:
        avg_complexity = 0.0

    return {
        "functions": functions,
        "classes": classes,
        "imports": sorted(set(imports)),
        "loc": len(code.splitlines()),
        "cyclomatic_complexity": round(avg_complexity, 2),
        "issues": issues,
        "summary": (
            f"{len(functions)} fonction(s), {len(classes)} classe(s), "
            f"complexité cyclomatique moyenne {round(avg_complexity, 2)}."
        ),
    }
