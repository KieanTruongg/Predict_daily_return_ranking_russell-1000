"""In-sample and Out-of-sample data splitting with leakage prevention guard."""
import os
import pandas as pd
from typing import Tuple
from src.data.preprocessor import CrossSectionalDataContainer

SPLIT_CUTOFF_DATE = "2024-01-01"


def split_and_persist_data(
    container: CrossSectionalDataContainer,
    cutoff_date: str = SPLIT_CUTOFF_DATE,
    in_sample_dir: str = os.path.join("data", "processed", "in_sample"),
    out_sample_dir: str = os.path.join("data", "processed", "out_sample")
) -> Tuple[CrossSectionalDataContainer, CrossSectionalDataContainer]:
    """
    Partitions the full dataset into:
    - In-sample: Data strictly BEFORE cutoff_date (e.g. < 2024-01-01)
    - Out-of-sample: Data from cutoff_date ONWARDS (>= 2024-01-01, locked for final evaluation)
    """
    ts_cutoff = pd.to_datetime(cutoff_date)

    def _split_df(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        ins = df[df.index < ts_cutoff]
        oos = df[df.index >= ts_cutoff]
        return ins, oos

    ins_open, oos_open = _split_df(container.open)
    ins_high, oos_high = _split_df(container.high)
    ins_low, oos_low = _split_df(container.low)
    ins_close, oos_close = _split_df(container.close)
    ins_adj_close, oos_adj_close = _split_df(container.adj_close)
    ins_volume, oos_volume = _split_df(container.volume)
    ins_returns, oos_returns = _split_df(container.returns)
    ins_fwd_ret, oos_fwd_ret = _split_df(container.forward_returns)

    in_sample_container = CrossSectionalDataContainer(
        open_=ins_open,
        high=ins_high,
        low=ins_low,
        close=ins_close,
        adj_close=ins_adj_close,
        volume=ins_volume,
        returns=ins_returns,
        forward_returns=ins_fwd_ret
    )

    out_sample_container = CrossSectionalDataContainer(
        open_=oos_open,
        high=oos_high,
        low=oos_low,
        close=oos_close,
        adj_close=oos_adj_close,
        volume=oos_volume,
        returns=oos_returns,
        forward_returns=oos_fwd_ret
    )

    # Save to disk
    in_sample_container.save(in_sample_dir)
    out_sample_container.save(out_sample_dir)

    print(f"Data partitioning complete:")
    print(f"  [IN-SAMPLE]  {len(in_sample_container.get_dates())} trading days ({in_sample_container.get_dates()[0].strftime('%Y-%m-%d')} to {in_sample_container.get_dates()[-1].strftime('%Y-%m-%d')}) -> Saved to {in_sample_dir}")
    print(f"  [OUT-SAMPLE] {len(out_sample_container.get_dates())} trading days ({out_sample_container.get_dates()[0].strftime('%Y-%m-%d')} to {out_sample_container.get_dates()[-1].strftime('%Y-%m-%d')}) -> Saved to {out_sample_dir} [LOCKED]")

    return in_sample_container, out_sample_container


def load_in_sample_data(in_sample_dir: str = os.path.join("data", "processed", "in_sample")) -> CrossSectionalDataContainer:
    """
    Standard function to load only in-sample data during research and alpha development.
    Prevents accidental lookahead into out-of-sample data.
    """
    if not os.path.exists(os.path.join(in_sample_dir, "close.parquet")):
        raise FileNotFoundError(f"In-sample data not found in {in_sample_dir}. Please run download and preprocessing scripts first.")
    return CrossSectionalDataContainer.load(in_sample_dir)
