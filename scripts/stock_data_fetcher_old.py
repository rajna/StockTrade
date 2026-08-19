#!/usr/bin/env python3
"""
Stock Data Fetcher - Fixed version with GameStateManager
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
from game_state_manager import GameStateManager

# Import baostock for stock data
try:
    import baostock as bs
    BS_AVAILABLE = True
except ImportError:
    BS_AVAILABLE = False
    print("⚠️  baostock not installed. Install with: pip install baostock")

# ==================== Data Type Definitions ====================

class TradingDecision(TypedDict):
    """AI Trading Decision data type"""
    reasoning: str          # Detailed reasoning for the decision
    reasoning_abstract: str  # Abstract summary of reasoning
    reasoning_symbol: float # Confidence score (0-1)
    decision: str           # '买入', '卖出', '持有', '不建仓'
    confidence: str        # 'high', 'medium', 'low'
    tradePrice: float      # Target price for trade
    quantity: int          # Number of shares to trade

class StockPosition(TypedDict):
    """Stock Position data type"""
    symbol: str        # Stock symbol
    quantity: int      # Number of shares
    avg_price: float   # Average purchase price
    timestamp: datetime # Purchase timestamp

class TradingGame(TypedDict):
    """Trading Game state data type"""
    cash_balance: float                    # Available cash
    initial_cash: float                    # Initial cash
    portfolio: Dict[str, StockPosition]     # Current holdings
    transaction_history: List[Dict]        # Trade history
    current_prices: Dict[str, Dict]        # Current market prices
    pre_prices: Dict[str, float]          # Previous day prices
    current_date: str                      # Current trading date
    train_start_date: str                  # Training start date
    current_stock: str                    # Current trading stock
    current_day_k_observing: str          # Daily K-line data for LLM
    current_week_k_observing: str         # Weekly K-line data for LLM
    current_month_k_observing: str        # Monthly K-line data for LLM

# ==================== Data Fetching Functions ====================
def get_current(stock_code):
    formatted_data = None
    """
    将股票代码转换为新浪财经链接并获取股票数据
    """
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

# 获取所有A股实时行情数据（含代码和名称）
def get_all_stocks():
    try:
        # 获取实时行情数据 [1,4](@ref)
        # 获取A股代码与名称的映射表
        stock_spot_df = ak.stock_info_a_code_name()
        # 提取关键字段并去重 [1,4](@ref)
        stock_list = stock_spot_df[["code", "name"]].drop_duplicates()
        # 保存到CSV文件
        stock_list.to_csv("A股股票列表.csv", index=False, encoding="utf-8-sig")
        return stock_list
    except Exception as e:
        print(f"获取失败: {e}")
        return None
def get_stock_daily_data(stock_code, start_date='2026-1-13', end_date='2026-2-24', k_type='d', isCurrent= False):
    """
    获取单只股票的历史日线数据
    :param stock_code: 股票代码（需带交易所前缀，如'sh.600000'）
    :param start_date: 开始日期（格式'YYYY-MM-DD'）
    :param end_date: 结束日期
    :return: DataFrame包含日期、成交量、股价等信息
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
        
        if isCurrent == True:
            current = get_current(stock_code)
            
            if current:
                data_list.append(current)
        
        df = pd.DataFrame(data_list, columns=rs.fields)
        
        # 类型转换（字符串转数值）
        numeric_cols = ['open', 'high', 'low', 'close', 'volume','pctChg']
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
    :param data: 包含日期、开盘价、最高价、最低价、收盘价、成交量的DataFrame
    :return: 放量阳线日期及关键参数（最高价、成交量）
    """
    # 创建数据副本，避免SettingWithCopyWarning
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



def is_within_n_days(target_date_str, count ,reference_date_str=None):
    """
    判断目标日期是否在参考日期的7天之内
    
    Args:
        target_date_str: 目标日期字符串，格式如'2026-01-21'
        reference_date_str: 参考日期字符串，如果不提供则使用当前日期
    
    Returns:
        bool: 如果在7天内返回True，否则返回False
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

