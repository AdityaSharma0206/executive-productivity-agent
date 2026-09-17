from pathlib import Path
from query_engine import answer, load_tasks, retrieve_tasks

BASE = Path(__file__).resolve().parent
PAYLOAD = load_tasks(BASE / "data" / "final_tasks.json")


def expect(question: str, *needles: str) -> None:
    result = answer(question, PAYLOAD).lower()
    for needle in needles:
        assert needle.lower() in result, f"{question!r} -> missing {needle!r}\n{result}"


def check():
    # Original expected behaviours.
    expect("What did I promise Raghav?", "vendor list", "Raghav")
    expect("What am I waiting on?", "campaign deck", "Neha")
    expect("What is overdue?", "vendor list")
    expect("What has unclear ownership?", "Mumbai", "owner")
    expect("What needs action today?", "vendor list")

    # Natural-language paraphrases — none of these are the old fixed prompts.
    expect("When should the presentation be ready for my review?", "campaign deck", "09:30")
    expect("What's the latest on the Q3 slides?", "campaign deck")
    expect("Can you give me the rundown on the Mumbai office documents?", "Mumbai", "signature")
    expect("Who is supposed to handle the Mumbai renewal?", "no owner assigned")
    expect("What is going on with the financial variance report?", "expense variance report", "completed")
    expect("Where do things stand with the client meeting?", "Meridian", "completed")
    expect("What do I still have to get done?", "vendor list")
    expect("Anything I need to follow up on?", "vendor list")
    expect("Show me the work connected to the supplier list.", "vendor list")

    # Small spelling/wording variations should still retrieve the right topic.
    expect("when will the campain presntation be ready", "campaign deck")
    expect("tell me about mumbai lease renewal paperwork", "Mumbai", "signature")

    # Retrieval itself should return more than exact-phrase matches.
    titles = [t["title"] for t in retrieve_tasks(PAYLOAD["tasks"], "presentation slides")]
    assert any("campaign deck" in t.lower() for t in titles)

    print("All Phase G natural-language query tests passed.")


if __name__ == "__main__":
    check()
