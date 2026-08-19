#!/usr/bin/env python3
"""持股周期 + 股票切换 单元测试（不依赖网络，全部 mock）。

验证:
1. 默认持股周期 = 5, 可配置
2. get_hold_days 按交易日计算
3. can_switch_stock 周期未到 False / 已到 True
4. switch_stock 周期未到拒绝; force 可强制
5. switch_stock 切换: 自动清仓、日期对齐、hold_start_date 重置、记录轨迹
6. random_switch_stock 随机选股并排除已切换过的
"""
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stock_trading_game as stg


def make_dummy_game(stock_code="sh.600000", hold_period=5, hold_days_from=0):
    """构造不触发网络的 StockTradingGame 桩对象。"""
    game = object.__new__(stg.StockTradingGame)
    # 构造 30 个交易日
    dates = pd.bdate_range("2025-06-02", periods=30)
    n = len(dates)
    df = pd.DataFrame({
        "date": dates,
        "open": np.linspace(10, 12, n),
        "high": np.linspace(10.2, 12.3, n),
        "low": np.linspace(9.8, 11.7, n),
        "close": np.linspace(10, 12, n) + 0.1,
        "volume": np.full(n, 1_000_000),
    })
    game.historical_data = df
    game.current_data_index = n - 1
    game.date_start = "2025-06-02"
    game.available_stocks = [stock_code]
    game.game_state = {
        "cash_balance": 100000.0,
        "initial_cash": 100000.0,
        "portfolio": {},
        "transaction_history": [],
        "current_prices": {},
        "pre_prices": {},
        # 持有开始日固定在首个交易日, current_date 由 hold_days_from 决定 → 持有天数 = hold_days_from + 1
        "current_date": dates[hold_days_from].strftime("%Y-%m-%d 00:00:00"),
        "current_stock": stock_code,
        "train_start_date": dates[0].strftime("%Y-%m-%d 00:00:00"),
        "current_day_k_observing": "",
        "current_week_k_observing": "",
        "current_month_k_observing": "",
        "hold_period": hold_period,
        "hold_start_date": dates[0].strftime("%Y-%m-%d 00:00:00"),
        "stock_switch_count": 0,
        "switched_stocks": [],
    }
    game.id = f"{stock_code}:{game.game_state['current_date']}"
    game.auto_save_enabled = False  # 测试桩跳过存档
    game.last_save_time = None
    return game


def test_hold_period_default():
    """默认持股周期 5。"""
    game = make_dummy_game(hold_period=5)
    assert game.game_state["hold_period"] == 5
    print("✅ 默认持股周期 = 5")


def test_hold_days_and_can_switch():
    """持有天数计算: 第1天=1天(未到周期), 第5天=5天(可切换)。"""
    # 持有开始后第 0 个交易日(当天)
    g1 = make_dummy_game(hold_days_from=0)
    assert stg.get_hold_days(g1) == 1
    assert stg.can_switch_stock(g1) is False
    # 持有开始后第 5 个交易日(索引4)
    g2 = make_dummy_game(hold_days_from=4)
    assert stg.get_hold_days(g2) == 5
    assert stg.can_switch_stock(g2) is True
    # 持有开始后第 10 个交易日
    g3 = make_dummy_game(hold_days_from=9)
    assert stg.get_hold_days(g3) == 10
    assert stg.can_switch_stock(g3) is True
    print("✅ 持有天数按交易日计数, 满 5 天可切换")


def test_switch_reject_before_period():
    """周期未到: 拒绝切换。"""
    game = make_dummy_game(hold_days_from=0)
    r = stg.switch_stock(game, "sz.000001")
    assert r["success"] is False
    assert "未到持股周期" in r["message"]
    print("✅ 周期未到拒绝切换")


def test_switch_force_ok():
    """force=True 跳过周期校验(需要网络加载, mock _load_historical_data)。"""
    game = make_dummy_game(hold_days_from=0)
    # mock 数据加载: 返回一份同样结构的 sz.000001 数据
    def fake_load(code, start):
        df = game.historical_data.copy()
        return df
    game._load_historical_data = fake_load
    stg._update_market_prices = lambda g: None  # 不刷新观察文本
    r = stg.switch_stock(game, "sz.000001", force=True)
    assert r["success"] is True, r
    assert game.game_state["current_stock"] == "sz.000001"
    assert game.game_state["hold_start_date"] == game.game_state["current_date"]
    assert game.game_state["stock_switch_count"] == 1
    assert "sz.000001" in [t["symbol"] for t in game.game_state["transaction_history"] if t["action"] == "切换股票"]
    print("✅ force 强制切换成功, 状态更新正确")


def test_switch_auto_liquidate():
    """切换时自动清仓: 持仓股票被按当前价卖出, 现金回笼。"""
    game = make_dummy_game(hold_days_from=9)
    # 模拟持仓
    price = float(game.historical_data.iloc[game.current_data_index]["close"])
    game.game_state["portfolio"]["sh.600000"] = {
        "symbol": "sh.600000", "quantity": 1000, "avg_price": price - 1, "timestamp": datetime.now(),
    }
    game.game_state["cash_balance"] = 50000.0
    def fake_load(code, start):
        df = game.historical_data.copy()
        return df
    game._load_historical_data = fake_load
    stg._update_market_prices = lambda g: None
    before_cash = game.game_state["cash_balance"]
    r = stg.switch_stock(game, "sz.000001")
    assert r["success"] is True, r
    assert "sh.600000" not in game.game_state["portfolio"]  # 已清仓
    assert game.game_state["cash_balance"] > before_cash  # 卖出回款
    sell_actions = [t for t in game.game_state["transaction_history"] if t["action"] == "卖出"]
    assert len(sell_actions) == 1
    print(f"✅ 切换自动清仓: 现金 {before_cash:,.0f} → {game.game_state['cash_balance']:,.0f}")


