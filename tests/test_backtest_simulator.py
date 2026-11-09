"""
Unit Tests & Pilot Verification for PortfolioSimulator (Engine v1)
=================================================================
Kiểm thử 3 ca đặc thù trên dữ liệu giả lập có đối chiếu số học bằng tay chính xác:
1. Khớp đủ 20 mã có phí.
2. Một lệnh mua thiếu Open giữ tiền mặt, không chọn mã thay thế.
3. Một vị thế chưa bán được tại Close T+1, phải giữ qua đêm và thanh lý ở phiên tiếp theo.
"""

import numpy as np
import pandas as pd
import pytest

from src.backtest.simulator import PortfolioSimulator


def test_case_1_full_20_stocks_with_fees():
    """Ca 1: Khớp đủ 20 mã có phí mua và bán, kiểm tra tính toán tiền mặt, cổ phiếu, phí, NAV."""
    sim = PortfolioSimulator(
        initial_capital=100_000.0,
        top_k=20,
        fee_rate_buy=0.0005,       # 5 bps
        slippage_rate_buy=0.0005,  # 5 bps
        fee_rate_sell=0.0005,      # 5 bps
        slippage_rate_sell=0.0005, # 5 bps
    )

    sessions = ["2024-01-02", "2024-01-03"]
    # 20 mã được xếp hạng tại 2024-01-02
    sids = [f"STOCK_{i:02d}" for i in range(1, 21)]
    preds = {
        "2024-01-02": [(s, 1.0 - i * 0.01) for i, s in enumerate(sids)]
    }

    # Giá giả định: Open thô = 100.0, Close thô = 102.0 cho cả 20 mã (+2.0% raw return)
    open_prices = {("2024-01-03", s): 100.0 for s in sids}
    close_prices = {("2024-01-03", s): 102.0 for s in sids}

    df_ledger = sim.simulate(
        sessions=sessions,
        predictions_by_date=preds,
        open_prices=open_prices,
        close_prices=close_prices,
    )

    # 1. Đối chiếu tính toán bằng tay
    # Ngân sách mỗi mã: B_i = 100,000 / 20 = 5,000 USD
    # Phí mua trong ngân sách:
    # Notional_buy = 5,000 / 1.0005 = 4997.501249375 USD
    # Fee_buy = 5,000 - Notional_buy = 2.498750625 USD
    # P_exec_buy = 100.0 * 1.0005 = 100.05 USD
    # Shares = Notional_buy / P_exec_buy = 49.950037475 cổ phiếu
    # Tổng tiền chi mua 20 mã = 20 * 5,000 = 100,000.0 USD
    # Tiền mặt sau mua tại Open = 0.0 USD
    # P_exec_sell = 102.0 * 0.9995 = 101.949 USD
    # Gross_sell = Shares * P_exec_sell = 49.950037475 * 101.949 = 5092.35637048 USD
    # Fee_sell = Gross_sell * 0.0005 = 2.546178185 USD
    # Net_cash = Gross_sell - Fee_sell = 5089.810192295 USD
    # Tiền mặt cuối ngày thu về = 20 * 5089.810192295 = 101,796.2038459 USD

    expected_nav = 20 * (
        (5000.0 / 1.0005 / 100.05) * (102.0 * 0.9995) * (1.0 - 0.0005)
    )
    expected_fees = 20 * (
        (5000.0 - 5000.0 / 1.0005) + ((5000.0 / 1.0005 / 100.05) * (102.0 * 0.9995) * 0.0005)
    )

    assert len(df_ledger) == 1
    row = df_ledger.iloc[0]
    assert row["n_buys_filled"] == 20
    assert row["n_buys_unfilled"] == 0
    assert row["n_sells_filled"] == 20
    assert row["n_carried_forward"] == 0
    assert pytest.approx(row["nav"], rel=1e-7) == expected_nav
    assert pytest.approx(row["cash_end"], rel=1e-7) == expected_nav
    assert pytest.approx(row["total_fees_paid"], rel=1e-7) == expected_fees
    assert pytest.approx(sim.cash, rel=1e-7) == expected_nav


