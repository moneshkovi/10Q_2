"""
DCF (Discounted Cash Flow) Calculator - Phase 7

Industry-standard DCF valuation model following JP Morgan / Goldman Sachs
equity research methodology.

Approach: Unlevered DCF (FCFF → Enterprise Value → Equity Value → Per Share)

Components:
1. Historical Financial Extraction (from XBRL data)
2. Free Cash Flow to Firm (FCFF) calculation
3. WACC (Weighted Average Cost of Capital)
4. Revenue & FCF forecasting (5-year projection)
5. Terminal Value (Gordon Growth + Exit Multiple)
6. Enterprise Value → Equity Value bridge
7. Sensitivity analysis (WACC × Growth matrix)
8. Bull / Base / Bear scenario analysis

Author: SEC Filing Parser Team
Date: March 2026
"""

import logging
import csv
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

import config

logger = logging.getLogger(__name__)


# ============================================================================
# XBRL METRIC MAPPINGS
# ============================================================================

# Maps conceptual metrics to XBRL taxonomy names (US-GAAP)
# A company may report under different names; we try multiple.
REVENUE_KEYS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueNet",
    "SalesRevenueGoodsNet",
    "SalesRevenueServicesNet",
    "TotalRevenuesAndOtherIncome",
]

OPERATING_INCOME_KEYS = [
    "OperatingIncomeLoss",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
]

NET_INCOME_KEYS = [
    "NetIncomeLoss",
    "NetIncomeLossAvailableToCommonStockholdersBasic",
    "ProfitLoss",
]

EBIT_KEYS = [
    "OperatingIncomeLoss",
]

TAX_EXPENSE_KEYS = [
    "IncomeTaxExpenseBenefit",
]

PRETAX_INCOME_KEYS = [
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesDomestic",
    "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
]

DA_KEYS = [
    "DepreciationDepletionAndAmortization",
    "DepreciationAndAmortization",
    "Depreciation",
]

INTEREST_EXPENSE_KEYS = [
    "InterestExpense",
    "InterestExpenseDebt",
    "InterestIncomeExpenseNet",
]

CAPEX_KEYS = [
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
    "CapitalExpendituresIncurredButNotYetPaid",
]

OPERATING_CF_KEYS = [
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
]

# Balance sheet keys
TOTAL_ASSETS_KEYS = ["Assets"]
CURRENT_ASSETS_KEYS = ["AssetsCurrent"]
CURRENT_LIABILITIES_KEYS = ["LiabilitiesCurrent"]
TOTAL_DEBT_KEYS = ["LongTermDebt", "LongTermDebtNoncurrent"]
SHORT_TERM_DEBT_KEYS = ["ShortTermBorrowings", "DebtCurrent", "LongTermDebtCurrent"]
CASH_KEYS = [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
]
SHORT_TERM_INVESTMENTS_KEYS = [
    "ShortTermInvestments",
    "AvailableForSaleSecuritiesCurrent",
    "MarketableSecuritiesCurrent",
]
EQUITY_KEYS = [
    "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
]
SHARES_OUTSTANDING_KEYS = [
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    "CommonStockSharesOutstanding",
    "EntityCommonStockSharesOutstanding",
    "WeightedAverageNumberOfShareOutstandingBasicAndDiluted",
]
GROSS_PROFIT_KEYS = ["GrossProfit"]
COGS_KEYS = [
    "CostOfGoodsAndServicesSold",
    "CostOfRevenue",
    "CostOfGoodsSold",
]
EBITDA_KEYS = [
    # Not a standard XBRL field - we calculate it
]


