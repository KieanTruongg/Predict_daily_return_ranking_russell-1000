"""Unit tests for alpha operators (WorldQuant IQC style)."""
import numpy as np
import pandas as pd
from src.alphas.operators import delta, delay, ts_mean, cs_rank, cs_demean


def test_delta_and_delay():
    df = pd.DataFrame({
        "A": [10.0, 12.0, 15.0, 14.0],
        "B": [20.0, 19.0, 18.0, 22.0]
    })
    d1 = delta(df, 1)
    assert d1.iloc[1]["A"] == 2.0
    assert d1.iloc[2]["B"] == -1.0

    del1 = delay(df, 1)
    assert pd.isna(del1.iloc[0]["A"])
    assert del1.iloc[1]["A"] == 10.0


def test_cross_sectional_rank_and_demean():
    df = pd.DataFrame({
        "A": [1.0, 10.0],
        "B": [2.0, 20.0],
        "C": [3.0, 30.0]
    })
    ranked = cs_rank(df)
    assert ranked.iloc[0]["A"] < ranked.iloc[0]["B"] < ranked.iloc[0]["C"]

    demeaned = cs_demean(df)
    assert np.allclose(demeaned.sum(axis=1), 0.0)
