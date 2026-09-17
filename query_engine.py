"""Phase G — grounded natural-language query engine.

Retrieval is topic-first: specific project/document/person terms are treated as
anchors, while generic words such as "report", "status", "task", "work" and
"update" are not allowed to pull unrelated tasks into the answer.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = BASE_DIR / "data" / "final_tasks.json"

STOPWORDS = {
    "a","about","after","all","am","an","and","are","be","been","before","can","could",
    "did","do","does","for","from","get","give","has","have","how","i","if","in","is",
    "it","me","my","of","on","or","please","show","tell","that","the","their","there",
    "this","to","was","what","when","where","which","who","why","will","with","would","you",
    "your","anything","any","currently","still","just","really","regarding","related","something",
    "thing","going","stand","things","thing","about","me","need","needs","do","does","did",
    "latest","rundown","update","status","progress","happened","done","finished","complete","completed",
    "pending","open","closed","ready","finish","finished","when","deadline","due","target","by",
    "soon","owner","owns","own","responsible","handling","handles","assigned","assignment","whose",
    "waiting","owe","owes","dependency","dependencies","someone","others","work","task","tasks",
    "item","items","action","actions","today","have","to","i","my","on","for","the",
}

# Only the domain concepts below are topic anchors. Generic terms are kept out
# of the anchor system so "report" alone cannot retrieve every report-like task.
CONCEPTS = {
    "deck": {"deck", "campaign", "presentation", "presentations", "slides", "slide", "q3"},
    "vendor": {"vendor", "vendors", "supplier", "suppliers", "vendorlist"},
    "mumbai": {"mumbai", "office", "lease", "renewal", "paperwork", "signature", "signoff", "signing", "facilities"},
    "expense": {"expense", "expenses", "variance", "july", "financial"},
    "meridian": {"meridian", "logistics", "client", "call", "meeting", "priya", "reschedule", "rescheduled"},
}

PHRASE_ALIASES = {
    "presentation": "deck", "presentations": "deck", "slides": "deck", "slide": "deck",
    "campaign materials": "deck", "campaign presentation": "deck", "q3 slides": "deck",
    "supplier list": "vendor", "supplier lists": "vendor", "vendor list": "vendor",
    "office lease": "mumbai", "lease renewal": "mumbai", "office renewal": "mumbai",
    "renewal documents": "mumbai", "sign off": "mumbai", "sign-off": "mumbai",
    "financial report": "expense", "variance report": "expense", "expense report": "expense",
    "expense variance": "expense", "july variance": "expense",
    "client meeting": "meridian", "client call": "meridian", "meridian meeting": "meridian",
}

PEOPLE = {
    "arjun": "Arjun Malhotra", "malhotra": "Arjun Malhotra", "neha": "Neha Kapoor", "kapoor": "Neha Kapoor",
    "raghav": "Raghav Sethi", "sethi": "Raghav Sethi", "divya": "Divya Rao", "rao": "Divya Rao",
    "priya": "Priya Nair", "nair": "Priya Nair",
}

TOPIC_GROUPS = {
    "deck": ("campaign_deck", "TCAMPAIGN", "CDECK", "deck", "campaign"),
    "vendor": ("vendor", "TVENDOR", "vendorlist", "supplier"),
    "mumbai": ("mumbai_lease", "TLEASE", "mumbai", "lease", "renewal"),
    "meridian": ("meridian_call", "TMERIDIAN", "meridian", "logistics", "priya"),
    "expense": ("expense_variance", "TEXPENSE", "expense", "variance", "july"),
}


def load_tasks(path: Path = DEFAULT_INPUT) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(text: str) -> str:
    text = str(text or "").lower().replace("’", "'")
    text = re.sub(r"[^a-z0-9@.'-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def stem(word: str) -> str:
    w = word.lower()
    if len(w) > 5 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 5 and w.endswith("ing"):
        base = w[:-3]
        if len(base) > 3 and base[-1] == base[-2]:
            base = base[:-1]
        return base
    if len(w) > 4 and w.endswith("ed"):
        return w[:-2]
    if len(w) > 4 and w.endswith("es"):
        return w[:-2]
    if len(w) > 3 and w.endswith("s"):
        return w[:-1]
    return w


def tokens(text: str) -> set[str]:
    raw = re.findall(r"[a-z0-9]+", normalize(text))
    return {stem(w) for w in raw if w not in STOPWORDS and len(w) > 1}


def phrase_concepts(question: str) -> set[str]:
    q = normalize(question)
    return {concept for phrase, concept in PHRASE_ALIASES.items() if phrase in q}


def expanded_query(question: str) -> tuple[set[str], set[str]]:
    base = tokens(question)
    concepts = phrase_concepts(question)
    stemmed_concepts = {c: {stem(x) for x in words} for c, words in CONCEPTS.items()}
    for word in base:
        for concept, words in stemmed_concepts.items():
            if word in words:
                concepts.add(concept)
    expanded = set(base)
    for concept in concepts:
        expanded.update(stem(x) for x in CONCEPTS[concept])
    return expanded, concepts


def person_names(question: str) -> set[str]:
    q_tokens = tokens(question)
    return {full for short, full in PEOPLE.items() if stem(short) in q_tokens}


def task_search_text(task: dict[str, Any]) -> str:
    pieces = [
        task.get("title", ""), task.get("task_id", ""), task.get("type", ""),
        task.get("owner", "") or "", task.get("related_person", "") or "", task.get("status", ""),
        task.get("deadline_text", "") or "", task.get("deadline", "") or "", task.get("deadline_date", "") or "",
        task.get("deadline_time", "") or "", task.get("resolution", {}).get("group_key", ""),
    ]
    pieces.extend(str(x) for x in task.get("evidence", []))
    for source in task.get("sources", []):
        pieces.extend(str(source.get(k, "") or "") for k in (
            "source_type","source_reference","source_date","evidence","deadline_text","deadline_date","deadline_time","status"
        ))
    return " ".join(pieces)


def field_text(task: dict[str, Any], field: str) -> str:
    if field == "title":
        return task.get("title", "")
    if field == "people":
        return " ".join(x for x in (task.get("owner"), task.get("related_person")) if x)
    if field == "status":
        return " ".join(str(task.get(k, "")) for k in ("status", "type", "overdue", "ownership_ambiguous"))
    if field == "deadline":
        return " ".join(str(task.get(k, "")) for k in ("deadline", "deadline_text", "deadline_date", "deadline_time"))
    if field == "evidence":
        return " ".join(str(x) for x in task.get("evidence", []))
    return task_search_text(task)


def fuzzy_token_match(q: str, candidates: set[str]) -> float:
    if not q or not candidates:
        return 0.0
    if q in candidates:
        return 1.0
    best = max((SequenceMatcher(None, q, c).ratio() for c in candidates), default=0.0)
    return best if best >= 0.78 else 0.0


def query_mode(question: str) -> str:
    q = normalize(question)
    if re.search(r"\b(when|deadline|due|date|time|ready|finish|by when|how soon)\b", q):
        return "deadline"
    if re.search(r"\b(who|whose|owner|owns|responsible|handling|assigned)\b", q):
        return "owner"
    if re.search(r"\b(happened|status|progress|done|completed|finished|pending|open|closed|update|what's the status)\b", q):
        return "status"
    return "summary"


def query_scope(question: str) -> str:
    q = normalize(question)
    if re.search(r"\b(all|everything|entire|every)\b", q) and re.search(r"\b(task|work|commitment|item)s?\b", q):
        return "all"
    if re.search(r"\b(what do i need|what should i|what needs action|what do i still have to get done|my action|my task|i need to|i have to|follow up|follow-up)\b", q):
        return "my_open"
    if re.search(r"\b(waiting|waiting on|waiting for|owe|owes|blocked|dependency|dependencies)\b", q):
        return "waiting"
    if re.search(r"\b(overdue|late|past due)\b", q):
        return "overdue"
    if re.search(r"\b(unclear|unowned|unassigned|no owner|whose desk)\b", q):
        return "unclear"
    return "topic"


def topic_hit(task: dict[str, Any], concept: str) -> tuple[bool, int]:
    text = normalize(task_search_text(task))
    group = normalize(task.get("resolution", {}).get("group_key", ""))
    title = normalize(task.get("title", ""))
    strong = TOPIC_GROUPS[concept]
    # Exact/near-exact topic identifiers are stronger than incidental evidence words.
    if any(normalize(x) in group for x in strong[:2]):
        return True, 3
    if any(re.search(rf"\b{re.escape(normalize(x))}\b", title) for x in strong[2:]):
        return True, 3
    if any(re.search(rf"\b{re.escape(normalize(x))}\b", text) for x in strong[2:]):
        return True, 1
    return False, 0


def score_task(task: dict[str, Any], question: str) -> tuple[float, bool]:
    q_norm = normalize(question)
    q_tokens, concepts = expanded_query(question)
    if not q_tokens and not concepts:
        return 0.0, False

    # If the question contains a specific topic anchor, enforce that anchor.
    # This is the key precision guard against unrelated tasks.
    topic_scores = {c: topic_hit(task, c) for c in concepts}
    if concepts and not any(hit for hit, _ in topic_scores.values()):
        return 0.0, False

    title_tokens = tokens(field_text(task, "title"))
    people_tokens = tokens(field_text(task, "people"))
    status_tokens = tokens(field_text(task, "status"))
    deadline_tokens = tokens(field_text(task, "deadline"))
    evidence_tokens = tokens(field_text(task, "evidence"))
    all_tokens = tokens(task_search_text(task))

    score = 0.0
    score += 20 * len(q_tokens & title_tokens)
    score += 10 * len(q_tokens & people_tokens)
    score += 2 * len(q_tokens & status_tokens)
    score += 2 * len(q_tokens & deadline_tokens)
    score += 1 * len(q_tokens & evidence_tokens)

    for concept, (hit, strength) in topic_scores.items():
        if hit:
            score += 28 if strength >= 3 else 16

    # Multi-word title matches.
    q_words = [w for w in re.findall(r"[a-z0-9]+", q_norm) if w not in STOPWORDS]
    title_norm = normalize(task.get("title", ""))
    search_norm = normalize(task_search_text(task))
    for n in (4, 3, 2):
        for i in range(len(q_words) - n + 1):
            phrase = " ".join(q_words[i:i+n])
            if len(phrase) >= 7 and phrase in title_norm:
                score += 14
            elif len(phrase) >= 7 and phrase in search_norm:
                score += 4

    # Typo tolerance applies only when a topic anchor is already present.
    if concepts:
        for token in q_tokens:
            if len(token) >= 5:
                fuzzy = fuzzy_token_match(token, all_tokens)
                if fuzzy >= 0.86:
                    score += 1.5 * fuzzy

    mode = query_mode(question)
    if mode == "deadline" and task.get("deadline"):
        score += 3
    if mode == "owner" and (task.get("owner") or task.get("ownership_ambiguous")):
        score += 3
    if mode == "status" and task.get("status"):
        score += 2

    q_stems = {stem(w) for w in re.findall(r"[a-z0-9]+", q_norm)}
    if "ready" in q_stems or "receive" in q_stems or "delivery" in q_stems:
        if task.get("type") == "WAITING_ON_OTHERS":
            score += 7
        if any("ready" in normalize(e) or "send" in normalize(e) for e in task.get("evidence", [])):
            score += 4
    if "review" in q_stems and "review" in title_norm:
        score += 8

    return score, bool(concepts)


def retrieve_tasks(tasks: list[dict[str, Any]], question: str, limit: int = 4) -> list[dict[str, Any]]:
    scope = query_scope(question)
    candidates = list(tasks)

    if scope == "my_open":
        candidates = [t for t in candidates if t.get("type") == "MY_ACTION" and t.get("status") == "OPEN"]
    elif scope == "waiting":
        candidates = [t for t in candidates if t.get("type") == "WAITING_ON_OTHERS" and t.get("status") == "OPEN"]
    elif scope == "overdue":
        candidates = [t for t in candidates if t.get("overdue") and t.get("status") == "OPEN"]
    elif scope == "unclear":
        candidates = [t for t in candidates if t.get("ownership_ambiguous") or t.get("type") == "AMBIGUOUS"]
    elif scope == "all":
        return candidates

    scored = []
    for idx, task in enumerate(candidates):
        score, has_topic = score_task(task, question)
        # Topic queries need a meaningful score. Scope-only questions can use
        # the scope filter when they have no topic vocabulary.
        if has_topic and score >= 18:
            scored.append((score, idx, task))
        elif not has_topic and score >= 4:
            scored.append((score, idx, task))

    scored.sort(key=lambda x: (-x[0], x[1]))

    if not scored and scope in {"my_open", "waiting", "overdue", "unclear"}:
        return candidates[:limit]
    return [t for _, _, t in scored[:limit]]


def format_deadline(task: dict[str, Any]) -> str:
    if not task.get("deadline"):
        return "no deadline recorded"
    return str(task["deadline"]).replace("T", " ")


def status_label(task: dict[str, Any]) -> str:
    if task.get("ownership_ambiguous"):
        return "Unclear ownership"
    return str(task.get("status", "UNKNOWN")).replace("_", " ").title()


def relevant_evidence(task: dict[str, Any], question: str, maximum: int = 2) -> list[str]:
    q_tokens, concepts = expanded_query(question)
    evidence = task.get("evidence", [])
    if not evidence:
        return []
    scored = []
    for i, text in enumerate(evidence):
        et = tokens(text)
        s = len(q_tokens & et) * 2
        norm = normalize(text)
        for concept in concepts:
            if any(re.search(rf"\b{re.escape(normalize(w))}\b", norm) for w in CONCEPTS[concept]):
                s += 3
        scored.append((s, i, text))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    return [x[2] for x in scored[:maximum] if x[0] > 0] or evidence[-maximum:]


def describe_task(task: dict[str, Any], question: str) -> str:
    title = task.get("title", "Untitled task")
    owner = task.get("owner") or "no owner assigned"
    related = task.get("related_person")
    deadline = format_deadline(task)
    mode = query_mode(question)
    status = status_label(task)
    lines = [f"### {title}"]
    if mode == "deadline":
        lines += [f"- **Deadline:** {deadline}", f"- **Status:** {status}"]
        if task.get("completed_on"):
            lines.append(f"- **Completed:** {task['completed_on']}")
        evidence = relevant_evidence(task, question, 1)
        if evidence:
            lines.append(f"- **Latest evidence:** {evidence[0]}")
    elif mode == "owner":
        lines += [f"- **Owner:** {owner}"]
        if related:
            lines.append(f"- **Related person:** {related}")
        if task.get("ownership_ambiguous"):
            lines.append("- **Ownership:** explicitly unclear in the supplied evidence")
        lines.append(f"- **Due:** {deadline}")
    elif mode == "status":
        lines += [f"- **Status:** {status}", f"- **Owner:** {owner}", f"- **Due:** {deadline}"]
        evidence = relevant_evidence(task, question, 1)
        if evidence:
            lines.append(f"- **Latest evidence:** {evidence[0]}")
    else:
        lines += [f"- **Status:** {status}", f"- **Owner:** {owner}", f"- **Due:** {deadline}"]
        if related:
            lines.append(f"- **Related person:** {related}")
        if task.get("ownership_ambiguous"):
            lines.append("- **Ownership:** unclear in the supplied evidence")
        evidence = relevant_evidence(task, question, 1)
        if evidence:
            lines.append(f"- **Evidence:** {evidence[0]}")
    if task.get("overdue") and task.get("status") == "OPEN":
        lines.append("- **Flag:** OVERDUE")
    return "\n".join(lines)


def summary_answer(matches: list[dict[str, Any]], question: str) -> str:
    if len(matches) == 1:
        return describe_task(matches[0], question)
    sections = [f"### {len(matches)} related tasks found"]
    sections.extend(describe_task(task, question) for task in matches)
    return "\n\n".join(sections)


def answer_all(tasks: list[dict[str, Any]]) -> str:
    return "Resolved task state:\n" + "\n".join(
        f"- {t.get('title')} — {status_label(t)}; due {format_deadline(t)}" for t in tasks
    )


def answer(question: str, payload: dict[str, Any]) -> str:
    tasks = payload.get("tasks", [])
    if not str(question).strip():
        return "Please ask a question about the resolved task data."
    if query_scope(question) == "all":
        return answer_all(tasks)
    matches = retrieve_tasks(tasks, question)
    if not matches:
        return ("I couldn't match that question to a resolved task. Try describing the work in your own words—"
                "for example, a project, person, document, meeting, deadline, or status.")
    return summary_answer(matches, question)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask natural-language questions about resolved executive tasks.")
    parser.add_argument("question", nargs="*", help="Question to ask")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    args = parser.parse_args()
    payload = load_tasks(args.input)
    question = " ".join(args.question).strip() or input("Ask: ").strip()
    print(answer(question, payload))


if __name__ == "__main__":
    main()
