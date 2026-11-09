"""
Module Portfolio Simulator (Backtest Engine v1)
==============================================
Triển khai động cơ mô phỏng kiểm thử danh mục đầu tư định lượng:
- Chiến lược Long-Only Top K (mặc định Top 20, mỗi mã 5% NAV).
- Chọn mã sau Close T, vào tại Open T+1, thoát tại Close T+1.
- Tự cân đối ngân sách: Phí mua được tính trực tiếp trong ngân sách từng mã (self-financing).
- Bỏ khối lượng cả ngày khỏi quyết định khớp Open; chỉ kiểm tra khối lượng khi thoát ở Close.
- Lệnh mua thiếu giá Open: giữ nguyên tiền mặt, tuyệt đối không chọn mã thay thế.
- Vị thế không thoát được ở Close: theo dõi sổ lệnh đa phiên, Mark-to-Market, ưu tiên thanh lý ở phiên tiếp theo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd


@dataclass
class TradeRecord:
    """Bản ghi chi tiết một lệnh giao dịch trong sổ lệnh (Order / Trade Execution Log)."""
    date: str
    canonical_sid: str
    action: str           # 'BUY', 'SELL', 'CANCELLED_BUY', 'HELD_OVERNIGHT'
    timing: str           # 'OPEN', 'CLOSE', 'OVERNIGHT'
    price_raw: float
    price_exec: float
    shares: float
    notional: float
    fee: float
    slippage_cost: float
    cash_impact: float    # Âm khi chi tiền mua, Dương khi thu tiền bán
    note: str = ""


@dataclass
class Position:
    """Trạng thái một vị thế nắm giữ trong danh mục."""
    canonical_sid: str
    shares: float
    entry_date: str
    entry_price_raw: float
    entry_price_exec: float
    entry_fee: float
    entry_cash_outlay: float
    last_price: float     # Giá thị trường gần nhất dùng cho Mark-to-Market


@dataclass
class DailyLedgerRecord:
    """Bản ghi sổ cái hạch toán danh mục theo từng ngày giao dịch."""
    date: str
    cash_start: float
    cash_end: float
    invested_value: float
    nav: float
    daily_return: float
    n_positions_open: int
    n_carried_forward: int
    n_buys_filled: int
    n_buys_unfilled: int
    n_sells_filled: int
    total_fees_paid: float


class PortfolioSimulator:
    """
    Động cơ mô phỏng danh mục định lượng chuẩn mực học thuật:
    - Long-Only Top K (mặc định K=20, trọng số đều 5% NAV).
    - Hạch toán phí và trượt giá từng chiều.
    - Quản lý trạng thái sổ lệnh và vị thế kẹt thanh khoản.
    """

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        top_k: int = 20,
        fee_rate_buy: float = 0.0005,       # 5 bps
        slippage_rate_buy: float = 0.0005,  # 5 bps
        fee_rate_sell: float = 0.0005,      # 5 bps
        slippage_rate_sell: float = 0.0005, # 5 bps
    ) -> None:
        self.initial_capital = float(initial_capital)
        self.top_k = int(top_k)
        self.target_weight = 1.0 / self.top_k
        self.fee_rate_buy = float(fee_rate_buy)
        self.slippage_rate_buy = float(slippage_rate_buy)
        self.fee_rate_sell = float(fee_rate_sell)
        self.slippage_rate_sell = float(slippage_rate_sell)

        # Trạng thái danh mục
        self.cash: float = self.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trade_logs: List[TradeRecord] = []
        self.daily_ledger: List[DailyLedgerRecord] = []

    def reset(self) -> None:
        """Đặt lại trạng thái danh mục về ban đầu."""
        self.cash = self.initial_capital
        self.positions.clear()
        self.trade_logs.clear()
        self.daily_ledger.clear()

    def simulate(
        self,
        sessions: List[str],
        predictions_by_date: Dict[str, List[Tuple[str, float]]],
        open_prices: Dict[Tuple[str, str], float],
        close_prices: Dict[Tuple[str, str], float],
        bad_data_flags: Optional[Dict[Tuple[str, str], bool]] = None,
        volume_data: Optional[Dict[Tuple[str, str], float]] = None,
        split_factors: Optional[Dict[Tuple[str, str], float]] = None,
        dividend_data: Optional[Dict[Tuple[str, str], float]] = None,
        halt_flags: Optional[Dict[Tuple[str, str], bool]] = None,
    ) -> pd.DataFrame:
        """
        Thực thi mô phỏng qua chuỗi các phiên giao dịch.

        Parameters
        ----------
        sessions : List[str]
            Danh sách ngày giao dịch đã sắp xếp theo thứ tự thời gian [T_0, T_1, T_2, ...].
            Dự đoán sinh tại Close T_0 sẽ được khớp lệnh tại T_1.
        predictions_by_date : Dict[str, List[Tuple[str, float]]]
            Dict ánh xạ ngày T -> danh sách (canonical_sid, score) đã xếp hạng giảm dần.
        open_prices : Dict[Tuple[str, str], float]
            (date, sid) -> raw open price.
        close_prices : Dict[Tuple[str, str], float]
            (date, sid) -> raw close price.
        bad_data_flags : Optional[Dict[Tuple[str, str], bool]]
            (date, sid) -> True nếu phiên đó bị lỗi dữ liệu / full-bar quarantine.
        volume_data : Optional[Dict[Tuple[str, str], float]]
            (date, sid) -> full-day volume (chỉ dùng ở Close).
        split_factors : Optional[Dict[Tuple[str, str], float]]
            (date, sid) -> hệ số chia tách hiệu lực vào ngày giao dịch (S = cf_{t-1} / cf_t).
        dividend_data : Optional[Dict[Tuple[str, str], float]]
            (date, sid) -> cổ tức tiền mặt trên mỗi cổ phần (D).
        halt_flags : Optional[Dict[Tuple[str, str], bool]]
            (date, sid) -> True nếu có bằng chứng ngừng giao dịch / suspension thực tế.
        """
        self.reset()
        if bad_data_flags is None:
            bad_data_flags = {}
        if volume_data is None:
            volume_data = {}
        if split_factors is None:
            split_factors = {}
        if dividend_data is None:
            dividend_data = {}
        if halt_flags is None:
            halt_flags = {}

        n_sessions = len(sessions)
        if n_sessions < 2:
            return pd.DataFrame()

        current_nav = self.initial_capital

        # Duyệt qua các phiên thực thi T_1, T_2, ...
        for t_idx in range(1, n_sessions):
            prev_date = sessions[t_idx - 1]
            curr_date = sessions[t_idx]

            cash_start_of_day = self.cash
            nav_prev = current_nav
            n_buys_filled = 0
            n_buys_unfilled = 0
            n_sells_filled = 0
            fees_paid_today = 0.0

            # -------------------------------------------------------------
            # BƯỚC 0: Điều chỉnh Corporate Actions cho vị thế giữ qua đêm
            # -------------------------------------------------------------
            carried_sids = list(self.positions.keys())
            for sid in carried_sids:
                pos = self.positions[sid]
                # 0.1. Stock Split / Reverse Split Adjustment
                s_factor = split_factors.get((curr_date, sid), 1.0)
                if pd.notna(s_factor) and s_factor > 0 and abs(s_factor - 1.0) > 1e-5:
                    old_shares = pos.shares
                    pos.shares = float(pos.shares * s_factor)
                    pos.last_price = float(pos.last_price / s_factor)
                    pos.entry_price_raw = float(pos.entry_price_raw / s_factor)
                    pos.entry_price_exec = float(pos.entry_price_exec / s_factor)
                    self.trade_logs.append(
                        TradeRecord(
                            date=curr_date,
                            canonical_sid=sid,
                            action="SPLIT_ADJUSTMENT",
                            timing="OVERNIGHT",
                            price_raw=float(pos.last_price),
                            price_exec=float(pos.last_price),
                            shares=float(pos.shares),
                            notional=float(pos.shares * pos.last_price),
                            fee=0.0,
                            slippage_cost=0.0,
                            cash_impact=0.0,
                            note=f"Split factor {s_factor:.4f} adjusted shares from {old_shares:.4f} to {pos.shares:.4f}",
                        )
                    )

                # 0.2. Cash Dividend Payout
                div_amount = dividend_data.get((curr_date, sid), 0.0)
                if pd.notna(div_amount) and div_amount > 0:
                    cash_dividend = float(pos.shares * div_amount)
                    self.cash += cash_dividend
                    self.trade_logs.append(
                        TradeRecord(
                            date=curr_date,
                            canonical_sid=sid,
                            action="DIVIDEND_PAYOUT",
                            timing="OVERNIGHT",
                            price_raw=float(div_amount),
                            price_exec=float(div_amount),
                            shares=float(pos.shares),
                            notional=float(cash_dividend),
                            fee=0.0,
                            slippage_cost=0.0,
                            cash_impact=float(cash_dividend),
                            note=f"Cash dividend {div_amount:.4f}/share paid to carried position",
                        )
                    )

            # -------------------------------------------------------------
            # BƯỚC 1: Xử lý vị thế kẹt từ các phiên trước (Priority Liquidation at Open)
            # -------------------------------------------------------------
            carried_sids = list(self.positions.keys())
            for sid in carried_sids:
                pos = self.positions[sid]
                raw_open = open_prices.get((curr_date, sid), np.nan)
                is_bad = bad_data_flags.get((curr_date, sid), False)
                is_halted = halt_flags.get((curr_date, sid), False)

                # Kiểm tra tính hợp lệ của Open (hữu hạn, > 0, không bad data, không halt)
                can_liquidate = (
                    pd.notna(raw_open)
                    and np.isfinite(raw_open)
                    and (raw_open > 0)
                    and (not is_bad)
                    and (not is_halted)
                )

                if can_liquidate:
                    # Bán thanh lý tại Open
                    p_exec_sell = raw_open * (1.0 - self.slippage_rate_sell)
                    gross_val = pos.shares * p_exec_sell
                    fee_sell = gross_val * self.fee_rate_sell
                    net_cash = gross_val - fee_sell
                    slip_cost = pos.shares * (raw_open - p_exec_sell)

                    self.cash += net_cash
                    fees_paid_today += fee_sell
                    n_sells_filled += 1

                    self.trade_logs.append(
                        TradeRecord(
                            date=curr_date,
                            canonical_sid=sid,
                            action="SELL",
                            timing="OPEN",
                            price_raw=float(raw_open),
                            price_exec=float(p_exec_sell),
                            shares=float(pos.shares),
                            notional=float(gross_val),
                            fee=float(fee_sell),
                            slippage_cost=float(slip_cost),
                            cash_impact=float(net_cash),
                            note="Liquidate carried position at Open",
                        )
                    )
                    del self.positions[sid]
                else:
                    # Vẫn tiếp tục bị kẹt tại Open, ghi nhận lý do
                    if is_halted:
                        reason = "MARKET_HALT: Pre-market trading halt or suspension at Open"
                    elif is_bad:
                        reason = "DATA_QUARANTINE: Bar quarantined by quality flag"
                    else:
                        reason = "SIMULATION_CONDITION: Open price missing, non-finite, or non-positive"
                    pos.last_price = float(raw_open) if (pd.notna(raw_open) and np.isfinite(raw_open) and raw_open > 0) else pos.last_price
                    self.trade_logs.append(
                        TradeRecord(
                            date=curr_date,
                            canonical_sid=sid,
                            action="HELD_OVERNIGHT",
                            timing="OPEN",
                            price_raw=float(raw_open) if pd.notna(raw_open) else 0.0,
                            price_exec=0.0,
                            shares=float(pos.shares),
                            notional=float(pos.shares * pos.last_price),
                            fee=0.0,
                            slippage_cost=0.0,
                            cash_impact=0.0,
                            note=f"Carried position unable to liquidate at Open ({reason})",
                        )
                    )

            # -------------------------------------------------------------
            # BƯỚC 2: Phân bổ ngân sách và vào lệnh mua mới tại Open
            # -------------------------------------------------------------
            candidates = predictions_by_date.get(prev_date, [])
            remaining_carried_count = len(self.positions)
            slots_available = max(0, self.top_k - remaining_carried_count)

            if slots_available > 0 and len(candidates) > 0:
                # Lấy Top slots_available mã
                top_picks = candidates[:slots_available]
                # Ngân sách mỗi mã: Không quá 5% NAV hôm trước và không vượt tiền mặt khả dụng
                target_per_stock = nav_prev * self.target_weight
                budget_per_stock = min(target_per_stock, self.cash / slots_available)

                for sid, _score in top_picks:
                    raw_open = open_prices.get((curr_date, sid), np.nan)
                    is_bad = bad_data_flags.get((curr_date, sid), False)
                    is_halted = halt_flags.get((curr_date, sid), False)

                    # ĐIỀU KIỆN MỞ CỬA: Hữu hạn, > 0, không có cờ bad data, không halt (KHÔNG xét volume cả ngày)
                    can_buy = (
                        pd.notna(raw_open)
                        and np.isfinite(raw_open)
                        and (raw_open > 0)
                        and (not is_bad)
                        and (not is_halted)
                    )

                    if can_buy:
                        # Khớp mua thành công
                        p_exec_buy = raw_open * (1.0 + self.slippage_rate_buy)
                        # Tính phí mua trong ngân sách
                        notional_buy = budget_per_stock / (1.0 + self.fee_rate_buy)
                        fee_buy = budget_per_stock - notional_buy
                        shares = notional_buy / p_exec_buy
                        slip_cost = shares * (p_exec_buy - raw_open)

                        cash_spent = budget_per_stock
                        self.cash -= cash_spent
                        fees_paid_today += fee_buy
                        n_buys_filled += 1

                        self.positions[sid] = Position(
                            canonical_sid=sid,
                            shares=float(shares),
                            entry_date=curr_date,
                            entry_price_raw=float(raw_open),
                            entry_price_exec=float(p_exec_buy),
                            entry_fee=float(fee_buy),
                            entry_cash_outlay=float(cash_spent),
                            last_price=float(raw_open),
                        )

                        self.trade_logs.append(
                            TradeRecord(
                                date=curr_date,
                                canonical_sid=sid,
                                action="BUY",
                                timing="OPEN",
                                price_raw=float(raw_open),
                                price_exec=float(p_exec_buy),
                                shares=float(shares),
                                notional=float(notional_buy),
                                fee=float(fee_buy),
                                slippage_cost=float(slip_cost),
                                cash_impact=float(-cash_spent),
                                note="New position filled at Open",
                            )
                        )
                    else:
                        # Lệnh mua không khớp: Giữ nguyên tiền mặt, tuyệt đối KHÔNG đôn mã thay thế
                        n_buys_unfilled += 1
                        if is_halted:
                            reason = "MARKET_HALT: Pre-market trading halt or suspension"
                        elif is_bad:
                            reason = "DATA_QUARANTINE: Bar quarantined by quality flag"
                        else:
                            reason = "SIMULATION_CONDITION: Open price missing, non-finite, or non-positive"

                        self.trade_logs.append(
                            TradeRecord(
                                date=curr_date,
                                canonical_sid=sid,
                                action="CANCELLED_BUY",
                                timing="OPEN",
                                price_raw=float(raw_open) if (pd.notna(raw_open) and np.isfinite(raw_open)) else 0.0,
                                price_exec=0.0,
                                shares=0.0,
                                notional=0.0,
                                fee=0.0,
                                slippage_cost=0.0,
                                cash_impact=0.0,
                                note=reason,
                            )
                        )

            # -------------------------------------------------------------
            # BƯỚC 3: Thoát lệnh tại Close cho tất cả vị thế đang mở
            # -------------------------------------------------------------
            open_sids = list(self.positions.keys())
            for sid in open_sids:
                pos = self.positions[sid]
                raw_close = close_prices.get((curr_date, sid), np.nan)
                is_bad = bad_data_flags.get((curr_date, sid), False)
                vol = volume_data.get((curr_date, sid), 1.0)  # Mặc định hợp lệ nếu không cung cấp matrix

                # ĐIỀU KIỆN ĐÓNG CỬA: Cần Close hữu hạn, > 0, Volume ngày > 0, không có cờ lỗi
                is_close_valid = (
                    pd.notna(raw_close)
                    and np.isfinite(raw_close)
                    and (raw_close > 0)
                    and (not is_bad)
                )
                has_volume = (pd.notna(vol) and vol > 0)

                can_exit = is_close_valid and has_volume

                if can_exit:
                    # Bán tại Close
                    p_exec_sell = raw_close * (1.0 - self.slippage_rate_sell)
                    gross_val = pos.shares * p_exec_sell
                    fee_sell = gross_val * self.fee_rate_sell
                    net_cash = gross_val - fee_sell
                    slip_cost = pos.shares * (raw_close - p_exec_sell)

                    self.cash += net_cash
                    fees_paid_today += fee_sell
                    n_sells_filled += 1

                    self.trade_logs.append(
                        TradeRecord(
                            date=curr_date,
                            canonical_sid=sid,
                            action="SELL",
                            timing="CLOSE",
                            price_raw=float(raw_close),
                            price_exec=float(p_exec_sell),
                            shares=float(pos.shares),
                            notional=float(gross_val),
                            fee=float(fee_sell),
                            slippage_cost=float(slip_cost),
                            cash_impact=float(net_cash),
                            note="Intraday exit at Close",
                        )
                    )
                    del self.positions[sid]
                else:
                    # Không bán được tại Close! Giữ qua đêm sang phiên sau
                    if is_close_valid and not has_volume:
                        reason = "SIMULATION_CONDITION: Zero or missing daily volume prevents Close exit"
                        pos.last_price = float(raw_close)
                    elif is_bad:
                        reason = "DATA_QUARANTINE: Close bar quarantined by quality flag"
                    else:
                        reason = "MISSING_SIM_PRICE: Close price NaN, non-finite, or non-positive"

                    self.trade_logs.append(
                        TradeRecord(
                            date=curr_date,
                            canonical_sid=sid,
                            action="HELD_OVERNIGHT",
                            timing="CLOSE",
                            price_raw=float(raw_close) if (pd.notna(raw_close) and np.isfinite(raw_close)) else 0.0,
                            price_exec=0.0,
                            shares=float(pos.shares),
                            notional=float(pos.shares * pos.last_price),
                            fee=0.0,
                            slippage_cost=0.0,
                            cash_impact=0.0,
                            note=f"Close execution prevented ({reason}) - carried forward overnight",
                        )
                    )

            # -------------------------------------------------------------
            # BƯỚC 4: Hạch toán tổng kết phiên (Mark-to-Market & NAV)
            # -------------------------------------------------------------
            invested_val = sum(p.shares * p.last_price for p in self.positions.values())
            current_nav = self.cash + invested_val
            daily_ret = (current_nav / nav_prev) - 1.0

            self.daily_ledger.append(
                DailyLedgerRecord(
                    date=curr_date,
                    cash_start=float(cash_start_of_day),
                    cash_end=float(self.cash),
                    invested_value=float(invested_val),
                    nav=float(current_nav),
                    daily_return=float(daily_ret),
                    n_positions_open=len(self.positions),
                    n_carried_forward=len(self.positions),
                    n_buys_filled=n_buys_filled,
                    n_buys_unfilled=n_buys_unfilled,
                    n_sells_filled=n_sells_filled,
                    total_fees_paid=float(fees_paid_today),
                )
            )

        return pd.DataFrame([r.__dict__ for r in self.daily_ledger])

    def get_trade_log_df(self) -> pd.DataFrame:
        """Trả về DataFrame toàn bộ sổ lệnh."""
        return pd.DataFrame([t.__dict__ for t in self.trade_logs])
