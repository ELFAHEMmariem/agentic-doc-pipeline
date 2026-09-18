"""Tests d'intégration du graphe avec un LLM factice (pas d'appel réseau)."""
from langchain_core.messages import AIMessage, HumanMessage

from src.agents.supervisor import RouteDecision
from src.graph import build_graph
from src.state import AgentState


class FakeStructuredLLM:
    def __init__(self, decisions):
        self._decisions = list(decisions)

    def invoke(self, _messages):
        return self._decisions.pop(0)


class FakeChatLLM:
    def __init__(self, content="Réponse factice."):
        self._content = content

    def invoke(self, _messages):
        return AIMessage(content=self._content)


def _base_state(**overrides) -> AgentState:
    state = {
        "messages": [HumanMessage(content="Analyse ce code puis rédige la doc")],
        "current_step": "",
        "next_agent": "",
        "task_type": "unknown",
        "code_input": "def f(x):\n    return x\n",
        "scan_result": None,
        "final_documentation": None,
        "human_approved": None,
        "iteration": 0,
    }
    state.update(overrides)
    return state


def test_supervisor_routes_to_code_scanner_then_interrupts_before_redacteur(monkeypatch):
    decisions = [
        RouteDecision(next="code_scanner", task_type="both", reason="code fourni"),
        RouteDecision(next="redacteur", task_type="both", reason="analyse prête"),
    ]
    fake_supervisor_llm = FakeStructuredLLM(decisions)

    monkeypatch.setattr(
        "src.agents.supervisor.get_llm",
        lambda temperature=None: type(
            "M", (), {"with_structured_output": lambda self, _cls: fake_supervisor_llm}
        )(),
    )
    monkeypatch.setattr("src.agents.code_scanner.get_llm", lambda temperature=None: FakeChatLLM())

    from langgraph.checkpoint.memory import MemorySaver

    graph = build_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test-thread"}}

    graph.invoke(_base_state(), config=config)
    snapshot = graph.get_state(config)

    # Le graphe doit s'être arrêté juste avant "redacteur" (Human-in-the-loop)
    assert snapshot.next == ("redacteur",)
    assert snapshot.values["scan_result"] is not None
    assert "f" in snapshot.values["scan_result"]["functions"]


def test_resume_after_human_approval_runs_redacteur(monkeypatch):
    decisions = [RouteDecision(next="redacteur", task_type="redaction", reason="prêt")]
    fake_supervisor_llm = FakeStructuredLLM(decisions)

    monkeypatch.setattr(
        "src.agents.supervisor.get_llm",
        lambda temperature=None: type(
            "M", (), {"with_structured_output": lambda self, _cls: fake_supervisor_llm}
        )(),
    )
    monkeypatch.setattr(
        "src.agents.redacteur.get_llm",
        lambda temperature=None: FakeChatLLM(content="# Documentation finale"),
    )

    from langgraph.checkpoint.memory import MemorySaver

    graph = build_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test-thread-2"}}

    graph.invoke(_base_state(code_input=None), config=config)
    snapshot = graph.get_state(config)
    assert snapshot.next == ("redacteur",)

    graph.invoke(None, config=config)  # reprise = validation humaine simulée
    snapshot = graph.get_state(config)

    assert snapshot.next == ()
    assert snapshot.values["final_documentation"] == "# Documentation finale"


def test_supervisor_max_iterations_forces_end(monkeypatch):
    """Garde-fou anti-boucle infinie : au-delà de MAX_ITERATIONS -> end."""
    from src.agents.supervisor import supervisor_node

    state = _base_state(iteration=10)
    result = supervisor_node(state)
    assert result["next_agent"] == "end"
