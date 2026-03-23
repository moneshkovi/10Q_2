---
paths:
  - "src/alpaca_client.py"
  - "tests/test_alpaca_client.py"
---

Before making any changes to Alpaca market data integration, read:
- @docs/beta_and_capm.md — OLS beta calculation, why daily log returns, why SPY, why 252 days
- @docs/data_sources.md — Alpaca API endpoints, data URL vs paper trading URL, what free tier provides

Key invariants:
- Always use ALPACA_DATA_URL (data.alpaca.markets), never ALPACA_BASE_URL (paper-api) for data
- Beta uses daily LOG returns: r_t = ln(close_t / close_{t-1}), not percentage returns
- Minimum 30 overlapping trading days required — return None below this threshold
- Beta result must be clamped to [-1.0, 5.0]
- All methods must return None / [] on any exception — never crash the pipeline
- Split-adjusted bars only: adjustment=split parameter required
