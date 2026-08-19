#!/usr/bin/env python3
"""
Stock Data Fetcher - Data fetching and analysis functions only
StockTradingGame has been moved to stock_trading_game.py
"""

import time
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional, List, Dict, Any, TypedDict
import traceback
import re
import json
import xml.etree.ElementTree as ET

# Import baostock for stock data
try:
    import baostock as bs
    BS_AVAILABLE = True
except ImportError:
    BS_AVAILABLE = False
    print("⚠️  baostock not installed. Install with: pip install baostock")



# ==================== Data Fetching Functions ====================

def get_current(stock_code):
    """
    将股票代码转换为新浪财经链接并获取股票数据
    
    Args:
        stock_code: 股票代码（如'sh.600000'）
    
    Returns:
        List: 格式化的股票数据 [date, open, high, low, close, volume]
    """
    formatted_data = None
    
    # 提取纯数字代码
    code = stock_code.split('.')[-1]
    
    # 判断市场（深市为sz，沪市为sh）
    if stock_code.startswith('sh'):
        market_code = 'sh'
    else:  # sz或默认
        market_code = 'sz'
        
    sector_url = f"https://finance.sina.com.cn/realstock/company/{market_code}{code}/nc.shtml"
    
    print(sector_url)
    
    try:
        # 初始化浏览器
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        from bs4 import BeautifulSoup
        
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # 无头模式
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(sector_url)
        time.sleep(5)  # 等待页面加载完成

        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        # 解析新的HTML结构 - 找到hqDetails div
        hq_details = soup.find("div", id="hqDetails")
        if not hq_details:
            print("未找到hqDetails div")
            return None
            
        table = hq_details.find("table")
        if not table:
            print("未找到表格")
            return None
        
        # 解析新的HTML结构 - 找到hqDetails div
        price = soup.find("div", id="price")
        
        currentPrice = price.get_text(strip=True)
        
        data = {}
        
        # 获取所有行
        rows = table.find_all("tr")
        
        for row in rows:
            # 获取该行所有的th和td
            ths = row.find_all("th")
            tds = row.find_all("td")
            
            # 确保有相同数量的th和td
            for i in range(min(len(ths), len(tds))):
                field_name = ths[i].get_text(strip=True).replace('：', '')
                field_value = tds[i].get_text(strip=True)
                
                # 清理字段名中的空格和特殊字符
                field_name = field_name.replace('&nbsp;', '').strip()
                
                # 存储字段
                if "开" in field_name:
                    data["open"] = field_value
                elif "高" in field_name:
                    data["high"] = field_value
                elif "低" in field_name:
                    data["low"] = field_value
                elif "收" in field_name:
                    data["close"] = currentPrice
                elif "成交量" in field_name:
                    data["volume"] = field_value
                elif "成交额" in field_name:
                    data["amount"] = field_value

        # 如果数据完整，转换为所需格式
        if all(key in data for key in ["open", "high", "low", "close", "volume"]):
            # 转换成交量（处理"万手"、"亿手"等单位）
            volume_str = data["volume"]
            
            if "万手" in volume_str:
                # 万手 -> 手 -> 股 (1手=100股)
                volume = float(volume_str.replace("万手", "")) * 10000 * 100
            elif "亿手" in volume_str:
                volume = float(volume_str.replace("亿手", "")) * 100000000 * 100
            elif "万" in volume_str:
                # 假设是万手
                volume = float(volume_str.replace("万", "")) * 10000 * 100
            elif "亿" in volume_str:
                volume = float(volume_str.replace("亿", "")) * 100000000 * 100
            elif "手" in volume_str:
                volume = float(volume_str.replace("手", "")) * 100
            else:
                # 假设已经是手数
                volume = float(volume_str) * 100

            # 使用当前日期
            current_date = datetime.now().strftime("%Y-%m-%d")

            # 格式化数据
            formatted_data = [
                current_date,
                f"{float(data['open']):.10f}",
                f"{float(data['high']):.10f}",
                f"{float(data['low']):.10f}",
                f"{float(data['close']):.10f}",
                str(int(volume))
            ]
            
    except Exception as e:
        print(f"股票代码 {stock_code} 处理出错：{e}")
    
    return formatted_data

