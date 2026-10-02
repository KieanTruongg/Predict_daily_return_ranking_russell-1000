"""In-sample and Out-of-sample data splitting with leakage prevention guard.

Default split: everything before 2024-01-01 is IN-SAMPLE,
               everything from 2024-01-01 onwards is OUT-OF-SAMPLE (locked).
"""
import os
import pandas as pd
from typing import Tuple
from src.data.preprocessor import CrossSectionalDataContainer

SPLIT_CUTOFF_DATE = "2024-01-01"


def split_container(
    container: CrossSectionalDataContainer,
    cutoff_date: str = SPLIT_CUTOFF_DATE,
) -> Tuple[CrossSectionalDataContainer, CrossSectionalDataContainer]:
    """
    Partitions a CrossSectionalDataContainer into in-sample and out-of-sample.

    Parameters
    ----------
    container : CrossSectionalDataContainer
        The full dataset container.
    cutoff_date : str
        Date string (YYYY-MM-DD). Data < cutoff is in-sample, >= cutoff is out-of-sample.

    Returns
    -------
    Tuple[CrossSectionalDataContainer, CrossSectionalDataContainer]
        (in_sample, out_sample) containers.
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

    in_sample = CrossSectionalDataContainer(
        open_=ins_open,
        high=ins_high,
        low=ins_low,
        close=ins_close,
        adj_close=ins_adj_close,
        volume=ins_volume,
        returns=ins_returns,
        forward_returns=ins_fwd_ret,
    )

    out_sample = CrossSectionalDataContainer(
        open_=oos_open,
        high=oos_high,
        low=oos_low,
        close=oos_close,
        adj_close=oos_adj_close,
        volume=oos_volume,
        returns=oos_returns,
        forward_returns=oos_fwd_ret,
    )

    return in_sample, out_sample


def split_and_persist_data(
    container: CrossSectionalDataContainer,
    cutoff_date: str = SPLIT_CUTOFF_DATE,
    in_sample_dir: str = os.path.join("data", "processed", "in_sample"),
    out_sample_dir: str = os.path.join("data", "processed", "out_sample"),
) -> Tuple[CrossSectionalDataContainer, CrossSectionalDataContainer]:
    """
    Partitions the full dataset into in-sample and out-of-sample, then saves to disk.

    Parameters
    ----------
    container : CrossSectionalDataContainer
        The full dataset container.
    cutoff_date : str
        Split boundary date.
    in_sample_dir : str
        Directory to save in-sample matrices.
    out_sample_dir : str
        Directory to save out-of-sample matrices.

    Returns
    -------
    Tuple[CrossSectionalDataContainer, CrossSectionalDataContainer]
        (in_sample, out_sample) containers.
    """
    in_sample, out_sample = split_container(container, cutoff_date)

    # Save to disk
    in_sample.save(in_sample_dir)
    out_sample.save(out_sample_dir)

    ins_dates = in_sample.get_dates()
    oos_dates = out_sample.get_dates()

    print(f"Data partitioning complete (cutoff: {cutoff_date}):")
    print(f"  [IN-SAMPLE]  {in_sample.get_n_dates():,} trading days "
          f"({ins_dates[0].strftime('%Y-%m-%d')} → {ins_dates[-1].strftime('%Y-%m-%d')}) "
          f"| {in_sample.get_n_tickers():,} tickers "
          f"→ Saved to {in_sample_dir}")
    print(f"  [OUT-SAMPLE] {out_sample.get_n_dates():,} trading days "
          f"({oos_dates[0].strftime('%Y-%m-%d')} → {oos_dates[-1].strftime('%Y-%m-%d')}) "
          f"| {out_sample.get_n_tickers():,} tickers "
          f"→ Saved to {out_sample_dir} [LOCKED]")

    return in_sample, out_sample


def load_in_sample_data(
    in_sample_dir: str = os.path.join("data", "processed", "in_sample"),
) -> CrossSectionalDataContainer:
    """
    Standard function to load only in-sample data during research and alpha development.
    Prevents accidental lookahead into out-of-sample data.
    """
    if not os.path.exists(os.path.join(in_sample_dir, "close.parquet")):
        raise FileNotFoundError(
            f"In-sample data not found in {in_sample_dir}. "
            "Please run 'scripts/01_pipeline/05_build_cross_sectional.py' first."
        )
    return CrossSectionalDataContainer.load(in_sample_dir)


def load_out_sample_data(
    out_sample_dir: str = os.path.join("data", "processed", "out_sample"),
) -> CrossSectionalDataContainer:
    """
    Load out-of-sample data. Use ONLY for final evaluation.

    ⚠️ WARNING: Do NOT use this during model development or feature engineering!
    """
    if not os.path.exists(os.path.join(out_sample_dir, "close.parquet")):
        raise FileNotFoundError(
            f"Out-of-sample data not found in {out_sample_dir}. "
            "Please run 'scripts/01_pipeline/05_build_cross_sectional.py' first."
        )
    return CrossSectionalDataContainer.load(out_sample_dir)
