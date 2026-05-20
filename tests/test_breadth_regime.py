import pandas as pd

from src.breadth_regime import add_regime, classify_regime


def test_classify_regime_thresholds():
    assert classify_regime(80) == "Strong Bull"
    assert classify_regime(65) == "Bull"
    assert classify_regime(50) == "Neutral"
    assert classify_regime(35) == "Bear Warning"
    assert classify_regime(20) == "Bear"


def test_add_regime():
    df = pd.DataFrame({"breadth_score": [80, 20]})

    result = add_regime(df)

    assert result["regime"].tolist() == ["Strong Bull", "Bear"]
