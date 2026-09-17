from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROMPTS_DIR = BASE_DIR / "prompts"

DATAPACK_PDF = DATA_DIR / "Assignment 1_DataPack_ExecutiveProductivityAgent.pdf"
SOURCE_JSON = DATA_DIR / "source_data.json"

# The datapack explicitly defines this working week.
WEEK_START = "2026-09-21"
WEEK_END = "2026-09-25"

EXECUTIVE_NAME = "Arjun Malhotra"
EXECUTIVE_EMAIL = "arjun.malhotra@veridian-corp.example"
