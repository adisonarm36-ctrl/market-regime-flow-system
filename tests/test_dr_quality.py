import pandas as pd

from src.dr_quality import build_dr_quality_table, calculate_average_traded_value, rank_dr_candidates


def test_average_traded_value_and_dr_quality_ranking():
    dates = pd.date_range("2026-01-01", periods=30)
    dr_price = pd.DataFrame({"AAA80": [10] * 30, "AAA81": [10] * 30}, index=dates, dtype=float)
    dr_volume = pd.DataFrame({"AAA80": [100] * 30, "AAA81": [300] * 30}, index=dates, dtype=float)
    underlying = pd.DataFrame({"AAA": [100 + i for i in range(30)]}, index=dates, dtype=float)
    mapping = pd.DataFrame({"DR_Ticker": ["AAA80", "AAA81"], "Underlying_Ticker": ["AAA", "AAA"]})

    avg_value = calculate_average_traded_value(dr_price, dr_volume)
    quality = build_dr_quality_table(dr_price, dr_volume, mapping, underlying_price_df=underlying)
    ranked = rank_dr_candidates(quality)

    assert avg_value["AAA81"] > avg_value["AAA80"]
    assert ranked.loc[0, "Underlying_Ticker"] == "AAA"
    assert ranked.loc[0, "execution_rank"] == 1
    assert "missing_bid_ask_spread" in ranked.loc[0, "data_quality_warning"]
