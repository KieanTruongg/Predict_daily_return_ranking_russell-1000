"""
Module Backtest Danh Mục Định Lượng (Quant Portfolio Backtest Module)
====================================================================
Cung cấp engine mô phỏng thực thi danh mục Long-Only Top K Open-to-Close
tuân thủ nghiêm ngặt tính khả thi thực tế, tự cân đối ngân sách và quản lý vị thế kẹt.
"""

from src.backtest.simulator import PortfolioSimulator, Position, TradeRecord, DailyLedgerRecord

__all__ = [
    "PortfolioSimulator",
    "Position",
    "TradeRecord",
    "DailyLedgerRecord",
]
