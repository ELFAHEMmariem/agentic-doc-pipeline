"""Agent Rédacteur — formate la documentation finale (Markdown).

Ce nœud n'est atteint qu'après validation humaine : le graphe est compilé avec
interrupt_before=["redacteur"], donc l'exécution s'arrête juste avant ce nœud
et attend un signal de reprise (voir api/main.py -> POST /chat/resume).
"""
from langchain_core.messages import AIMessage, SystemMessage

from src.llm import get_llm, invoke_with_retry
from src.state import AgentState

REDACTEUR_SYSTEM_PROMPT = """Tu es l'agent Rédacteur.
À partir du résultat d'analyse de code (scan_result) et de l'historique de la
conversation, rédige une documentation technique complète au format Markdown :
- Titre
- Vue d'ensemble (résumé)
- Structure (fonctions, classes, imports)
- Complexité et points d'attention (issues)
- Recommandations

Sois précis, structuré, et n'invente aucune donnée absente de scan_result."""


def redacteur_node(state: AgentState) -> dict:
    scan_result = state.get("scan_result")
    llm = get_llm(temperature=0.3)

    messages = [SystemMessage(content=REDACTEUR_SYSTEM_PROMPT)] + state["messages"]
    if scan_result:
        messages.append(
            SystemMessage(content=f"Données d'analyse disponibles (JSON) : {scan_result}")
        )

    result = invoke_with_retry(llm, messages)

    return {
        "final_documentation": result.content,
        "next_agent": "end",
        "current_step": "redacteur",
        "messages": [AIMessage(content=result.content)],
    }
