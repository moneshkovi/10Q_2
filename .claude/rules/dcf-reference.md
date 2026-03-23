---
paths:
  - "src/dcf_calculator.py"
  - "tests/test_dcf_calculator.py"
---

Before making any changes to the DCF model, read:
- @docs/dcf_methodology.md — formulas, OCF vs EBIT method, terminal value logic
- @docs/design_decisions.md — why FCFF over FCFE, why median FCF margin, why annual-only data

Key invariants that must never be broken:
- OCF method is always preferred over EBIT method (see design_decisions.md #2)
- Annual-only data in historical FCF series (10-K / 20-F only, never 10-Q)
- Terminal growth rate must not exceed DCF_TERMINAL_GROWTH_RATE in config.py
- beta_override param must flow through run_dcf → _calculate_wacc unchanged
- beta_source must be set to "computed" or "sector_lookup" in the returned WACC dict
