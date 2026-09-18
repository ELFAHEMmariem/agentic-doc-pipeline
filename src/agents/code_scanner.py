"""Agent Code Scanner — analyse statique (AST) + interprétation LLM courte."""
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.llm import get_llm, invoke_with_retry
from src.state import AgentState
from src.tools.code_analysis_tools import analyze_code_structure

SCANNER_SYSTEM_PROMPT = """Tu es l'agent Code Scanner.
Tu reçois le résultat brut (JSON) d'une analyse AST d'un code source.
Rédige un court paragraphe (3-5 phrases) résumant la qualité et la structure
du code pour un lecteur non-technique. Ne réinvente pas de chiffres : utilise
uniquement les données fournies."""


def code_scanner_node(state: AgentState) -> dict:
    code = state.get("code_input")
    if not code:
        return {
            "current_step": "code_scanner",
            "messages": [
                AIMessage(content="[Code Scanner] Aucun code source fourni à analyser.")
            ],
        }

    # Étape déterministe : jamais déléguée au LLM.
    scan_result = analyze_code_structure.invoke({"code": code})

    llm = get_llm(temperature=0.2)
    messages = [
        SystemMessage(content=SCANNER_SYSTEM_PROMPT),
        HumanMessage(content=f"Résultat d'analyse (JSON) : {scan_result}"),
    ]
    interpretation = invoke_with_retry(llm, messages)

    return {
        "scan_result": scan_result,
        "current_step": "code_scanner",
        "messages": [AIMessage(content=f"[Code Scanner] {interpretation.content}")],
    }
