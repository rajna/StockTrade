#!/usr/bin/env python3
"""
Query Chaoyang Technology (002981) stock data
"""

import sys
sys.path.insert(0, '/Users/rama/Documents/agi_nanobot/nanobot/nanobot/skills/stock-data-fetcher/scripts')

from stock_data_fetcher import (
    get_current,
    get_stock_daily_data,
    detect_boom_day,
    check_price_near_ma_safe,
    analyze_stock
)

def main():
    stock_code = 'sz.002981'
    print("=" * 80)
    print(f"朝阳科技 (002981) - 股票数据分析")
    print("=" * 80)

    # 1. 获取实时行情
    print("\n【1】实时行情数据")
    print("-" * 80)
    current_data = get_current(stock_code)
    if current_data:
        print(f"日期: {current_data[0]}")
        print(f"开盘价: ¥{float(current_data[1]):.2f}")
        print(f"最高价: ¥{float(current_data[2]):.2f}")
        print(f"最低价: ¥{float(current_data[3]):.2f}")
        print(f"收盘价: ¥{float(current_data[4]):.2f}")
        print(f"成交量: {int(current_data[5]):,} 手")
    else:
        print("无法获取实时数据")

    # 2. 获取历史K线数据
    print("\n【2】历史K线数据 (最近30个交易日)")
    print("-" * 80)
    end_date = '2026-03-14'
    start_date = '2026-02-14'
    df = get_stock_daily_data(stock_code, start_date, end_date, isCurrent=True)
    if df is not None and len(df) > 0:
        print(f"获取到 {len(df)} 天的数据")
        print("\n最近5天数据:")
        print(df.tail().to_string(index=False))
    else:
        print("无法获取历史数据")

    # 3. 技术分析
    print("\n【3】技术分析")
    print("-" * 80)

    # 3.1 放量阳线检测
    print("\n3.1 放量阳线检测 (启动放量阳线)")
    boom_days = detect_boom_day(df)
    if len(boom_days) > 0:
        print(f"发现 {len(boom_days)} 个放量阳线:")
        for _, row in boom_days.iterrows():
            print(f"  日期: {row['date']}")
            print(f"  开盘: ¥{row['open']:.2f}, 收盘: ¥{row['close']:.2f}")
            print(f"  最高: ¥{row['high']:.2f}, 最低: ¥{row['low']:.2f}")
            print(f"  成交量: {int(row['volume']):,} 手")
            if row['merged']:
                print(f"  合并天数: {row['merge_count']} 天")
            print()
    else:
        print("未发现放量阳线")

    # 3.2 移动平均线分析
    print("\n3.2 移动平均线分析")
    if len(df) >= 20:
        near_ma20 = check_price_near_ma_safe(df, 20, 2.0)
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        print(f"20日均线: ¥{ma20:.2f}")
        print(f"当前价格: ¥{df['close'].iloc[-1]:.2f}")
        print(f"价格距离20日均线: {abs((df['close'].iloc[-1] - ma20) / ma20 * 100):.2f}%")
        print(f"价格在20日均线±2%范围内: {'是' if near_ma20 else '否'}")

    if len(df) >= 60:
        near_ma60 = check_price_near_ma_safe(df, 60, 2.0)
        ma60 = df['close'].rolling(60).mean().iloc[-1]
        print(f"\n60日均线: ¥{ma60:.2f}")
        print(f"价格距离60日均线: {abs((df['close'].iloc[-1] - ma60) / ma60 * 100):.2f}%")
        print(f"价格在60日均线±2%范围内: {'是' if near_ma60 else '否'}")

    # 3.3 价格趋势分析
    print("\n3.3 价格趋势分析")
    if len(df) >= 5:
        recent_5 = df.tail(5)
        price_change_5d = (recent_5['close'].iloc[-1] - recent_5['close'].iloc[0]) / recent_5['close'].iloc[0] * 100
        print(f"近5日涨跌幅: {price_change_5d:.2f}%")
        if len(df) >= 11:
            print(f"近10日涨跌幅: {(df['close'].iloc[-1] - df['close'].iloc[-11]) / df['close'].iloc[-11] * 100:.2f}%")
        if len(df) >= 21:
            print(f"近20日涨跌幅: {(df['close'].iloc[-1] - df['close'].iloc[-21]) / df['close'].iloc[-21] * 100:.2f}%")

    # 3.4 成交量分析
    print("\n3.4 成交量分析")
    if len(df) >= 5:
        recent_5_vol = df.tail(5)['volume']
        avg_vol_5 = recent_5_vol.mean()
        current_vol = df['volume'].iloc[-1]
        vol_ratio = current_vol / avg_vol_5
        print(f"近5日平均成交量: {int(avg_vol_5):,} 手")
        print(f"当前成交量: {int(current_vol):,} 手")
        print(f"成交量倍数: {vol_ratio:.2f}x")

    # 4. 综合分析
    print("\n【4】综合分析")
    print("-" * 80)

    # 判断趋势
    if len(df) >= 20:
        ma5 = df['close'].rolling(5).mean().iloc[-1]
        ma10 = df['close'].rolling(10).mean().iloc[-1]
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        current_price = df['close'].iloc[-1]

        trend = ""
        if current_price > ma5 > ma10 > ma20:
            trend = "多头排列 - 强势上涨趋势"
        elif current_price < ma5 < ma10 < ma20:
            trend = "空头排列 - 弱势下跌趋势"
        elif current_price > ma5 and current_price > ma10:
            trend = "短期上涨"
        elif current_price < ma5 and current_price < ma10:
            trend = "短期下跌"
        else:
            trend = "震荡整理"

        print(f"趋势判断: {trend}")

    # 5. 完整分析结果
    print("\n【5】完整分析结果")
    print("-" * 80)
    results = analyze_stock(stock_code, start_date, end_date, include_current=True)
    if results['historical_data'] is not None:
        print(f"股票代码: {stock_code}")
        print(f"数据天数: {len(results['historical_data'])} 天")
        print(f"发现放量阳线: {len(results['boom_days'])} 个")
        print(f"价格在20日均线±2%范围内: {'是' if results['near_ma20'] else '否'}")
        print(f"价格在60日均线±2%范围内: {'是' if results['near_ma60'] else '否'}")
        if results['error']:
            print(f"错误信息: {results['error']}")

    print("\n" + "=" * 80)
    print("分析完成!")
    print("=" * 80)

if __name__ == '__main__':
    main()
