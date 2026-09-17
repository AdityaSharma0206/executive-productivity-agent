"""Phase F - deterministic executive daily brief generator.

Builds a concise daily brief from Phase D's resolved task state.
It uses the Phase D metadata `as_of` timestamp by default so the brief is
reproducible and does not invent facts.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = BASE_DIR / "data" / "final_tasks.json"
DEFAULT_OUTPUT = BASE_DIR / "data" / "daily_brief.json"


def load_tasks(path: Path = DEFAULT_INPUT) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def format_deadline(task: dict[str, Any]) -> str:
    deadline = task.get("deadline")
    if not deadline:
        return "No deadline recorded"
    return deadline.replace("T", " ")


def task_line(task: dict[str, Any]) -> str:
    line = task["title"]
    if task.get("deadline"):
        line += " — due " + format_deadline(task)
    if task.get("overdue"):
        line += " [OVERDUE]"
    return line


def build_brief(payload: dict[str, Any], as_of: datetime | None = None) -> dict[str, Any]:
    tasks = payload.get("tasks", [])
    metadata = payload.get("metadata", {})

    if as_of is None:
        as_of_text = metadata.get("as_of")
        as_of = datetime.fromisoformat(as_of_text) if as_of_text else datetime.now()

    my_open = [
        t for t in tasks
        if t.get("type") == "MY_ACTION" and t.get("status") == "OPEN"
    ]
    waiting = [
        t for t in tasks
        if t.get("type") == "WAITING_ON_OTHERS" and t.get("status") == "OPEN"
    ]
    ambiguous = [
        t for t in tasks
        if t.get("type") == "AMBIGUOUS" or t.get("ownership_ambiguous")
    ]
    overdue = [
        t for t in tasks
        if t.get("overdue") and t.get("status") == "OPEN"
    ]
    due_today = [
        t for t in my_open
        if t.get("deadline") and t["deadline"][:10] == as_of.date().isoformat()
    ]
    completed = [
        t for t in tasks if t.get("status") == "COMPLETED"
    ]

    # Put urgent items first, then known deadlines.
    def sort_key(t: dict[str, Any]) -> tuple:
        return (
            not t.get("overdue", False),
            t.get("deadline") is None,
            t.get("deadline") or "9999-12-31T23:59:59",
            t.get("title", ""),
        )

    my_open.sort(key=sort_key)
    waiting.sort(key=sort_key)
    ambiguous.sort(key=sort_key)
    overdue.sort(key=sort_key)

    priorities = []
    for task in overdue:
        priorities.append("Resolve overdue: " + task["title"])
    for task in ambiguous:
        priorities.append("Assign an owner: " + task["title"])
    for task in due_today:
        if task not in overdue:
            priorities.append("Complete today: " + task["title"])

    # Avoid duplicate priority lines.
    priorities = list(dict.fromkeys(priorities))

    if overdue:
        headline = f"{len(overdue)} open task(s) are overdue."
    elif ambiguous:
        headline = f"{len(ambiguous)} task(s) need ownership clarification."
    elif due_today:
        headline = f"{len(due_today)} Arjun-owned task(s) are due today."
    elif my_open or waiting:
        headline = "No overdue Arjun-owned task is recorded."
    else:
        headline = "No open work is recorded in the resolved task state."

    brief = {
        "metadata": {
            "phase": "F",
            "generated_for": metadata.get("executive_name", "Arjun Malhotra"),
            "as_of": as_of.isoformat(sep=" "),
            "source_phase": metadata.get("phase", "D"),
            "source_file": str(DEFAULT_INPUT.name),
        },
        "headline": headline,
        "summary": {
            "open_my_actions": len(my_open),
            "due_today": len(due_today),
            "overdue": len(overdue),
            "waiting_on_others": len(waiting),
            "ownership_unclear": len(ambiguous),
            "completed": len(completed),
            "total_resolved_tasks": len(tasks),
        },
        "priority_actions": [
            {
                "task_id": t["task_id"],
                "title": t["title"],
                "reason": (
                    "OVERDUE" if t.get("overdue")
                    else "DUE_TODAY" if t in due_today
                    else "OWNERSHIP_UNCLEAR"
                ),
                "deadline": t.get("deadline"),
            }
            for t in (
                overdue
                + [t for t in ambiguous if t not in overdue]
                + [t for t in due_today if t not in overdue and t not in ambiguous]
            )
        ],
        "my_actions": [
            {
                "task_id": t["task_id"],
                "title": t["title"],
                "deadline": t.get("deadline"),
                "deadline_text": t.get("deadline_text"),
                "overdue": bool(t.get("overdue")),
            }
            for t in my_open
        ],
        "waiting_on_others": [
            {
                "task_id": t["task_id"],
                "title": t["title"],
                "owner": t.get("owner"),
                "deadline": t.get("deadline"),
                "overdue": bool(t.get("overdue")),
            }
            for t in waiting
        ],
        "ownership_unclear": [
            {
                "task_id": t["task_id"],
                "title": t["title"],
                "deadline": t.get("deadline"),
                "evidence": t.get("evidence", [])[-1:] if t.get("evidence") else [],
            }
            for t in ambiguous
        ],
        "completed": [
            {
                "task_id": t["task_id"],
                "title": t["title"],
                "completed_on": t.get("completed_on"),
            }
            for t in completed
        ],
    }
    return brief


def render_text(brief: dict[str, Any]) -> str:
    s = brief["summary"]
    lines = [
        "EXECUTIVE DAILY BRIEF",
        "=" * 60,
        f"As of: {brief['metadata']['as_of']}",
        "",
        brief["headline"],
        "",
        "PRIORITIES",
        "-" * 60,
    ]

    priorities = brief["priority_actions"]
    if priorities:
        for item in priorities:
            lines.append(f"- {item['title']} [{item['reason']}]")
    else:
        lines.append("- No immediate priority action identified.")

    lines += ["", "MY ACTIONS", "-" * 60]
    if brief["my_actions"]:
        for t in brief["my_actions"]:
            marker = " [OVERDUE]" if t["overdue"] else ""
            due = f"; due {t['deadline']}" if t["deadline"] else "; no deadline"
            lines.append(f"- {t['title']}{due}{marker}")
    else:
        lines.append("- None.")

    lines += ["", "WAITING ON OTHERS", "-" * 60]
    if brief["waiting_on_others"]:
        for t in brief["waiting_on_others"]:
            marker = " [OVERDUE]" if t["overdue"] else ""
            due = f"; due {t['deadline']}" if t["deadline"] else "; no deadline"
            lines.append(f"- {t['title']} — owner: {t['owner']}{due}{marker}")
    else:
        lines.append("- None.")

    lines += ["", "OWNERSHIP / CLARITY FLAGS", "-" * 60]
    if brief["ownership_unclear"]:
        for t in brief["ownership_unclear"]:
            due = f"; due {t['deadline']}" if t["deadline"] else "; no deadline"
            lines.append(f"- {t['title']} — owner unclear{due}")
    else:
        lines.append("- None.")

    lines += [
        "",
        "STATUS",
        "-" * 60,
        f"- Open my actions: {s['open_my_actions']}",
        f"- Due today: {s['due_today']}",
        f"- Overdue: {s['overdue']}",
        f"- Waiting on others: {s['waiting_on_others']}",
        f"- Ownership unclear: {s['ownership_unclear']}",
        f"- Completed: {s['completed']}",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Phase F executive daily brief.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--as-of", default=None, help="YYYY-MM-DD HH:MM; defaults to Phase D metadata.")
    args = parser.parse_args()

    payload = load_tasks(args.input)
    as_of = datetime.strptime(args.as_of, "%Y-%m-%d %H:%M") if args.as_of else None
    brief = build_brief(payload, as_of)
    args.output.write_text(json.dumps(brief, indent=2, ensure_ascii=False), encoding="utf-8")
    print(render_text(brief))
    print("\nPhase F daily brief saved to:", args.output)


if __name__ == "__main__":
    main()
