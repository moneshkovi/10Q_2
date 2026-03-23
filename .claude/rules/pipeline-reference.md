---
paths:
  - "main.py"
  - "config.py"
  - "src/sec_client.py"
  - "src/xbrl_parser.py"
  - "src/email_reporter.py"
---

Before making any changes to the pipeline or configuration, read:
- @docs/pipeline_architecture.md — all 9 phases, data flow, the result{} dict structure
- @docs/data_sources.md — SEC EDGAR API endpoints, XBRL taxonomy, Alpaca API

Key invariants:
- All secrets must come from os.getenv() loaded via load_dotenv() — never hardcode keys
- config.ANNUAL_FORM_TYPES = ["10-K", "20-F"] — only annual filings for DCF
- The result{} dict is the single contract between phases — new phases add keys, never remove
- AlpacaClient and EmailReporter must fail silently (enabled flag pattern)
- SEC rate limit: 0.1s delay between requests — do not remove