def get_all_stocks():
    """
    获取所有A股实时行情数据（含代码和名称）
    
    Returns:
        DataFrame: 股票列表，包含code和name列
    """
    try:
        import akshare as ak
        
        # 获取实时行情数据
        # 获取A股代码与名称的映射表
        stock_spot_df = ak.stock_info_a_code_name()
        # 提取关键字段并去重
        stock_list = stock_spot_df[["code", "name"]].drop_duplicates()
        # 保存到CSV文件
        stock_list.to_csv("A股股票列表.csv", index=False, encoding="utf-8-sig")
        return stock_list
    except Exception as e:
        print(f"获取失败: {e}")
        return None

def get_stock_daily_data(stock_code, start_date='2026-1-13', end_date='2026-2-24', k_type='d', isCurrent=False):
    """
    获取单只股票的历史日线数据
    
    Args:
        stock_code: 股票代码（需带交易所前缀，如'sh.600000'）
        start_date: 开始日期（格式'YYYY-MM-DD'）
        end_date: 结束日期
        k_type: K线类型（'d'=日线, 'w'=周线, 'm'=月线）
        isCurrent: 是否包含当前实时数据
    
    Returns:
        DataFrame: 包含日期、成交量、股价等信息
    """
    # 检查 baostock 是否可用
    if not BS_AVAILABLE:
        print("⚠️  baostock not available, returning None")
        return None
    
    # 登录 baostock
    lg = bs.login()
    if lg.error_code != '0':
        print(f"Baostock login failed: {lg.error_msg}")
        return None
    
    try:
        # 查询股票日K线数据
        rs = bs.query_history_k_data_plus(
            stock_code,
            fields="date,open,high,low,close,volume,pctChg",
            start_date=start_date, end_date=end_date,
            frequency=k_type, adjustflag="2"  # 默认不复权
        )
        
        # 转换为DataFrame
        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())
        
        if isCurrent:
            current = get_current(stock_code)
            
            if current:
                data_list.append(current)
        
        df = pd.DataFrame(data_list, columns=rs.fields)
        
        # 类型转换（字符串转数值）
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'pctChg']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
        
        return df
    finally:
        # 登出 baostock
        bs.logout()

def detect_boom_day(data):
    """
    识别符合标准的启动放量阳线
    如果后一日价格创新高，合并两日K线为一个K线
    一直合并直到价格不创新高
    
    Args:
        data: 包含日期、开盘价、最高价、最低价、收盘价、成交量的DataFrame
    
    Returns:
        DataFrame: 放量阳线日期及关键参数（最高价、成交量）
    """
    # 创建数据副本，避免SettingWithCopyWarning
    data = data.copy()
    
    # 计算3日平均成交量
    data['vol_ma5'] = data['volume'].rolling(4, closed='left').mean()  # 3日均量
    data['pct_change'] = data['close'].pct_change() * 100  # 日涨幅
    
    # 找出所有满足基本条件的放量阳线
    # 修改后：添加涨停条件（涨幅>=9.9%）
    boom_criteria = ((data['pct_change'] > 3.5) & (data['volume'] > 1.35 * data['vol_ma5'])) | (data['pct_change'] >= 9.9)
    boom_indices = data[boom_criteria].index.tolist()
    boom_days_info = []
    i = 0
    n = len(boom_indices)
    
    # 遍历所有符合条件的索引
    while i < n:
        # 获取当前放量阳线的索引
        start_idx = boom_indices[i]
        
        # 初始化合并后的K线值
        merged_high = data.loc[start_idx, 'high']
        merged_low = data.loc[start_idx, 'low']
        merged_volume = data.loc[start_idx, 'volume']
        merged_open = data.loc[start_idx, 'open']
        merged_close = data.loc[start_idx, 'close']
        merged_dates = [data.loc[start_idx, 'date']]  # 记录合并的所有日期
        merged_index = i  # 记录合并的原始索引位置
        
        # 初始化合并次数
        merge_count = 1
        
        # 检查下一个交易日是否存在且是否连续
        j = start_idx + 1
        while j < len(data):
            # 获取下一个交易日的索引
            next_idx = j
            # 检查是否创新高
            if data.loc[next_idx, 'close'] >= merged_close:
                # 合并K线
                merged_high = max(merged_high, data.loc[next_idx, 'high'])
                merged_low = min(merged_low, data.loc[next_idx, 'low'])
                merged_volume = max(merged_volume, data.loc[next_idx, 'volume'])  # 取最大成交量
                merged_close = data.loc[next_idx, 'close']  # 收盘价取最后一天的收盘价
                merged_dates.append(data.loc[next_idx, 'date'])
                
                # 更新索引位置
                merged_index = j
                merge_count += 1
                j += 1
            else:
                # 不再创新高，停止合并
                break
        
        # 计算合并后的涨幅
        merged_change = ((merged_close - merged_open) / merged_open) * 100
        
        # 记录合并后的K线信息
        boom_days_info.append({
            'date': merged_dates[-1].strftime('%Y-%m-%d') if hasattr(merged_dates[-1], 'strftime') else str(merged_dates[-1]),  # 使用最后一天的日期
            'high': merged_high,
            'low': merged_low,
            'volume': merged_volume,
            'open': merged_open,
            'close': merged_close,
            'pct_change': merged_change,
            'merged': True,
            'merge_count': merge_count,
            'original_dates': ','.join([d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d) for d in merged_dates])
        })
        
        # 移动到下一个未处理的索引
        i += 1
    
    # 转换为DataFrame
    if boom_days_info:
        boom_days_df = pd.DataFrame(boom_days_info)
        
        # 保留date一样的数据中merge_count最多的那些数据
        # 按date分组，对每个date保留merge_count最大的行
        boom_days_df = boom_days_df.loc[
            boom_days_df.groupby('date')['merge_count'].idxmax()
        ].reset_index(drop=True)
        
        return boom_days_df[['date', 'high', 'low', 'close', 'volume', 'merged', 'merge_count', 'original_dates']]
    else:
        return pd.DataFrame(columns=['date', 'high', 'low', 'close', 'volume', 'merged', 'merge_count', 'original_dates'])

