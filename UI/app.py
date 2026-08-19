#!/usr/bin/env python3
"""
Stock Trading Game Web Service

给 scripts/stock_trading_game.py 提供一个轻量 Flask Web 服务：
- 初始化模拟
- 执行单步模拟
- 查看每一步交易轨迹
- 查看当前账户与当前股票 K 线
"""

from __future__ import annotations

import concurrent.futures
import copy
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import stock_trading_game as stg  # noqa: E402
from stock_trading_game import (  # noqa: E402
    StockTradingGame,
    detect_boom_day,
    get_portfolio_value,
    handle_trade,
    next_trading_day,
    render_portfolio,
)

app = Flask(__name__, static_folder=".", static_url_path="")


@dataclass
class GameSession:
    """内存中的 Web 会话。"""

    id: str
    game: StockTradingGame
    created_at: str
    step_index: int = 0
    trajectory: List[Dict[str, Any]] = field(default_factory=list)
    finished: bool = False


SESSIONS: Dict[str, GameSession] = {}
DEFAULT_SESSION_ID: Optional[str] = None


def _format_kline_text(df: pd.DataFrame, limit: int = 12) -> str:
    """把真实 K 线切片格式化成观察文本；不请求额外数据源。"""
    if df is None or df.empty:
        return "K线数据不可用"
    rows = []
    for item in df.tail(limit).to_dict(orient="records"):
        rows.append(
            f"{str(item.get('date'))[:10]} 开{float(item.get('open', 0)):.2f} "
            f"高{float(item.get('high', 0)):.2f} 低{float(item.get('low', 0)):.2f} "
            f"收{float(item.get('close', 0)):.2f} 量{int(float(item.get('volume', 0) or 0))}"
        )
    return "\n".join(rows)


def _patch_market_update_to_local_kline() -> None:
    """修复初始化过慢：只用 StockTradingGame 已加载的真实日线更新价格和观察文本。"""
    def update_market_prices_local(game: StockTradingGame) -> None:
        if game.current_data_index >= len(game.historical_data):
            return
        current_row = game.historical_data.iloc[game.current_data_index]
        pre_row = game.historical_data.iloc[game.current_data_index - 1] if game.current_data_index else None
        for symbol in game.available_stocks:
            game.game_state["current_prices"][symbol] = current_row
            game.game_state["pre_prices"][symbol] = float(pre_row["close"]) if pre_row is not None else float(current_row["open"])
        game.game_state["current_date"] = pd.to_datetime(current_row["date"]).strftime("%Y-%m-%d %H:%M:%S")

        end = game.current_data_index + 1
        day_df = game.historical_data.iloc[max(0, end - 21):end]
        all_df = game.historical_data.iloc[:end].copy()
        all_df["date"] = pd.to_datetime(all_df["date"], errors="coerce")
        all_df = all_df.dropna(subset=["date"]).set_index("date")
        agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
        last_day = all_df.index.max() if not all_df.empty else pd.NaT
        # 排除未完整周期桶(当月/当周未结束不输出),与 _resample_kline 同规则:桶标签<=数据末日
        week_res = all_df.resample("W-FRI").agg(agg).dropna() if not all_df.empty else pd.DataFrame()
        month_res = all_df.resample("M").agg(agg).dropna() if not all_df.empty else pd.DataFrame()
        # 未完整周期桶(标签>数据末日): 不删除, 标签修正为数据末日(as-of),保留"当月/当周至今"半截K线
        if not week_res.empty and pd.notna(last_day):
            week_res = week_res.copy()
            week_res.index = pd.Index([d if d <= last_day else last_day for d in week_res.index], name=week_res.index.name)
        if not month_res.empty and pd.notna(last_day):
            month_res = month_res.copy()
            month_res.index = pd.Index([d if d <= last_day else last_day for d in month_res.index], name=month_res.index.name)
        week_df = week_res.reset_index() if not week_res.empty else pd.DataFrame()
        month_df = month_res.reset_index() if not month_res.empty else pd.DataFrame()
        game.game_state["current_day_k_observing"] = _format_kline_text(day_df)
        game.game_state["current_week_k_observing"] = _format_kline_text(week_df)
        game.game_state["current_month_k_observing"] = _format_kline_text(month_df)

    stg._update_market_prices = update_market_prices_local


_patch_market_update_to_local_kline()


def _tencent_symbol(stock_code: str) -> str:
    code = stock_code.split(".")[-1]
    if stock_code.startswith("sh") or code.startswith("6"):
        return f"sh{code}"
    return f"sz{code}"


