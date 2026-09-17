from pathlib import Path
from query_engine import answer, load_tasks, retrieve_tasks

BASE = Path(__file__).resolve().parent
PAYLOAD = load_tasks(BASE / "data" / "final_tasks.json")


def titles(q):
    return [t["title"] for t in retrieve_tasks(PAYLOAD["tasks"], q)]


def assert_only(q, required, forbidden=()):
    got = titles(q)
    low = [x.lower() for x in got]
    assert any(required.lower() in x for x in low), (q, got)
    for bad in forbidden:
        assert not any(bad.lower() in x for x in low), (q, got)


def check():
    assert_only("tell about expense variance report", "expense variance report", ["vendor list", "campaign deck", "meridian", "mumbai"])
    assert_only("what is the status of the deck", "review q3 campaign deck", ["vendor list", "meridian", "expense variance", "mumbai"])
    assert_only("what is the status of the campaign presentation", "review q3 campaign deck", ["vendor list", "meridian", "expense variance", "mumbai"])
    assert_only("where do things stand with the client meeting", "meridian", ["vendor list", "campaign deck", "expense variance", "mumbai"])
    assert_only("tell me about mumbai lease renewal paperwork", "mumbai", ["vendor list", "campaign deck", "expense variance", "meridian"])
    assert_only("show me the work connected to the supplier list", "vendor list", ["campaign deck", "expense variance", "meridian", "mumbai"])

    # Scope-only queries intentionally return the complete matching scope.
    assert len(titles("what is overdue?")) == 3
    assert any("vendor list" in x.lower() for x in titles("what is overdue?"))

    # Natural-language/typo coverage remains.
    assert_only("when will the campain presntation be ready", "campaign deck")
    assert_only("what is going on with the financial variance report", "expense variance report")

    print("Phase G precision tests passed.")


if __name__ == "__main__":
    check()
