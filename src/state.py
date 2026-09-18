"""Définition de l'état global partagé entre tous les nœuds du graphe."""
from typing import Annotated, Literal, Optional, TypedDict

from langgraph.graph.message import add_messages


class ScanResult(TypedDict, total=False):
    functions: list[str]
    classes: list[str]
    imports: list[str]
    loc: int
    cyclomatic_complexity: float
    issues: list[str]
    summary: str


class AgentState(TypedDict):
    """État global (shared memory) du graphe multi-agents.

    - messages : historique de conversation (réducteur add_messages => append,
      jamais d'écrasement, gère aussi la dédup par id de message).
    - current_step : nom du dernier nœud exécuté (traçabilité / debug).
    - next_agent : décision de routage émise par le Superviseur.
    - task_type : classification de la demande utilisateur.
    - code_input : code source brut fourni par l'utilisateur, si présent.
    - scan_result : sortie structurée de l'agent Code Scanner.
    - final_documentation : sortie finale de l'agent Rédacteur.
    - human_approved : statut de la validation humaine (Human-in-the-loop).
    - iteration : compteur de boucles superviseur -> agent (garde-fou anti-boucle infinie).
    """

    messages: Annotated[list, add_messages]
    current_step: str
    next_agent: Literal["code_scanner", "redacteur", "end", ""]
    task_type: Literal["code_scan", "redaction", "both", "unknown"]
    code_input: Optional[str]
    scan_result: Optional[ScanResult]
    final_documentation: Optional[str]
    human_approved: Optional[bool]
    iteration: int
