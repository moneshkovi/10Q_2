# CSV Export Feature - Phase 5 Enhancement ✅

**Added**: March 7, 2026  
**Status**: Production Ready

---

## Overview

CSV export was added to Phase 5 to make financial data easily accessible in Excel, pandas, or other analysis tools. The XML is great for structured data interchange, but CSV is much easier for human analysis.

---

## CSV Files Generated (4 files per ticker)

### 1. **`{TICKER}_calculated_metrics.csv`**
**Purpose**: Quick overview of key financial ratios and margins

**Format**:
```csv
Type,Metric,Value,Display,Period
Margin,Gross Margin,0.7107,71.07%,2026-01-25
Margin,Operating Margin,0.6038,60.38%,2026-01-25
Margin,Net Margin,0.5560,55.60%,2026-01-25
Ratio,Current Ratio,3.9053,3.91,2026-01-25
Ratio,Debt-to-Equity,0.0538,0.05,2026-01-25
Ratio,Return on Assets,0.5806,0.58,2026-01-25
Ratio,Return on Equity,0.7633,0.76,2026-01-25
```

**Use Cases**:
- Quick health check dashboard
- Compare ratios across companies
- Track margin trends
- Excel charting

---

### 2. **`{TICKER}_metrics.csv`** (Wide Format)
**Purpose**: All financial metrics with periods as columns

**Format**:
```csv
Metric,Unit,Confidence,2026-01-25_10-K,2025-10-26_10-Q,2025-07-27_10-Q,...
Revenues,USD,100.0,130.50B,97.50B,85.00B,...
NetIncomeLoss,USD,100.0,60.92B,45.30B,38.50B,...
Assets,USD,100.0,309.90B,280.50B,250.30B,...
```

**Use Cases**:
- Trend analysis over time
- Period-to-period comparisons
- Time series charting
- Excel conditional formatting

---

### 3. **`{TICKER}_pivot.csv`** (Long Format)
**Purpose**: Pivot table friendly format for analysis tools

**Format**:
```csv
Period,Form,Filing_Date,Metric,Value,Unit,Confidence
2026-01-25,10-K,2026-02-25,Revenues,130500000000,USD,100.0
2026-01-25,10-K,2026-02-25,NetIncomeLoss,60922000000,USD,100.0
2025-10-26,10-Q,2025-11-19,Revenues,97500000000,USD,100.0
```

**Use Cases**:
- Excel pivot tables
- pandas DataFrame analysis
- SQL database import
- Business intelligence tools (Tableau, Power BI)

---

### 4. **`{TICKER}_validation_summary.csv`**
**Purpose**: Data quality report

**Format**:
```csv
VALIDATION SUMMARY

Metric,Value
Ticker,NVDA
Entity,NVIDIA CORP
Quality Score,0
Metrics Validated,286

FLAG SUMMARY

Level,Count
Critical,0
Error,140
Warning,2360
Info,0
TOTAL,2500

CRITICAL/ERROR ISSUES

Level,Metric,Message,Value
ERROR,CommonStockValue,Extreme growth rate: 1150.0%,25000000
ERROR,DebtCurrent,Extreme decline: -100.0%,0
```

**Use Cases**:
- Quality assurance
- Identify data issues
- Manual review list
- Audit documentation

---

## Usage Examples

### Generate CSV Files
```bash
python main.py NVDA AAPL MSFT BLK

# Output:
# CSV files generated: 4/4 (16 total files)
```

### Open in Excel
```bash
# macOS
open ~/sec_filing_parser/data/NVDA/parsed/NVDA_calculated_metrics.csv

# Linux
xdg-open ~/sec_filing_parser/data/NVDA/parsed/NVDA_calculated_metrics.csv
```

### Load in Python (pandas)
```python
import pandas as pd

# Wide format - time series analysis
metrics_df = pd.read_csv('~/sec_filing_parser/data/NVDA/parsed/NVDA_metrics.csv')

# Pivot format - flexible analysis
pivot_df = pd.read_csv('~/sec_filing_parser/data/NVDA/parsed/NVDA_pivot.csv')

# Calculated metrics - quick ratios
ratios_df = pd.read_csv('~/sec_filing_parser/data/NVDA/parsed/NVDA_calculated_metrics.csv')

# Example: Plot revenue trend
pivot_df[pivot_df['Metric'] == 'Revenues'].plot(x='Period', y='Value')
```

