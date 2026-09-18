"""CLI interactif pour tester le graphe en local sans API HTTP.

Usage:
    python scripts/run_cli.py
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import HumanMessage  # noqa: E402

from src.config import configure_langsmith, get_settings  # noqa: E402
from src.graph import get_graph  # noqa: E402


def main():
    settings = get_settings()
    configure_langsmith(settings)
    graph = get_graph()

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    print(f"[thread_id={thread_id}]")

    message = input("Votre demande : ")
    code_path = input("Chemin d'un fichier de code à analyser (vide si aucun) : ").strip()
    code_input = Path(code_path).read_text() if code_path else None

    state = {
        "messages": [HumanMessage(content=message)],
        "code_input": code_input,
        "current_step": "",
        "next_agent": "",
        "task_type": "unknown",
        "scan_result": None,
        "final_documentation": None,
        "human_approved": None,
        "iteration": 0,
    }

    graph.invoke(state, config=config)
    snapshot = graph.get_state(config)

    if snapshot.next:
        print("\n--- Exécution interrompue avant rédaction (Human-in-the-loop) ---")
        print("scan_result :", snapshot.values.get("scan_result"))
        approve = input("Valider et lancer la rédaction finale ? (o/n) : ").strip().lower()
        if approve == "o":
            graph.invoke(None, config=config)
            snapshot = graph.get_state(config)
            print("\n=== Documentation finale ===\n")
            print(snapshot.values.get("final_documentation"))
        else:
            print("Rédaction annulée par l'utilisateur.")
    else:
        print("\n=== Résultat ===\n")
        print(snapshot.values["messages"][-1].content)


if __name__ == "__main__":
    main()
