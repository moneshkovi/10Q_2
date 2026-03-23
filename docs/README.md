# SEC Filing Parser — Study Guide

This folder is your reference for understanding **every method, tool, and decision** in this project.
Written to be read by someone learning finance and software engineering simultaneously.

---

## Documents in This Folder

| File | What You'll Learn |
|------|-------------------|
| [data_sources.md](data_sources.md) | Where the data comes from — SEC EDGAR, XBRL taxonomy, Alpaca Markets API |
| [beta_and_capm.md](beta_and_capm.md) | What beta is, how OLS regression computes it, why it matters for valuation |
| [dcf_methodology.md](dcf_methodology.md) | Full DCF walkthrough tied directly to the code — formulas, choices, pitfalls |
| [pipeline_architecture.md](pipeline_architecture.md) | How the 9 phases connect, what each file does, data flow diagrams |
| [design_decisions.md](design_decisions.md) | The "why" behind every non-obvious choice in this codebase |
| [glossary.md](glossary.md) | A–Z reference for every financial and technical term used in the project |

---

## Recommended Reading Order (for beginners)

1. **Start here →** [pipeline_architecture.md](pipeline_architecture.md) — understand the big picture
2. [data_sources.md](data_sources.md) — understand where data comes from before trying to use it
3. [glossary.md](glossary.md) — bookmark this, refer back whenever a term is unfamiliar
4. [dcf_methodology.md](dcf_methodology.md) — the core finance: valuing a company
5. [beta_and_capm.md](beta_and_capm.md) — the statistics behind the risk model
6. [design_decisions.md](design_decisions.md) — read last, after you understand the pieces

---

## How to Run the Pipeline (Quick Reference)

```bash
# Activate environment
source ~/miniconda3/etc/profile.d/conda.sh && conda activate 10Q

# Run single ticker (all 9 phases)
python main.py NVDA

# Run multiple tickers
python main.py NVDA AAPL MSFT AZN

# Run all tests
pytest tests/ -v
```

**Output location:** `~/sec_filing_parser/data/{TICKER}/parsed/`

---

## Project at a Glance

```
User types:  python main.py NVDA
                     |
           ┌─────────▼──────────┐
           │  Phase 1-2: SEC    │  → Find the company CIK, get filing list
           │  EDGAR lookup      │
           └─────────┬──────────┘
                     │
           ┌─────────▼──────────┐
           │  Phase 3: XBRL     │  → Download 275+ financial metrics from SEC API
           │  extraction        │
           └─────────┬──────────┘
                     │
           ┌─────────▼──────────┐
           │  Phase 4: Data     │  → Validate data quality, flag anomalies
           │  validation        │
           └─────────┬──────────┘
                     │
           ┌─────────▼──────────┐
           │  Phase 5: Output   │  → Write XML + CSV files
           │  generation        │
           └─────────┬──────────┘
                     │
           ┌─────────▼──────────┐
           │  Phase 6: CLI      │  → Progress bars, colors, multi-ticker comparison
           │  enhancements      │
           └─────────┬──────────┘
                     │
           ┌─────────▼──────────┐
           │  Phase 7: DCF      │  → Compute fair value per share
           │  valuation         │
           └─────────┬──────────┘
                     │
           ┌─────────▼──────────┐
           │  Phase 8: Alpaca   │  → Fetch live stock price + compute OLS beta
           │  market data       │
           └─────────┬──────────┘
                     │
           ┌─────────▼──────────┐
           │  Phase 9: Email    │  → Send HTML report to your inbox
           │  reporting         │
           └─────────────────────┘
```

---

## Also See

- `DCF_MODEL.md` (project root) — DCF formula reference with examples
- `CSV_EXPORT_GUIDE.md` (project root) — How to use the CSV output files in Excel
- `config.py` — All constants: API URLs, DCF parameters, beta table