def _fetch_tencent_daily(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """用腾讯真实行情接口获取日 K；禁用环境代理，避免本机坏代理影响请求。
    增强：①本地缓存(按股票+截至日,固定数据版本防漂移) ②拉取校验(行数/NaN/high>=low/异常涨跌)
    ③拉取失败回退缓存。init/load 复用同一缓存版本,消除"每次重拉不同版本"的漂移。"""
    start = pd.to_datetime((start_date or "2025-01-01").split(" ")[0], errors="coerce")
    if pd.isna(start):
        raise ValueError(f"开始日期无效: {start_date}")
    end = pd.to_datetime(end_date, errors="coerce")
    if pd.isna(end):
        end = pd.Timestamp.today()
    symbol = _tencent_symbol(stock_code)
    cache_dir = Path(_default_save_dir()) / "kline_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = f"{symbol}_{end.strftime('%Y%m%d')}"
    cache_file = cache_dir / f"{cache_key}.json"

    def _validate(df: pd.DataFrame) -> bool:
        if df is None or len(df) < 20:
            return False
        if df[["open", "high", "low", "close"]].isna().any().any():
            return False
        if (df["high"] < df["low"]).any():
            return False
        # 单日涨跌幅 >25% 视为数据异常(一字板也≤20%)
        chg = df["close"].pct_change().abs()
        if (chg.dropna() > 0.25).any():
            return False
        return True

    def _to_df(rows: list) -> pd.DataFrame:
        return pd.DataFrame(rows)

    def _cache_hit() -> Optional[pd.DataFrame]:
        if cache_file.exists():
            try:
                rows = json.loads(cache_file.read_text(encoding="utf-8"))
                df = _to_df(rows)
                return df if _validate(df) else None
            except Exception:
                return None
        return None

    cached = _cache_hit()
    if cached is not None and pd.to_datetime(cached["date"]).max().date() >= end.date() - pd.Timedelta(days=10):
        return cached

    param = f"{symbol},day,{start.strftime('%Y-%m-%d')},{end.strftime('%Y-%m-%d')},640,qfq"
    df = None
    for attempt in range(12):  # 腾讯CDN多节点复权版本不一致, 每次新建Session打破粘滞
        session = requests.Session()
        session.trust_env = False
        last_error: Optional[Exception] = None
        payload = None
        for url in ["https://web.ifzq.gtimg.cn/appstock/app/fqkline/get", "http://web.ifzq.gtimg.cn/appstock/app/fqkline/get"]:
            print(f"[kline] req#{attempt + 1}: {url} param={param}")
            for _ in range(3):
                try:
                    resp = session.get(url, params={"param": param}, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                    resp.raise_for_status()
                    payload = resp.json()
                    last_error = None
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    time.sleep(0.4)
            if payload is not None:
                break
        if payload is None:
            break
        stock_payload = (payload.get("data") or {}).get(symbol) or {}
        klines = stock_payload.get("qfqday") or stock_payload.get("day") or []
        rows = []
        previous_close = None
        for item in klines:
            if len(item) < 6:
                continue
            open_price = float(item[1])
            close_price = float(item[2])
            high_price = float(item[3])
            low_price = float(item[4])
            volume = float(item[5]) * 100  # 腾讯返回单位通常为手，换算为股
            pct_chg = ((close_price - previous_close) / previous_close * 100) if previous_close else 0.0
            rows.append(
                {
                    "date": item[0],
                    "open": open_price,
                    "high": high_price,
                    "low": low_price,
                    "close": close_price,
                    "volume": volume,
                    "pctChg": pct_chg,
                }
            )
            previous_close = close_price
        candidate = pd.DataFrame(rows)
        if candidate.empty:
            break
        if _validate(candidate):
            df = candidate
            break
        print(f"[kline] 校验不通过(attempt {attempt + 1}): 行数={len(candidate)} "
              f"NaN={candidate[['open','high','low','close']].isna().sum().sum()} "
              f"h<l={(candidate['high']<candidate['low']).sum()} "
              f"chg25={int(((candidate['close'].pct_change().abs().dropna())>0.25).sum())} "
              f"chg_max={candidate['close'].pct_change().abs().max():.3f} "
              f"首={str(candidate['date'].iloc[0])[:10]} 末={str(candidate['date'].iloc[-1])[:10]}")
        time.sleep(1.0)
    if df is None:
        if cached is not None:
            print(f"[kline] 拉取/校验失败, 回退缓存 {cache_file.name}")
            return cached
        if payload is None:
            raise RuntimeError(f"腾讯真实K线请求失败: {last_error}")
        raise ValueError(f"{stock_code} 拉取数据校验失败(残缺/异常K线)")
    # 校验通过 → 写缓存(固定版本,防后续漂移)
    try:
        records = [
            {
                "date": str(row["date"])[:10],
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]),
                "pctChg": float(row.get("pctChg", 0)),
            }
            for _, row in df.iterrows()
        ]
        cache_file.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
        print(f"[kline] 已缓存 {len(records)} 行 → {cache_file.name}")
    except Exception as exc:
        print(f"[kline] 写缓存失败: {exc}")
    return df


def _patch_historical_loader_to_tencent() -> None:
    """让 StockTradingGame 初始化使用可控超时的真实腾讯 K 线。
    拉取起点自动往前推 400 天(约13个月),保证月K≥12根/周K≥50根;
    游戏起点仍从用户指定 date_start 之后找启动信号(见 _find_start_index_from_date)。"""
    def load_historical_data(self: StockTradingGame, stock_code: str, date_start: str) -> pd.DataFrame:
        today = datetime.today().strftime("%Y-%m-%d")
        try:
            ds = pd.to_datetime(str(date_start).split(" ")[0], errors="coerce")
        except Exception:
            ds = pd.NaT
        if pd.isna(ds):
            ds = pd.Timestamp.today() - pd.Timedelta(days=400)
        fetch_start = min(ds, pd.Timestamp.today() - pd.Timedelta(days=400)).strftime("%Y-%m-%d")
        data = _fetch_tencent_daily(stock_code, fetch_start, today)
        data["date"] = pd.to_datetime(data["date"])
        data = data.sort_values("date").reset_index(drop=True)
        self.date_start = ds
        return data

    def _find_start_index_from_date(self: StockTradingGame) -> int:
        """启动信号限定在用户指定 date_start 之后,不因拉取窗口前推而提前。"""
        boom_days = detect_boom_day(self.historical_data)
        ds = getattr(self, "date_start", None)
        if ds is not None and pd.notna(ds) and not boom_days.empty:
            ts = pd.Timestamp(ds)
            boom_days = boom_days[pd.to_datetime(boom_days["date"]) >= ts]
        if len(boom_days) == 0:
            if ds is not None and pd.notna(ds):
                after = self.historical_data[pd.to_datetime(self.historical_data["date"]) >= pd.Timestamp(ds)]
                return after.index[0] if not after.empty else 0
            return 0
        first_boom_date = pd.to_datetime(boom_days.iloc[0]["date"])
        boom_indices = self.historical_data[pd.to_datetime(self.historical_data["date"]) == first_boom_date].index
        if len(boom_indices) == 0:
            return 0
        start_index = int(boom_indices[0]) + 1
        return min(start_index, max(0, len(self.historical_data) - 1))

    StockTradingGame._load_historical_data = load_historical_data
    StockTradingGame._find_start_index = _find_start_index_from_date


