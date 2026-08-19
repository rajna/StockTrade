#!/usr/bin/env python3
"""stock-trade 交易循环编排器（Agent A 侧确定性操作封装）。

职责: 初始化账户 / 取AI观察prompt / 执行交易step / 计算本次交易盈亏。
coms 通信(通知决策者B、收JSON决策、发盈亏反馈)由 Agent A(pi会话)用 coms_send/coms_await 完成。

用法:
  python3 orchestrator.py init  --stock sh.600000 --cash 100000 --date 2025-04-01
  python3 orchestrator.py prompt                          # 输出观察数据(发给B做决策)
  python3 orchestrator.py step  --decision 买入 --price 9.18 --qty 1000 --reason "..."
  python3 orchestrator.py pnl                              # 输出本次交易后盈亏(反馈给B)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import requests

BASE = os.environ.get("STOCK_TRADE_BASE", "http://127.0.0.1:7860")
STATE_FILE = Path(__file__).resolve().parent / "loop_state.json"


def api(path: str, method: str = "GET", **kw) -> Dict[str, Any]:
    try:
        resp = requests.request(method, BASE + path, timeout=90, **kw)
        data = resp.json()
    except Exception as exc:
        raise RuntimeError(f"{path} 请求失败: {exc}")
    if not data.get("ok"):
        raise RuntimeError(data.get("error", f"{path} 返回错误"))
    return data.get("data") or {}


def save_state(**updates) -> None:
    state: Dict[str, Any] = {}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            state = {}
    state.update(updates)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def money(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def cmd_init(a) -> None:
    data = api("/api/init", "POST", json={
        "stock_code": a.stock, "initial_cash": a.cash, "date_start": a.date,
        "hold_period": a.hold_period, "auto_switch": a.auto_switch})
    save_state(
        stock=a.stock, initial_cash=float(a.cash), date_start=a.date,
        hold_period=int(a.hold_period), auto_switch=bool(a.auto_switch),
        last_decision=None, last_total_assets=None,
    )
    print(json.dumps({
        "ok": True, "stock": data.get("current_stock"),
        "current_date": data.get("current_date"),
        "hold_period": (data.get("hold") or {}).get("hold_period"),
        "auto_switch": (data.get("hold") or {}).get("auto_switch"),
        "cash": data.get("portfolio_text", "").split("现金余额")[-1][:30] if data.get("portfolio_text") else "?",
    }, ensure_ascii=False))


def cmd_switch(a) -> None:
    """切换当前交易股票: --stock 指定或 --random 随机选股; --force 跳过持股周期校验。"""
    payload: Dict[str, Any] = {}
    if a.random or not a.stock:
        payload["random"] = True
    if a.stock:
        payload["stock_code"] = a.stock
    if a.force:
        payload["force"] = True
    data = api("/api/switch", "POST", json=payload)
    sw = data.get("switch") or {}
    hold = data.get("hold") or {}
    save_state(stock=data.get("stock"), last_decision=None)
    print(json.dumps({
        "ok": True,
        "message": sw.get("message"),
        "current_stock": data.get("stock"),
        "current_date": data.get("current_date"),
        "hold_days": hold.get("hold_days"),
        "hold_period": hold.get("hold_period"),
        "can_switch": hold.get("can_switch"),
    }, ensure_ascii=False))


def cmd_prompt(_a) -> None:
    data = api("/api/prompt")
    print(data.get("prompt", ""))


def cmd_step(a) -> None:
    prev = load_state()
    # step 前先取 state 记录基准总资产
    before = api("/api/state")
    before_text = before.get("portfolio_text") or ""
    before_assets = _extract_total_assets(before_text) or money(before.get("portfolio", {}).get("total_value"))
    data = api("/api/step", "POST", json={
        "decision": a.decision, "tradePrice": a.price,
        "quantity": a.qty, "reasoning": a.reason,
    })
    step = data.get("step", {})
    after_text = data.get("portfolio_text") or _portfolio_text_of(data)
    after_assets = _extract_total_assets(after_text) or money((data.get("portfolio") or {}).get("total_value"))
    delta = (after_assets - before_assets) if (before_assets and after_assets) else None
    # 本次交易盈亏: step 后未实现盈亏(持仓浮盈) + 总资产变化
    unrealized = _extract_unrealized(after_text)
    save_state(last_decision=a.decision, last_total_assets=after_assets)
    print(json.dumps({
        "ok": True,
        "decision": a.decision,
        "executed_at": step.get("date"),
        "next_date": step.get("next_date") or step.get("date"),
        "trade_result": step.get("trade_result"),
        "total_assets_delta": round(delta, 2) if delta is not None else None,
        "unrealized_pnl": unrealized,
    }, ensure_ascii=False))


def _portfolio_text_of(data: Dict[str, Any]) -> str:
    return str(data.get("portfolio_text") or data.get("observations", {}).get("portfolio") or "")


def _extract_total_assets(text: str) -> Optional[float]:
    import re
    m = re.search(r"总资产[:：]\s*¥?\s*([\d,\.]+)", text)
    return float(m.group(1).replace(",", "")) if m else None


def _extract_unrealized(text: str) -> Optional[float]:
    import re
    m = re.search(r"未实现盈亏[:：]\s*¥?\s*([+\-]?[\d,\.]+)", text)
    if m:
        return float(m.group(1).replace(",", ""))
    m2 = re.search(r"([+\-]?\d+\.\d+)%", text)
    return None


def cmd_pnl(_a) -> None:
    data = api("/api/state")
    text = data.get("portfolio_text") or ""
    port = data.get("portfolio") or {}
    hold = data.get("hold") or {}
    print(json.dumps({
        "current_date": data.get("current_date"),
        "cash": port.get("cash_balance"),
        "market_value": port.get("market_value") if "market_value" in port else None,
        "total_assets": _extract_total_assets(text) or port.get("total_value"),
        "unrealized_pnl": _extract_unrealized(text) or port.get("unrealized_pnl"),
        "return_pct": port.get("return_pct") or port.get("total_return_pct"),
        "hold": {
            "hold_days": hold.get("hold_days"),
            "hold_period": hold.get("hold_period"),
            "can_switch": hold.get("can_switch"),
            "stock_switch_count": hold.get("stock_switch_count"),
        },
    }, ensure_ascii=False))


def main() -> int:
    parser = argparse.ArgumentParser(description="stock-trade 交易 loop 编排器(A侧)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("--stock", default="sh.600000"); p.add_argument("--cash", type=float, default=100000.0); p.add_argument("--date", default="2025-01-01"); p.add_argument("--hold-period", type=int, default=5, help="持股周期(交易日), 默认5, 持有满周期后可切换股票"); p.add_argument("--no-auto-switch", dest="auto_switch", action="store_false", help="关闭自动切换(默认开启: 推进满周期自动随机换股)")
    sub.add_parser("prompt")
    s = sub.add_parser("step"); s.add_argument("--decision", choices=["买入","卖出","持有","不建仓"], default="不建仓"); s.add_argument("--price", type=float, default=0); s.add_argument("--qty", type=int, default=0); s.add_argument("--reason", default="loop决策")
    sw = sub.add_parser("switch"); sw.add_argument("--stock", default="", help="指定切换的股票代码; 留空则随机选股"); sw.add_argument("--random", action="store_true", help="随机切换(默认行为)"); sw.add_argument("--force", action="store_true", help="跳过持股周期校验强制切换")
    sub.add_parser("pnl")
    a = parser.parse_args()
    try:
        if a.cmd == "init": cmd_init(a)
        elif a.cmd == "prompt": cmd_prompt(a)
        elif a.cmd == "step": cmd_step(a)
        elif a.cmd == "switch": cmd_switch(a)
        elif a.cmd == "pnl": cmd_pnl(a)
        return 0
    except Exception as exc:
        print(f"orchestrator error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
