# AGENTS.md

This project builds a top-down global market research system.

## Core Objective

Build a research dashboard that analyzes markets in this order:

1. Global Money Flow
2. Country Market Breadth
3. Sector / Industry Breadth
4. Theme / Correlation Cluster
5. Stock / DR Selection
6. Execution Quality
7. Dashboard and Daily Report

The system must produce research signals only.
It must not produce financial advice or guaranteed buy/sell recommendations.

## Required Principles

- Never invent financial data.
- Never invent tickers, prices, sectors, countries, or DR mappings.
- If data is missing, report it clearly and skip that layer.
- Use adjusted close when available.
- Keep domestic market breadth separate from DR/foreign proxy instruments.
- DRs must never be mixed into Thailand domestic market breadth.
- For DRs, use the underlying instrument for signal and the DR price/liquidity for execution quality.
- All outputs must show the metrics behind the conclusion.

## Project Language

Use Python.

Preferred libraries:
- pandas
- numpy
- scipy
- scikit-learn
- networkx
- plotly
- streamlit
- pyyaml
- pytest

## System Layers

### 1. Global Money Flow

Estimate relative rotation across:
- Equities
- Commodities
- Bonds
- Currencies
- Crypto
- Cash / USD proxy

Use:
- 1D return
- 5D return
- 20D return
- 60D return
- volume z-score
- relative strength versus benchmark

Important:
Price-based flow is only a proxy.
Use labels like:
- flow signal
- rotation signal
- relative strength signal

Do not say money is definitely flowing unless actual fund flow data is provided.

### 2. Country Market Breadth

Support multiple countries and universes:
- Thailand
- United States
- Japan
- China / Hong Kong
- Vietnam
- India
- Europe
- Emerging Markets

Metrics:
- percent within 5% of 52-week high
- percent within 10% of 52-week high
- percent down more than 20% from 52-week high
- percent down more than 30% from 52-week high
- percent above 50-day moving average
- percent above 200-day moving average
- new 52-week highs
- new 52-week lows
- advance / decline ratio if available
- turnover breadth if available

Classify each country:
- Strong Bull
- Bull
- Neutral
- Bear Warning
- Bear

### 3. Thailand Market Breadth

For Thailand, support:
- SET50
- SET100
- SET ex-DR
- mai
- sector-level breadth
- industry-level breadth

Exclude from domestic Thailand breadth:
- DR
- DRx
- DW
- ETF
- warrants
- suspended securities
- illiquid securities

### 4. Sector / Industry Breadth

Aggregate country breadth by sector and industry.

Rank:
- strongest sectors
- weakest sectors
- improving sectors
- deteriorating sectors

### 5. Correlation / Theme Cluster

Cluster stocks by return correlation.

Use:
- daily returns
- rolling correlation
- hierarchical clustering or network clustering
- cluster momentum
- cluster breadth
- redundancy detection

Purpose:
Find groups of stocks that move together, even if they are from different industries.

### 6. Momentum Engine

Calculate:
- 1-month momentum
- 3-month momentum
- 6-month momentum
- 12-month momentum
- volatility-adjusted momentum
- distance from 52-week high
- moving average trend filters

### 7. Redundancy Engine

If two instruments have very high correlation, prefer the better one.

Use:
- higher momentum
- higher liquidity
- tighter spread if available
- lower volatility if needed
- better trend quality

### 8. DR / DRx Engine

DRs are global proxy instruments traded in Thailand.

Rules:
- Do not use DRs to judge Thailand market health.
- Use underlying stock / ETF / index for signal.
- Use DR data for execution quality.

DR quality metrics:
- average traded value 20D
- bid-ask spread if available
- volume consistency
- tracking correlation with underlying adjusted for FX
- premium / discount if fair value data is available

If multiple DRs track the same underlying, rank by execution quality.

### 9. Dashboard

Build a Streamlit dashboard with pages:

1. Global Flow Map
2. Country Market Health
3. Thailand Market Health
4. Sector Breadth
5. Theme / Correlation Cluster
6. Stock Ranking
7. DR Global Proxy
8. Redundancy Report
9. Daily Market Report

### 10. Testing

Add pytest tests for:
- data validation
- return calculation
- 52-week high calculation
- distance from high
- market breadth buckets
- regime classification
- flow score
- sector aggregation
- correlation clustering
- redundancy detection
- DR mapping
- DR quality ranking

## Engineering Rules

- Keep files modular.
- Do not create one huge script.
- Add docstrings to public functions.
- Add type hints where useful.
- Create tests before or alongside core logic.
- Do not edit unrelated files.
- Do not hardcode fake financial data except in tests.
- Use config files for thresholds, tickers, universes, and mappings.

## Definition of Done

The project is done when it can:

1. Load market data from CSV or configured adapters.
2. Calculate global money flow signals.
3. Calculate country market breadth.
4. Calculate Thailand market breadth while excluding DR/DW/ETF/warrants.
5. Calculate sector and industry breadth.
6. Cluster instruments by correlation.
7. Rank instruments by momentum.
8. Detect redundant instruments.
9. Rank DR candidates by execution quality.
10. Display all results in a Streamlit dashboard.
11. Export daily reports as CSV and HTML.
12. Pass all tests.
