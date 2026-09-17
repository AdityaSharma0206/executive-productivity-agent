from data_loader import load_source_record
from config import SOURCE_JSON


def main():
    data = load_source_record(SOURCE_JSON)

    print("\n=== EXECUTIVE PRODUCTIVITY AGENT: INGESTED DATA ===")
    print("Executive:", data["metadata"]["executive"])
    print("Week:", data["metadata"]["week_start"], "to", data["metadata"]["week_end"])

    print("\n=== DETECTED SOURCE SECTIONS ===")
    for section_name, section_text in data["sections"].items():
        print("\n--- {} ---".format(section_name.upper()))
        preview = section_text[:1200]
        print(preview)
        if len(section_text) > 1200:
            print("... [preview truncated]")

    print("\nData is ready for Phase C: commitment extraction.")


if __name__ == "__main__":
    main()