_patch_historical_loader_to_tencent()


def _patch_limit_order_validation() -> None:
    """限价单模型: 决策在观察日(T)盘后做, 限价单在成交日(T+1)撮合。
    ①校验基准=成交日(current_data_index+1)K线范围;
    ②成交价=限价单真实撮合: 买入按 min(限价, 成交日开盘价)(开盘价低于限价→按市价成交),
      卖出按 max(限价, 成交日开盘价)——消除"观察日收盘价硬塞交易日"的成交价失真。
    用包装函数实现, 不改核心文件逻辑, 完成后恢复 current_data_index。"""
    def _wrap(action_fn):
        is_buy = "buy" in action_fn.__name__
        def wrapper(game: StockTradingGame, symbol: str, price: float, quantity: int) -> Dict[str, Any]:
            saved = int(game.current_data_index)
            n = len(game.historical_data)
            trade_idx = min(saved + 1, n - 1)
            day_open = float(game.historical_data.iloc[trade_idx]["open"])
            # 限价单真实撮合: 开盘价触及即按市价成交
            effective = min(price, day_open) if is_buy else max(price, day_open)
            game.current_data_index = trade_idx  # 校验/成交基准=成交日(T+1)
            try:
                return action_fn(game, symbol, effective, quantity)
            finally:
                game.current_data_index = saved
        wrapper.__name__ = f"patched_{action_fn.__name__}"
        return wrapper
    stg.buy_stock = _wrap(stg.buy_stock)
    stg.sell_stock = _wrap(stg.sell_stock)


_patch_limit_order_validation()


def _json_safe(value: Any) -> Any:
    """将 pandas/numpy/datetime 等对象转换成 JSON 友好格式。"""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.strftime("%Y-%m-%d %H:%M:%S") if hasattr(value, "hour") else value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if isinstance(value, pd.Series):
        return {str(k): _json_safe(v) for k, v in value.to_dict().items()}
    if isinstance(value, pd.DataFrame):
        return [_json_safe(row) for row in value.to_dict(orient="records")]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return str(value)


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def _current_price(game: StockTradingGame) -> float:
    symbol = game.game_state["current_stock"]
    current = game.game_state.get("current_prices", {}).get(symbol)
    if current is not None:
        try:
            return float(current["close"])
        except Exception:
            pass
    try:
        return float(game.historical_data.iloc[game.current_data_index]["close"])
    except Exception:
        return 0.0


