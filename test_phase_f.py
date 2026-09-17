"""Basic Phase F tests."""
from datetime import datetime
from pathlib import Path

from brief_generator import build_brief, load_tasks

BASE_DIR = Path(__file__).resolve().parent
payload = load_tasks(BASE_DIR / "data" / "final_tasks.json")
brief = build_brief(payload)

assert brief["metadata"]["phase"] == "F"
assert brief["summary"]["total_resolved_tasks"] == len(payload["tasks"])
assert brief["summary"]["overdue"] == sum(
    1 for t in payload["tasks"] if t.get("overdue") and t.get("status") == "OPEN"
)
assert brief["summary"]["ownership_unclear"] >= 1
assert len(brief["my_actions"]) == sum(
    1 for t in payload["tasks"] if t.get("type") == "MY_ACTION" and t.get("status") == "OPEN"
)

print("Phase F tests passed.")
print("Headline:", brief["headline"])