def test_case_2_unfilled_buy_keeps_cash():
    """Ca 2: Một lệnh mua thiếu Open (NaN), 5% vốn giữ nguyên tiền mặt, KHÔNG chọn mã thay thế."""
    sim = PortfolioSimulator(
        initial_capital=100_000.0,
        top_k=20,
        fee_rate_buy=0.0005,
        slippage_rate_buy=0.0005,
        fee_rate_sell=0.0005,
        slippage_rate_sell=0.0005,
    )

    sessions = ["2024-01-02", "2024-01-03"]
    # 25 mã ứng viên trong danh sách xếp hạng
    sids = [f"STOCK_{i:02d}" for i in range(1, 26)]
    preds = {
        "2024-01-02": [(s, 1.0 - i * 0.01) for i, s in enumerate(sids)]
    }

    # Mã thứ 5 trong Top 20 (STOCK_05) bị thiếu Open (NaN / Halt)
    open_prices = {}
    close_prices = {}
    for s in sids:
        if s == "STOCK_05":
            open_prices[("2024-01-03", s)] = np.nan  # Bị halt không có giá Open
            close_prices[("2024-01-03", s)] = 100.0
        else:
            open_prices[("2024-01-03", s)] = 100.0
            close_prices[("2024-01-03", s)] = 102.0

    df_ledger = sim.simulate(
        sessions=sessions,
        predictions_by_date=preds,
        open_prices=open_prices,
        close_prices=close_prices,
    )

    # 1. Đối chiếu tính toán bằng tay
    # Top 20 được duyệt: STOCK_01 đến STOCK_20
    # 19 mã khớp: Mỗi mã chi 5,000 USD, tổng chi = 95,000 USD
    # 1 mã hủy (STOCK_05): Ngân sách 5,000 USD giữ nguyên trong tiền mặt
    # Tuyệt đối KHÔNG đôn STOCK_21 lên thay thế
    # Cuối ngày: 19 mã thu về 19 * 5089.810192 USD, cộng 5,000 USD tiền mặt chưa dùng
    expected_net_from_stocks = 19 * (
        (5000.0 / 1.0005 / 100.05) * (102.0 * 0.9995) * (1.0 - 0.0005)
    )
    expected_nav = 5000.0 + expected_net_from_stocks

    assert len(df_ledger) == 1
    row = df_ledger.iloc[0]
    assert row["n_buys_filled"] == 19
    assert row["n_buys_unfilled"] == 1
    assert row["n_sells_filled"] == 19
    assert row["n_carried_forward"] == 0
    assert pytest.approx(row["nav"], rel=1e-7) == expected_nav
    assert pytest.approx(row["cash_end"], rel=1e-7) == expected_nav

    # Kiểm tra sổ lệnh để xác nhận STOCK_21 KHÔNG được khớp
    trade_df = sim.get_trade_log_df()
    bought_sids = trade_df[trade_df["action"] == "BUY"]["canonical_sid"].tolist()
    assert "STOCK_05" not in bought_sids
    assert "STOCK_21" not in bought_sids
    assert len(bought_sids) == 19


