"""Construction du StateGraph : Superviseur + Code Scanner + Rédacteur.

Topologie :

    START -> supervisor -> (conditionnel) -> code_scanner -> supervisor
                                         `-> redacteur [INTERRUPT_BEFORE] -> END
                                         `-> END

Le Superviseur reboucle après chaque agent spécialisé pour ré-évaluer l'état
et décider de la suite (permet un enchaînement code_scanner -> redacteur sans
intervention externe, tout en gardant le contrôle centralisé).
"""
from langgraph.graph import END, START, StateGraph

from src.agents.code_scanner import code_scanner_node
from src.agents.redacteur import redacteur_node
from src.agents.supervisor import route_from_supervisor, supervisor_node
from src.config import get_settings
from src.state import AgentState


def get_checkpointer():
    settings = get_settings()
    if settings.checkpointer_backend == "postgres":
        from langgraph.checkpoint.postgres import PostgresSaver

        cm = PostgresSaver.from_conn_string(settings.postgres_dsn)
        checkpointer = cm.__enter__()
        checkpointer.setup()
        return checkpointer

    from langgraph.checkpoint.memory import MemorySaver

    return MemorySaver()


def build_graph(checkpointer=None):
    builder = StateGraph(AgentState)

    builder.add_node("supervisor", supervisor_node)
    builder.add_node("code_scanner", code_scanner_node)
    builder.add_node("redacteur", redacteur_node)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "code_scanner": "code_scanner",
            "redacteur": "redacteur",
            "end": END,
        },
    )
    builder.add_edge("code_scanner", "supervisor")
    builder.add_edge("redacteur", END)

    checkpointer = checkpointer or get_checkpointer()

    # Human-in-the-loop : l'exécution se fige AVANT redacteur. Il faut un appel
    # explicite à graph.invoke(None, config) (reprise) après validation humaine.
    return builder.compile(checkpointer=checkpointer, interrupt_before=["redacteur"])


_graph_singleton = None


def get_graph():
    global _graph_singleton
    if _graph_singleton is None:
        _graph_singleton = build_graph()
    return _graph_singleton