def _normalize_decision(game: StockTradingGame, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """把前端输入规范化成 stock_trading_game.handle_trade 可消费的 TradingDecision。"""
    payload = payload or {}
    decision = payload.get("decision") or payload.get("action") or "不建仓"
    if decision not in {"买入", "卖出", "持有", "不建仓"}:
        decision = "不建仓"

    price = _number(payload.get("tradePrice", payload.get("price")), 0.0)
    quantity = _int(payload.get("quantity", payload.get("tradeQuantity")), 0)
    if price <= 0:
        price = _current_price(game)

    # A 股通常 100 股一手；前端传入 0 时保持非交易动作。
    if decision in {"持有", "不建仓"}:
        quantity = 0
    elif quantity <= 0:
        quantity = 100

    return {
        "reasoning": payload.get("reasoning", "Web 单步模拟输入"),
        "reasoning_abstract": payload.get("reasoning_abstract", "Web模拟"),
        "reasoning_symbol": _number(payload.get("reasoning_symbol"), 0.5),
        "decision": decision,
        "confidence": payload.get("confidence", "medium"),
        "tradePrice": price,
        "quantity": quantity,
    }


def _boom_signal_info(game: StockTradingGame) -> Dict[str, Any]:
    """计算启动阳线信号及合并明细，用于图表特殊着色。"""
    if not hasattr(game, "historical_data") or game.historical_data is None:
        return {"signals": [], "dates": []}
    try:
        boom = detect_boom_day(game.historical_data)
    except Exception:
        return {"signals": [], "dates": []}
    signals = []
    dates = set()
    for row in boom.to_dict(orient="records"):
        original = str(row.get("original_dates") or row.get("date") or "")
        original_dates = [d.strip()[:10] for d in original.split(",") if d.strip()]
        for day in original_dates:
            dates.add(day)
        signal_date = str(row.get("date", ""))[:10]
        if signal_date:
            dates.add(signal_date)
        signals.append(
            {
                "date": signal_date,
                "original_dates": original_dates,
                "merge_count": int(row.get("merge_count", 1) or 1),
                "high": _number(row.get("high"), 0),
                "low": _number(row.get("low"), 0),
                "close": _number(row.get("close"), 0),
                "volume": _number(row.get("volume"), 0),
            }
        )
    return {"signals": signals, "dates": sorted(dates)}


def _kline_window(game: StockTradingGame, before: int = 60, after: int = 0, boom_dates: Optional[set] = None, full: bool = False) -> List[Dict[str, Any]]:
    """获取当前索引附近 K 线窗口。full=True 时从数据起点显示到 current_date(防未来K线)。"""
    if not hasattr(game, "historical_data") or game.historical_data is None:
        return []
    if full:
        start = 0
        end = min(len(game.historical_data), int(game.current_data_index) + 1)
    else:
        start = max(0, int(game.current_data_index) - before + 1)
        end = min(len(game.historical_data), int(game.current_data_index) + after + 1)
    df = game.historical_data.iloc[start:end].copy()
    cols = [c for c in ["date", "open", "high", "low", "close", "volume", "pctChg"] if c in df.columns]
    rows = _json_safe(df[cols])
    boom_dates = boom_dates or set()
    for row in rows:
        row["is_boom"] = str(row.get("date", ""))[:10] in boom_dates
    return rows


def _resample_kline(game: StockTradingGame, rule: str, limit: int, boom_dates: Optional[set] = None, full: bool = False) -> List[Dict[str, Any]]:
    """从日线 historical_data 聚合出周线/月线，供 UI 绘图。
    full=True 时用全部历史上下文(截止 current_date);
    排除未完整周期桶(当月/当周未结束不输出),避免画出未来日期K线。"""
    if not hasattr(game, "historical_data") or game.historical_data is None:
        return []
    end = min(len(game.historical_data), int(game.current_data_index) + 1)
    df = game.historical_data.iloc[:end].copy()
    if df.empty or "date" not in df.columns:
        return []
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).set_index("date")
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "volume" in df.columns:
        agg["volume"] = "sum"
    resampled = df.resample(rule).agg(agg).dropna(subset=["open", "high", "low", "close"])
    # 未完整周期桶(标签>数据末日): 不删除, 将标签修正为数据末日(as-of)
    # 使 bar.date ≤ as-of(UI防未来K线原则), 保留"当月/当周至今"的半截K线而非未来日期标签
    last_trade_day = df.index.max()
    partial_flag = [False] * len(resampled)
    if not resampled.empty and pd.notna(last_trade_day):
        partial_flag = [d > last_trade_day for d in resampled.index]
        resampled = resampled.copy()
        resampled.index = pd.Index(
            [d if d <= last_trade_day else last_trade_day for d in resampled.index],
            name=resampled.index.name,
        )
    out = resampled.tail(limit).reset_index()
    if not out.empty:
        out["is_partial"] = partial_flag[-len(out):]
    if "volume" not in out.columns:
        out["volume"] = 0
    out["pctChg"] = out["close"].pct_change().fillna(0) * 100
    cols = ["date", "open", "high", "low", "close", "volume", "pctChg", "is_partial"]
    rows = _json_safe(out[cols])
    boom_dates = boom_dates or set()
    if rows and boom_dates:
        source = game.historical_data.copy()
        source["date"] = pd.to_datetime(source["date"], errors="coerce")
        source = source.dropna(subset=["date"])
        for row in rows:
            period_end = pd.to_datetime(row.get("date"), errors="coerce")
            if pd.isna(period_end):
                row["is_boom"] = False
                continue
            if rule.startswith("W"):
                period_start = period_end - pd.Timedelta(days=6)
            else:
                period_start = period_end.replace(day=1)
            period_dates = source[(source["date"] >= period_start) & (source["date"] <= period_end)]["date"].dt.strftime("%Y-%m-%d")
            row["is_boom"] = any(day in boom_dates for day in period_dates)
    else:
        for row in rows:
            row["is_boom"] = False
    return rows


def _kline_periods(game: StockTradingGame) -> Dict[str, List[Dict[str, Any]]]:
    """返回日线、周线、月线三组 K 线。"""
    boom_dates = set(_boom_signal_info(game)["dates"])
    return {
        "day": _kline_window(game, before=45, boom_dates=boom_dates, full=True),
        "week": _resample_kline(game, "W-FRI", 60, boom_dates=boom_dates, full=True),
        "month": _resample_kline(game, "M", 60, boom_dates=boom_dates, full=True),
    }


def _current_pct_change(game: StockTradingGame) -> float:
    try:
        row = game.historical_data.iloc[game.current_data_index]
        if "pctChg" in row and pd.notna(row["pctChg"]):
            return float(row["pctChg"])
        previous = game.historical_data.iloc[game.current_data_index - 1]["close"] if game.current_data_index else row["open"]
        return (float(row["close"]) - float(previous)) / float(previous) * 100 if previous else 0.0
    except Exception:
        return 0.0


def _current_market_line(game: StockTradingGame) -> str:
    return f"当前价: ¥{_current_price(game):.2f}\n当日涨跌幅: {_current_pct_change(game):+.2f}%"


def _render_portfolio_cny(game: StockTradingGame) -> str:
    """原 render_portfolio 使用 $，UI 使用人民币符号；这里统一成 ¥。"""
    return render_portfolio(game).replace("$", "¥")


