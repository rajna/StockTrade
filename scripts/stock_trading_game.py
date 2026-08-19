#!/usr/bin/env python3
"""
Stock Trading Game - Independent module for stock trading simulation
"""

import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, TypedDict
import traceback
import json
from game_state_manager import GameStateManager

# Import data fetching functions from stock_data_fetcher
from stock_data_fetcher import (
    get_stock_daily_data,
    detect_boom_day,
    stock_data_to_llm_string
)

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
        
        # 添加股票走势信息
        result.append("")
        result.append(f"股票{game.game_state['current_stock']}走势:")
        result.append(f"月线: {game.game_state['current_month_k_observing']}")
        result.append(f"周线: {game.game_state['current_week_k_observing']}")
        result.append(f"日线: {game.game_state['current_day_k_observing']}")
        
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
        # 价格范围校验：成交价必须落在当前交易日最高/最低价范围内，否则交易失败（防失真成交）
        current_row = game.historical_data.iloc[game.current_data_index]
        day_high = float(current_row['high'])
        day_low = float(current_row['low'])
        if price < day_low or price > day_high:
            return {
                'success': False,
                'message': f'买入价 {price:.2f} 超出当日价格范围 [{day_low:.2f}, {day_high:.2f}]，交易失败'
            }

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

        # 价格范围校验：成交价必须落在当前交易日最高/最低价范围内，否则交易失败
        current_row = game.historical_data.iloc[game.current_data_index]
        day_high = float(current_row['high'])
        day_low = float(current_row['low'])
        if price < day_low or price > day_high:
            return {
                'success': False,
                'message': f'卖出价 {price:.2f} 超出当日价格范围 [{day_low:.2f}, {day_high:.2f}]，交易失败'
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
    从历史数据中获取当前日期的价格
    """
    if game.current_data_index < len(game.historical_data):
        current_row = game.historical_data.iloc[game.current_data_index]
        pre_row = None
        if game.current_data_index != 0:
            pre_row = game.historical_data.iloc[game.current_data_index - 1]
        
        # 使用收盘价作为当前价格
        for symbol in game.available_stocks:
            print('stock', current_row)
            game.game_state['current_prices'][symbol] = current_row
            game.game_state['pre_prices'][symbol] = pre_row['close'] if pre_row is not None else current_row['open']
        
        # 更新当前日期
        if hasattr(current_row['date'], 'strftime'):
            game.game_state['current_date'] = current_row['date'].strftime('%Y-%m-%d %H:%M:%S')
        else:
            game.game_state['current_date'] = str(current_row['date'])
        
        day_end = game.game_state['current_date']
        # 交易日前一天
        before_day = get_date_before(day_end, 1)
        stock_code = game.game_state['current_stock'] 
        #获取日K
        day_start = get_date_before(day_end, 21)
        day_data = get_stock_daily_data(stock_code, day_start, before_day, 'd')
        current_day_k_observing = stock_data_to_llm_string(day_data) if day_data is not None else "日K数据不可用"
        
        #获取周K
        week_start = get_monday_x_weeks_ago(day_end, 5)
        week_data = get_stock_daily_data(stock_code, week_start, before_day, 'w')
        current_week_k_observing = stock_data_to_llm_string(week_data) if week_data is not None else "周K数据不可用"
        
        #获取月K
        month_start = get_first_day_of_month_before(day_end, 10)
        month_data = get_stock_daily_data(stock_code, month_start, before_day, 'm')
        current_month_k_observing = stock_data_to_llm_string(month_data) if month_data is not None else "月K数据不可用"
        
        game.game_state['current_day_k_observing'] = current_day_k_observing
        game.game_state['current_week_k_observing'] = current_week_k_observing
        game.game_state['current_month_k_observing'] = current_month_k_observing

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
        date_start: str = "2026-2-03 00:00:00",
        load_from_save: bool = False,
        save_dir: str = "./game_states",
        hold_period: int = 5
    ):
        # 持股周期(交易日): 当前股票持有满 hold_period 个交易日后才允许切换股票
        self.hold_period = max(1, int(hold_period))
        
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
        self.date_start = date_start  # 切换股票时按同一起点重新加载数据
        
        # Determine starting position (must have boom signal, otherwise exit)
        self.current_data_index = self._find_start_index()
        
        # Initialize game state
        self._init_game_state(stock_code, initial_cash, hold_period=self.hold_period)
        
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
            # 如果没有找到启动信号，使用第一个交易日
            return 0  # 使用第一个交易日作为启动信号
                
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
        initial_cash: float,
        hold_period: int = 5
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
            'current_month_k_observing': '',
            # 持股周期(交易日): 持有满 hold_period 个交易日后可切换股票
            'hold_period': max(1, int(hold_period)),
            # 当前股票的持有开始日期(切换股票时重置为切换当日)
            'hold_start_date': current_date,
            # 累计切换股票次数
            'stock_switch_count': 0,
            # 已切换过的股票列表(随机切换时排除,避免切回旧股)
            'switched_stocks': []
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

# ==================== Date Helper Functions ====================

def get_date_before(date_str: str, days: int) -> str:
    """
    获取指定日期前N天的日期
    
    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD HH:MM:SS'
        days: 要减去的天数
    
    Returns:
        str: 前N天的日期字符串 (YYYY-MM-DD)
    """
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        before_date = date_obj - timedelta(days=days)
        return before_date.strftime('%Y-%m-%d')
    except:
        # 如果格式解析失败，返回当前日期
        return datetime.now().strftime('%Y-%m-%d')

def get_monday_x_weeks_ago(date_str: str, weeks: int) -> str:
    """
    获取指定日期前N周的周一日期
    
    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD HH:MM:SS'
        weeks: 要减去的周数
    
    Returns:
        str: 前N周周一的日期字符串 (YYYY-MM-DD)
    """
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        # 找到当前日期的周一
        days_since_monday = date_obj.weekday()
        monday_this_week = date_obj - timedelta(days=days_since_monday)
        # 减去指定的周数
        monday_x_weeks_ago = monday_this_week - timedelta(weeks=weeks)
        return monday_x_weeks_ago.strftime('%Y-%m-%d')
    except:
        # 如果格式解析失败，返回当前日期
        return datetime.now().strftime('%Y-%m-%d')

def get_first_day_of_month_before(date_str: str, months: int) -> str:
    """
    获取指定日期前N个月的第一天
    
    Args:
        date_str: 日期字符串，格式 'YYYY-MM-DD HH:MM:SS'
        months: 要减去的月数
    
    Returns:
        str: 前N个月第一天的日期字符串 (YYYY-MM-DD)
    """
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        # 计算前N个月的第一天
        year = date_obj.year
        month = date_obj.month
        
        # 减去月份
        for _ in range(months):
            month -= 1
            if month < 1:
                month = 12
                year -= 1
        
        # 创建该月的第一天
        first_day = datetime(year, month, 1)
        return first_day.strftime('%Y-%m-%d')
    except:
        # 如果格式解析失败，返回当前日期
        return datetime.now().strftime('%Y-%m-%d')

def get_unrealized_pnl_percent(game: StockTradingGame) -> float:
    """
    获取当前未实现盈亏百分比
    
    Args:
        game: StockTradingGame实例
    
    Returns:
        float: 未实现盈亏百分比
    """
    portfolio_info = get_portfolio_value(game)
    return portfolio_info['unrealized_pnl_percent'] or 0.0

# ==================== 持股周期与股票切换 ====================

def get_hold_days(game: 'StockTradingGame') -> int:
    """
    当前股票已持有的交易日数(含持有开始日, 截止 current_date)。
    从 hold_start_date 到当前日期之间落在当前股票历史数据内的交易日计数。
    
    Args:
        game: StockTradingGame实例
    
    Returns:
        int: 已持有交易日数(至少 1)
    """
    try:
        hold_start = game.game_state.get('hold_start_date')
        if not hold_start:
            return 1
        dates = pd.to_datetime(game.historical_data['date'])
        start_dt = pd.to_datetime(hold_start)
        cur_dt = pd.to_datetime(game.game_state['current_date'])
        in_range = dates[(dates >= start_dt) & (dates <= cur_dt)]
        return max(1, len(in_range))
    except Exception:
        return 1

def can_switch_stock(game: 'StockTradingGame') -> bool:
    """
    当前股票是否达到持股周期(可以切换)。
    持有交易日数 >= hold_period 时返回 True。
    """
    period = int(game.game_state.get('hold_period', 5))
    return get_hold_days(game) >= period

def _load_stock_pool() -> pd.DataFrame:
    """
    加载 A 股股票列表(scripts/A股股票列表.csv)。
    
    Returns:
        DataFrame: 含 code(6位数字字符串)/name 两列
    """
    csv_path = Path(__file__).resolve().parent / 'A股股票列表.csv'
    if not csv_path.exists():
        raise FileNotFoundError(f'股票列表不存在: {csv_path}')
    df = pd.read_csv(csv_path)
    df['code'] = df['code'].astype(str).str.zfill(6)
    return df

def get_random_stock(exclude: Optional[List[str]] = None, n: int = 1) -> Any:
    """
    从 A 股股票列表随机选取股票代码。
    
    Args:
        exclude: 要排除的代码列表(如已切换过的股票), 格式 sh.xxxxxx/sz.xxxxxx 或裸 6 位码
        n: 选取数量
    
    Returns:
        str: n=1 时返回单个代码(如 'sh.600000'); 否则返回代码列表
    """
    df = _load_stock_pool()
    if exclude:
        exclude_codes = {str(c).split('.')[-1].zfill(6) for c in exclude if c}
        pool = df[~df['code'].isin(exclude_codes)]
        if len(pool) > 0:
            df = pool
    picked = df.sample(n=min(n, len(df)))
    codes = []
    for code in picked['code']:
        prefix = 'sh' if str(code).startswith('6') else 'sz'
        codes.append(f'{prefix}.{code}')
    return codes[0] if n == 1 else codes

def switch_stock(game: 'StockTradingGame', new_stock_code: str, force: bool = False) -> Dict[str, Any]:
    """
    切换当前交易股票到 new_stock_code。
    
    规则:
    - 当前股票持有交易日数 < hold_period 时拒绝切换(force=True 可强制)
    - 有持仓时按当前收盘价自动清仓(记录交易历史)
    - 新股票历史数据从同一 date_start 加载, 并定位到当前游戏日期(不回退不回跳)
    - 切换后 hold_start_date 重置为当前日期, 新股票重新开始计算持股周期
    - 已切换过的股票记录进 switched_stocks(随机切换时排除)
    
    Args:
        game: StockTradingGame实例
        new_stock_code: 目标股票代码(sh.xxxxxx/sz.xxxxxx)
        force: 是否跳过持股周期校验
    
    Returns:
        Dict: 切换结果
    """
    try:
        current_stock = game.game_state['current_stock']
        if not new_stock_code or new_stock_code == current_stock:
            return {'success': False, 'message': f'目标股票无效: {new_stock_code}'}
        
        # 持股周期校验
        if not force and not can_switch_stock(game):
            hold_days = get_hold_days(game)
            period = int(game.game_state.get('hold_period', 5))
            return {
                'success': False,
                'message': f'当前股票已持有 {hold_days}/{period} 个交易日, 未到持股周期, 不能切换 (force=true 可强制)'
            }
        
        current_date = game.game_state['current_date']
        old_stock = current_stock
        
        # 1) 自动清仓(按当前收盘价)
        for symbol, position in list(game.game_state['portfolio'].items()):
            price = float(game.historical_data.iloc[game.current_data_index]['close'])
            result = sell_stock(game, symbol, price, int(position['quantity']))
            if not result.get('success'):
                print(f"[switch] 清仓 {symbol} 失败: {result.get('message')}")
        
        # 2) 加载新股票历史数据(与游戏同一起点)
        start = getattr(game, 'date_start', None)
        if start is None:
            start = str(game.game_state.get('train_start_date') or current_date)
        new_data = game._load_historical_data(new_stock_code, start)
        
        # 3) 定位到当前游戏日期(最后一个 ≤ 当前日期的交易日)
        dates = pd.to_datetime(new_data['date'])
        cur_dt = pd.to_datetime(current_date)
        idx = int(dates.searchsorted(cur_dt, side='right')) - 1
        idx = max(0, min(idx, len(new_data) - 1))
        
        # 4) 更新游戏状态
        game.historical_data = new_data
        game.current_data_index = idx
        game.available_stocks = [new_stock_code]
        game.game_state['current_stock'] = new_stock_code
        game.game_state['hold_start_date'] = current_date  # 新股票重新计算持股周期
        game.game_state['stock_switch_count'] = int(game.game_state.get('stock_switch_count', 0)) + 1
        game.game_state.setdefault('switched_stocks', [])
        game.game_state['switched_stocks'].append(old_stock)
        game.id = f"{new_stock_code}:{current_date}"
        
        # 5) 刷新市场数据与日/周/月K观察文本
        _update_market_prices(game)
        
        # 6) 记录切换事件
        game.game_state['transaction_history'].append({
            'date': current_date,
            'action': '切换股票',
            'symbol': new_stock_code,
            'from_symbol': old_stock,
            'price': 0,
            'quantity': 0,
            'total': 0,
            'timestamp': datetime.now()
        })
        
        # 7) 存档
        game._auto_save()
        
        return {
            'success': True,
            'message': f'已从 {old_stock} 切换至 {new_stock_code}, 持有开始日重置为 {str(current_date)[:10]}',
            'current_stock': new_stock_code,
            'current_date': current_date,
            'hold_days': 1,
            'hold_period': int(game.game_state.get('hold_period', 5)),
            'switch_count': int(game.game_state.get('stock_switch_count', 0))
        }
    except Exception as e:
        traceback.print_exc()
        return {'success': False, 'message': f'切换股票失败: {e}'}

def random_switch_stock(game: 'StockTradingGame', force: bool = False) -> Dict[str, Any]:
    """
    随机切换当前交易股票: 从 A 股股票池随机选一只(排除当前股票与已切换过的)。
    
    Args:
        game: StockTradingGame实例
        force: 是否跳过持股周期校验
    
    Returns:
        Dict: 切换结果(同 switch_stock)
    """
    exclude = list(game.game_state.get('switched_stocks', [])) + [game.game_state['current_stock']]
    try:
        new_stock = get_random_stock(exclude=exclude, n=1)
    except Exception as e:
        return {'success': False, 'message': f'随机选股失败: {e}'}
    return switch_stock(game, new_stock, force=force)
