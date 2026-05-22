# Sample Data

These files are fake/demo data for smoke testing only.

They are not real tickers, prices, sectors, countries, DR mappings, or financial data.
Do not use them for research conclusions.

Files:

- `prices_sample.csv`: fake OHLCV data with adjusted close.
- `metadata_sample.csv`: fake metadata with stocks, one DR, one ETF, and one DW-style excluded instrument.
- `asset_map_sample.csv`: fake asset-class mapping for flow aggregation.
- `dr_mapping_sample.csv`: fake CSV DR mapping for dashboard upload.
- `dr_mapping_sample.yaml`: fake YAML DR mapping for tests/scripts.

The sample is intentionally small and designed only to verify that the pipeline, dashboard, and report generator run without live APIs.
