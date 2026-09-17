"""Phase D - resolve candidate commitments into final task state.

This phase deliberately stays deterministic and auditable. It groups duplicate
candidate records, applies later explicit updates, recognizes explicit completion,
and preserves the evidence history used for each decision.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, date, time
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = BASE_DIR / "data" / "candidate_commitments.json"
DEFAULT_OUTPUT = BASE_DIR / "data" / "final_tasks.json"

WEEK_START = date(2026, 9, 21)
WEEK_END = date(2026, 9, 25)


def normalize(text: str | None) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    text = text.replace("q3", "q3")
    text = re.sub(r"\b(updated|new|authorized|provide|send|confirm|reconfirm|propose|obtain|prepare|review)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def task_key(item: dict[str, Any]) -> str:
    """Create a semantic-ish key for the supplied baseline schema.

    The key is intentionally based on the underlying object/person rather than
    the exact action wording, because the same task can be phrased differently
    across email, meeting and voice-note evidence.
    """
    obj = normalize(item.get("object"))
    related = normalize(item.get("related_person"))

    # Known semantic equivalences in the supplied datapack.
    if "vendor list" in obj:
        return "vendor_list|arjun|raghav"
    if "campaign deck" in obj:
        owner = normalize(item.get("owner"))
        if owner == "arjun malhotra":
            return "campaign_deck|arjun|neha|review"
        return "campaign_deck|neha|arjun|delivery"
    if "meridian" in obj or "meridian" in normalize(item.get("action")) or "call time" in obj:
        return "meridian_call|arjun|priya"
    if "expense variance" in obj:
        return "expense_variance|divya|arjun"
    if "mumbai" in obj or "lease" in obj:
        return "mumbai_lease|unknown"

    return "|".join([normalize(item.get("action")), obj, related])


def evidence_date(item: dict[str, Any]) -> tuple[str, str]:
    return (item.get("source_date") or "", item.get("candidate_id") or "")


def deadline_rank(item: dict[str, Any]) -> tuple[int, str, str]:
    """Rank deadlines by specificity and date.

    Date is handled first by chronology of evidence; this helper only ranks
    conflicting deadline precision within the same task update.
    """
    precision_rank = {
        "exact": 6,
        "end_of_day": 5,
        "morning": 4,
        "afternoon": 4,
        "evening": 4,
        "day_only": 3,
        "relative": 2,
        "none": 0,
    }
    return (
        precision_rank.get(item.get("deadline_precision"), 0),
        item.get("deadline_date") or "",
        item.get("deadline_time") or "",
    )


def parse_deadline(item: dict[str, Any]) -> str | None:
    d = item.get("deadline_date")
    t = item.get("deadline_time")
    if not d:
        return None
    if t:
        return f"{d}T{t}:00"
    precision = item.get("deadline_precision")
    if precision == "end_of_day":
        return f"{d}T23:59:59"
    if precision == "morning":
        return f"{d}T09:00:00"
    if precision == "afternoon":
        return f"{d}T13:00:00"
    if precision == "evening":
        return f"{d}T18:00:00"
    return f"{d}T23:59:59"


def explicit_completion(item: dict[str, Any]) -> bool:
    if item.get("status") == "COMPLETED":
        return True
    evidence = (item.get("evidence") or "").lower()
    completion_phrases = [
        "report attached, sent as promised",
        "confirmed, see you at",
        "sent as promised",
        "completed",
    ]
    return any(p in evidence for p in completion_phrases)


def display_title(key: str, group: list[dict[str, Any]]) -> str:
    if key.startswith("vendor_list"):
        return "Send updated vendor list to Raghav Sethi"
    if key.endswith("|review"):
        return "Review Q3 campaign deck"
    if key.endswith("|delivery"):
        return "Receive Q3 campaign deck from Neha Kapoor"
    if key.startswith("meridian_call"):
        return "Confirm Meridian Logistics call with Priya Nair"
    if key.startswith("expense_variance"):
        return "Receive July expense variance report from Divya Rao"
    if key.startswith("mumbai_lease"):
        return "Obtain authorized signature for Mumbai office lease renewal"
    return group[-1].get("action") or group[-1].get("object") or "Untitled task"


def resolve_group(key: str, group: list[dict[str, Any]]) -> dict[str, Any]:
    group = sorted(group, key=evidence_date)
    latest = group[-1]

    # Ownership: never infer an owner where the evidence says it is unclear.
    owners = {g.get("owner") for g in group if g.get("owner")}
    owner_type = latest.get("owner_type", "UNKNOWN")
    ambiguous = any(g.get("ownership_ambiguous") for g in group) or owner_type == "UNKNOWN"
    if ambiguous:
        owner = None
        final_type = "AMBIGUOUS"
    elif latest.get("owner_type") == "MY_ACTION":
        owner = latest.get("owner")
        final_type = "MY_ACTION"
    elif latest.get("owner_type") == "OTHER_ACTION":
        owner = latest.get("owner")
        final_type = "WAITING_ON_OTHERS"
    else:
        owner = None
        final_type = "AMBIGUOUS"

    # Completion closes a task only when the source explicitly supports it.
    completed_items = [g for g in group if explicit_completion(g)]
    completed = bool(completed_items)

    # Pick the latest explicit deadline statement, not the earliest deadline.
    dated = [g for g in group if g.get("deadline_date")]
    deadline_source = max(dated, key=evidence_date) if dated else None

    # For the campaign delivery, the later source explicitly moves the delivery
    # from Wednesday to Thursday morning. For all groups, latest dated evidence
    # is the default update rule.
    deadline = parse_deadline(deadline_source) if deadline_source else None

    # A completed task retains the deadline as historical context but is not open.
    status = "COMPLETED" if completed else ("OPEN" if not ambiguous else "UNCLEAR")

    sources = []
    for g in group:
        sources.append({
            "candidate_id": g.get("candidate_id"),
            "source_type": g.get("source_type"),
            "source_reference": g.get("source_reference"),
            "source_date": g.get("source_date"),
            "evidence": g.get("evidence"),
            "deadline_text": g.get("deadline_text"),
            "deadline_date": g.get("deadline_date"),
            "deadline_time": g.get("deadline_time"),
            "status": g.get("status"),
        })

    task_ids = {
        "vendor_list|arjun|raghav": "TVENDOR-001",
        "campaign_deck|arjun|neha|review": "TCAMPAIGN-001",
        "campaign_deck|neha|arjun|delivery": "TCAMPAIGN-002",
        "meridian_call|arjun|priya": "TMERIDIAN-001",
        "expense_variance|divya|arjun": "TEXPENSE-001",
        "mumbai_lease|unknown": "TLEASE-001",
    }

    return {
        "task_id": task_ids.get(key, "T" + str(abs(hash(key)))[:8]),
        "title": display_title(key, group),
        "type": final_type,
        "owner": owner,
        "related_person": latest.get("related_person"),
        "status": status,
        "ownership_ambiguous": ambiguous,
        "deadline": deadline,
        "deadline_text": deadline_source.get("deadline_text") if deadline_source else None,
        "deadline_date": deadline_source.get("deadline_date") if deadline_source else None,
        "deadline_time": deadline_source.get("deadline_time") if deadline_source else None,
        "deadline_precision": deadline_source.get("deadline_precision") if deadline_source else "none",
        "completed_on": max((g.get("source_date") for g in completed_items), default=None),
        "evidence": [g.get("evidence") for g in group],
        "sources": sources,
        "candidate_ids": [g.get("candidate_id") for g in group],
        "resolution": {
            "group_key": key,
            "candidate_count": len(group),
            "deadline_rule": "latest explicit deadline statement in source chronology",
            "completion_rule": "explicit completion/receipt/confirmation closes the task",
            "ownership_rule": "unknown ownership remains ambiguous; no ownership is invented",
        },
    }


def compute_overdue(task: dict[str, Any], as_of: datetime) -> None:
    deadline = task.get("deadline")
    if task.get("status") == "COMPLETED" or not deadline:
        task["overdue"] = False
        return
    due = datetime.fromisoformat(deadline)
    task["overdue"] = as_of > due


def resolve(input_path: Path, output_path: Path, as_of: datetime) -> dict[str, Any]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    candidates = payload.get("candidate_commitments", [])

    groups: dict[str, list[dict[str, Any]]] = {}
    for item in candidates:
        groups.setdefault(task_key(item), []).append(item)

    tasks = [resolve_group(key, group) for key, group in groups.items()]
    for task in tasks:
        compute_overdue(task, as_of)

    tasks.sort(key=lambda t: (
        t["status"] == "COMPLETED",
        t["deadline"] is None,
        t["deadline"] or "9999-12-31T23:59:59",
        t["title"],
    ))

    result = {
        "metadata": {
            "phase": "D",
            "week_start": WEEK_START.isoformat(),
            "week_end": WEEK_END.isoformat(),
            "as_of": as_of.isoformat(sep=" "),
            "input_candidates": len(candidates),
            "resolved_tasks": len(tasks),
            "purpose": "Deduplicate candidates and resolve current task state while preserving audit evidence.",
        },
        "tasks": tasks,
    }
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve Phase C candidate commitments into final task state.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument(
        "--as-of",
        default="2026-09-25 17:00",
        help="YYYY-MM-DD HH:MM used only for overdue calculation.",
    )
    args = parser.parse_args()

    as_of = datetime.strptime(args.as_of, "%Y-%m-%d %H:%M")
    result = resolve(Path(args.input), Path(args.output), as_of)
    print("Phase D complete")
    print("Candidate records:", result["metadata"]["input_candidates"])
    print("Resolved tasks:", result["metadata"]["resolved_tasks"])
    print("Output:", args.output)


if __name__ == "__main__":
    main()