def is_within_n_days(target_date_str, count, reference_date_str=None):
    """
    判断目标日期是否在参考日期的count天之内
    
    Args:
        target_date_str: 目标日期字符串，格式如'2026-01-21'
        count: 天数范围
        reference_date_str: 参考日期字符串，如果不提供则使用当前日期
    
    Returns:
        bool: 如果在count天内返回True，否则返回False
    """
    # 将目标日期转换为datetime
    target_date = pd.to_datetime(target_date_str)
    
    # 获取参考日期
    if reference_date_str:
        reference_date = pd.to_datetime(reference_date_str)
    else:
        reference_date = pd.to_datetime(datetime.now().strftime('%Y-%m-%d'))
    
    # 计算日期差
    days_diff = (target_date - reference_date).days
    
    # 判断是否在count天内（包括未来day天和过去count天）
    return -count <= days_diff <= count

def check_price_near_ma_safe(df, rolling_number, threshold=2.0):
    """
    检查价格是否接近均线
    
    Args:
        df: 股票数据DataFrame
        rolling_number: 均线周期
        threshold: 阈值（百分比）
    
    Returns:
        bool: 如果价格在均线阈值范围内返回True
    """
    # 仅计算，不赋值回 df
    ma = df['close'].rolling(rolling_number).mean()

    latest_close = df.iloc[-1]['close']
    latest_ma = ma.iloc[-1]

    near_ma = False

    if latest_ma > 0:
        if abs((latest_close - latest_ma) / latest_ma) * 100 <= threshold:
            near_ma = True

    return near_ma

# ==================== LLM Integration Functions ====================

def stock_data_to_llm_string(df: pd.DataFrame, max_rows: int = 100) -> str:
    """
    将股票数据转换为LLM友好的字符串格式
    
    Args:
        df: 股票数据DataFrame
        max_rows: 最大行数
    
    Returns:
        str: LLM友好的数据字符串
    """
    if df is None or len(df) == 0:
        return "No data available"
    
    try:
        # 限制行数，但增加最大行数以确保数据完整
        if len(df) > max_rows:
            df = df.tail(max_rows)
        
        # 转换为字符串
        result = []
        result.append("股票数据摘要:")
        
        # 处理日期格式
        def format_date(date_val):
            if isinstance(date_val, str):
                return date_val
            elif hasattr(date_val, 'strftime'):
                return date_val.strftime('%Y-%m-%d')
            else:
                return str(date_val)
        
        result.append(f"数据范围: {format_date(df['date'].iloc[0])} 至 {format_date(df['date'].iloc[-1])}")
        result.append(f"数据点数: {len(df)}")
        result.append("")
        
        result.append("最新数据:")
        latest = df.iloc[-1]
        result.append(f"日期: {format_date(latest['date'])}")
        result.append(f"开盘: {latest['open']:.2f}")
        result.append(f"最高: {latest['high']:.2f}")
        result.append(f"最低: {latest['low']:.2f}")
        result.append(f"收盘: {latest['close']:.2f}")
        result.append(f"成交量: {latest['volume']:.0f}")
        result.append("")
        
        result.append("历史数据:")
        for _, row in df.iterrows():
            result.append(
                f"{format_date(row['date'])}: "
                f"开{row['open']:.2f} 高{row['high']:.2f} "
                f"低{row['low']:.2f} 收{row['close']:.2f} "
                f"量{row['volume']:.0f}"
            )
        
        return "\n".join(result)
        
    except Exception as e:
        print(f"转换数据为LLM格式失败: {e}")
        return "Data conversion failed"