def test_switch_date_alignment():
    """切换后新股票定位到当前游戏日期(不回退)。"""
    game = make_dummy_game(hold_days_from=9)
    target_date = game.game_state["current_date"]
    def fake_load(code, start):
        df = game.historical_data.copy()
        return df
    game._load_historical_data = fake_load
    stg._update_market_prices = lambda g: None
    r = stg.switch_stock(game, "sz.000001")
    assert r["success"] is True, r
    new_date = pd.to_datetime(game.historical_data.iloc[game.current_data_index]["date"]).strftime("%Y-%m-%d")
    assert new_date == target_date[:10], f"切换后日期应保持 {target_date[:10]}, 实际 {new_date}"
    print(f"✅ 切换后日期对齐: {new_date} == {target_date[:10]}")


def test_random_switch_excludes_switched():
    """随机切换排除当前股票与已切换过的。"""
    game = make_dummy_game(hold_days_from=9)
    game.game_state["switched_stocks"] = ["sh.600000"]
    exclude = game.game_state["switched_stocks"] + [game.game_state["current_stock"]]
    code = stg.get_random_stock(exclude=exclude, n=1)
    assert isinstance(code, str) and code.startswith(("sh.", "sz."))
    assert code not in exclude
    print(f"✅ 随机选股: {code} (已排除 {exclude})")


def test_random_switch_flow():
    """random_switch_stock 全流程(force 跳过周期)。"""
    game = make_dummy_game(hold_days_from=9)
    def fake_load(code, start):
        df = game.historical_data.copy()
        return df
    game._load_historical_data = fake_load
    stg._update_market_prices = lambda g: None
    r = stg.random_switch_stock(game)
    assert r["success"] is True, r
    assert game.game_state["current_stock"] != "sh.600000"
    assert game.game_state["stock_switch_count"] == 1
    print(f"✅ random_switch_stock: 切至 {game.game_state['current_stock']}")


def test_should_auto_switch():
    """should_auto_switch: 周期未到 False / 周期到且开启 True / 关闭 False。"""
    g1 = make_dummy_game(hold_days_from=0)   # 持有1天, 未到周期
    assert stg.should_auto_switch(g1) is False
    g2 = make_dummy_game(hold_days_from=9)   # 持有10天, 到周期, auto_switch 默认开启
    assert stg.should_auto_switch(g2) is True
    g2.game_state["auto_switch"] = False    # 关闭自动切换
    assert stg.should_auto_switch(g2) is False
    print("✅ should_auto_switch: 周期+开关双条件判定")


def test_auto_switch_records_last_switch():
    """自动切换(auto=True)记录 last_auto_switch 供观察prompt告知决策者。"""
    game = make_dummy_game(hold_days_from=9)
    def fake_load(code, start):
        df = game.historical_data.copy()
        return df
    game._load_historical_data = fake_load
    stg._update_market_prices = lambda g: None
    r = stg.random_switch_stock(game, auto=True)
    assert r["success"] is True, r
    assert r.get("auto") is True
    last = game.game_state["last_auto_switch"]
    assert last is not None
    assert last["from_symbol"] == "sh.600000"
    assert last["to_symbol"] == game.game_state["current_stock"]
    actions = [t["action"] for t in game.game_state["transaction_history"]]
    assert "自动切换" in actions
    print(f"✅ 自动切换: last_auto_switch={last}, 交易记录含'自动切换'")


def test_auto_switch_step_simulation():
    """模拟 step 推进流程: 推进后到周期 -> 自动切换 -> 周期重置不再连续触发。"""
    game = make_dummy_game(hold_days_from=9)  # current_date=第10个交易日, 持有10天已到周期
    def fake_load(code, start):
        df = game.historical_data.copy()
        return df
    game._load_historical_data = fake_load
    stg._update_market_prices = lambda g: None
    assert stg.should_auto_switch(game) is True
    # 执行自动切换
    r = stg.random_switch_stock(game, auto=True)
    assert r["success"] is True, r
    # 切换后周期重置, 不再触发
    assert stg.should_auto_switch(game) is False
    assert stg.get_hold_days(game) == 1
    print("✅ step模拟: 达周期自动切换, 切换后周期重置不连续触发")


if __name__ == "__main__":
    tests = [
        test_hold_period_default,
        test_hold_days_and_can_switch,
        test_switch_reject_before_period,
        test_switch_force_ok,
        test_switch_auto_liquidate,
        test_switch_date_alignment,
        test_random_switch_excludes_switched,
        test_random_switch_flow,
        test_should_auto_switch,
        test_auto_switch_records_last_switch,
        test_auto_switch_step_simulation,
    ]
    for t in tests:
        t()
    print("\n🎉 全部测试通过")
