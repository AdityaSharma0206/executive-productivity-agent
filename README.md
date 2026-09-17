# Executive Productivity Agent — Clean B→G Rebuild (Readable Output Edition)

This is a **fresh, separate rebuild** of the Executive Productivity Agent from Phase B through Phase G.
It preserves the working B–F pipeline, the Phase G natural-language retrieval behaviour, and fixes the presentation of query answers so the UI displays readable multi-line Markdown task cards instead of long one-line sentences.

## What is preserved

- Phase B data ingestion from the supplied assignment PDF.
- Phase C commitment extraction with the dependency-free baseline extractor.
- Phase D semantic grouping, deduplication, deadline updates, ownership handling, completion handling, and audit evidence.
- Phase F deterministic Daily Action Brief and Streamlit interface.
- Phase G natural-language retrieval: questions do **not** have to match a fixed list of phrases.
- Small spelling variations and paraphrases are supported.
- Answers remain grounded in `data/final_tasks.json`; no external LLM is required.

## What is fixed

The query engine now returns Markdown like:

### Receive Q3 campaign deck from Neha Kapoor
- **Status:** Open
- **Owner:** Neha Kapoor
- **Due:** 2026-09-24 09:00:00
- **Related person:** Arjun Malhotra
- **Evidence:** ...

The Streamlit chat renders this directly as Markdown, so each field appears on its own line.

## Phases

### Phase B — ingestion
```bash
python data_loader.py
```

### Phase C — extraction
```bash
python extractor.py
```

### Phase D — resolution
```bash
python resolver.py --as-of "2026-09-25 17:00"
```

### Phase F — daily brief
```bash
python brief_generator.py --as-of "2026-09-25 17:00"
```

### Phase G — query engine
```bash
python test_query_engine.py
```

## Verify the complete rebuild

Run:

```bash
python test_all.py
```

Expected final line:

```text
All B→G verification tests passed.
```

## Start the agent

Recommended on Windows:

```bash
run_agent.bat
```

Or manually:

```bash
pip install -r requirements.txt
python run_pipeline.py
streamlit run app.py
```

## Example questions

These are examples, not a fixed question list:

- `What did I promise Raghav?`
- `When should the presentation be ready for my review?`
- `What's the latest on the Q3 slides?`
- `Can you give me the rundown on the Mumbai office documents?`
- `Who is supposed to handle the Mumbai renewal?`
- `What is going on with the financial variance report?`
- `Where do things stand with the client meeting?`
- `What do I still have to get done?`
- `Anything I need to follow up on?`
- `Show me the work connected to the supplier list.`
- `when will the campain presntation be ready`

## Important

Use **this new folder as a standalone project**. Do not copy files from the older error-prone project into it.

The important Phase G file is now named exactly:

```text
query_engine.py
```

There is no need to use the earlier `query_engine_updated.py` file.

## Phase G retrieval precision

This rebuild uses topic-first retrieval. Specific anchors such as deck/presentation, vendor/supplier list, Mumbai lease/renewal, Meridian/client meeting, and expense/variance report are required before a task is returned for a topic question. Generic words such as status, report, task, work, update, or completed cannot by themselves pull unrelated tasks into the result. Scope-only questions such as “what is overdue?” still return the complete matching scope.

The project also includes `test_query_precision.py`, which checks both positive natural-language matches and negative cases where unrelated tasks must not be returned.