class DCFCalculator:
    """
    Industry-standard Discounted Cash Flow valuation model.

    Implements the Unlevered DCF (FCFF) approach:
    1. Calculate historical Free Cash Flow to Firm
    2. Forecast 5 years of future FCF
    3. Calculate Terminal Value (Gordon Growth + Exit Multiple)
    4. Discount to present using WACC
    5. Bridge from Enterprise Value to Equity Value per share

    Usage:
        calculator = DCFCalculator()
        dcf_result = calculator.run_dcf(ticker, xbrl_metrics)
    """

    def __init__(self):
        """Initialize DCF Calculator with config defaults."""
        self.forecast_years = config.DCF_FORECAST_YEARS
        self.risk_free_rate = config.DCF_RISK_FREE_RATE
        self.equity_risk_premium = config.DCF_EQUITY_RISK_PREMIUM
        self.terminal_growth = config.DCF_TERMINAL_GROWTH_RATE
        self.growth_taper = config.DCF_GROWTH_TAPER

    # ========================================================================
    # MAIN ENTRY POINT
    # ========================================================================

    def run_dcf(self, ticker: str, xbrl_metrics: Dict) -> Dict:
        """
        Run complete DCF valuation for a ticker.

        Args:
            ticker: Stock ticker symbol
            xbrl_metrics: XBRL metrics from Phase 3

        Returns:
            Complete DCF result dictionary with all components
        """
        ticker = ticker.upper()
        logger.info(f"Running DCF valuation for {ticker}...")

        # Step 1: Extract historical financials from XBRL data
        historicals = self._extract_historicals(xbrl_metrics)

        if not historicals or len(historicals) < 2:
            logger.error(f"Insufficient historical data for DCF ({len(historicals) if historicals else 0} periods)")
            return {"success": False, "error": "Insufficient historical data (need at least 2 annual periods)"}

        # Step 2: Calculate historical FCF and key metrics
        historical_fcf = self._calculate_historical_fcf(historicals)

        # Step 3: Calculate WACC
        wacc_result = self._calculate_wacc(ticker, historicals)

        # Step 4: Forecast future FCF
        fcf_forecast = self._forecast_fcf(historicals, historical_fcf)

        # Step 5: Calculate Terminal Value (both methods)
        terminal_value = self._calculate_terminal_value(
            fcf_forecast, historicals, wacc_result["wacc"]
        )

        # Step 6: Calculate Enterprise Value
        ev_result = self._calculate_enterprise_value(
            fcf_forecast, terminal_value, wacc_result["wacc"]
        )

        # Step 7: Bridge to Equity Value per share
        equity_result = self._bridge_to_equity(ev_result, historicals)

        # Step 8: Sensitivity analysis
        sensitivity = self._run_sensitivity_analysis(
            fcf_forecast, historicals, wacc_result["wacc"]
        )

        # Step 9: Bull / Base / Bear scenarios
        scenarios = self._run_scenario_analysis(
            historicals, historical_fcf, wacc_result["wacc"]
        )

        # Step 10: Calculate JPM-style key metrics
        key_metrics = self._calculate_key_metrics(
            historicals, historical_fcf, wacc_result,
            ev_result, equity_result, fcf_forecast
        )

        # Assemble final result
        result = {
            "success": True,
            "ticker": ticker,
            "entity_name": xbrl_metrics.get("entity_name", ""),
            "valuation_date": datetime.now().strftime('%Y-%m-%d'),
            "model_version": "1.0",

            # Historical data
            "historicals": historicals,
            "historical_fcf": historical_fcf,

            # WACC
            "wacc": wacc_result,

            # Forecast
            "fcf_forecast": fcf_forecast,

            # Terminal value
            "terminal_value": terminal_value,

            # Enterprise value
            "enterprise_value": ev_result,

            # Equity value
            "equity_value": equity_result,

            # Sensitivity
            "sensitivity_analysis": sensitivity,

            # Scenarios
            "scenarios": scenarios,

            # Key metrics (JPM-style highlights)
            "key_metrics": key_metrics,
        }

        logger.info(f"DCF complete for {ticker}: "
                     f"Fair value = ${equity_result.get('fair_value_per_share', 0):.2f}")

        return result

    # ========================================================================
    # STEP 1: EXTRACT HISTORICAL FINANCIALS
    # ========================================================================

    def _extract_historicals(self, xbrl_metrics: Dict) -> List[Dict]:
        """
        Extract historical annual (10-K) financial data from XBRL metrics.

        Returns list of dicts, one per fiscal year, sorted most recent first.
        Each dict contains: revenue, ebit, net_income, d_a, capex, etc.
        """
        metrics = xbrl_metrics.get("metrics", {})
        annual_data = {}

        for metric_key, metric_data in metrics.items():
            metric_name = metric_data.get("name", "")

            for value_entry in metric_data.get("values", []):
                form = value_entry.get("form", "")
                if form != "10-K":
                    continue

                period_end = value_entry.get("end", "")
                if not period_end:
                    continue

                if period_end not in annual_data:
                    annual_data[period_end] = {"period_end": period_end}

                val = value_entry.get("val")
                if val is not None:
                    annual_data[period_end][metric_name] = val

        # Sort by period (most recent first)
        sorted_periods = sorted(annual_data.keys(), reverse=True)
        result = [annual_data[p] for p in sorted_periods]

        logger.info(f"Extracted {len(result)} annual periods for DCF")
        return result

    def _lookup_metric(self, period_data: Dict, key_list: List[str],
                       default: Optional[float] = None) -> Optional[float]:
        """Look up a metric value trying multiple XBRL names."""
        for key in key_list:
            val = period_data.get(key)
            if val is not None:
                return float(val)
        return default

    # ========================================================================
    # STEP 2: CALCULATE HISTORICAL FCF
    # ========================================================================

    def _calculate_historical_fcf(self, historicals: List[Dict]) -> List[Dict]:
        """
        Calculate Free Cash Flow to Firm (FCFF) for each historical period.

        FCFF = EBIT × (1 - Tax Rate) + D&A - CapEx - ΔNWC

        Alternative (when cash flow data available):
        FCFF = Operating Cash Flow - CapEx + Interest × (1 - Tax Rate)

        Returns list of FCF data dicts (one per period).
        """
        fcf_data = []

        for i, period in enumerate(historicals):
            period_end = period.get("period_end", "Unknown")

            # Extract key financials
            revenue = self._lookup_metric(period, REVENUE_KEYS)
            ebit = self._lookup_metric(period, EBIT_KEYS)
            net_income = self._lookup_metric(period, NET_INCOME_KEYS)
            d_a = self._lookup_metric(period, DA_KEYS, 0)
            capex = self._lookup_metric(period, CAPEX_KEYS, 0)
            operating_cf = self._lookup_metric(period, OPERATING_CF_KEYS)
            tax_expense = self._lookup_metric(period, TAX_EXPENSE_KEYS, 0)
            pretax_income = self._lookup_metric(period, PRETAX_INCOME_KEYS)
            interest_expense = self._lookup_metric(period, INTEREST_EXPENSE_KEYS, 0)
            gross_profit = self._lookup_metric(period, GROSS_PROFIT_KEYS)
            cogs = self._lookup_metric(period, COGS_KEYS)

            # Current assets/liabilities for NWC
            current_assets = self._lookup_metric(period, CURRENT_ASSETS_KEYS, 0)
            current_liabilities = self._lookup_metric(period, CURRENT_LIABILITIES_KEYS, 0)
            cash = self._lookup_metric(period, CASH_KEYS, 0)

            # Calculate effective tax rate
            if pretax_income and pretax_income > 0 and tax_expense is not None:
                effective_tax_rate = abs(tax_expense) / pretax_income
                effective_tax_rate = min(max(effective_tax_rate, 0.0), 0.50)  # Cap at 50%
            elif ebit and ebit > 0 and tax_expense is not None:
                effective_tax_rate = abs(tax_expense) / ebit
                effective_tax_rate = min(max(effective_tax_rate, 0.0), 0.50)
            else:
                effective_tax_rate = 0.21  # US corporate default

            # Calculate EBITDA
            ebitda = (ebit + d_a) if ebit is not None else None

            # CapEx is reported as a payment (positive in XBRL = cash outflow)
            capex_abs = abs(capex) if capex else 0

            # Calculate NWC (Net Working Capital) — exclude cash
            nwc = (current_assets - cash) - current_liabilities if current_assets else 0

            # Calculate ΔNWC (change vs prior period)
            delta_nwc = 0
            if i < len(historicals) - 1:
                prior = historicals[i + 1]
                prior_ca = self._lookup_metric(prior, CURRENT_ASSETS_KEYS, 0)
                prior_cl = self._lookup_metric(prior, CURRENT_LIABILITIES_KEYS, 0)
                prior_cash = self._lookup_metric(prior, CASH_KEYS, 0)
                prior_nwc = (prior_ca - prior_cash) - prior_cl if prior_ca else 0
                delta_nwc = nwc - prior_nwc

            # === PRIMARY FCF CALCULATION ===
            # Method 1: EBIT-based (preferred by JPM equity research)
            # FCFF = EBIT × (1 - t) + D&A - CapEx - ΔNWC
            fcff_ebit = None
            if ebit is not None:
                nopat = ebit * (1 - effective_tax_rate)
                fcff_ebit = nopat + d_a - capex_abs - delta_nwc

            # Method 2: Operating Cash Flow based (cross-check)
            # FCFF = Operating CF - CapEx + Interest × (1 - t)
            fcff_ocf = None
            if operating_cf is not None:
                interest_tax_shield = abs(interest_expense) * (1 - effective_tax_rate) if interest_expense else 0
                fcff_ocf = operating_cf - capex_abs + interest_tax_shield

            # Use EBIT method as primary, OCF as fallback
            fcff = fcff_ebit if fcff_ebit is not None else fcff_ocf

            # Calculate margins
            gross_margin = (gross_profit / revenue) if (revenue and gross_profit) else None
            operating_margin = (ebit / revenue) if (revenue and ebit) else None
            net_margin = (net_income / revenue) if (revenue and net_income) else None
            fcf_margin = (fcff / revenue) if (revenue and fcff) else None

            entry = {
                "period_end": period_end,
                "revenue": revenue,
                "cogs": cogs,
                "gross_profit": gross_profit,
                "ebit": ebit,
                "ebitda": ebitda,
                "net_income": net_income,
                "d_a": d_a,
                "capex": capex_abs,
                "operating_cf": operating_cf,
                "interest_expense": abs(interest_expense) if interest_expense else 0,
                "tax_expense": abs(tax_expense) if tax_expense else 0,
                "effective_tax_rate": effective_tax_rate,
                "nwc": nwc,
                "delta_nwc": delta_nwc,
                "nopat": ebit * (1 - effective_tax_rate) if ebit else None,
                "fcff": fcff,
                "fcff_method": "EBIT" if fcff_ebit is not None else "OCF",
                "fcff_ebit_method": fcff_ebit,
                "fcff_ocf_method": fcff_ocf,

                # Margins
                "gross_margin": gross_margin,
                "operating_margin": operating_margin,
                "net_margin": net_margin,
                "fcf_margin": fcf_margin,

                # Balance sheet items
                "total_assets": self._lookup_metric(period, TOTAL_ASSETS_KEYS),
                "current_assets": current_assets,
                "current_liabilities": current_liabilities,
                "cash": cash,
                "short_term_investments": self._lookup_metric(period, SHORT_TERM_INVESTMENTS_KEYS, 0),
                "total_debt": self._lookup_metric(period, TOTAL_DEBT_KEYS, 0),
                "short_term_debt": self._lookup_metric(period, SHORT_TERM_DEBT_KEYS, 0),
                "equity": self._lookup_metric(period, EQUITY_KEYS),
                "shares_outstanding": self._lookup_metric(period, SHARES_OUTSTANDING_KEYS),
            }

            fcf_data.append(entry)

        return fcf_data

    # ========================================================================
    # STEP 3: CALCULATE WACC
    # ========================================================================

    def _calculate_wacc(self, ticker: str, historicals: List[Dict]) -> Dict:
        """
        Calculate Weighted Average Cost of Capital (WACC).

        WACC = (E/V) × Ke + (D/V) × Kd × (1 - t)

        Where:
        - Ke = Rf + β × ERP  (CAPM)
        - Kd = Interest Expense / Total Debt
        - E = Equity (book value as proxy)
        - D = Total Debt
        - V = E + D
        - t = Effective Tax Rate
        """
        latest = historicals[0] if historicals else {}

        # Get beta
        beta = config.DCF_INDUSTRY_BETAS.get(ticker,
               config.DCF_INDUSTRY_BETAS.get("DEFAULT", 1.0))

        # Cost of Equity (CAPM)
        cost_of_equity = self.risk_free_rate + beta * self.equity_risk_premium

        # Cost of Debt
        interest_expense = self._lookup_metric(latest, INTEREST_EXPENSE_KEYS, 0)
        total_debt = self._lookup_metric(latest, TOTAL_DEBT_KEYS, 0)
        short_term_debt = self._lookup_metric(latest, SHORT_TERM_DEBT_KEYS, 0)
        total_debt_all = total_debt + short_term_debt

        if total_debt_all > 0 and interest_expense:
            cost_of_debt = abs(interest_expense) / total_debt_all
            cost_of_debt = min(cost_of_debt, 0.15)  # Cap at 15%
        else:
            cost_of_debt = self.risk_free_rate + 0.015  # Rf + 1.5% credit spread

        # Tax rate
        tax_expense = self._lookup_metric(latest, TAX_EXPENSE_KEYS, 0)
        pretax_income = self._lookup_metric(latest, PRETAX_INCOME_KEYS)
        if pretax_income and pretax_income > 0 and tax_expense:
            tax_rate = abs(tax_expense) / pretax_income
            tax_rate = min(max(tax_rate, 0.0), 0.50)
        else:
            tax_rate = 0.21

        # Capital structure weights
        equity = self._lookup_metric(latest, EQUITY_KEYS, 0)
        if equity and equity > 0:
            total_capital = equity + total_debt_all
            weight_equity = equity / total_capital
            weight_debt = total_debt_all / total_capital
        else:
            weight_equity = 0.80
            weight_debt = 0.20

        # WACC calculation
        wacc = (weight_equity * cost_of_equity) + \
               (weight_debt * cost_of_debt * (1 - tax_rate))

        # Sanity check: WACC should be between 5% and 25%
        wacc = min(max(wacc, 0.05), 0.25)

        result = {
            "wacc": wacc,
            "cost_of_equity": cost_of_equity,
            "cost_of_debt": cost_of_debt,
            "after_tax_cost_of_debt": cost_of_debt * (1 - tax_rate),
            "beta": beta,
            "risk_free_rate": self.risk_free_rate,
            "equity_risk_premium": self.equity_risk_premium,
            "tax_rate": tax_rate,
            "weight_equity": weight_equity,
            "weight_debt": weight_debt,
            "total_debt": total_debt_all,
            "equity_book_value": equity,
        }

        logger.info(f"WACC: {wacc:.2%} (Ke={cost_of_equity:.2%}, "
                     f"Kd={cost_of_debt:.2%}, β={beta:.2f})")

        return result

    # ========================================================================
    # STEP 4: FORECAST FCF
    # ========================================================================

    def _forecast_fcf(self, historicals: List[Dict],
                      historical_fcf: List[Dict]) -> List[Dict]:
        """
        Forecast 5 years of Free Cash Flow.

        Methodology:
        1. Calculate historical revenue CAGR
        2. Apply tapering growth (converging to terminal rate)
        3. Maintain operating margin trend (or stabilize)
        4. Project CapEx as % of revenue
        5. Project D&A and NWC changes

        This follows JP Morgan's approach of revenue-driven FCF forecasting.
        """
        # Get valid historical periods with revenue and FCF
        valid_periods = [p for p in historical_fcf if p.get("revenue") and p.get("fcff")]

        if len(valid_periods) < 2:
            logger.warning("Insufficient data for FCF forecast, using simplified model")
            return self._simplified_forecast(historical_fcf)

        # === Revenue Growth ===
        # Calculate CAGR over available history
        latest = valid_periods[0]
        earliest = valid_periods[-1]
        years_span = max(len(valid_periods) - 1, 1)

        revenue_cagr = (latest["revenue"] / earliest["revenue"]) ** (1 / years_span) - 1
        # Cap historical CAGR at reasonable levels
        revenue_cagr = min(max(revenue_cagr, -0.10), 0.50)

        # === Margin Assumptions ===
        # Use average of last 2-3 years for stability
        recent_margins = valid_periods[:min(3, len(valid_periods))]
        avg_operating_margin = self._safe_avg([p.get("operating_margin") for p in recent_margins])
        avg_fcf_margin = self._safe_avg([p.get("fcf_margin") for p in recent_margins])

        # CapEx as % of revenue (average historical)
        capex_pct = self._safe_avg([
            p["capex"] / p["revenue"] for p in valid_periods
            if p.get("revenue") and p.get("capex")
        ]) or 0.05

        # D&A as % of revenue
        da_pct = self._safe_avg([
            p["d_a"] / p["revenue"] for p in valid_periods
            if p.get("revenue") and p.get("d_a")
        ]) or 0.03

        # Tax rate (use latest)
        tax_rate = latest.get("effective_tax_rate", 0.21)

        # NWC change as % of revenue change
        nwc_pct = 0.02  # Assume 2% of revenue change goes to NWC

        # === Build Forecast ===
        forecasts = []
        base_revenue = latest["revenue"]

        for year in range(1, self.forecast_years + 1):
            # Tapered growth rate
            taper_idx = min(year - 1, len(self.growth_taper) - 1)
            taper = self.growth_taper[taper_idx]

            # Growth rate converges from historical CAGR toward terminal rate
            growth_rate = (revenue_cagr * taper) + (self.terminal_growth * (1 - taper))
            growth_rate = max(growth_rate, self.terminal_growth)  # Floor at terminal

            # Project revenue
            projected_revenue = base_revenue * (1 + growth_rate)

            # Project EBIT using operating margin (slight margin improvement/stability)
            projected_ebit = projected_revenue * avg_operating_margin

            # Project components
            projected_da = projected_revenue * da_pct
            projected_capex = projected_revenue * capex_pct
            projected_ebitda = projected_ebit + projected_da
            projected_nopat = projected_ebit * (1 - tax_rate)
            projected_delta_nwc = (projected_revenue - base_revenue) * nwc_pct

            # FCFF = NOPAT + D&A - CapEx - ΔNWC
            projected_fcff = projected_nopat + projected_da - projected_capex - projected_delta_nwc

            forecasts.append({
                "year": year,
                "period": f"FY+{year}",
                "revenue": projected_revenue,
                "revenue_growth": growth_rate,
                "ebit": projected_ebit,
                "ebitda": projected_ebitda,
                "operating_margin": avg_operating_margin,
                "nopat": projected_nopat,
                "d_a": projected_da,
                "capex": projected_capex,
                "delta_nwc": projected_delta_nwc,
                "fcff": projected_fcff,
                "fcf_margin": projected_fcff / projected_revenue if projected_revenue else 0,
                "tax_rate": tax_rate,
            })

            base_revenue = projected_revenue

        # Store assumptions used
        self._forecast_assumptions = {
            "revenue_cagr": revenue_cagr,
            "avg_operating_margin": avg_operating_margin,
            "avg_fcf_margin": avg_fcf_margin,
            "capex_pct_revenue": capex_pct,
            "da_pct_revenue": da_pct,
            "nwc_pct_revenue_change": nwc_pct,
            "tax_rate": tax_rate,
            "terminal_growth": self.terminal_growth,
        }

        return forecasts

    def _simplified_forecast(self, historical_fcf: List[Dict]) -> List[Dict]:
        """Simplified forecast when insufficient historical data."""
        latest = historical_fcf[0] if historical_fcf else {}
        base_fcf = latest.get("fcff", 0) or latest.get("revenue", 0) * 0.15
        base_revenue = latest.get("revenue", 0)

        forecasts = []
        for year in range(1, self.forecast_years + 1):
            growth = self.terminal_growth + 0.03  # terminal + 3%
            projected_revenue = base_revenue * (1 + growth)
            projected_fcf = base_fcf * (1 + growth)

            forecasts.append({
                "year": year,
                "period": f"FY+{year}",
                "revenue": projected_revenue,
                "revenue_growth": growth,
                "fcff": projected_fcf,
                "ebit": projected_revenue * 0.20,
                "ebitda": projected_revenue * 0.25,
                "operating_margin": 0.20,
                "nopat": projected_revenue * 0.20 * 0.79,
                "d_a": projected_revenue * 0.03,
                "capex": projected_revenue * 0.05,
                "delta_nwc": (projected_revenue - base_revenue) * 0.02,
                "fcf_margin": projected_fcf / projected_revenue if projected_revenue else 0,
                "tax_rate": 0.21,
            })
            base_revenue = projected_revenue
            base_fcf = projected_fcf

        self._forecast_assumptions = {
            "revenue_cagr": growth,
            "note": "Simplified forecast due to limited data",
        }
        return forecasts

    # ========================================================================
    # STEP 5: TERMINAL VALUE
    # ========================================================================

    def _calculate_terminal_value(self, fcf_forecast: List[Dict],
                                   historicals: List[Dict],
                                   wacc: float) -> Dict:
        """
        Calculate Terminal Value using two methods:

        1. Gordon Growth Model (Perpetuity):
           TV = FCF_n × (1 + g) / (WACC - g)

        2. Exit Multiple Method:
           TV = EBITDA_n × EV/EBITDA multiple
        """
        final_year = fcf_forecast[-1] if fcf_forecast else {}
        final_fcf = final_year.get("fcff", 0)
        final_ebitda = final_year.get("ebitda", 0)

        # Method 1: Gordon Growth
        g = self.terminal_growth
        if wacc > g:
            tv_gordon = final_fcf * (1 + g) / (wacc - g)
        else:
            tv_gordon = final_fcf * 25  # Fallback: 25x FCF

        # Method 2: Exit Multiple
        exit_multiple = config.DCF_DEFAULT_EXIT_MULTIPLE
        tv_exit = final_ebitda * exit_multiple

        # Average of both methods (JP Morgan practice)
        tv_blended = (tv_gordon + tv_exit) / 2

        # Implied metrics
        implied_gordon_multiple = tv_gordon / final_ebitda if final_ebitda else 0
        implied_exit_growth = None
        if final_fcf and tv_exit > 0:
            # Solve for g: TV = FCF × (1+g) / (WACC-g)
            # g = (TV × WACC - FCF) / (TV + FCF)
            implied_exit_growth = (tv_exit * wacc - final_fcf) / (tv_exit + final_fcf)

        result = {
            "gordon_growth": {
                "terminal_value": tv_gordon,
                "growth_rate": g,
                "implied_multiple": implied_gordon_multiple,
            },
            "exit_multiple": {
                "terminal_value": tv_exit,
                "multiple": exit_multiple,
                "implied_growth": implied_exit_growth,
            },
            "blended_terminal_value": tv_blended,
            "final_year_fcf": final_fcf,
            "final_year_ebitda": final_ebitda,
        }

        logger.info(f"Terminal Value: Gordon=${tv_gordon/1e9:.1f}B, "
                     f"Exit=${tv_exit/1e9:.1f}B, Blended=${tv_blended/1e9:.1f}B")

        return result

    # ========================================================================
    # STEP 6: ENTERPRISE VALUE
    # ========================================================================

    def _calculate_enterprise_value(self, fcf_forecast: List[Dict],
                                     terminal_value: Dict,
                                     wacc: float) -> Dict:
        """
        Calculate Enterprise Value by discounting FCF and Terminal Value.

        EV = Σ [FCF_t / (1 + WACC)^t] + TV / (1 + WACC)^n
        """
        # Discount projected FCFs
        pv_fcf_components = []
        total_pv_fcf = 0

        for forecast in fcf_forecast:
            year = forecast["year"]
            fcf = forecast["fcff"]
            discount_factor = 1 / ((1 + wacc) ** year)
            pv = fcf * discount_factor

            pv_fcf_components.append({
                "year": year,
                "fcf": fcf,
                "discount_factor": discount_factor,
                "present_value": pv,
            })
            total_pv_fcf += pv

        # Discount terminal value
        n = self.forecast_years
        tv_discount_factor = 1 / ((1 + wacc) ** n)

        tv_gordon_pv = terminal_value["gordon_growth"]["terminal_value"] * tv_discount_factor
        tv_exit_pv = terminal_value["exit_multiple"]["terminal_value"] * tv_discount_factor
        tv_blended_pv = terminal_value["blended_terminal_value"] * tv_discount_factor

        # Enterprise Values
        ev_gordon = total_pv_fcf + tv_gordon_pv
        ev_exit = total_pv_fcf + tv_exit_pv
        ev_blended = total_pv_fcf + tv_blended_pv

        # Composition analysis (what % comes from terminal value)
        tv_pct_gordon = (tv_gordon_pv / ev_gordon * 100) if ev_gordon else 0
        tv_pct_exit = (tv_exit_pv / ev_exit * 100) if ev_exit else 0

        result = {
            "pv_fcf_components": pv_fcf_components,
            "total_pv_fcf": total_pv_fcf,
            "pv_terminal_gordon": tv_gordon_pv,
            "pv_terminal_exit": tv_exit_pv,
            "pv_terminal_blended": tv_blended_pv,
            "ev_gordon": ev_gordon,
            "ev_exit": ev_exit,
            "ev_blended": ev_blended,
            "tv_pct_of_ev_gordon": tv_pct_gordon,
            "tv_pct_of_ev_exit": tv_pct_exit,
            "wacc_used": wacc,
        }

        logger.info(f"Enterprise Value: ${ev_blended/1e9:.1f}B "
                     f"(TV is {tv_pct_gordon:.0f}% of EV via Gordon)")

        return result

    # ========================================================================
    # STEP 7: EQUITY VALUE BRIDGE
    # ========================================================================

    def _bridge_to_equity(self, ev_result: Dict,
                           historicals: List[Dict]) -> Dict:
        """
        Bridge from Enterprise Value to Equity Value per share.

        Equity Value = EV + Cash - Total Debt - Minority Interest
        Fair Value per Share = Equity Value / Diluted Shares Outstanding
        """
        latest = historicals[0] if historicals else {}
        latest_fcf = None

        # Get balance sheet items from latest period
        cash = self._lookup_metric(latest, CASH_KEYS, 0)
        st_investments = self._lookup_metric(latest, SHORT_TERM_INVESTMENTS_KEYS, 0)
        total_cash = cash + st_investments

        total_debt = self._lookup_metric(latest, TOTAL_DEBT_KEYS, 0)
        st_debt = self._lookup_metric(latest, SHORT_TERM_DEBT_KEYS, 0)
        total_debt_all = total_debt + st_debt

        shares = self._lookup_metric(latest, SHARES_OUTSTANDING_KEYS)

        # Calculate equity values for each TV method
        results = {}
        for method, ev_key in [("gordon", "ev_gordon"),
                                ("exit", "ev_exit"),
                                ("blended", "ev_blended")]:
            ev = ev_result[ev_key]
            equity_value = ev + total_cash - total_debt_all
            per_share = equity_value / shares if shares and shares > 0 else 0

            results[f"equity_value_{method}"] = equity_value
            results[f"fair_value_{method}"] = per_share

        # Primary fair value (blended)
        results["fair_value_per_share"] = results.get("fair_value_blended", 0)
        results["equity_value"] = results.get("equity_value_blended", 0)

        # Bridge components
        results["bridge"] = {
            "enterprise_value": ev_result["ev_blended"],
            "plus_cash": total_cash,
            "minus_debt": total_debt_all,
            "equity_value": results["equity_value"],
            "shares_outstanding": shares,
            "fair_value_per_share": results["fair_value_per_share"],
        }

        return results

    # ========================================================================
    # STEP 8: SENSITIVITY ANALYSIS
    # ========================================================================

    def _run_sensitivity_analysis(self, fcf_forecast: List[Dict],
                                   historicals: List[Dict],
                                   base_wacc: float) -> Dict:
        """
        Generate sensitivity tables:
        1. WACC vs Terminal Growth Rate → Fair Value matrix
        2. WACC vs Revenue Growth → Fair Value matrix
        """
        latest = historicals[0] if historicals else {}
        cash = self._lookup_metric(latest, CASH_KEYS, 0) + \
               self._lookup_metric(latest, SHORT_TERM_INVESTMENTS_KEYS, 0)
        total_debt = self._lookup_metric(latest, TOTAL_DEBT_KEYS, 0) + \
                     self._lookup_metric(latest, SHORT_TERM_DEBT_KEYS, 0)
        shares = self._lookup_metric(latest, SHARES_OUTSTANDING_KEYS, 1)

        # === Table 1: WACC vs Terminal Growth Rate ===
        wacc_range = [base_wacc + delta for delta in config.DCF_SENSITIVITY_WACC_RANGE]
        growth_range = [self.terminal_growth + delta for delta in config.DCF_SENSITIVITY_GROWTH_RANGE]

        wacc_growth_matrix = []
        for wacc_val in wacc_range:
            row = {"wacc": wacc_val, "values": []}
            for g in growth_range:
                fair_value = self._quick_dcf(fcf_forecast, wacc_val, g,
                                              cash, total_debt, shares)
                row["values"].append({
                    "terminal_growth": g,
                    "fair_value": fair_value,
                })
            wacc_growth_matrix.append(row)

        return {
            "wacc_vs_growth": {
                "wacc_values": wacc_range,
                "growth_values": growth_range,
                "matrix": wacc_growth_matrix,
                "base_wacc": base_wacc,
                "base_growth": self.terminal_growth,
            }
        }

    def _quick_dcf(self, fcf_forecast: List[Dict], wacc: float,
                    terminal_growth: float, cash: float, debt: float,
                    shares: float) -> float:
        """Quick DCF calculation for sensitivity table."""
        if wacc <= terminal_growth:
            return 0

        # PV of forecast FCFs
        total_pv = sum(
            f["fcff"] / ((1 + wacc) ** f["year"])
            for f in fcf_forecast
        )

        # Terminal value (Gordon Growth)
        final_fcf = fcf_forecast[-1]["fcff"]
        tv = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
        tv_pv = tv / ((1 + wacc) ** len(fcf_forecast))

        # Enterprise to equity
        ev = total_pv + tv_pv
        equity = ev + cash - debt
        per_share = equity / shares if shares and shares > 0 else 0

        return per_share

    # ========================================================================
    # STEP 9: SCENARIO ANALYSIS
    # ========================================================================

    def _run_scenario_analysis(self, historicals: List[Dict],
                                historical_fcf: List[Dict],
                                base_wacc: float) -> Dict:
        """
        Run Bull / Base / Bear scenario analysis.

        Bull: Higher growth, margin expansion
        Base: Current trajectory (our DCF output)
        Bear: Lower growth, margin compression
        """
        latest_fcf = historical_fcf[0] if historical_fcf else {}
        latest = historicals[0] if historicals else {}

        cash = self._lookup_metric(latest, CASH_KEYS, 0) + \
               self._lookup_metric(latest, SHORT_TERM_INVESTMENTS_KEYS, 0)
        debt = self._lookup_metric(latest, TOTAL_DEBT_KEYS, 0) + \
               self._lookup_metric(latest, SHORT_TERM_DEBT_KEYS, 0)
        shares = self._lookup_metric(latest, SHARES_OUTSTANDING_KEYS, 1)

        revenue = latest_fcf.get("revenue", 0)
        fcf = latest_fcf.get("fcff", 0)
        operating_margin = latest_fcf.get("operating_margin", 0.15)

        scenarios = {}
        scenario_configs = {
            "bull": {
                "revenue_growth_adj": config.DCF_SCENARIO_BULL_MULTIPLIER,
                "margin_adj": 1.05,  # 5% margin expansion
                "wacc_adj": -0.005,  # Slightly lower WACC
                "terminal_growth_adj": 0.005,
            },
            "base": {
                "revenue_growth_adj": 1.0,
                "margin_adj": 1.0,
                "wacc_adj": 0.0,
                "terminal_growth_adj": 0.0,
            },
            "bear": {
                "revenue_growth_adj": config.DCF_SCENARIO_BEAR_MULTIPLIER,
                "margin_adj": 0.90,  # 10% margin compression
                "wacc_adj": 0.01,  # Higher WACC (more risk)
                "terminal_growth_adj": -0.005,
            },
        }

        for scenario_name, adj in scenario_configs.items():
            # Build scenario-specific forecast
            scenario_forecasts = []
            base_rev = revenue

            assumptions = getattr(self, '_forecast_assumptions', {})
            base_cagr = assumptions.get("revenue_cagr", 0.10)
            base_op_margin = assumptions.get("avg_operating_margin", operating_margin)
            tax_rate = assumptions.get("tax_rate", 0.21)
            capex_pct = assumptions.get("capex_pct_revenue", 0.05)
            da_pct = assumptions.get("da_pct_revenue", 0.03)
            nwc_pct = assumptions.get("nwc_pct_revenue_change", 0.02)

            scenario_wacc = base_wacc + adj["wacc_adj"]
            scenario_terminal_g = self.terminal_growth + adj["terminal_growth_adj"]
            scenario_margin = base_op_margin * adj["margin_adj"]

            for year in range(1, self.forecast_years + 1):
                taper_idx = min(year - 1, len(self.growth_taper) - 1)
                taper = self.growth_taper[taper_idx]
                adj_cagr = base_cagr * adj["revenue_growth_adj"]
                growth = (adj_cagr * taper) + (scenario_terminal_g * (1 - taper))
                growth = max(growth, scenario_terminal_g)

                proj_rev = base_rev * (1 + growth)
                proj_ebit = proj_rev * scenario_margin
                proj_da = proj_rev * da_pct
                proj_capex = proj_rev * capex_pct
                proj_nopat = proj_ebit * (1 - tax_rate)
                proj_delta_nwc = (proj_rev - base_rev) * nwc_pct
                proj_fcf = proj_nopat + proj_da - proj_capex - proj_delta_nwc

                scenario_forecasts.append({
                    "year": year,
                    "revenue": proj_rev,
                    "revenue_growth": growth,
                    "ebit": proj_ebit,
                    "ebitda": proj_ebit + proj_da,
                    "fcff": proj_fcf,
                    "operating_margin": scenario_margin,
                })
                base_rev = proj_rev

            fair_value = self._quick_dcf(scenario_forecasts, scenario_wacc,
                                          scenario_terminal_g, cash, debt, shares)

            scenarios[scenario_name] = {
                "fair_value_per_share": fair_value,
                "wacc": scenario_wacc,
                "terminal_growth": scenario_terminal_g,
                "operating_margin": scenario_margin,
                "revenue_growth_yr1": scenario_forecasts[0]["revenue_growth"] if scenario_forecasts else 0,
                "final_year_revenue": scenario_forecasts[-1]["revenue"] if scenario_forecasts else 0,
                "final_year_fcf": scenario_forecasts[-1]["fcff"] if scenario_forecasts else 0,
            }

        return scenarios

    # ========================================================================
    # STEP 10: KEY METRICS (JPM ANALYST HIGHLIGHTS)
    # ========================================================================

    def _calculate_key_metrics(self, historicals: List[Dict],
                                historical_fcf: List[Dict],
                                wacc_result: Dict, ev_result: Dict,
                                equity_result: Dict,
                                fcf_forecast: List[Dict]) -> Dict:
        """
        Calculate the key metrics a JP Morgan equity analyst would
        highlight in a DCF presentation.

        These are the numbers that matter most to institutional investors.
        """
        latest = historicals[0] if historicals else {}
        latest_fcf = historical_fcf[0] if historical_fcf else {}
        assumptions = getattr(self, '_forecast_assumptions', {})

        fair_value = equity_result.get("fair_value_per_share", 0)
        ev_blended = ev_result.get("ev_blended", 0)
        tv_pct = ev_result.get("tv_pct_of_ev_gordon", 0)

        revenue = latest_fcf.get("revenue", 0)
        ebitda = latest_fcf.get("ebitda", 0)
        fcf = latest_fcf.get("fcff", 0)
        net_income = latest_fcf.get("net_income", 0)
        shares = latest_fcf.get("shares_outstanding", 1)
        equity = latest_fcf.get("equity", 0)
        total_assets = latest_fcf.get("total_assets", 0)

        # ★ KEY METRIC: ROIC vs WACC (value creation check)
        invested_capital = (equity or 0) + (latest_fcf.get("total_debt", 0))
        nopat = latest_fcf.get("nopat", 0)
        roic = nopat / invested_capital if invested_capital and invested_capital > 0 else 0
        wacc = wacc_result["wacc"]
        value_creation_spread = roic - wacc

        # ★ KEY METRIC: FCF Yield
        fcf_yield = fcf / ev_blended if ev_blended and ev_blended > 0 else 0

        # ★ KEY METRIC: Implied EV/EBITDA
        implied_ev_ebitda = ev_blended / ebitda if ebitda and ebitda > 0 else 0

        # ★ KEY METRIC: Revenue CAGR
        revenue_cagr = assumptions.get("revenue_cagr", 0)

        # ★ KEY METRIC: Margin trajectory
        margins_by_year = []
        for p in historical_fcf[:5]:
            if p.get("operating_margin") is not None:
                margins_by_year.append({
                    "period": p["period_end"],
                    "operating_margin": p["operating_margin"],
                    "net_margin": p.get("net_margin"),
                    "fcf_margin": p.get("fcf_margin"),
                })

        # ★ KEY METRIC: Earnings per share trajectory
        eps = net_income / shares if shares and shares > 0 else 0

        # ★ KEY METRIC: Terminal value % of EV (risk indicator)
        # >80% is a red flag (too much value in terminal)
        tv_risk = "HIGH" if tv_pct > 80 else "MODERATE" if tv_pct > 65 else "LOW"

        # ★ KEY METRIC: Revenue per share growth
        projected_revenue_yr5 = fcf_forecast[-1]["revenue"] if fcf_forecast else revenue
        projected_fcf_yr5 = fcf_forecast[-1]["fcff"] if fcf_forecast else fcf
        implied_5yr_rev_cagr = (projected_revenue_yr5 / revenue) ** 0.2 - 1 if revenue else 0

        return {
            # === VALUATION HIGHLIGHTS ===
            "fair_value_per_share": fair_value,
            "implied_ev_ebitda": implied_ev_ebitda,
            "fcf_yield": fcf_yield,
            "terminal_value_pct_of_ev": tv_pct,
            "terminal_value_risk": tv_risk,

            # === RETURNS & VALUE CREATION ===
            "roic": roic,
            "wacc": wacc,
            "roic_wacc_spread": value_creation_spread,
            "value_creation": "POSITIVE" if value_creation_spread > 0 else "NEGATIVE",
            "roe": net_income / equity if equity and equity > 0 else 0,
            "roa": net_income / total_assets if total_assets and total_assets > 0 else 0,

            # === GROWTH ===
            "historical_revenue_cagr": revenue_cagr,
            "implied_5yr_revenue_cagr": implied_5yr_rev_cagr,
            "eps_ltm": eps,

            # === PROFITABILITY ===
            "gross_margin": latest_fcf.get("gross_margin"),
            "operating_margin": latest_fcf.get("operating_margin"),
            "net_margin": latest_fcf.get("net_margin"),
            "fcf_margin": latest_fcf.get("fcf_margin"),
            "margin_trajectory": margins_by_year,

            # === CAPITAL STRUCTURE ===
            "net_debt": (latest_fcf.get("total_debt", 0) +
                        latest_fcf.get("short_term_debt", 0) -
                        latest_fcf.get("cash", 0) -
                        latest_fcf.get("short_term_investments", 0)),
            "debt_to_equity": ((latest_fcf.get("total_debt", 0)) / equity
                              if equity and equity > 0 else 0),

            # === MODEL ASSUMPTIONS ===
            "forecast_assumptions": assumptions,
        }

    # ========================================================================
    # OUTPUT: SAVE & EXPORT
    # ========================================================================

    def save_dcf_json(self, dcf_result: Dict, output_path: Path) -> bool:
        """Save DCF results to JSON file."""
        try:
            # Convert non-serializable values
            def clean_for_json(obj):
                if isinstance(obj, float):
                    if obj != obj:  # NaN check
                        return None
                    if abs(obj) == float('inf'):
                        return None
                    return round(obj, 6)
                if isinstance(obj, dict):
                    return {k: clean_for_json(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [clean_for_json(v) for v in obj]
                return obj

            cleaned = clean_for_json(dcf_result)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned, f, indent=2, default=str)

            logger.info(f"DCF JSON saved to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save DCF JSON: {e}", exc_info=True)
            return False

    def save_dcf_csv(self, dcf_result: Dict, output_dir: Path) -> Dict[str, bool]:
        """
        Save DCF results to multiple CSV files.

        Files generated:
        1. {TICKER}_dcf_summary.csv - Executive summary
        2. {TICKER}_dcf_forecast.csv - Detailed forecast
        3. {TICKER}_dcf_sensitivity.csv - Sensitivity matrix
        """
        ticker = dcf_result.get("ticker", "UNKNOWN")
        results = {}

        # 1. Executive Summary CSV
        summary_path = output_dir / f"{ticker}_dcf_summary.csv"
        results["summary"] = self._write_summary_csv(dcf_result, summary_path)

        # 2. Forecast Detail CSV
        forecast_path = output_dir / f"{ticker}_dcf_forecast.csv"
        results["forecast"] = self._write_forecast_csv(dcf_result, forecast_path)

        # 3. Sensitivity Matrix CSV
        sensitivity_path = output_dir / f"{ticker}_dcf_sensitivity.csv"
        results["sensitivity"] = self._write_sensitivity_csv(dcf_result, sensitivity_path)

        return results

    def _write_summary_csv(self, dcf_result: Dict, path: Path) -> bool:
        """Write executive summary CSV."""
        try:
            km = dcf_result.get("key_metrics", {})
            wacc = dcf_result.get("wacc", {})
            ev = dcf_result.get("enterprise_value", {})
            eq = dcf_result.get("equity_value", {})
            tv = dcf_result.get("terminal_value", {})
            scenarios = dcf_result.get("scenarios", {})

            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)

                w.writerow([f"DCF VALUATION SUMMARY - {dcf_result.get('ticker', '')}"])
                w.writerow([f"Entity: {dcf_result.get('entity_name', '')}"])
                w.writerow([f"Date: {dcf_result.get('valuation_date', '')}"])
                w.writerow([])

                # === VALUATION ===
                w.writerow(["★ VALUATION HIGHLIGHTS"])
                w.writerow(["Metric", "Value"])
                w.writerow(["Fair Value per Share (Blended)", f"${km.get('fair_value_per_share', 0):.2f}"])
                w.writerow(["Fair Value (Gordon Growth)", f"${eq.get('fair_value_gordon', 0):.2f}"])
                w.writerow(["Fair Value (Exit Multiple)", f"${eq.get('fair_value_exit', 0):.2f}"])
                w.writerow(["Enterprise Value", self._fmt_b(ev.get('ev_blended', 0))])
                w.writerow(["Implied EV/EBITDA", f"{km.get('implied_ev_ebitda', 0):.1f}x"])
                w.writerow(["FCF Yield", f"{km.get('fcf_yield', 0):.1%}"])
                w.writerow([])

                # === WACC ===
                w.writerow(["★ WACC BREAKDOWN"])
                w.writerow(["Component", "Value"])
                w.writerow(["WACC", f"{wacc.get('wacc', 0):.2%}"])
                w.writerow(["Cost of Equity (Ke)", f"{wacc.get('cost_of_equity', 0):.2%}"])
                w.writerow(["Cost of Debt (Kd)", f"{wacc.get('cost_of_debt', 0):.2%}"])
                w.writerow(["Beta", f"{wacc.get('beta', 0):.2f}"])
                w.writerow(["Risk-Free Rate", f"{wacc.get('risk_free_rate', 0):.2%}"])
                w.writerow(["Equity Risk Premium", f"{wacc.get('equity_risk_premium', 0):.2%}"])
                w.writerow(["Weight Equity", f"{wacc.get('weight_equity', 0):.1%}"])
                w.writerow(["Weight Debt", f"{wacc.get('weight_debt', 0):.1%}"])
                w.writerow(["Tax Rate", f"{wacc.get('tax_rate', 0):.1%}"])
                w.writerow([])

                # === VALUE CREATION ===
                w.writerow(["★ VALUE CREATION (ROIC vs WACC)"])
                w.writerow(["ROIC", f"{km.get('roic', 0):.2%}"])
                w.writerow(["WACC", f"{wacc.get('wacc', 0):.2%}"])
                w.writerow(["Spread (ROIC - WACC)", f"{km.get('roic_wacc_spread', 0):.2%}"])
                w.writerow(["Value Creation", km.get("value_creation", "")])
                w.writerow([])

                # === PROFITABILITY ===
                w.writerow(["★ PROFITABILITY"])
                w.writerow(["Gross Margin", f"{km.get('gross_margin', 0):.1%}" if km.get('gross_margin') else "N/A"])
                w.writerow(["Operating Margin", f"{km.get('operating_margin', 0):.1%}" if km.get('operating_margin') else "N/A"])
                w.writerow(["Net Margin", f"{km.get('net_margin', 0):.1%}" if km.get('net_margin') else "N/A"])
                w.writerow(["FCF Margin", f"{km.get('fcf_margin', 0):.1%}" if km.get('fcf_margin') else "N/A"])
                w.writerow([])

                # === TERMINAL VALUE ===
                w.writerow(["★ TERMINAL VALUE"])
                gordon = tv.get("gordon_growth", {})
                exit_m = tv.get("exit_multiple", {})
                w.writerow(["Gordon Growth TV", self._fmt_b(gordon.get("terminal_value", 0))])
                w.writerow(["Gordon Implied Multiple", f"{gordon.get('implied_multiple', 0):.1f}x"])
                w.writerow(["Exit Multiple TV", self._fmt_b(exit_m.get("terminal_value", 0))])
                w.writerow(["Exit Multiple Used", f"{exit_m.get('multiple', 0):.1f}x"])
                w.writerow(["TV % of EV", f"{km.get('terminal_value_pct_of_ev', 0):.0f}%"])
                w.writerow(["TV Risk Level", km.get("terminal_value_risk", "")])
                w.writerow([])

                # === SCENARIOS ===
                w.writerow(["★ SCENARIO ANALYSIS"])
                w.writerow(["Scenario", "Fair Value", "WACC", "Terminal Growth"])
                for name in ["bull", "base", "bear"]:
                    s = scenarios.get(name, {})
                    w.writerow([
                        name.upper(),
                        f"${s.get('fair_value_per_share', 0):.2f}",
                        f"{s.get('wacc', 0):.2%}",
                        f"{s.get('terminal_growth', 0):.2%}",
                    ])
                w.writerow([])

                # === GROWTH ===
                w.writerow(["★ GROWTH"])
                w.writerow(["Historical Revenue CAGR", f"{km.get('historical_revenue_cagr', 0):.1%}"])
                w.writerow(["Implied 5-Year Revenue CAGR", f"{km.get('implied_5yr_revenue_cagr', 0):.1%}"])
                w.writerow(["EPS (LTM)", f"${km.get('eps_ltm', 0):.2f}"])

            logger.info(f"DCF summary CSV saved to {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to write DCF summary CSV: {e}", exc_info=True)
            return False

    def _write_forecast_csv(self, dcf_result: Dict, path: Path) -> bool:
        """Write detailed forecast CSV."""
        try:
            historical_fcf = dcf_result.get("historical_fcf", [])
            fcf_forecast = dcf_result.get("fcf_forecast", [])

            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)

                w.writerow([f"DCF FORECAST - {dcf_result.get('ticker', '')}"])
                w.writerow([])

                # Header
                w.writerow([
                    "Period", "Type", "Revenue", "Revenue Growth",
                    "EBIT", "EBITDA", "Operating Margin",
                    "NOPAT", "D&A", "CapEx", "ΔNWC", "FCFF", "FCF Margin"
                ])

                # Historical rows
                for h in reversed(historical_fcf):
                    rev_growth = ""
                    w.writerow([
                        h.get("period_end", ""),
                        "Historical",
                        self._fmt_b(h.get("revenue", 0)),
                        rev_growth,
                        self._fmt_b(h.get("ebit", 0)),
                        self._fmt_b(h.get("ebitda", 0)),
                        f"{h.get('operating_margin', 0):.1%}" if h.get('operating_margin') else "",
                        self._fmt_b(h.get("nopat", 0)),
                        self._fmt_b(h.get("d_a", 0)),
                        self._fmt_b(h.get("capex", 0)),
                        self._fmt_b(h.get("delta_nwc", 0)),
                        self._fmt_b(h.get("fcff", 0)),
                        f"{h.get('fcf_margin', 0):.1%}" if h.get('fcf_margin') else "",
                    ])

                # Forecast rows
                for fc in fcf_forecast:
                    w.writerow([
                        fc.get("period", ""),
                        "Forecast",
                        self._fmt_b(fc.get("revenue", 0)),
                        f"{fc.get('revenue_growth', 0):.1%}",
                        self._fmt_b(fc.get("ebit", 0)),
                        self._fmt_b(fc.get("ebitda", 0)),
                        f"{fc.get('operating_margin', 0):.1%}",
                        self._fmt_b(fc.get("nopat", 0)),
                        self._fmt_b(fc.get("d_a", 0)),
                        self._fmt_b(fc.get("capex", 0)),
                        self._fmt_b(fc.get("delta_nwc", 0)),
                        self._fmt_b(fc.get("fcff", 0)),
                        f"{fc.get('fcf_margin', 0):.1%}",
                    ])

            logger.info(f"DCF forecast CSV saved to {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to write DCF forecast CSV: {e}", exc_info=True)
            return False

    def _write_sensitivity_csv(self, dcf_result: Dict, path: Path) -> bool:
        """Write sensitivity matrix CSV."""
        try:
            sensitivity = dcf_result.get("sensitivity_analysis", {})
            wg = sensitivity.get("wacc_vs_growth", {})

            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)

                w.writerow([f"SENSITIVITY ANALYSIS - {dcf_result.get('ticker', '')}"])
                w.writerow([])
                w.writerow(["WACC vs Terminal Growth Rate → Fair Value per Share"])
                w.writerow([])

                # Header row with growth rates
                growth_values = wg.get("growth_values", [])
                header = ["WACC \\ Growth"] + [f"{g:.2%}" for g in growth_values]
                w.writerow(header)

                # Data rows
                for row in wg.get("matrix", []):
                    wacc_val = row.get("wacc", 0)
                    is_base = abs(wacc_val - wg.get("base_wacc", 0)) < 0.001
                    label = f"{wacc_val:.2%}" + (" ←BASE" if is_base else "")

                    values = []
                    for v in row.get("values", []):
                        fv = v.get("fair_value", 0)
                        is_base_g = abs(v.get("terminal_growth", 0) - wg.get("base_growth", 0)) < 0.001
                        cell = f"${fv:.2f}"
                        if is_base and is_base_g:
                            cell += " ★"
                        values.append(cell)

                    w.writerow([label] + values)

                w.writerow([])
                w.writerow(["★ = Base case"])

                # Scenarios
                scenarios = dcf_result.get("scenarios", {})
                if scenarios:
                    w.writerow([])
                    w.writerow(["SCENARIO ANALYSIS"])
                    w.writerow(["Scenario", "Fair Value", "WACC", "Terminal Growth", "Operating Margin"])
                    for name in ["bull", "base", "bear"]:
                        s = scenarios.get(name, {})
                        w.writerow([
                            name.upper(),
                            f"${s.get('fair_value_per_share', 0):.2f}",
                            f"{s.get('wacc', 0):.2%}",
                            f"{s.get('terminal_growth', 0):.2%}",
                            f"{s.get('operating_margin', 0):.1%}",
                        ])

            logger.info(f"DCF sensitivity CSV saved to {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to write DCF sensitivity CSV: {e}", exc_info=True)
            return False

    # ========================================================================
    # CONSOLE OUTPUT (JPM-STYLE)
    # ========================================================================

    def print_dcf_summary(self, dcf_result: Dict):
        """Print JPM-style DCF summary to console."""
        from src.cli_enhancements import Colors

        if not dcf_result.get("success"):
            print(f"{Colors.FAIL}DCF Failed: {dcf_result.get('error', 'Unknown')}{Colors.ENDC}")
            return

        ticker = dcf_result.get("ticker", "")
        km = dcf_result.get("key_metrics", {})
        wacc = dcf_result.get("wacc", {})
        ev = dcf_result.get("enterprise_value", {})
        eq = dcf_result.get("equity_value", {})
        scenarios = dcf_result.get("scenarios", {})

        print(f"\n{Colors.HEADER}{'=' * 70}{Colors.ENDC}")
        print(f"{Colors.HEADER}  DCF VALUATION: {ticker} - {dcf_result.get('entity_name', '')}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'=' * 70}{Colors.ENDC}\n")

        # Fair Value
        fair_value = km.get("fair_value_per_share", 0)
        print(f"  {Colors.BOLD}★ FAIR VALUE PER SHARE: ${fair_value:.2f}{Colors.ENDC}")
        print(f"    Gordon Growth: ${eq.get('fair_value_gordon', 0):.2f}")
        print(f"    Exit Multiple: ${eq.get('fair_value_exit', 0):.2f}")
        print()

        # Key Metrics
        print(f"  {Colors.BOLD}★ KEY METRICS{Colors.ENDC}")
        print(f"    EV/EBITDA (implied):   {km.get('implied_ev_ebitda', 0):.1f}x")
        print(f"    FCF Yield:             {km.get('fcf_yield', 0):.1%}")
        print(f"    WACC:                  {wacc.get('wacc', 0):.2%}")

        # ROIC vs WACC (value creation)
        spread = km.get("roic_wacc_spread", 0)
        spread_color = Colors.OKGREEN if spread > 0 else Colors.FAIL
        print(f"    ROIC:                  {km.get('roic', 0):.2%}")
        print(f"    ROIC - WACC:           {spread_color}{spread:.2%} "
              f"({km.get('value_creation', '')}){Colors.ENDC}")
        print()

        # Profitability
        print(f"  {Colors.BOLD}★ PROFITABILITY{Colors.ENDC}")
        if km.get("gross_margin"):
            print(f"    Gross Margin:          {km['gross_margin']:.1%}")
        if km.get("operating_margin"):
            print(f"    Operating Margin:      {km['operating_margin']:.1%}")
        if km.get("net_margin"):
            print(f"    Net Margin:            {km['net_margin']:.1%}")
        if km.get("fcf_margin"):
            print(f"    FCF Margin:            {km['fcf_margin']:.1%}")
        print()

        # Terminal Value risk
        tv_pct = km.get("terminal_value_pct_of_ev", 0)
        tv_risk = km.get("terminal_value_risk", "")
        tv_color = Colors.OKGREEN if tv_risk == "LOW" else Colors.WARNING if tv_risk == "MODERATE" else Colors.FAIL
        print(f"  {Colors.BOLD}★ TERMINAL VALUE{Colors.ENDC}")
        print(f"    TV % of Enterprise Value: {tv_color}{tv_pct:.0f}% ({tv_risk} risk){Colors.ENDC}")
        print()

        # Scenarios
        print(f"  {Colors.BOLD}★ SCENARIO ANALYSIS{Colors.ENDC}")
        for name, label_color in [("bull", Colors.OKGREEN), ("base", Colors.OKCYAN), ("bear", Colors.FAIL)]:
            s = scenarios.get(name, {})
            print(f"    {label_color}{name.upper():5s}{Colors.ENDC}: "
                  f"${s.get('fair_value_per_share', 0):>8.2f}  "
                  f"(WACC={s.get('wacc', 0):.2%}, g={s.get('terminal_growth', 0):.2%})")
        print()

        # Growth
        print(f"  {Colors.BOLD}★ GROWTH{Colors.ENDC}")
        print(f"    Historical Revenue CAGR: {km.get('historical_revenue_cagr', 0):.1%}")
        print(f"    Implied 5-Year CAGR:     {km.get('implied_5yr_revenue_cagr', 0):.1%}")

        print(f"\n{Colors.HEADER}{'=' * 70}{Colors.ENDC}\n")

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def _safe_avg(self, values: List) -> Optional[float]:
        """Calculate average, ignoring None values."""
        valid = [v for v in values if v is not None]
        return sum(valid) / len(valid) if valid else None

    def _fmt_b(self, value: float) -> str:
        """Format number in billions/millions for display."""
        if value is None:
            return "N/A"
        if abs(value) >= 1e9:
            return f"${value / 1e9:.2f}B"
        elif abs(value) >= 1e6:
            return f"${value / 1e6:.1f}M"
        elif abs(value) >= 1e3:
            return f"${value / 1e3:.0f}K"
        else:
            return f"${value:.0f}"
