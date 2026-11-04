"""
src.utils.config
================
Configuration loader and path resolver for institutional research pipeline.
Loads configs/base_config.yaml with dynamic root detection and attribute access.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union
import yaml


def get_project_root() -> Path:
    """
    Locates the project root directory by traversing upwards from this file
    until finding 'configs/base_config.yaml' or '.git'.
    """
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "configs" / "base_config.yaml").exists() or (parent / ".git").exists():
            return parent
    # Fallback to 2 levels up from src/utils/
    return Path(__file__).resolve().parent.parent.parent


class ConfigDict(dict):
    """
    Dictionary subclass supporting nested attribute-style dot access:
    e.g. config.data.matrices_dir instead of config['data']['matrices_dir'].
    """
    def __getattr__(self, key: str) -> Any:
        try:
            val = self[key]
            if isinstance(val, dict) and not isinstance(val, ConfigDict):
                val = ConfigDict(val)
                self[key] = val
            return val
        except KeyError:
            raise AttributeError(f"'ConfigDict' object has no attribute '{key}'")

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value

    def __delattr__(self, key: str) -> None:
        try:
            del self[key]
        except KeyError:
            raise AttributeError(f"'ConfigDict' object has no attribute '{key}'")


class Config:
    """
    Master configuration wrapper with typed property accessors and
    path resolution relative to project root.
    """
    def __init__(self, raw_config: Dict[str, Any], config_path: Path):
        self._raw = raw_config
        self._path = config_path
        self._root = get_project_root()
        self._dict = ConfigDict(raw_config)

    @property
    def raw(self) -> Dict[str, Any]:
        return self._raw

    @property
    def universe(self) -> ConfigDict:
        return self._dict.universe

    @property
    def data(self) -> ConfigDict:
        return self._dict.data

    @property
    def portfolio(self) -> ConfigDict:
        return self._dict.portfolio

    @property
    def backtest(self) -> ConfigDict:
        return self._dict.backtest

    @property
    def metrics(self) -> ConfigDict:
        return self._dict.metrics

    @property
    def project_root(self) -> Path:
        return self._root

    def resolve_path(self, relative_path: Union[str, Path]) -> Path:
        """Resolves a relative path against the project root."""
        p = Path(relative_path)
        if p.is_absolute():
            return p
        return (self._root / p).resolve()

    # Convenience Path Accessors
    def get_matrices_dir(self) -> Path:
        return self.resolve_path(self.data.matrices_dir)

    def get_raw_warehouse_path(self) -> Path:
        return self.resolve_path(self.data.raw_warehouse)

    def get_canonical_warehouse_path(self) -> Path:
        return self.resolve_path(self.data.canonical_warehouse)

    def get_adjusted_warehouse_path(self) -> Path:
        return self.resolve_path(self.data.adjusted_warehouse)

    def get_corporate_actions_dir(self) -> Path:
        return self.resolve_path(self.data.corporate_actions_dir)

    def get_pit_by_year_json_path(self) -> Path:
        return self.resolve_path(self.universe.pit_by_year_json)

    def get_constituents_csv_path(self) -> Path:
        return self.resolve_path(self.universe.constituents_csv)

    # Convenience Date Accessors
    @property
    def start_date(self) -> str:
        return str(self.data.start_date)

    @property
    def warmup_end_date(self) -> str:
        return str(self.data.warmup_end_date)

    @property
    def dev_start_date(self) -> str:
        return str(self.data.dev_start_date)

    @property
    def dev_end_date(self) -> str:
        return str(self.data.dev_end_date)

    @property
    def oos_start_date(self) -> str:
        return str(self.data.oos_start_date)

    @property
    def oos_end_date(self) -> str:
        return str(self.data.oos_end_date)

    @property
    def oos_strictly_frozen(self) -> bool:
        return bool(self.data.oos_strictly_frozen)

    def __getitem__(self, item: str) -> Any:
        return self._dict[item]

    def __repr__(self) -> str:
        return f"<Config loaded from {self._path}>"


def load_config(config_path: Optional[Union[str, Path]] = None) -> Config:
    """
    Loads configuration from base_config.yaml (or specified path).
    """
    root = get_project_root()
    if config_path is None:
        target_path = root / "configs" / "base_config.yaml"
    else:
        target_path = Path(config_path)
        if not target_path.is_absolute():
            target_path = (root / target_path).resolve()

    if not target_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {target_path}")

    with open(target_path, "r", encoding="utf-8") as f:
        raw_config = yaml.safe_load(f)

    return Config(raw_config, target_path)