def _build_ai_prompt(game: StockTradingGame) -> str:
    """构造当前模拟交易将要输入 AI 的 prompt。"""
    portfolio_result = _render_portfolio_cny(game)
    cur = str(game.game_state.get("current_date", ""))[:10]
    idx = int(getattr(game, "current_data_index", 0)) + 1
    df = getattr(game, "historical_data", None)
    if df is not None and 0 <= idx < len(df):
        next_date = str(df.iloc[idx]["date"])[:10]
    else:
        next_date = "无更多交易日(已到最后)"
    prompt = f"""
决策基准: 观察信息截止最近收盘日 {cur}(K线不含其后再交易日); 本次交易决策面向下一交易日 {next_date}, 成交价默认参考最近收盘价。
根据以下股票投资组合分析，生成交易策略：

{_current_market_line(game)}

{portfolio_result}
最终决策和关键信息用以下JSON格式输出，确保无需额外处理即可被程序解析：
{{
"decision": "买入/卖出/持有/不建仓",
"tradePrice": "买入/卖出的精确价格，不是价格范围",
"tradeQuantity":"买入/卖出的股票精确数量，不是范围",
"confidence": "高/中/低"
}}
"""
    return prompt


def _positions(game: StockTradingGame) -> List[Dict[str, Any]]:
    rows = []
    for symbol, position in game.game_state.get("portfolio", {}).items():
        current_price = 0.0
        current = game.game_state.get("current_prices", {}).get(symbol)
        if current is not None:
            try:
                current_price = float(current["close"])
            except Exception:
                current_price = 0.0
        quantity = _int(position.get("quantity"), 0)
        avg_price = _number(position.get("avg_price"), 0.0)
        market_value = quantity * current_price
        cost = quantity * avg_price
        pnl = market_value - cost
        rows.append(
            {
                "symbol": symbol,
                "quantity": quantity,
                "avg_price": avg_price,
                "current_price": current_price,
                "market_value": market_value,
                "pnl": pnl,
                "pnl_percent": (pnl / cost * 100) if cost else 0,
            }
        )
    return rows


def _snapshot(session: GameSession, include_render: bool = False) -> Dict[str, Any]:
    """生成前端展示用状态快照。"""
    game = session.game
    portfolio = get_portfolio_value(game)
    state = game.game_state
    symbol = state.get("current_stock", "")
    price = _current_price(game)
    previous = state.get("pre_prices", {}).get(symbol, price) or price
    change = price - float(previous or price)
    change_pct = _current_pct_change(game)

    snapshot = {
        "session_id": session.id,
        "created_at": session.created_at,
        "step_index": session.step_index,
        "current_index": int(getattr(game, "current_data_index", 0)),
        "total_days": int(len(getattr(game, "historical_data", []))),
        "finished": bool(getattr(game, "current_data_index", 0) >= len(getattr(game, "historical_data", [])) - 1),
        "stock": symbol,
        "current_date": state.get("current_date"),
        "current_price": price,
        "previous_price": float(previous or 0),
        "change": change,
        "change_pct": change_pct,
        "portfolio": portfolio,
        "positions": _positions(game),
        "transactions": _json_safe(state.get("transaction_history", [])),
        "kline": _kline_window(game, boom_dates=set(_boom_signal_info(game)["dates"])),
        "kline_periods": _kline_periods(game),
        "boom_signals": _boom_signal_info(game),
        "observations": {
            "day": state.get("current_day_k_observing", ""),
            "week": state.get("current_week_k_observing", ""),
            "month": state.get("current_month_k_observing", ""),
        },
        "trajectory": session.trajectory,
    }
    if include_render:
        snapshot["portfolio_text"] = _current_market_line(game) + "\n\n" + _render_portfolio_cny(game)
    return _json_safe(snapshot)


def _get_session(session_id: Optional[str] = None) -> Optional[GameSession]:
    if session_id and session_id in SESSIONS:
        return SESSIONS[session_id]
    if DEFAULT_SESSION_ID and DEFAULT_SESSION_ID in SESSIONS:
        return SESSIONS[DEFAULT_SESSION_ID]
    return None


def _default_save_dir() -> str:
    return os.path.join(SCRIPTS_DIR, "game_states")


def _persist_session(session: GameSession) -> Optional[str]:
    """把 session 完整状态(账户/索引/轨迹)持久化为 JSON 存档,供 /api/load 恢复。
    文件: game_states/session_{stock}_latest.json + 时间戳版本(不覆盖历史)。"""
    try:
        game = session.game
        stock = str(game.game_state.get("current_stock") or "unknown")
        payload = {
            "version": 2,
            "stock": stock,
            "date_start": str(getattr(game, "date_start", "")),
            "current_date": game.game_state.get("current_date"),
            "current_data_index": int(getattr(game, "current_data_index", 0)),
            "step_index": int(session.step_index),
            "game_state": _json_safe(game.game_state),
            "trajectory": _json_safe(session.trajectory),
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_dir = Path(_default_save_dir())
        save_dir.mkdir(parents=True, exist_ok=True)
        latest = save_dir / f"session_{stock}_latest.json"
        latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        snap = save_dir / f"session_{stock}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        snap.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(latest)
    except Exception as exc:
        print(f"[persist] failed: {exc}")
        return None


@app.route("/")
def index():
    return send_from_directory(os.path.dirname(__file__), "index.html")


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "sessions": len(SESSIONS), "default_session_id": DEFAULT_SESSION_ID})


