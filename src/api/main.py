"""API FastAPI exposant le graphe multi-agents avec Human-in-the-loop."""
import logging

from fastapi import Depends, FastAPI, Header, HTTPException
from langchain_core.messages import HumanMessage
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request

from src.api.schemas import ChatRequest, ChatResponse, ResumeRequest
from src.config import configure_langsmith, get_settings
from src.graph import get_graph

settings = get_settings()
configure_langsmith(settings)
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("sprint2-multi-agent-system")

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Sprint 2 — Système Multi-Agents (Superviseur & Mémoire)")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def verify_api_key(x_api_key: str = Header(...)) -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Clé API invalide")


def _snapshot_to_response(thread_id: str, snapshot) -> ChatResponse:
    state = snapshot.values
    status = "interrupted" if snapshot.next else "completed"
    last_message = state["messages"][-1].content if state.get("messages") else None
    return ChatResponse(
        thread_id=thread_id,
        status=status,
        current_step=state.get("current_step", ""),
        scan_result=state.get("scan_result"),
        final_documentation=state.get("final_documentation"),
        last_message=last_message,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
def chat(request: Request, body: ChatRequest):
    graph = get_graph()
    config = {"configurable": {"thread_id": body.thread_id}}

    initial_state = {
        "messages": [HumanMessage(content=body.message)],
        "code_input": body.code_input,
        "current_step": "",
        "next_agent": "",
        "task_type": "unknown",
        "scan_result": None,
        "final_documentation": None,
        "human_approved": None,
        "iteration": 0,
    }

    try:
        graph.invoke(initial_state, config=config)
    except Exception:
        logger.exception("Échec de l'exécution du graphe (thread_id=%s)", body.thread_id)
        raise HTTPException(status_code=500, detail="Erreur interne lors de l'exécution du graphe")

    snapshot = graph.get_state(config)
    return _snapshot_to_response(body.thread_id, snapshot)


@app.post("/chat/resume", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
def resume(request: Request, body: ResumeRequest):
    """Reprend l'exécution après le point d'interruption (interrupt_before=['redacteur'])."""
    graph = get_graph()
    config = {"configurable": {"thread_id": body.thread_id}}

    snapshot = graph.get_state(config)
    if not snapshot.next:
        raise HTTPException(status_code=409, detail="Aucune exécution en attente de validation")

    if not body.approved:
        graph.update_state(config, {"next_agent": "end", "current_step": "human_rejected"})
        snapshot = graph.get_state(config)
        return _snapshot_to_response(body.thread_id, snapshot)

    if body.edited_scan_result is not None:
        graph.update_state(config, {"scan_result": body.edited_scan_result})

    try:
        graph.invoke(None, config=config)  # reprise depuis le checkpoint
    except Exception:
        logger.exception("Échec de la reprise du graphe (thread_id=%s)", body.thread_id)
        raise HTTPException(status_code=500, detail="Erreur interne lors de la reprise du graphe")

    snapshot = graph.get_state(config)
    return _snapshot_to_response(body.thread_id, snapshot)


@app.get("/chat/state/{thread_id}", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
def get_state(thread_id: str):
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    if not snapshot.values:
        raise HTTPException(status_code=404, detail="thread_id inconnu")
    return _snapshot_to_response(thread_id, snapshot)