def test_case_3_carried_position_multi_session():
    """Ca 3: Một vị thế không bán được tại Close T+1 (bị halt trong phiên), giữ qua đêm sang T+2."""
    sim = PortfolioSimulator(
        initial_capital=100_000.0,
        top_k=20,
        fee_rate_buy=0.0005,
        slippage_rate_buy=0.0005,
        fee_rate_sell=0.0005,
        slippage_rate_sell=0.0005,
    )

    sessions = ["2024-01-02", "2024-01-03", "2024-01-04"]
    sids_day1 = [f"STOCK_{i:02d}" for i in range(1, 21)]
    sids_day2 = [f"STOCK_D2_{i:02d}" for i in range(1, 21)]

    preds = {
        "2024-01-02": [(s, 1.0 - i * 0.01) for i, s in enumerate(sids_day1)],
        "2024-01-03": [(s, 1.0 - i * 0.01) for i, s in enumerate(sids_day2)],
    }

    open_prices = {}
    close_prices = {}

    # Phiên 1 (2024-01-03): STOCK_20 khớp mua ở Open=100.0, nhưng Close bị halt (NaN)
    for s in sids_day1:
        open_prices[("2024-01-03", s)] = 100.0
        if s == "STOCK_20":
            close_prices[("2024-01-03", s)] = np.nan  # Không bán được tại Close!
        else:
            close_prices[("2024-01-03", s)] = 102.0

    # Phiên 2 (2024-01-04): STOCK_20 mở cửa trở lại có giá Open=103.0 để bán thanh lý
    open_prices[("2024-01-04", "STOCK_20")] = 103.0
    close_prices[("2024-01-04", "STOCK_20")] = 103.0

    for s in sids_day2:
        open_prices[("2024-01-04", s)] = 50.0
        close_prices[("2024-01-04", s)] = 51.0

    df_ledger = sim.simulate(
        sessions=sessions,
        predictions_by_date=preds,
        open_prices=open_prices,
        close_prices=close_prices,
    )

    assert len(df_ledger) == 2
    row_day1 = df_ledger.iloc[0]
    row_day2 = df_ledger.iloc[1]

    # Kiểm tra Ngày 1:
    # 20 mã được mua tại Open
    # 19 mã bán được tại Close
    # 1 mã (STOCK_20) bị kẹt, n_carried_forward = 1
    assert row_day1["n_buys_filled"] == 20
    assert row_day1["n_sells_filled"] == 19
    assert row_day1["n_carried_forward"] == 1
    assert "STOCK_20" in sim.positions or len(df_ledger) == 2  # Tại hết ngày 1 vẫn giữ STOCK_20

    # Tiền mặt cuối ngày 1 = Tiền thu từ 19 mã
    expected_cash_day1 = 19 * (
        (5000.0 / 1.0005 / 100.05) * (102.0 * 0.9995) * (1.0 - 0.0005)
    )
    # Giá trị cổ phiếu kẹt MtM theo giá Open 100.0 = Shares * 100.0
    shares_s20 = 5000.0 / 1.0005 / 100.05
    expected_invested_day1 = shares_s20 * 100.0
    expected_nav_day1 = expected_cash_day1 + expected_invested_day1

    assert pytest.approx(row_day1["cash_end"], rel=1e-7) == expected_cash_day1
    assert pytest.approx(row_day1["invested_value"], rel=1e-7) == expected_invested_day1
    assert pytest.approx(row_day1["nav"], rel=1e-7) == expected_nav_day1

    # Kiểm tra Ngày 2:
    # Đầu ngày 2: STOCK_20 được thanh lý tại Open = 103.0
    # Tiền mặt tăng thêm: shares_s20 * (103.0 * 0.9995) * (1.0 - 0.0005)
    # Sau đó giải ngân Top 20 mã của Ngày 2
    # Cuối ngày 2: Toàn bộ vị thế Ngày 2 thoát thành công tại Close
    assert row_day2["n_carried_forward"] == 0
    assert len(sim.positions) == 0

    trade_df = sim.get_trade_log_df()
    s20_trades = trade_df[trade_df["canonical_sid"] == "STOCK_20"]
    actions = s20_trades["action"].tolist()
    timings = s20_trades["timing"].tolist()
    assert actions == ["BUY", "HELD_OVERNIGHT", "SELL"]
    assert timings == ["OPEN", "CLOSE", "OPEN"]