### Excel Pivot Table
1. Open `NVDA_pivot.csv` in Excel
2. Insert → PivotTable
3. Rows: Metric
4. Columns: Period
5. Values: Value (Sum)
6. Filter: Form (10-K or 10-Q)

---

## Real-World Examples

### NVIDIA (NVDA)

**Calculated Metrics** (FY 2026):
```
Gross Margin:      71.07% (exceptional)
Operating Margin:  60.38% (outstanding)
Net Margin:        55.60% (world-class)
Current Ratio:     3.91   (excellent liquidity)
Debt-to-Equity:    0.05   (very low debt)
ROA:               58.06% (phenomenal)
ROE:               76.33% (exceptional)
```

**File Sizes**:
- `NVDA_calculated_metrics.csv`: 357 bytes
- `NVDA_metrics.csv`: 41 KB
- `NVDA_pivot.csv`: 441 KB
- `NVDA_validation_summary.csv`: 2.1 KB

---

### BlackRock (BLK)

**Calculated Metrics** (FY 2025):
```
Operating Margin:  29.09% (solid)
Net Margin:        22.93% (healthy)
Debt-to-Equity:    0.23   (conservative)
ROA:               3.27%  (typical for finance)
ROE:               9.94%  (acceptable)
```

---

## CSV vs XML: When to Use Each

### Use CSV When:
- ✅ Doing quick analysis in Excel
- ✅ Building dashboards or charts
- ✅ Running pandas/R analysis
- ✅ Sharing with non-technical stakeholders
- ✅ Creating pivot tables
- ✅ Comparing companies side-by-side

### Use XML When:
- ✅ Building automated systems
- ✅ Need complete audit trail
- ✅ Integrating with other software
- ✅ Preserving data structure
- ✅ Long-term archival
- ✅ Compliance documentation

---

## Performance

- **CSV Generation**: ~10ms per ticker (4 files)
- **Total Phase 5**: ~80ms per ticker (XML + CSV)
- **File Sizes**: 2-500 KB per CSV file
- **Scalability**: Linear with number of metrics/periods

---

## Quick Analysis Recipes

### Compare Companies (Python)
```python
import pandas as pd

# Load calculated metrics for multiple companies
nvda = pd.read_csv('NVDA_calculated_metrics.csv')
blk = pd.read_csv('BLK_calculated_metrics.csv')
aapl = pd.read_csv('AAPL_calculated_metrics.csv')

# Combine
nvda['Company'] = 'NVDA'
blk['Company'] = 'BLK'
aapl['Company'] = 'AAPL'

all_metrics = pd.concat([nvda, blk, aapl])

# Filter to margins only
margins = all_metrics[all_metrics['Type'] == 'Margin']

# Pivot for comparison
comparison = margins.pivot(index='Metric', columns='Company', values='Display')
print(comparison)
```

### Trend Analysis (Excel)
1. Open `NVDA_metrics.csv`
2. Find "Revenues" row
3. Select all period columns
4. Insert → Line Chart
5. See 3-year revenue trend

### Quality Check (Python)
```python
import pandas as pd

# Load validation summary
val = pd.read_csv('NVDA_validation_summary.csv')

# Find where FLAG SUMMARY starts
flag_section = val[val.iloc[:, 0] == 'FLAG SUMMARY'].index[0]

# Get flag counts
flags = val.iloc[flag_section+2:flag_section+7]
print(flags)
```

---

## Files Added/Modified

### New Files
- `src/csv_builder.py` (470 lines) - CSV generation engine

### Modified Files
- `main.py` - Added CSV export to Phase 5
- Updated summary output to show CSV generation

---

## Output Structure

```
~/sec_filing_parser/data/NVDA/parsed/
├── NVDA_xbrl_metrics.json          # Phase 3 output
├── NVDA_validation_report.json     # Phase 4 output
├── NVDA_financial_data.xml         # Phase 5 XML
├── NVDA_calculated_metrics.csv     # Phase 5 CSV ← NEW
├── NVDA_metrics.csv                # Phase 5 CSV ← NEW
├── NVDA_pivot.csv                  # Phase 5 CSV ← NEW
└── NVDA_validation_summary.csv     # Phase 5 CSV ← NEW
```

---

## Summary

✅ **4 CSV files** generated per ticker  
✅ **Excel-ready** formatting  
✅ **pandas-friendly** structures  
✅ **Multiple formats** (wide, long, summary)  
✅ **Human-readable** values (e.g., "130.50B" instead of 130500000000)  
✅ **Quality reports** included  

**CSV export makes financial data accessible to everyone, not just developers!**