@app.post("/api/init")
def init_game():
    """初始化交易游戏。已有进行中的游戏(未finish)时拒绝覆盖,除非 force=true。"""
    global DEFAULT_SESSION_ID
    payload = request.get_json(silent=True) or {}
    # 保护: 初始化后只要不 finish 就一直玩同一个 game
    force = bool(payload.get("force"))
    if not force and DEFAULT_SESSION_ID and DEFAULT_SESSION_ID in SESSIONS:
        active = SESSIONS[DEFAULT_SESSION_ID]
        if not getattr(active, "finished", False):
            cur = str(active.game.game_state.get("current_date", ""))[:10]
            return jsonify({"ok": False, "error": f"已有进行中的游戏(当前日期 {cur})。请先【结束游戏】或传 force:true 强制重新初始化。"}), 409
    stock_code = payload.get("stock_code") or payload.get("stock") or "sh.600000"
    initial_cash = _number(payload.get("initial_cash"), 100000.0)
    date_start = payload.get("date_start") or "2025-01-01"
    save_dir = payload.get("save_dir") or os.path.join(SCRIPTS_DIR, "game_states")

    # 校验:开始日期距今至少 30 天。交易模拟有约 24 个交易日预热期,
    # 日期过近时历史数据不足(只剩1条日K),图表和预热逻辑都会异常。
    try:
        ds = pd.to_datetime(str(date_start).split(" ")[0], errors="coerce")
    except Exception:
        ds = pd.NaT
    if pd.isna(ds):
        return jsonify({"ok": False, "error": f"开始日期无效: {date_start}"}), 400
    min_start = pd.Timestamp.today() - pd.Timedelta(days=30)
    if ds >= min_start:
        suggestion = (pd.Timestamp.today() - pd.Timedelta(days=90)).strftime("%Y-%m-%d")
        return jsonify({
            "ok": False,
            "error": f"开始日期 {ds.strftime('%Y-%m-%d')} 距今不足30天,模拟交易需历史数据预热(约24个交易日),否则K线数据不足。请选择更早日期,例如 {suggestion}。",
        }), 400

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(
            StockTradingGame,
            stock_code=stock_code,
            initial_cash=initial_cash,
            date_start=date_start,
            save_dir=save_dir,
        )
        try:
            game = future.result(timeout=45)
        except concurrent.futures.TimeoutError:
            executor.shutdown(wait=False, cancel_futures=True)
            return jsonify({"ok": False, "error": "初始化超时：真实行情数据源 45 秒内没有返回"}), 504
        executor.shutdown(wait=False)
        session_id = uuid.uuid4().hex[:12]
        session = GameSession(
            id=session_id,
            game=game,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        session.trajectory.append(
            {
                "step": 0,
                "type": "初始化",
                "date": game.game_state.get("current_date"),
                "message": "交易模拟已初始化",
                "decision": None,
                "trade_result": None,
                "portfolio": get_portfolio_value(game),
                "price": _current_price(game),
            }
        )
        SESSIONS[session_id] = session
        DEFAULT_SESSION_ID = session_id
        _persist_session(session)
        return jsonify({"ok": True, "data": _snapshot(session, include_render=True)})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(exc)}), 500


def finish_game():
    """结束当前游戏:标记 finished、清空默认会话、持久化存档。之后才可重新 init。"""
    global DEFAULT_SESSION_ID
    payload = request.get_json(silent=True) or {}
    session = _get_session(payload.get("session_id"))
    if not session:
        return jsonify({"ok": False, "error": "没有进行中的游戏"}), 404
    session.finished = True
    session.trajectory.append({
        "step": session.step_index,
        "type": "结束",
        "date": session.game.game_state.get("current_date"),
        "message": "游戏已结束,存档已保留",
    })
    _persist_session(session)
    if DEFAULT_SESSION_ID == session.id:
        DEFAULT_SESSION_ID = None
    return jsonify({"ok": True, "data": {"finished": True, "session_id": session.id}})


