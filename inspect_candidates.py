import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
PATH = BASE / "data" / "candidate_commitments.json"


def main():
    if not PATH.exists():
        print("No candidate_commitments.json found.")
        print("Run: python extractor.py")
        return

    data = json.loads(PATH.read_text(encoding="utf-8"))
    records = data["candidate_commitments"]

    print("\n=== PHASE C: CANDIDATE COMMITMENTS ===")
    print("Total:", len(records))

    for item in records:
        print("\n[{}] {}".format(item["candidate_id"], item["action"]))
        print("Owner:", item["owner"] or "UNKNOWN")
        print("Type:", item["owner_type"])
        print("Related:", item["related_person"] or "None")
        print("Deadline:", item["deadline_text"] or "None",
              "| normalized:", item["deadline_date"] or "None",
              item["deadline_time"] or "")
        print("Status:", item["status"])
        print("Ambiguous owner:", item["ownership_ambiguous"])
        print("Source:", item["source_type"], "/", item["source_reference"])
        print("Evidence:", item["evidence"])


if __name__ == "__main__":
    main()
