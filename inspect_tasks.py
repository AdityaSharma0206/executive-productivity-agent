"""Human-readable inspection of Phase D final task state."""

import json
from pathlib import Path

PATH = Path(__file__).resolve().parent / "data" / "final_tasks.json"

data = json.loads(PATH.read_text(encoding="utf-8"))

print("\nFINAL TASK STATE")
print("=" * 80)
print("As of:", data["metadata"]["as_of"])
print("Tasks:", data["metadata"]["resolved_tasks"])

for task in data["tasks"]:
    print("\n" + task["task_id"] + " - " + task["title"])
    print("  Type:      ", task["type"])
    print("  Status:    ", task["status"])
    print("  Owner:     ", task["owner"] or "UNKNOWN / UNASSIGNED")
    print("  Related:   ", task["related_person"] or "—")
    print("  Deadline:  ", task["deadline_text"] or "—")
    print("  Overdue:   ", task["overdue"])
    print("  Candidates:", ", ".join(task["candidate_ids"]))