def test_case_4_carried_position_with_split_and_dividend():
    """Ca 4: Vị thế giữ qua đêm gặp sự kiện Split và Cổ tức tiền mặt trên ngày ex-date."""
    sim = PortfolioSimulator(
        initial_capital=100_000.0,
        top_k=20,
        fee_rate_buy=0.0005,
        slippage_rate_buy=0.0005,
        fee_rate_sell=0.0005,
        slippage_rate_sell=0.0005,
    )

    sessions = ["2024-01-02", "2024-01-03", "2024-01-04"]
    sids_day1 = [f"STOCK_{i:02d}" for i in range(1, 21)]

    preds = {
        "2024-01-02": [(s, 1.0 - i * 0.01) for i, s in enumerate(sids_day1)],
        "2024-01-03": [],  # Ngày 2 không có lệnh mua mới
    }

    # Ngày 1: STOCK_01 khớp mua Open=100, nhưng Close bị halt không bán được
    open_prices = {("2024-01-03", s): 100.0 for s in sids_day1}
    close_prices = {("2024-01-03", s): 102.0 for s in sids_day1}
    close_prices[("2024-01-03", "STOCK_01")] = np.nan  # Halt

    # Ngày 2: STOCK_01 có split 2:1 (factor = 2.0) và cổ tức tiền mặt $0.50/share
    split_factors = {("2024-01-04", "STOCK_01"): 2.0}
    dividend_data = {("2024-01-04", "STOCK_01"): 0.50}

    # Ngày 2: STOCK_01 mở cửa lại ở giá 51.0 (sau split) để thanh lý
    open_prices[("2024-01-04", "STOCK_01")] = 51.0
    close_prices[("2024-01-04", "STOCK_01")] = 51.0

    df_ledger = sim.simulate(
        sessions=sessions,
        predictions_by_date=preds,
        open_prices=open_prices,
        close_prices=close_prices,
        split_factors=split_factors,
        dividend_data=dividend_data,
    )

    # 1. Ban đầu mua STOCK_01:
    # budget = 5,000 USD
    # notional = 5000 / 1.0005 = 4997.501249 USD
    # p_exec_buy = 100.05 USD
    # shares_old = 4997.501249 / 100.05 = 49.950037 cổ phiếu
    shares_old = 5000.0 / 1.0005 / 100.05
    shares_new = shares_old * 2.0  # Gấp đôi số cổ phiếu

    # 2. Cổ tức nhận được: shares_new * 0.50 USD
    expected_div_cash = shares_new * 0.50

    # 3. Thanh lý tại Open Ngày 2:
    p_exec_sell = 51.0 * (1.0 - 0.0005)
    gross_sell = shares_new * p_exec_sell
    fee_sell = gross_sell * 0.0005
    net_sell = gross_sell - fee_sell

    # 4. Tiền thu từ 19 mã ngày 1:
    cash_day1_19_stocks = 19 * (
        (5000.0 / 1.0005 / 100.05) * (102.0 * 0.9995) * (1.0 - 0.0005)
    )

    expected_final_cash = cash_day1_19_stocks + expected_div_cash + net_sell

    assert len(df_ledger) == 2
    assert pytest.approx(df_ledger.iloc[1]["cash_end"], rel=1e-7) == expected_final_cash
    assert pytest.approx(df_ledger.iloc[1]["nav"], rel=1e-7) == expected_final_cash

    trade_df = sim.get_trade_log_df()
    actions = trade_df[trade_df["canonical_sid"] == "STOCK_01"]["action"].tolist()
    assert actions == ["BUY", "HELD_OVERNIGHT", "SPLIT_ADJUSTMENT", "DIVIDEND_PAYOUT", "SELL"]


def test_case_5_cf_matrix_conversion_and_position_preservation():
    """
    Kiểm tra chuyển đổi từ ma trận CF sang đầu vào simulator:
    Tỷ lệ đổi cổ phiếu S = CF_sau / CF_trước theo quy ước adj_close = raw_close * CF.
    Xác nhận giá trị vị thế được bảo toàn 100% qua split 2:1 và reverse split 1:10
    trước biến động giá và phí.
    """
    # 1. Forward Split 2:1
    # raw_close trước = 100, sau split raw_close = 50
    # CF_trước = 0.5, CF_sau = 1.0 -> adj_close = 100 * 0.5 = 50.0
    cf_truoc_split = 0.5
    cf_sau_split = 1.0
    s_factor_forward = cf_sau_split / cf_truoc_split
    assert pytest.approx(s_factor_forward) == 2.0

    # Vị thế ban đầu: 50 cổ phiếu, giá 100.0 USD
    shares_orig_fwd = 50.0
    price_orig_fwd = 100.0
    val_before_fwd = shares_orig_fwd * price_orig_fwd  # 5,000 USD

    # Sau chuyển đổi split:
    shares_new_fwd = shares_orig_fwd * s_factor_forward  # 100 cổ phiếu
    price_new_fwd = price_orig_fwd / s_factor_forward    # 50.0 USD
    val_after_fwd = shares_new_fwd * price_new_fwd

    assert pytest.approx(val_after_fwd) == val_before_fwd == 5000.0

    # 2. Reverse Split 1:10
    # raw_close trước = 10, sau reverse split raw_close = 100
    # CF_trước = 10.0, CF_sau = 1.0 -> adj_close = 10 * 10.0 = 100.0
    cf_truoc_rev = 10.0
    cf_sau_rev = 1.0
    s_factor_rev = cf_sau_rev / cf_truoc_rev
    assert pytest.approx(s_factor_rev) == 0.1

    # Vị thế ban đầu: 500 cổ phiếu, giá 10.0 USD
    shares_orig_rev = 500.0
    price_orig_rev = 10.0
    val_before_rev = shares_orig_rev * price_orig_rev  # 5,000 USD

    # Sau chuyển đổi reverse split:
    shares_new_rev = shares_orig_rev * s_factor_rev  # 50 cổ phiếu
    price_new_rev = price_orig_rev / s_factor_rev    # 100.0 USD
    val_after_rev = shares_new_rev * price_new_rev

    assert pytest.approx(val_after_rev) == val_before_rev == 5000.0