# 计算均线
def check_price_near_ma_safe(df, rolling_number, threshold=2.0):
    """
    不修改原 DataFrame，仅计算并返回结果。
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

def stock_data_to_llm_string(df: pd.DataFrame, max_rows: int = 30) -> str:
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
        # 限制行数
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

# ==================== Portfolio Management Functions ====================

def get_portfolio_value(game: 'StockTradingGame') -> Dict[str, Any]:
    """
    计算投资组合价值
    
    Args:
        game: StockTradingGame实例
    
    Returns:
        Dict: 投资组合信息
    """
    try:
        portfolio_value = 0.0
        cost_value = 0.0
        
        for symbol, position in game.game_state['portfolio'].items():
            if symbol in game.game_state['current_prices']:
                current_price = game.game_state['current_prices'][symbol]['close']
                position_value = position['quantity'] * current_price
                portfolio_value += position_value
                cost_value += position['quantity'] * position['avg_price']
        
        total_value = game.game_state['cash_balance'] + portfolio_value
        unrealized_pnl = portfolio_value - cost_value
        unrealized_pnl_percent = (unrealized_pnl / cost_value * 100) if cost_value > 0 else 0
        
        return {
            'cash_balance': game.game_state['cash_balance'],
            'portfolio_value': portfolio_value,
            'total_value': total_value,
            'cost_value': cost_value,
            'unrealized_pnl': unrealized_pnl,
            'unrealized_pnl_percent': unrealized_pnl_percent,
            'initial_cash': game.game_state['initial_cash'],
            'total_return': ((total_value - game.game_state['initial_cash']) / game.game_state['initial_cash'] * 100) if game.game_state['initial_cash'] > 0 else 0
        }
        
    except Exception as e:
        print(f"计算投资组合价值失败: {e}")
        return {
            'cash_balance': 0,
            'portfolio_value': 0,
            'total_value': 0,
            'cost_value': 0,
            'unrealized_pnl': 0,
            'unrealized_pnl_percent': 0,
            'initial_cash': 0,
            'total_return': 0
        }

def render_portfolio(game: 'StockTradingGame') -> str:
    """
    渲染投资组合状态
    
    Args:
        game: StockTradingGame实例
    
    Returns:
        str: 投资组合状态字符串
    """
    try:
        portfolio_info = get_portfolio_value(game)
        
        result = []
        result.append("=" * 50)
        result.append("投资组合状态")
        result.append("=" * 50)
        result.append(f"当前日期: {game.game_state['current_date']}")
        result.append(f"当前股票: {game.game_state['current_stock']}")
        result.append("")
        result.append(f"现金余额: ${portfolio_info['cash_balance']:,.2f}")
        result.append(f"持仓市值: ${portfolio_info['portfolio_value']:,.2f}")
        result.append(f"总资产: ${portfolio_info['total_value']:,.2f}")
        result.append(f"持仓成本: ${portfolio_info['cost_value']:,.2f}")
        result.append(f"未实现盈亏: ${portfolio_info['unrealized_pnl']:,.2f} ({portfolio_info['unrealized_pnl_percent']:+.2f}%)")
        result.append(f"总收益率: {portfolio_info['total_return']:+.2f}%")
        result.append("")
        
        if len(game.game_state['portfolio']) > 0:
            result.append("持仓明细:")
            result.append("-" * 50)
            for symbol, position in game.game_state['portfolio'].items():
                if symbol in game.game_state['current_prices']:
                    current_price = game.game_state['current_prices'][symbol]['close']
                    pnl = (current_price - position['avg_price']) * position['quantity']
                    pnl_pct = ((current_price - position['avg_price']) / position['avg_price'] * 100) if position['avg_price'] > 0 else 0
                    
                    result.append(
                        f"{symbol}: {position['quantity']}股 "
                        f"@ ${position['avg_price']:.2f} "
                        f"→ ${current_price:.2f} "
                        f"({pnl:+.2f}, {pnl_pct:+.2f}%)"
                    )
        else:
            result.append("当前无持仓")
        
        result.append("")
        result.append(f"交易次数: {len(game.game_state['transaction_history'])}")
        result.append("=" * 50)
        
        return "\n".join(result)
        
    except Exception as e:
        print(f"渲染投资组合状态失败: {e}")
        return "Portfolio rendering failed"

# ==================== Trading Operation Functions ====================

def buy_stock(game: 'StockTradingGame', symbol: str, price: float, quantity: int) -> Dict[str, Any]:
    """
    买入股票
    
    Args:
        game: StockTradingGame实例
        symbol: 股票代码
        price: 买入价格
        quantity: 买入数量
    
    Returns:
        Dict: 交易结果
    """
    try:
        total_cost = price * quantity
        
        # 检查资金是否足够
        if total_cost > game.game_state['cash_balance']:
            return {
                'success': False,
                'message': f'资金不足，需要 ${total_cost:,.2f}，可用 ${game.game_state["cash_balance"]:,.2f}'
            }
        
        # 扣除资金
        game.game_state['cash_balance'] -= total_cost
        
        # 更新持仓
        if symbol in game.game_state['portfolio']:
            # 已有持仓，计算新的平均成本
            old_position = game.game_state['portfolio'][symbol]
            old_cost = old_position['quantity'] * old_position['avg_price']
            new_cost = old_cost + total_cost
            new_quantity = old_position['quantity'] + quantity
            new_avg_price = new_cost / new_quantity
            
            game.game_state['portfolio'][symbol] = {
                'symbol': symbol,
                'quantity': new_quantity,
                'avg_price': new_avg_price,
                'timestamp': datetime.now()
            }
        else:
            # 新建持仓
            game.game_state['portfolio'][symbol] = {
                'symbol': symbol,
                'quantity': quantity,
                'avg_price': price,
                'timestamp': datetime.now()
            }
        
        # 记录交易
        game.game_state['transaction_history'].append({
            'date': game.game_state['current_date'],
            'action': '买入',
            'symbol': symbol,
            'price': price,
            'quantity': quantity,
            'total': total_cost,
            'timestamp': datetime.now()
        })
        
        return {
            'success': True,
            'message': f'成功买入 {symbol} {quantity}股 @ ${price:.2f}'
        }
        
    except Exception as e:
        print(f"买入股票失败: {e}")
        return {
            'success': False,
            'message': f'买入失败: {str(e)}'
        }

def sell_stock(game: 'StockTradingGame', symbol: str, price: float, quantity: int) -> Dict[str, Any]:
    """
    卖出股票
    
    Args:
        game: StockTradingGame实例
        symbol: 股票代码
        price: 卖出价格
        quantity: 卖出数量
    
    Returns:
        Dict: 交易结果
    """
    try:
        # 检查持仓是否足够
        if symbol not in game.game_state['portfolio']:
            return {
                'success': False,
                'message': f'没有 {symbol} 的持仓'
            }
        
        position = game.game_state['portfolio'][symbol]
        if quantity > position['quantity']:
            return {
                'success': False,
                'message': f'持仓不足，持有 {position["quantity"]}股，要卖出 {quantity}股'
            }
        
        total_value = price * quantity
        
        # 增加资金
        game.game_state['cash_balance'] += total_value
        
        # 更新持仓
        if quantity == position['quantity']:
            # 全部卖出
            del game.game_state['portfolio'][symbol]
        else:
            # 部分卖出
            game.game_state['portfolio'][symbol]['quantity'] -= quantity
        
        # 记录交易
        game.game_state['transaction_history'].append({
            'date': game.game_state['current_date'],
            'action': '卖出',
            'symbol': symbol,
            'price': price,
            'quantity': quantity,
            'total': total_value,
            'timestamp': datetime.now()
        })
        
        return {
            'success': True,
            'message': f'成功卖出 {symbol} {quantity}股 @ ${price:.2f}'
        }
        
    except Exception as e:
        print(f"卖出股票失败: {e}")
        return {
            'success': False,
            'message': f'卖出失败: {str(e)}'
        }

def hold_position(game: 'StockTradingGame', symbol: str) -> Dict[str, Any]:
    """
    持有仓位
    
    Args:
        game: StockTradingGame实例
        symbol: 股票代码
    
    Returns:
        Dict: 操作结果
    """
    try:
        # 记录操作
        game.game_state['transaction_history'].append({
            'date': game.game_state['current_date'],
            'action': '持有',
            'symbol': symbol,
            'price': 0,
            'quantity': 0,
            'total': 0,
            'timestamp': datetime.now()
        })
        
        return {
            'success': True,
            'message': f'持有 {symbol} 仓位'
        }
        
    except Exception as e:
        print(f"持有仓位失败: {e}")
        return {
            'success': False,
            'message': f'持有失败: {str(e)}'
        }

def no_position(game: 'StockTradingGame', symbol: str) -> Dict[str, Any]:
    """
    不建仓
    
    Args:
        game: StockTradingGame实例
        symbol: 股票代码
    
    Returns:
        Dict: 操作结果
    """
    try:
        # 记录操作
        game.game_state['transaction_history'].append({
            'date': game.game_state['current_date'],
            'action': '不建仓',
            'symbol': symbol,
            'price': 0,
            'quantity': 0,
            'total': 0,
            'timestamp': datetime.now()
        })
        
        return {
            'success': True,
            'message': f'不建仓 {symbol}'
        }
        
    except Exception as e:
        print(f"不建仓失败: {e}")
        return {
            'success': False,
            'message': f'不建仓失败: {str(e)}'
        }

def handle_trade(game: 'StockTradingGame', decision_str: str) -> Dict[str, Any]:
    """
    处理交易决策
    
    Args:
        game: StockTradingGame实例
        decision_str: 决策字符串（JSON格式的TradingDecision）
    
    Returns:
        Dict: 交易结果
    """
    try:
        # 解析决策
        decision = json.loads(decision_str)
        
        symbol = game.game_state['current_stock']
        action = decision.get('decision', '持有')
        price = decision.get('tradePrice', 0)
        quantity = decision.get('quantity', 0)
        
        # 根据决策执行交易
        if action == '买入':
            if price <= 0 or quantity <= 0:
                return {
                    'success': False,
                    'message': '买入价格或数量无效'
                }
            return buy_stock(game, symbol, price, quantity)
        elif action == '卖出':
            if price <= 0 or quantity <= 0:
                return {
                    'success': False,
                    'message': '卖出价格或数量无效'
                }
            return sell_stock(game, symbol, price, quantity)
        elif action == '持有':
            return hold_position(game, symbol)
        elif action == '不建仓':
            return no_position(game, symbol)
        else:
            return {
                'success': False,
                'message': f'未知决策: {action}'
            }
        
    except json.JSONDecodeError:
        return {
            'success': False,
            'message': '决策格式错误，需要JSON格式'
        }
    except Exception as e:
        print(f"处理交易决策失败: {e}")
        return {
            'success': False,
            'message': f'处理失败: {str(e)}'
        }

# ==================== Game Control Functions ====================

def next_trading_day(game: 'StockTradingGame') -> bool:
    """
    进入下一个交易日
    
    Args:
        game: StockTradingGame实例
    
    Returns:
        bool: True表示成功进入下一个交易日，False表示没有更多交易日
    """
    try:
        # 检查是否还有下一个交易日
        if game.current_data_index >= len(game.historical_data) - 1:
            return False
        
        # 移动到下一个交易日
        game.current_data_index += 1
        
        # 更新当前日期
        current_date = pd.to_datetime(
            game.historical_data.iloc[game.current_data_index]['date']
        ).strftime('%Y-%m-%d %H:%M:%S')
        game.game_state['current_date'] = current_date
        
        # 更新市场数据
        _update_market_prices(game)
        
        # 自动保存
        game._auto_save()
        
        return True
        
    except Exception as e:
        print(f"进入下一个交易日失败: {e}")
        return False

def check_trade_finished(game: 'StockTradingGame', trade_count: int) -> bool:
    """
    检查交易是否应该结束
    
    Args:
        game: StockTradingGame实例
        trade_count: 当前交易次数
    
    Returns:
        bool: True表示应该结束交易
    """
    try:
        # 获取投资组合信息
        portfolio_info = get_portfolio_value(game)
        
        # 检查止损条件（亏损超过5%）
        if portfolio_info['unrealized_pnl_percent'] <= -5:
            print(f"⚠️  触发止损: 亏损 {portfolio_info['unrealized_pnl_percent']:.2f}%")
            return True
        
        # 检查止盈条件（盈利超过10%）
        if portfolio_info['unrealized_pnl_percent'] >= 10:
            print(f"🎉 触发止盈: 盈利 {portfolio_info['unrealized_pnl_percent']:.2f}%")
            return True
        
        # 检查是否到达数据末尾
        if game.current_data_index >= len(game.historical_data) - 1:
            print("🏁 到达数据末尾")
            return True
        
        # 检查交易次数限制
        if trade_count >= 10:
            print(f"🔄 达到最大交易次数: {trade_count}")
            return True
        
        return False
        
    except Exception as e:
        print(f"检查交易结束条件失败: {e}")
        return False

# ==================== Helper Functions ====================

def _update_market_prices(game: 'StockTradingGame') -> None:
    """
    更新市场价格
    
    Args:
        game: StockTradingGame实例
    """
    try:
        # 获取当前交易日的数据
        current_data = game.historical_data.iloc[game.current_data_index]
        
        # 更新当前价格
        game.game_state['current_prices'][game.game_state['current_stock']] = {
            'date': current_data['date'],
            'open': current_data['open'],
            'high': current_data['high'],
            'low': current_data['low'],
            'close': current_data['close'],
            'volume': current_data['volume']
        }
        
        # 更新前一交易日价格
        if game.current_data_index > 0:
            prev_data = game.historical_data.iloc[game.current_data_index - 1]
            game.game_state['pre_prices'][game.game_state['current_stock']] = prev_data['close']
        else:
            game.game_state['pre_prices'][game.game_state['current_stock']] = current_data['open']
        
    except Exception as e:
        print(f"更新市场价格失败: {e}")

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

# ==================== StockTradingGame Class ====================

class StockTradingGame:
    """
    股票交易模拟游戏
    
    必须从启动信号后的交易日开始
    """
    
    def __init__(
        self,
        stock_code: str,
        initial_cash: float = 100000.0,
        date_start: str = "2015-12-03 00:00:00",
        load_from_save: bool = False,
        save_dir: str = "./game_states"
    ):
        # Initialize GameStateManager
        self.state_manager = GameStateManager(save_dir)
        
        # Generate game ID
        self.game_id = f"{stock_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Try to load saved state if requested
        if load_from_save:
            loaded_state = self.state_manager.load_game_state(stock_code)
            if loaded_state:
                print(f"📂 Loaded saved game state for {stock_code}")
                self._load_from_saved_state(loaded_state)
                return
        
        # Load historical data
        self.historical_data = self._load_historical_data(stock_code, date_start)
        
        # Determine starting position (must have boom signal, otherwise exit)
        self.current_data_index = self._find_start_index()
        
        # Initialize game state
        self._init_game_state(stock_code, initial_cash)
        
        # Update market data
        _update_market_prices(self)
        
        # Auto-save initial state
        self._auto_save()
        
        print(f"🎮 New game started: {self.game_id}")
        print(f"💰 Initial cash: ${initial_cash:,.2f}")
        print(f"📊 Current stock: {stock_code}")
        print(f"📅 Start date: {self.game_state['current_date']}")
    
    def _load_historical_data(
        self,
        stock_code: str,
        date_start: str
    ) -> pd.DataFrame:
        """加载历史K线数据"""
        today = datetime.today().strftime('%Y-%m-%d')
        # 确保日期格式正确
        if ' ' in date_start:
            date_start = date_start.split(' ')[0]
        
        data = get_stock_daily_data(stock_code, date_start, today, 'd')
        
        if data is None:
            raise ValueError(f"无法获取股票 {stock_code} 的数据")
        
        try:
            if len(data) <= 1:
                raise ValueError(f"股票 {stock_code} 数据不足")
        except (TypeError, AttributeError):
            raise ValueError(f"股票 {stock_code} 数据格式错误")
        
        data['date'] = pd.to_datetime(data['date'])
        data = data.sort_values('date').reset_index(drop=True)
        
        return data
    
    def _find_start_index(self) -> int:
        """
        找到起始索引（必须有启动信号）
        
        Returns:
            起始索引
        
        Raises:
            ValueError: 无启动信号或索引越界时抛出
        """
        # 检测启动信号
        boom_days = detect_boom_day(self.historical_data)
        
        # ========== 无启动信号，直接退出 ==========
        if len(boom_days) == 0:
            raise ValueError(
                f"股票数据期间无启动信号，跳过"
            )
        
        # 获取第一个启动信号
        first_boom_date = pd.to_datetime(boom_days.iloc[0]['date'])
        
        # 查找索引
        boom_indices = self.historical_data[
            self.historical_data['date'] == first_boom_date
        ].index
        
        if len(boom_indices) == 0:
            raise ValueError(f"无法定位启动信号日期")
        
        # 启动信号后一个交易日
        start_index = boom_indices[0] + 1
        
        # 检查越界
        if start_index >= len(self.historical_data):
            raise ValueError(f"启动信号后无交易日")
        
        return start_index
    
    def _init_game_state(
        self,
        stock_code: str,
        initial_cash: float
    ) -> None:
        """初始化游戏状态"""
        current_date = pd.to_datetime(
            self.historical_data.iloc[self.current_data_index]['date']
        ).strftime('%Y-%m-%d %H:%M:%S')
        
        self.game_state: TradingGame = {
            'cash_balance': initial_cash,
            'initial_cash': initial_cash,
            'portfolio': {},
            'transaction_history': [],
            'current_prices': {},
            'pre_prices': {},
            'current_date': current_date,
            'current_stock': stock_code,
            'train_start_date': current_date,
            'current_day_k_observing': '',
            'current_week_k_observing': '',
            'current_month_k_observing': ''
        }
        
        self.available_stocks = [stock_code]
        self.id = f"{stock_code}:{current_date}"
        
        # Auto-save settings
        self.auto_save_enabled = True
        self.last_save_time = None
    
    # GameState Management Methods
    def _load_from_saved_state(self, loaded_state: Dict[str, Any]) -> None:
        """
        Load game state from saved state
        
        Args:
            loaded_state: Loaded state dictionary
        """
        # This is a simplified implementation
        # In a real implementation, you would parse the full state
        print("⚠️  Full state loading not implemented yet")
        print("   Starting fresh game instead")
        
        # For now, start fresh game
        self._init_game_state(self.game_state['current_stock'], self.game_state['initial_cash'])
    
    def _auto_save(self) -> None:
        """
        Auto-save current game state
        """
        if not self.auto_save_enabled:
            return
        
        try:
            self.state_manager.save_game_state(
                self.game_state, 
                self.game_state['current_stock'],
                auto_save=True
            )
            self.last_save_time = datetime.now()
            print(f"💾 Auto-saved game state at {self.last_save_time.strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"⚠️  Auto-save failed: {e}")
    
    def save_game_state(self, description: str = "Manual save") -> str:
        """
        Manually save current game state
        
        Args:
            description: Description for the save
            
        Returns:
            Path to the saved file
        """
        try:
            filepath = self.state_manager.save_game_state(
                self.game_state,
                self.game_state['current_stock'],
                auto_save=False
            )
            print(f"💾 Game state saved: {description}")
            print(f"📁 File: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ Save failed: {e}")
            raise
    
    def load_game_state(self, game_id: str = None) -> bool:
        """
        Load game state from saved file
        
        Args:
            game_id: Game ID to load, None for latest
            
        Returns:
            True if loading was successful
        """
        try:
            if game_id is None:
                game_id = self.game_state['current_stock']
            
            loaded_state = self.state_manager.load_game_state(game_id)
            if loaded_state:
                self._load_from_saved_state(loaded_state)
                print(f"📂 Game state loaded for {game_id}")
                return True
            else:
                print(f"❌ No saved state found for {game_id}")
                return False
        except Exception as e:
            print(f"❌ Load failed: {e}")
            return False
    
    def list_game_states(self, game_id: str = None) -> List[Dict[str, Any]]:
        """
        List saved game states
        
        Args:
            game_id: Game ID to filter, None for all
            
        Returns:
            List of game state info dictionaries
        """
        return self.state_manager.list_game_states(game_id)
    
    def cleanup_old_files(self, game_id: str = None, keep_latest: int = 10) -> int:
        """
        Clean up old game state files
        
        Args:
            game_id: Game ID to clean, None for all
            keep_latest: Number of latest files to keep
            
        Returns:
            Number of files deleted
        """
        return self.state_manager.cleanup_old_files(game_id, keep_latest)
    
    def create_backup(self) -> str:
        """
        Create a backup of current game state
        
        Returns:
            Path to the backup file
        """
        return self.state_manager.create_backup(self.game_state['current_stock'])
    
    def enable_auto_save(self, enabled: bool = True) -> None:
        """
        Enable or disable auto-save
        
        Args:
            enabled: Whether to enable auto-save
        """
        self.auto_save_enabled = enabled
        if enabled:
            print("🔄 Auto-save enabled")
        else:
            print("⏸️  Auto-save disabled")
    
    def get_save_info(self) -> Dict[str, Any]:
        """
        Get information about current save state
        
        Returns:
            Dictionary with save information
        """
        return {
            'game_id': self.game_id,
            'auto_save_enabled': self.auto_save_enabled,
            'last_save_time': self.last_save_time,
            'current_stock': self.game_state['current_stock'],
            'current_date': self.game_state['current_date'],
            'cash_balance': self.game_state['cash_balance'],
            'portfolio_size': len(self.game_state['portfolio']),
            'transaction_count': len(self.game_state['transaction_history'])
        }

# ... (keep all the remaining functions)