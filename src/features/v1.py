"""
src.features.v1
===============
16 features ứng viên v1 theo docs/specifications/features_v1.md.

Mọi feature kế thừa FeatureBase:
  - input được làm sạch bằng bar_quality_mask (độc lập membership, giữ warm-up trước ngày vào rổ);
  - output tại T ngoài membership → NaN.
Quy tắc chung trong từng công thức:
  - Cửa sổ phải ĐỦ dữ liệu sạch, hữu hạn, dương (đúng miền) trên lịch giao dịch chung:
    thiếu một phiên ở giữa → NaN (không nối qua gap, không fill 0).
  - Return dùng adj_close (điều chỉnh split, chưa gồm cổ tức): r[T] = P[T] / P[T-1] − 1,
    cần cả P[T] và P[T-1] sạch → T và T-1 là hai phiên liên tiếp.
  - Không annualize volatility (đơn vị ngày).

`window` của từng class mặc định đúng spec; chỉ đổi khi viết test.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from src.features.base import FeatureBase


def _pos(df: pd.DataFrame) -> pd.DataFrame:
    """Giữ giá trị hữu hạn > 0, còn lại NaN."""
    return df.where(np.isfinite(df) & (df > 0))


def _full(valid: pd.DataFrame, window: int) -> pd.DataFrame:
    """True khi `window` ô liên tiếp kết thúc tại T đều hợp lệ."""
    return valid.astype(np.float32).rolling(window, min_periods=window).sum() == window


def _ret1(price: pd.DataFrame) -> pd.DataFrame:
    """Simple return 1 phiên; NaN nếu P[T] hoặc P[T-1] không hợp lệ."""
    return price / price.shift(1) - 1.0


def _dollar_volume(close: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    """DV = raw_close × raw_volume (USD); volume = 0 hoặc thiếu → NaN."""
    return _pos(close) * _pos(volume)


class FeatureV1(FeatureBase):
    """FeatureBase + danh sách ma trận input cần nạp."""

    inputs: Tuple[str, ...] = ("adj_close",)


# ---------------------------------------------------------------------------
# 3. Momentum
# ---------------------------------------------------------------------------

class PriceReturn(FeatureV1):
    """ret_Wd = P[T] / P[T-W] − 1, cần đủ W+1 giá sạch liên tiếp."""

    def __init__(self, window: int):
        super().__init__(f"ret_{window}d", "momentum", window, f"{window}-day split-adjusted price return")

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        p = _pos(data["adj_close"])
        return (p / p.shift(self.window) - 1.0).where(_full(p.notna(), self.window + 1))


class MomentumSkipMonth(FeatureV1):
    """mom_12m_skip_1m = P[T-21] / P[T-252] − 1, cần đủ giá sạch trên đoạn T-252 … T-21."""

    def __init__(self, lookback: int = 252, skip: int = 21):
        super().__init__("mom_12m_skip_1m", "momentum", lookback, "12-month momentum skipping last month")
        self.lookback, self.skip = lookback, skip

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        p = _pos(data["adj_close"])
        ps = p.shift(self.skip)
        span = self.lookback - self.skip + 1
        return (ps / p.shift(self.lookback) - 1.0).where(_full(ps.notna(), span))


# ---------------------------------------------------------------------------
# 4. Volatility
# ---------------------------------------------------------------------------

class RealizedVol(FeatureV1):
    """vol_realized_Wd = std(ddof=1) của W return sạch gần nhất (đơn vị ngày)."""

    def __init__(self, window: int):
        super().__init__(f"vol_realized_{window}d", "volatility", window, f"{window}-day daily return std")

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        r = _ret1(_pos(data["adj_close"]))
        return r.rolling(self.window, min_periods=self.window).std(ddof=1)


class ParkinsonVol(FeatureV1):
    """vol_parkinson_20d = sqrt(mean_20(ln(H/L)^2) / (4 ln 2)); cần high ≥ low > 0 mỗi phiên."""

    inputs = ("adj_high", "adj_low")

    def __init__(self, window: int = 20):
        super().__init__(f"vol_parkinson_{window}d", "volatility", window, "Parkinson high-low volatility")

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        h, l = _pos(data["adj_high"]), _pos(data["adj_low"])
        x = (np.log(h / l) ** 2).where(h >= l)
        m = x.rolling(self.window, min_periods=self.window).mean()
        return np.sqrt(m / (4.0 * np.log(2.0)))


class DownsideDeviation(FeatureV1):
    """downside_deviation_20d = sqrt(sum_20(min(r, 0)^2) / 20); ngưỡng 0, không trừ trung bình."""

    def __init__(self, window: int = 20):
        super().__init__(f"downside_deviation_{window}d", "volatility", window, "lower partial moment (order 2)")

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        r = _ret1(_pos(data["adj_close"]))
        d2 = r.clip(upper=0.0) ** 2
        return np.sqrt(d2.rolling(self.window, min_periods=self.window).sum() / self.window)


# ---------------------------------------------------------------------------
# 5. Liquidity / volume
# ---------------------------------------------------------------------------

class AmihudIlliquidity(FeatureV1):
    """amihud_illiq_20d = 1e6 × mean_20(|r| / DV); tỷ số từng phiên rồi mới lấy trung bình."""

    inputs = ("adj_close", "close", "volume")

    def __init__(self, window: int = 20):
        super().__init__(f"amihud_illiq_{window}d", "liquidity", window, "Amihud illiquidity (x1e6)")

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        r = _ret1(_pos(data["adj_close"]))
        ratio = r.abs() / _dollar_volume(data["close"], data["volume"])
        return 1e6 * ratio.rolling(self.window, min_periods=self.window).mean()


class VolumeRatio(FeatureV1):
    """volume_ratio_5_20 = mean_5(adj_volume) / mean_20(adj_volume); cần 20 volume sạch > 0."""

    inputs = ("adj_volume",)

    def __init__(self, short: int = 5, long: int = 20):
        super().__init__(f"volume_ratio_{short}_{long}", "liquidity", long, "short/long adjusted volume ratio")
        self.short, self.long = short, long

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        v = _pos(data["adj_volume"])
        long_mean = v.rolling(self.long, min_periods=self.long).mean()
        return v.rolling(self.short, min_periods=self.short).mean() / long_mean


class LogDollarVolume(FeatureV1):
    """log_dollar_volume_20d = log1p(mean_20(DV)), DV tính bằng USD."""

    inputs = ("close", "volume")

    def __init__(self, window: int = 20):
        super().__init__(f"log_dollar_volume_{window}d", "liquidity", window, "log1p of mean dollar volume")

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        dv = _dollar_volume(data["close"], data["volume"])
        return np.log1p(dv.rolling(self.window, min_periods=self.window).mean())


# ---------------------------------------------------------------------------
# 6. Intraday / technical
# ---------------------------------------------------------------------------

class IntradayReturn(FeatureV1):
    """ret_intraday = adj_close[T] / adj_open[T] − 1."""

    inputs = ("adj_open", "adj_close")

    def __init__(self):
        super().__init__("ret_intraday", "intraday", 1, "open-to-close return")

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        return _pos(data["adj_close"]) / _pos(data["adj_open"]) - 1.0


class OvernightReturn(FeatureV1):
    """ret_overnight = adj_open[T] / adj_close[T-1] − 1 (hai phiên liên tiếp trên lịch chung)."""

    inputs = ("adj_open", "adj_close")

    def __init__(self):
        super().__init__("ret_overnight", "intraday", 2, "previous close to open return")

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        return _pos(data["adj_open"]) / _pos(data["adj_close"]).shift(1) - 1.0


class WilderRSI(FeatureV1):
    """
    rsi_14d với Wilder smoothing.
    Seed: trung bình 14 delta sạch liên tiếp đầu tiên; sau đó Avg = (13·Avg + x) / 14.
    Delta không hợp lệ (thiếu/lỗi P[T] hoặc P[T-1]) → reset, chờ đủ 14 delta sạch mới seed lại.
    AvgLoss = 0 & AvgGain > 0 → 100; AvgGain = 0 & AvgLoss > 0 → 0; cả hai = 0 → 50.
    """

    def __init__(self, window: int = 14):
        super().__init__(f"rsi_{window}d", "technical", window, "Wilder RSI")

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        p = _pos(data["adj_close"]).to_numpy(dtype=np.float64)
        n_t, n_c = p.shape
        w = self.window
        out = np.full((n_t, n_c), np.nan)
        run = np.zeros(n_c, dtype=np.int64)
        sum_g = np.zeros(n_c)
        sum_l = np.zeros(n_c)
        avg_g = np.full(n_c, np.nan)
        avg_l = np.full(n_c, np.nan)
        for t in range(1, n_t):
            delta = p[t] - p[t - 1]
            ok = np.isfinite(delta)
            g = np.where(ok, np.maximum(delta, 0.0), 0.0)
            l = np.where(ok, np.maximum(-delta, 0.0), 0.0)

            run = np.where(ok, run + 1, 0)
            seeding = ok & (run <= w)
            sum_g = np.where(seeding, sum_g + g, np.where(ok, sum_g, 0.0))
            sum_l = np.where(seeding, sum_l + l, np.where(ok, sum_l, 0.0))

            seed_now = ok & (run == w)
            smooth = ok & (run > w)
            avg_g = np.where(seed_now, sum_g / w, np.where(smooth, ((w - 1) * avg_g + g) / w, avg_g))
            avg_l = np.where(seed_now, sum_l / w, np.where(smooth, ((w - 1) * avg_l + l) / w, avg_l))
            avg_g = np.where(ok, avg_g, np.nan)
            avg_l = np.where(ok, avg_l, np.nan)

            live = ok & (run >= w)
            with np.errstate(divide="ignore", invalid="ignore"):
                rsi = 100.0 - 100.0 / (1.0 + avg_g / avg_l)
            rsi = np.where((avg_l == 0) & (avg_g > 0), 100.0, rsi)
            rsi = np.where((avg_g == 0) & (avg_l > 0), 0.0, rsi)
            rsi = np.where((avg_g == 0) & (avg_l == 0), 50.0, rsi)
            out[t] = np.where(live, rsi, np.nan)
        ref = data["adj_close"]
        return pd.DataFrame(out, index=ref.index, columns=ref.columns)


class BollingerPctB(FeatureV1):
    """bollinger_pct_b_20d = (P − lower) / (upper − lower), std trên mức giá với ddof=0; dải = 0 → NaN."""

    def __init__(self, window: int = 20, k: float = 2.0):
        super().__init__(f"bollinger_pct_b_{window}d", "technical", window, "Bollinger %B")
        self.k = k

    def _calculate(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        p = _pos(data["adj_close"])
        roll = p.rolling(self.window, min_periods=self.window)
        mid, sd = roll.mean(), roll.std(ddof=0)
        width = 2.0 * self.k * sd
        width = width.where(width > 1e-10 * mid)      # dải bằng 0 (sai số làm tròn) → NaN
        return (p - (mid - self.k * sd)) / width


def features_v1() -> List[FeatureV1]:
    """16 feature theo đúng thứ tự trong features_v1.md."""
    return [
        PriceReturn(1), PriceReturn(5), PriceReturn(20), PriceReturn(60), MomentumSkipMonth(),
        RealizedVol(20), RealizedVol(60), ParkinsonVol(), DownsideDeviation(),
        AmihudIlliquidity(), VolumeRatio(), LogDollarVolume(),
        IntradayReturn(), OvernightReturn(), WilderRSI(), BollingerPctB(),
    ]
