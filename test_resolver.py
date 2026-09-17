"""Small regression tests for the supplied Assignment 1 datapack."""

import json
from pathlib import Path
from datetime import datetime

from resolver import resolve

BASE = Path(__file__).resolve().parent
INPUT = BASE / "data" / "candidate_commitments.json"
OUTPUT = BASE / "data" / "_test_final_tasks.json"

result = resolve(INPUT, OUTPUT, datetime(2026, 9, 25, 17, 0))
by_title = {t["title"]: t for t in result["tasks"]}

assert len(result["tasks"]) == 6, "Expected 6 semantic tasks after deduplication"

vendor = by_title["Send updated vendor list to Raghav Sethi"]
assert vendor["type"] == "MY_ACTION"
assert vendor["status"] == "OPEN"
assert vendor["deadline_date"] == "2026-09-23"
assert vendor["deadline_precision"] == "morning"
assert vendor["candidate_ids"] == ["C001", "C002", "C003", "C005", "C004"]

review = by_title["Review Q3 campaign deck"]
assert review["deadline"] == "2026-09-24T09:30:00"
assert review["status"] == "OPEN"

receive_deck = by_title["Receive Q3 campaign deck from Neha Kapoor"]
assert receive_deck["deadline_date"] == "2026-09-24"
assert receive_deck["status"] == "OPEN"

meridian = by_title["Confirm Meridian Logistics call with Priya Nair"]
assert meridian["status"] == "COMPLETED"

expense = by_title["Receive July expense variance report from Divya Rao"]
assert expense["status"] == "COMPLETED"

lease = by_title["Obtain authorized signature for Mumbai office lease renewal"]
assert lease["type"] == "AMBIGUOUS"
assert lease["owner"] is None
assert lease["status"] == "UNCLEAR"
assert lease["deadline_date"] == "2026-09-25"
assert lease["overdue"] is False

print("All Phase D tests passed.")
OUTPUT.unlink(missing_ok=True)
