import pandas as pd

from src.stock_selection import build_research_candidates


def test_build_research_candidates_with_reasons_filters_and_warnings():
    metadata = pd.DataFrame(
        {
            "Ticker": ["AAA", "BBB", "DR1"],
            "Country": ["Thailand", "Thailand", "Thailand"],
            "Sector": ["Tech", "Tech", "Tech"],
            "SecurityType": ["Stock", "Stock", "DR"],
            "liquidity": [100, 20, 100],
        }
    )
    momentum = pd.DataFrame(
        {
            "Ticker": ["AAA", "BBB", "DR1"],
            "momentum_score": [90, 70, 80],
            "above_200ma": [True, False, True],
        }
    )
    country = pd.DataFrame({"country": ["Thailand"], "breadth_score": [70], "regime": ["Bull"]})
    sector = pd.DataFrame({"Sector": ["Tech"], "breadth_score": [75]})
    redundancy = pd.DataFrame({"redundant_ticker": ["BBB"]})
    dr_quality = pd.DataFrame({"DR_Ticker": ["DR1"], "dr_quality_score": [85], "data_quality_warning": ["missing_spread"]})

    result = build_research_candidates(metadata, momentum, country, sector, redundancy_report_df=redundancy, dr_quality_df=dr_quality, min_liquidity=50)

    assert result.iloc[0]["Ticker"] in {"AAA", "DR1"}
    assert "research signal only" in set(result["signal_type"])
    assert "liquidity" in result.loc[result["Ticker"].eq("BBB"), "failed_filters"].iloc[0]
    assert "redundancy" in result.loc[result["Ticker"].eq("BBB"), "failed_filters"].iloc[0]
    assert "missing_spread" in result.loc[result["Ticker"].eq("DR1"), "data_quality_warning"].iloc[0]
