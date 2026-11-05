"""
src.models.baselines
====================
Baseline models cho walk-forward (thang so sánh Phase 3).

Mọi model theo interface của src.models.walk_forward:
    fit(X, y, dates) / predict(X, dates) -> np.ndarray
Input X là feature đã cross-sectional rank − 0.5 (src.models.panel.build_panel).
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
import pandas as pd


class SingleFactorModel:
    """Dùng thẳng 1 tín hiệu làm score (vd. reversal_5d — baseline của thầy). Không học gì."""

    def __init__(self, column: str, sign: int = 1):
        self.column = column
        self.sign = 1 if sign >= 0 else -1
        self.input_cols: List[str] = [column]
        self.name = f"factor_{'-' if self.sign < 0 else ''}{column}"

    def fit(self, X: pd.DataFrame, y: pd.Series, dates: pd.Series) -> None:
        pass

    def predict(self, X: pd.DataFrame, dates: pd.Series) -> np.ndarray:
        return self.sign * X[self.column].to_numpy()


class ICSignEqualWeightModel:
    """
    Trung bình cộng các feature, mỗi feature nhân dấu của Mean Rank IC trên TẬP TRAIN của fold.
    Dấu được học lại mỗi fold → không dùng thông tin kỳ val (khác chọn dấu bằng IC toàn kỳ).
    """

    name = "ic_sign_ew"

    def __init__(self):
        self.signs_: Optional[pd.Series] = None

    def fit(self, X: pd.DataFrame, y: pd.Series, dates: pd.Series) -> None:
        from src.models.walk_forward import daily_rank_ic

        d = X.copy()
        d["_y"] = y.to_numpy()
        d["_date"] = dates.to_numpy()
        ic = pd.Series({c: daily_rank_ic(d, c, "_y", "_date").mean() for c in X.columns})
        self.signs_ = np.sign(ic.fillna(0.0))

    def predict(self, X: pd.DataFrame, dates: pd.Series) -> np.ndarray:
        return (X * self.signs_.reindex(X.columns).to_numpy()).mean(axis=1).to_numpy()


class RidgeModel:
    """Ridge regression của target_next_rank (− 0.5) trên các feature — baseline tuyến tính."""

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.name = "ridge"
        self.coef_: Optional[pd.Series] = None

    def fit(self, X: pd.DataFrame, y: pd.Series, dates: pd.Series) -> None:
        from sklearn.linear_model import Ridge

        self._m = Ridge(alpha=self.alpha, fit_intercept=True)
        self._m.fit(X.to_numpy(dtype=np.float32), (y - 0.5).to_numpy(dtype=np.float32))
        self.coef_ = pd.Series(self._m.coef_, index=X.columns)

    def predict(self, X: pd.DataFrame, dates: pd.Series) -> np.ndarray:
        return self._m.predict(X.to_numpy(dtype=np.float32))


def get_model_factory(name: str):
    """Tên (CLI) → factory tạo model mới cho mỗi fold."""
    if name == "ic_sign_ew":
        return ICSignEqualWeightModel
    if name == "ridge":
        return lambda: RidgeModel(alpha=1.0)
    if name.startswith("factor:"):
        col = name.split(":", 1)[1]
        sign = -1 if col.startswith("-") else 1
        col = col.lstrip("-")
        return lambda: SingleFactorModel(col, sign)
    raise ValueError(f"Model không hỗ trợ: {name} (dùng ic_sign_ew | ridge | factor:[-]<cột>)")
