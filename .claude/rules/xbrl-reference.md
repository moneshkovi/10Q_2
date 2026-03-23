---
paths:
  - "src/xbrl_parser.py"
  - "tests/test_xbrl_parser.py"
---

Before making any changes to XBRL extraction, read:
- @docs/data_sources.md — XBRL taxonomy (US-GAAP vs IFRS), SEC API endpoints, what XBRL provides

Key invariants:
- Auto-detect taxonomy: check for "ifrs-full" key in facts, else use "us-gaap"
- Always try US-GAAP tags first, then IFRS tags — combined lookup for 20-F filers
- Never mix annual and quarterly period data in the same historicals list
- Confidence score must be computed and stored per metric (0-100)
- Period end dates must be extracted and stored for every value
