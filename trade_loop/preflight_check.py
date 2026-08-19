#!/usr/bin/env python3
"""漂移前置校验：step 执行前比对 观察日K线 与服务端当前行，防止数据漂移误成交。

用法:
  python3 preflight_check.py            # 校验当前状态, 输出 OK / 冻结标志
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

BASE = os.environ.get("STOCK_TRADE_BASE", "http://127.0.0.1:7860")


def get_json(path: str) -> dict:
    resp = requests.get(BASE + path, timeout=30)
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("error", path))
    return data.get("data") or {}


def main() -> int:
    state = get_json("/api/state")
    kline = get_json("/api/kline?period=day&before=10")
    rows = kline if isinstance(kline, list) else (kline.get("data") or kline.get("day") or [])
    cur_date = (state.get("current_date") or "")[:10]
    if not rows:
        print(json.dumps({"ok": False, "reason": "无日线数据"}, ensure_ascii=False))
        return 1
    last = rows[-1]
    last_date = str(last.get("date", ""))[:10]
    high = float(last.get("high") or 0)
    low = float(last.get("low") or 0)
    close = float(last.get("close") or 0)
    issues = []
    if last_date != cur_date:
        issues.append(f"日期不一致: 服务端当前日 {cur_date} vs K线末日 {last_date}")
    if high <= 0 or low <= 0:
        issues.append(f"K线异常: high={high} low={low}")
    if abs(high - low) < 1e-9:
        issues.append(f"一字异常线: high==low=={high} (疑似残缺数据)")
    if close <= 0:
        issues.append(f"收盘价异常: {close}")
    result = {
        "ok": not issues,
        "current_date": cur_date,
        "kline_last": {"date": last_date, "high": high, "low": low, "close": close},
        "issues": issues,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