@app.post("/api/load")
def load_session_from_disk():
    """从 JSON 存档恢复游戏:重建数据+定位索引+恢复账户状态+恢复轨迹。"""
    global DEFAULT_SESSION_ID
    payload = request.get_json(silent=True) or {}
    stock_filter = payload.get("stock_code") or payload.get("stock")
    save_dir = Path(payload.get("save_dir") or _default_save_dir())
    save_dir.mkdir(parents=True, exist_ok=True)
    if stock_filter:
        files = sorted(save_dir.glob(f"session_{stock_filter}_latest.json"))
    else:
        # 未指定股票: 选最近修改的存档(跨股票)
        files = sorted(save_dir.glob("session_*_latest.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return jsonify({"ok": False, "error": "没有找到可恢复的存档"}), 404
    try:
        data = json.loads(files[0].read_text(encoding="utf-8"))
        stock = str(data.get("stock") or stock_filter)
        # 覆盖保护: 已有进行中游戏且标的与存档不同 -> 409,除非 force=true
        target_stock = stock
        if not payload.get("force") and DEFAULT_SESSION_ID and DEFAULT_SESSION_ID in SESSIONS:
            active = SESSIONS[DEFAULT_SESSION_ID]
            if not getattr(active, "finished", False):
                active_stock = str(active.game.game_state.get("current_stock", ""))
                if active_stock and target_stock and active_stock != target_stock:
                    return jsonify({"ok": False, "error": f"已有进行中的游戏({active_stock})。恢复 {target_stock} 存档会覆盖它，请先【结束游戏】或传 force:true。"}), 409
        date_start = str(data.get("date_start") or "2025-01-01").split(" ")[0]
        game = StockTradingGame(
            stock_code=stock,
            initial_cash=100000.0,
            date_start=date_start,
            save_dir=_default_save_dir(),
        )
        target = pd.to_datetime(data.get("current_date"), errors="coerce")
        if pd.notna(target):
            dates = pd.to_datetime(game.historical_data["date"])
            idx = int(dates.searchsorted(target))
            game.current_data_index = min(idx, max(0, len(game.historical_data) - 1))
        saved_state = data.get("game_state") or {}
        game.game_state.update(saved_state)
        try:
            stg._update_market_prices(game)
        except Exception as exc:
            print(f"[load] update_market_prices: {exc}")
        session = GameSession(
            id=uuid.uuid4().hex[:12],
            game=game,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        session.step_index = int(data.get("step_index", 0))
        session.trajectory = _json_safe(data.get("trajectory") or [])
        SESSIONS[session.id] = session
        DEFAULT_SESSION_ID = session.id
        _persist_session(session)
        return jsonify({"ok": True, "data": _snapshot(session, include_render=True)})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": f"恢复失败: {exc}"}), 500


@app.get("/api/state")
def get_state():
    session = _get_session(request.args.get("session_id"))
    if not session:
        return jsonify({"ok": False, "error": "还没有初始化模拟，请先调用 /api/init"}), 404
    return jsonify({"ok": True, "data": _snapshot(session, include_render=True)})


def _extract_fill_price(trade_result: Optional[Dict[str, Any]]) -> Optional[float]:
    """从 trade_result.message("成功买入 xx @ $50.04") 提取实际成交价。"""
    if not trade_result or not trade_result.get("success"):
        return None
    m = re.search(r"@ \$([\d.]+)", str(trade_result.get("message", "")))
    return float(m.group(1)) if m else None


@app.post("/api/step")
def step_once():
    """执行一次模拟：按决策交易，然后推进到下一个交易日。"""
    payload = request.get_json(silent=True) or {}
    session = _get_session(payload.get("session_id"))
    if not session:
        return jsonify({"ok": False, "error": "还没有初始化模拟，请先初始化"}), 404

    try:
        game = session.game
        before_date = game.game_state.get("current_date")
        decision = _normalize_decision(game, payload)
        # 成交前快照: 供 /api/rollback 精确回退(仅成功成交时更新)
        snapshot_before = {
            "cash_balance": game.game_state["cash_balance"],
            "portfolio": copy.deepcopy(game.game_state["portfolio"]),
            "transaction_history": copy.deepcopy(game.game_state["transaction_history"]),
        }
        trade_result = handle_trade(game, json.dumps(decision, ensure_ascii=False))
        if trade_result.get("success") and decision.get("decision") in ("买入", "卖出"):
            session.prev_snapshot = snapshot_before
        portfolio_after_trade = get_portfolio_value(game)
        advanced = next_trading_day(game)
        session.step_index += 1

        step_record = {
            "step": session.step_index,
            "type": "单步模拟",
            "date": before_date,
            "next_date": game.game_state.get("current_date"),
            "trade_date": game.game_state.get("current_date"),  # 成交日(=推进后)
            "fill_price": _extract_fill_price(trade_result),  # 实际成交价
            "decision": decision,
            "trade_result": trade_result,
            "advanced": advanced,
            "portfolio": portfolio_after_trade,
            "price": decision.get("tradePrice"),
            "current_price_after_advance": _current_price(game),
        }
        session.trajectory.append(_json_safe(step_record))
        _persist_session(session)  # 每步落盘: 买卖记录+账户+轨迹持久化
        return jsonify({"ok": True, "data": _snapshot(session, include_render=True), "step": _json_safe(step_record)})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.post("/api/advance")
def advance_only():
    """只推进交易日，不执行交易。"""
    payload = request.get_json(silent=True) or {}
    session = _get_session(payload.get("session_id"))
    if not session:
        return jsonify({"ok": False, "error": "还没有初始化模拟，请先初始化"}), 404
    try:
        advanced = next_trading_day(session.game)
        session.step_index += 1
        record = {
            "step": session.step_index,
            "type": "仅推进",
            "date": session.game.game_state.get("current_date"),
            "advanced": advanced,
            "portfolio": get_portfolio_value(session.game),
            "price": _current_price(session.game),
        }
        session.trajectory.append(_json_safe(record))
        _persist_session(session)  # 推进也落盘
        return jsonify({"ok": True, "data": _snapshot(session, include_render=True), "step": _json_safe(record)})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.post("/api/rollback")
def rollback_dispatch():
    """统一回退: ①payload 含 date/steps → 拨日期(账户/持仓不动); ②否则回退最近一笔已成交交易。"""
    payload = request.get_json(silent=True) or {}
    if payload.get("date") or payload.get("steps") is not None:
        return _rollback_to_date(payload)
    return _rollback_trade_impl(payload)


def _rollback_to_date(payload: Dict[str, Any]):
    """回退 current_data_index 到目标日期(仅拨日期与状态,账户/持仓不动)。
    用户指定 date(YYYY-MM-DD) 或 steps(往前N个交易日)。"""
    session = _get_session(payload.get("session_id"))
    if not session:
        return jsonify({"ok": False, "error": "没有进行中的游戏"}), 404
    try:
        game = session.game
        dates = pd.to_datetime(game.historical_data["date"])
        target = payload.get("date") or payload.get("to")
        if target:
            t = pd.to_datetime(str(target), errors="coerce")
            if pd.isna(t):
                return jsonify({"ok": False, "error": f"日期无效: {target}"}), 400
            idx = int(dates.searchsorted(t, side="right")) - 1  # 最后一个 ≤ 目标日
        else:
            steps = int(payload.get("steps", 1))
            idx = int(game.current_data_index) - steps
        idx = max(0, min(idx, len(game.historical_data) - 1))
        game.current_data_index = idx
        stg._update_market_prices(game)
        session.step_index = max(0, int(session.step_index) - 1)
        _persist_session(session)
        return jsonify({"ok": True, "data": _snapshot(session, include_render=True)})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": f"回退失败: {exc}"}), 500


def _rollback_trade_impl(payload: Dict[str, Any]):
    """回退最近一笔已成交交易(买入/卖出): 恢复现金/持仓/成本/交易记录到成交前, 保留日期推进。
    失败交易(价格超范围/资金不足)不会成为回退目标。"""
    session = _get_session(payload.get("session_id"))
    if not session:
        return jsonify({"ok": False, "error": "还没有初始化模拟，请先初始化"}), 404
    traj = session.trajectory
    idx = None
    for i in range(len(traj) - 1, -1, -1):
        t = traj[i]
        if t.get("type") != "单步模拟":
            continue
        dec = t.get("decision") or {}
        if dec.get("decision") not in ("买入", "卖出"):
            continue
        tr = t.get("trade_result") or {}
        if tr.get("success"):
            idx = i
            break
    if idx is None:
        return jsonify({"ok": False, "error": "没有可回退的已成交交易"}), 400
    record = traj[idx]
    dec = record.get("decision") or {}
    action = dec.get("decision")
    price = float(dec.get("tradePrice") or 0)
    qty = int(dec.get("quantity") or 0)
    symbol = str(dec.get("symbol") or session.game.game_state.get("current_stock") or "")
    gs = session.game.game_state
    prev = getattr(session, "prev_snapshot", None)
    if prev is not None:
        # 精确恢复: 成交前快照(含持仓成本 avg_price)
        gs["cash_balance"] = prev["cash_balance"]
        gs["portfolio"] = copy.deepcopy(prev["portfolio"])
        gs["transaction_history"] = copy.deepcopy(prev["transaction_history"])
    else:
        # 兜底: 反向逻辑回退
        total = price * qty
        if action == "买入":
            gs["cash_balance"] += total
            pos = gs["portfolio"].get(symbol)
            if pos:
                pos["quantity"] -= qty
                if pos["quantity"] <= 0:
                    del gs["portfolio"][symbol]
        else:
            gs["cash_balance"] -= total
            if symbol not in gs["portfolio"]:
                gs["portfolio"][symbol] = {"symbol": symbol, "quantity": qty, "avg_price": price, "timestamp": datetime.now()}
            else:
                gs["portfolio"][symbol]["quantity"] += qty
        for i in range(len(gs["transaction_history"]) - 1, -1, -1):
            t = gs["transaction_history"][i]
            if t.get("action") == action and abs(float(t.get("price", 0)) - price) < 1e-6 and int(t.get("quantity", 0)) == qty:
                del gs["transaction_history"][i]
                break
    # 截断轨迹到该笔成交之前, 步进回退; 保留 current_date(不回退日期推进)
    session.trajectory = traj[:idx]
    session.step_index = max(0, session.step_index - 1)
    session.prev_snapshot = None
    _persist_session(session)
    return jsonify({
        "ok": True,
        "data": _snapshot(session, include_render=True),
        "rollback": {
            "action": action, "symbol": symbol, "price": price, "quantity": qty,
            "current_date": gs.get("current_date"),
        },
    })


@app.get("/api/trajectory")
def trajectory():
    session = _get_session(request.args.get("session_id"))
    if not session:
        return jsonify({"ok": False, "error": "还没有初始化模拟，请先初始化"}), 404
    return jsonify({"ok": True, "data": _json_safe(session.trajectory)})


@app.get("/api/prompt")
def prompt_preview():
    session = _get_session(request.args.get("session_id"))
    if not session:
        return jsonify({"ok": False, "error": "还没有初始化模拟，请先初始化"}), 404
    prompt = _build_ai_prompt(session.game)
    return jsonify({
        "ok": True,
        "data": {
            "prompt": prompt,
            "current_date": session.game.game_state.get("current_date"),
            "current_price": _current_price(session.game),
            "change_pct": _current_pct_change(session.game),
        }
    })


@app.get("/api/kline")
def kline():
    session = _get_session(request.args.get("session_id"))
    if not session:
        return jsonify({"ok": False, "error": "还没有初始化模拟，请先初始化"}), 404
    period = request.args.get("period", "day")
    if period == "all":
        return jsonify({"ok": True, "data": _kline_periods(session.game)})
    before = _int(request.args.get("before"), 120)
    boom_dates = set(_boom_signal_info(session.game)["dates"])
    if period == "week":
        return jsonify({"ok": True, "data": _resample_kline(session.game, "W-FRI", before, boom_dates=boom_dates)})
    if period == "month":
        return jsonify({"ok": True, "data": _resample_kline(session.game, "M", before, boom_dates=boom_dates)})
    return jsonify({"ok": True, "data": _kline_window(session.game, before=before, boom_dates=boom_dates)})


if __name__ == "__main__":
    port = _int(os.environ.get("PORT"), 7860)
    # use_reloader=False: 禁用 werkzeug reloader 子进程, 防止双实例共享监听 7860 导致状态错乱
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