# ==================== Visualization Functions ====================

def drawK(df: pd.DataFrame, dateArray: Any = None) -> None:
    """
    绘制K线图
    
    Args:
        df: 股票数据DataFrame
        dateArray: 要高亮显示的日期（字符串或列表）
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from matplotlib.font_manager import FontProperties
        from typing import Any
        
        # 检查数据
        if df is None or len(df) == 0:
            print("没有数据可绘制")
            return
        
        # 准备数据
        df = df.copy()
        df['date_num'] = mdates.date2num(df['date'])
        
        # 解析要高亮的日期
        highlight_dates = set()
        if dateArray:
            if isinstance(dateArray, str):
                # 逗号分隔的字符串
                dates = dateArray.split(',')
                highlight_dates = set(pd.to_datetime(d).strftime('%Y-%m-%d') for d in dates)
            elif isinstance(dateArray, list):
                # 列表
                highlight_dates = set(pd.to_datetime(d).strftime('%Y-%m-%d') for d in dateArray)
            elif hasattr(dateArray, 'tolist'):
                # DataFrame列
                highlight_dates = set(pd.to_datetime(d).strftime('%Y-%m-%d') for d in dateArray.tolist())
        
        # 创建图表
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 10), gridspec_kw={'height_ratios': [3, 1]})
        
        # 绘制K线
        for i, row in df.iterrows():
            date_str = row['date'].strftime('%Y-%m-%d')
            color = 'red' if row['close'] >= row['open'] else 'green'
            
            # 如果是要高亮的日期，使用紫色
            if date_str in highlight_dates:
                color = 'purple'
            
            # 绘制K线实体
            ax1.bar([row['date_num']], [abs(row['close'] - row['open'])], 
                   bottom=[min(row['open'], row['close'])], 
                   width=0.6, color=color, edgecolor='black')
            
            # 绘制上下影线
            ax1.plot([row['date_num'], row['date_num']], 
                    [row['low'], row['high']], 
                    color=color, linewidth=1)
        
        # 绘制移动平均线
        if len(df) >= 5:
            df['ma5'] = df['close'].rolling(window=5).mean()
            ax1.plot(df['date_num'], df['ma5'], label='MA5', color='blue', linewidth=1)
        
        if len(df) >= 10:
            df['ma10'] = df['close'].rolling(window=10).mean()
            ax1.plot(df['date_num'], df['ma10'], label='MA10', color='red', linewidth=1)
        
        if len(df) >= 18:
            df['ma18'] = df['close'].rolling(window=18).mean()
            ax1.plot(df['date_num'], df['ma18'], label='MA18', color='yellow', linewidth=1)
        
        # 设置主图样式
        ax1.set_title('K线图', fontsize=16, fontproperties=FontProperties(fname='/System/Library/Fonts/PingFang.ttc'))
        ax1.set_ylabel('价格', fontsize=12, fontproperties=FontProperties(fname='/System/Library/Fonts/PingFang.ttc'))
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)
        
        # 设置x轴格式
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # 绘制成交量
        for i, row in df.iterrows():
            date_str = row['date'].strftime('%Y-%m-%d')
            color = 'red' if row['close'] >= row['open'] else 'green'
            
            # 如果是要高亮的日期，使用紫色
            if date_str in highlight_dates:
                color = 'purple'
            
            ax2.bar([row['date_num']], [row['volume']], 
                   width=0.6, color=color, edgecolor='black')
        
        # 设置成交量图样式
        ax2.set_ylabel('成交量', fontsize=12, fontproperties=FontProperties(fname='/System/Library/Fonts/PingFang.ttc'))
        ax2.set_xlabel('日期', fontsize=12, fontproperties=FontProperties(fname='/System/Library/Fonts/PingFang.ttc'))
        ax2.grid(True, alpha=0.3)
        
        # 设置x轴格式
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax2.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        plt.show()
        
    except ImportError:
        print("matplotlib未安装，无法绘制K线图")
    except Exception as e:
        print(f"绘制K线图失败: {e}")
        traceback.print_exc()
