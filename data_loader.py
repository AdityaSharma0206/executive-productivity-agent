import json
import re
from pathlib import Path

from pypdf import PdfReader

from config import DATAPACK_PDF, SOURCE_JSON


SECTION_PATTERNS = {
    "people": re.compile(r"People\s*&\s*Email\s*Addresses", re.I),
    "meeting_transcript": re.compile(r"1\.\s*Meeting\s*Transcript", re.I),
    "calendars": re.compile(r"2\.\s*Calendars", re.I),
    "email_threads": re.compile(r"3\.\s*Email\s*Threads", re.I),
    "voice_notes": re.compile(r"4\.\s*Voice\s*Note\s*Transcripts", re.I),
    "prototype_note": re.compile(r"Note\s*on\s*Your\s*Prototype", re.I),
}


def clean_text(text):
    text = text.replace("\u00ad", "")
    text = text.replace("\ufffd", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pages(pdf_path):
    reader = PdfReader(str(pdf_path))
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append({
            "page": page_number,
            "text": clean_text(text)
        })

    return pages


def classify_sections(full_text):
    matches = []

    for name, pattern in SECTION_PATTERNS.items():
        match = pattern.search(full_text)
        if match:
            matches.append((match.start(), name))

    matches.sort()

    sections = {}

    for index, (start, name) in enumerate(matches):
        end = matches[index + 1][0] if index + 1 < len(matches) else len(full_text)
        sections[name] = full_text[start:end].strip()

    return sections


def build_source_record(pdf_path=DATAPACK_PDF):
    pages = extract_pages(pdf_path)
    full_text = "\n\n".join(
        "=== PAGE {} ===\n{}".format(p["page"], p["text"])
        for p in pages
    )

    sections = classify_sections(full_text)

    return {
        "metadata": {
            "source_file": pdf_path.name,
            "executive": "Arjun Malhotra",
            "executive_email": "arjun.malhotra@veridian-corp.example",
            "week_start": "2026-09-21",
            "week_end": "2026-09-25",
            "source_types": [
                "meeting_transcript",
                "calendars",
                "email_threads",
                "voice_notes"
            ]
        },
        "pages": pages,
        "sections": sections
    }


def save_source_record(record, output_path=SOURCE_JSON):
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(record, file, indent=2, ensure_ascii=False)


def load_source_record(input_path=SOURCE_JSON):
    with open(input_path, "r", encoding="utf-8") as file:
        return json.load(file)


if __name__ == "__main__":
    if not DATAPACK_PDF.exists():
        raise FileNotFoundError(
            "Datapack PDF not found at: {}".format(DATAPACK_PDF)
        )

    record = build_source_record()
    save_source_record(record)

    print("Data ingestion completed.")
    print("PDF:", DATAPACK_PDF.name)
    print("Pages extracted:", len(record["pages"]))
    print("Sections detected:", ", ".join(record["sections"].keys()))
    print("Saved:", SOURCE_JSON)
