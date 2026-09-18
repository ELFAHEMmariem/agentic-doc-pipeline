from src.tools.code_analysis_tools import analyze_code_structure

SAMPLE_CODE = '''
import os
from typing import List


class Foo:
    """Classe d'exemple."""

    def bar(self, x: int) -> int:
        """Retourne x+1."""
        return x + 1


def baz(items: List[int]) -> int:
    total = 0
    for i in items:
        if i % 2 == 0:
            total += i
    return total
'''

BAD_SYNTAX_CODE = "def foo(:\n    pass"

MISSING_DOCSTRING_CODE = "def foo(x):\n    return x\n"


def test_analyze_code_structure_extracts_structure():
    result = analyze_code_structure.invoke({"code": SAMPLE_CODE})
    assert "Foo" in result["classes"]
    assert "bar" in result["functions"]
    assert "baz" in result["functions"]
    assert "os" in result["imports"]
    assert result["loc"] > 0


def test_analyze_code_structure_handles_syntax_error():
    result = analyze_code_structure.invoke({"code": BAD_SYNTAX_CODE})
    assert result["functions"] == []
    assert "Erreur de syntaxe" in result["issues"][0]


def test_analyze_code_structure_flags_missing_docstring():
    result = analyze_code_structure.invoke({"code": MISSING_DOCSTRING_CODE})
    assert any("sans docstring" in issue for issue in result["issues"])
