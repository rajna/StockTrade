#!/usr/bin/env python3
"""
股票数据 HTTP 服务 — 封装 stock_data_fetcher

启动: python3 stock_service.py --port 8768
调用:
  curl "http://localhost:8768/kline?symbol=sh000001&start=2026-07-01&end=2026-07-18"
  curl "http://localhost:8768/quote?symbol=sh000001"
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import akshare as ak
import pandas as pd
import argparse
from datetime import datetime
import json

app = FastAPI(title="Stock Data Service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok", "service": "stock-data"}


@app.get("/kline")
def get_kline(
    symbol: str = Query("sh000001", description="股票/指数代码 (sh000001=上证, sz399001=深证)"),
    start: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end: str = Query(..., description="结束日期 YYYY-MM-DD"),
    freq: str = Query("d", description="频率: d=日线, w=周线, m=月线"),
):
    """
    获取历史K线数据。
    返回: [{"date":"2026-07-01","open":4090.76,...}, ...]
    """
    try:
        df = ak.stock_zh_index_daily(symbol=symbol)
        df['date'] = pd.to_datetime(df['date'])
        mask = (df['date'] >= start) & (df['date'] <= end)
        df = df[mask]

        if freq == 'w':
            df = df.resample('W-FRI', on='date').agg({
                'open': 'first', 'high': 'max', 'low': 'min',
                'close': 'last', 'volume': 'sum'
            }).dropna().reset_index()
        elif freq == 'm':
            df = df.resample('ME', on='date').agg({
                'open': 'first', 'high': 'max', 'low': 'min',
                'close': 'last', 'volume': 'sum'
            }).dropna().reset_index()

        records = df.to_dict(orient='records')
        for r in records:
            r['date'] = r['date'].strftime('%Y-%m-%d') if hasattr(r['date'], 'strftime') else str(r['date'])
            for k in ['open', 'high', 'low', 'close']:
                r[k] = round(float(r[k]), 2)

        return JSONResponse(content={"symbol": symbol, "count": len(records), "data": records})
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"数据获取失败: {e}")


@app.get("/quote")
def get_quote(
    symbol: str = Query("sh000001", description="股票/指数代码"),
):
    """
    获取最新行情（通过 akshare 实时接口）。
    """
    try:
        # 尝试获取最新日线（含最近交易日）
        df = ak.stock_zh_index_daily(symbol=symbol)
        df['date'] = pd.to_datetime(df['date'])
        latest = df.iloc[-1]
        return JSONResponse(content={
            "symbol": symbol,
            "date": latest['date'].strftime('%Y-%m-%d'),
            "open": round(float(latest['open']), 2),
            "high": round(float(latest['high']), 2),
            "low": round(float(latest['low']), 2),
            "close": round(float(latest['close']), 2),
            "volume": int(latest['volume']),
        })
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"行情获取失败: {e}")


@app.get("/kline/range")
def get_kline_range(
    symbol: str = Query("sh000001", description="代码"),
    before: int = Query(5, description="取目标日期前几个交易日"),
    target: str = Query(..., description="目标日期 YYYY-MM-DD"),
):
    """
    获取目标日期前N个交易日的K线（用于预测用例组装）。

    示例: /kline/range?symbol=sh000001&target=2026-07-17&before=5
    返回: {
      "target": "2026-07-17",
      "before_days": 5,
      "data_before": [...前5日K线...],
      "data_target": {...当日K线...}  // 不含当日则省略
    }
    """
    try:
        df = ak.stock_zh_index_daily(symbol=symbol)
        df['date'] = pd.to_datetime(df['date'])
        target_dt = pd.to_datetime(target)

        # 找目标日期在数据中的位置
        df = df.sort_values('date').reset_index(drop=True)
        idx = df[df['date'] == target_dt].index

        data_before = []
        data_target = None
        if len(idx) > 0:
            pos = idx[0]
            start_pos = max(0, pos - before)
            before_df = df.iloc[start_pos:pos]
            data_before = before_df.to_dict(orient='records')
            for r in data_before:
                r['date'] = r['date'].strftime('%Y-%m-%d') if hasattr(r['date'], 'strftime') else str(r['date'])
                for k in ['open', 'high', 'low', 'close']:
                    r[k] = round(float(r[k]), 2)

            tgt_row = df.iloc[pos]
            data_target = {
                "date": tgt_row['date'].strftime('%Y-%m-%d'),
                "open": round(float(tgt_row['open']), 2),
                "high": round(float(tgt_row['high']), 2),
                "low": round(float(tgt_row['low']), 2),
                "close": round(float(tgt_row['close']), 2),
                "volume": int(tgt_row['volume']),
            }
        else:
            # 目标日期不在数据中（可能是未来日期），取最近 before 个交易日
            recent = df.tail(before)
            data_before = recent.to_dict(orient='records')
            for r in data_before:
                r['date'] = r['date'].strftime('%Y-%m-%d') if hasattr(r['date'], 'strftime') else str(r['date'])
                for k in ['open', 'high', 'low', 'close']:
                    r[k] = round(float(r[k]), 2)

        result = {
            "symbol": symbol,
            "target": target,
            "before_days": before,
            "data_before": data_before,
        }
        if data_target:
            result["data_target"] = data_target
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"数据获取失败: {e}")


def _fmt_kline_records(df):
    """统一格式化K线记录: date转字符串, OHLC保留2位小数。"""
    records = df.to_dict(orient='records')
    for r in records:
        r['date'] = r['date'].strftime('%Y-%m-%d') if hasattr(r['date'], 'strftime') else str(r['date'])
        for k in ['open', 'high', 'low', 'close']:
            if k in r and r[k] is not None:
                r[k] = round(float(r[k]), 2)
        if 'volume' in r and r['volume'] is not None:
            r['volume'] = int(r['volume'])
    return records


@app.get("/kline/multi")
def get_kline_multi(
    symbol: str = Query("sh000001", description="股票/指数代码 (sh000001=上证, sz399001=深证)"),
    target: str = Query(..., description="目标日期 YYYY-MM-DD"),
    daily: int = Query(30, description="前N条日K (默认30)"),
    weekly: int = Query(18, description="前N条周K (默认18)"),
    monthly: int = Query(10, description="前N条月K (默认10)"),
):
    """
    多周期窗口: 目标日期前的 日K + 周K + 月K，一次返回（测试步骤①取数据用）。
    周K/月K由日K重采样(与 /kline 相同口径: W-FRI / ME)。
    所有窗口均【不含】目标日期当日数据（防泄漏）。

    示例: /kline/multi?symbol=sh000001&target=2026-07-17
    返回: {"symbol","target","daily":[30条],"weekly":[18条],"monthly":[10条]}
    """
    try:
        df = ak.stock_zh_index_daily(symbol=symbol)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        target_dt = pd.to_datetime(target)

        # 严格取目标日期之前的数据（防泄漏：未来日期则取全量最近）
        hist = df[df['date'] < target_dt].copy()

        # 日K窗口
        daily_records = _fmt_kline_records(hist.tail(daily))

        # 周K窗口 (W-FRI, 与 /kline 一致)。Pandas 默认用周五作周期标签，
        # 即使数据只到周二也会显示未来周五；改为周期内实际最后交易日，避免误判泄漏。
        weekly_source = hist.assign(_last_trade_date=hist['date'])
        wk = weekly_source.resample('W-FRI', on='date').agg({
            'open': 'first', 'high': 'max', 'low': 'min',
            'close': 'last', 'volume': 'sum', '_last_trade_date': 'max'
        }).dropna().reset_index(drop=True).rename(columns={'_last_trade_date': 'date'})
        weekly_records = _fmt_kline_records(wk.tail(weekly))

        # 月K窗口同样使用周期内实际最后交易日，而非名义月末标签。
        monthly_source = hist.assign(_last_trade_date=hist['date'])
        mo = monthly_source.resample('ME', on='date').agg({
            'open': 'first', 'high': 'max', 'low': 'min',
            'close': 'last', 'volume': 'sum', '_last_trade_date': 'max'
        }).dropna().reset_index(drop=True).rename(columns={'_last_trade_date': 'date'})
        monthly_records = _fmt_kline_records(mo.tail(monthly))

        return JSONResponse(content={
            "symbol": symbol,
            "target": target,
            "windows": {"daily": daily, "weekly": weekly, "monthly": monthly},
            "counts": {"daily": len(daily_records), "weekly": len(weekly_records), "monthly": len(monthly_records)},
            "daily": daily_records,
            "weekly": weekly_records,
            "monthly": monthly_records,
        })
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"数据获取失败: {e}")


@app.get("/kline/actual")
def get_kline_actual(
    symbol: str = Query("sh000001", description="股票/指数代码"),
    target: str = Query(..., description="目标日期 YYYY-MM-DD"),
):
    """
    对答案专用（测试步骤④）：target 当日实际涨跌结果，一次返回。
    direction: up/down/flat（收盘 vs 前一交易日收盘）

    示例: /kline/actual?symbol=sh000001&target=2026-07-17
    返回: {"symbol","target","prev_date","prev_close","close","change","change_pct","direction"}
    """
    try:
        df = ak.stock_zh_index_daily(symbol=symbol)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        target_dt = pd.to_datetime(target)
        idx = df[df['date'] == target_dt].index
        if len(idx) == 0:
            raise HTTPException(status_code=404, detail=f"{target} 非交易日或无数据")
        pos = idx[0]
        if pos == 0:
            raise HTTPException(status_code=404, detail="无前一交易日数据")
        tgt, prv = df.iloc[pos], df.iloc[pos - 1]
        close, prev_close = float(tgt['close']), float(prv['close'])
        change = close - prev_close
        pct = change / prev_close * 100
        return JSONResponse(content={
            "symbol": symbol,
            "target": target,
            "prev_date": prv['date'].strftime('%Y-%m-%d'),
            "prev_close": round(prev_close, 2),
            "close": round(close, 2),
            "change": round(change, 2),
            "change_pct": round(pct, 3),
            "direction": "up" if change > 0 else ("down" if change < 0 else "flat"),
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"数据获取失败: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="股票数据服务")
    parser.add_argument("--port", type=int, default=8768, help="端口 (默认 8768)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="绑定地址")
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
