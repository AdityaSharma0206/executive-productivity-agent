"""Quick demonstration of the Phase E query engine."""
from pathlib import Path
from query_engine import answer, load_tasks

BASE_DIR = Path(__file__).resolve().parent
payload = load_tasks(BASE_DIR / "data" / "final_tasks.json")

questions = [
    "What did I promise Raghav?",
    "What needs action today?",
    "What am I waiting on?",
    "What is overdue?",
    "What has unclear ownership?",
]

for question in questions:
    print("\n" + "=" * 70)
    print("QUESTION:", question)
    print("-" * 70)
    print(answer(question, payload))
