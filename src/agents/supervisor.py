"""Agent Superviseur — route la demande vers Code Scanner ou Rédacteur.

Utilise une sortie structurée (Pydantic) plutôt qu'un parsing de texte libre :
plus fiable, testable, et observable dans LangSmith comme un appel "tool call".
"""
from typing import Literal

from langchain_core.messages import SystemMessage
from pydantic import BaseModel, Field

from src.llm import get_llm, invoke_with_retry
from src.state import AgentState

MAX_ITERATIONS = 6

SUPERVISOR_SYSTEM_PROMPT = """Tu es le Superviseur d'un système multi-agents.
Deux agents sont disponibles :
- "code_scanner" : analyse la structure d'un code source fourni par l'utilisateur
  (fonctions, classes, imports, complexité). Choisis-le si un code source est présent
  dans la demande ET n'a pas encore été analysé (scan_result vide).
- "redacteur" : rédige la documentation finale à partir du résultat d'analyse
  (scan_result). Choisis-le uniquement si scan_result est déjà disponible, ou si
  la demande ne contient aucun code et porte sur de la rédaction pure.

Réponds uniquement via l'outil structuré demandé. Termine par "end" si aucune
action supplémentaire n'est nécessaire (documentation déjà produite)."""


class RouteDecision(BaseModel):
    next: Literal["code_scanner", "redacteur", "end"] = Field(
        description="Prochain agent à activer, ou 'end' si le travail est terminé."
    )
    task_type: Literal["code_scan", "redaction", "both", "unknown"] = Field(
        description="Nature de la demande utilisateur."
    )
    reason: str = Field(description="Justification courte de la décision (1 phrase).")


def supervisor_node(state: AgentState) -> dict:
    llm = get_llm(temperature=0.0).with_structured_output(RouteDecision)

    # Garde-fou anti-boucle infinie : au-delà de MAX_ITERATIONS on force la fin.
    iteration = state.get("iteration", 0) + 1
    if iteration > MAX_ITERATIONS:
        return {
            "next_agent": "end",
            "current_step": "supervisor",
            "iteration": iteration,
        }

    context_hint = (
        f"\n\n[État courant] scan_result présent: {bool(state.get('scan_result'))}, "
        f"final_documentation présent: {bool(state.get('final_documentation'))}, "
        f"code_input présent: {bool(state.get('code_input'))}."
    )
    messages = [SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT + context_hint)] + state["messages"]

    decision: RouteDecision = invoke_with_retry(llm, messages)

    return {
        "next_agent": decision.next,
        "task_type": decision.task_type,
        "current_step": "supervisor",
        "iteration": iteration,
        "messages": [
            SystemMessage(content=f"[Superviseur] -> {decision.next} ({decision.reason})")
        ],
    }


def route_from_supervisor(state: AgentState) -> str:
    """Fonction de routage utilisée par add_conditional_edges."""
    return state.get("next_agent") or "end"
