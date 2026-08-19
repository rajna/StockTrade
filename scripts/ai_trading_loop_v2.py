#!/usr/bin/env python3
"""
AI驱动的自动交易循环系统 v2.0
基于抽象AI策略生成器，支持多种AI实现方式
"""

import json
import time
from abc import ABC, abstractmethod
from typing import Dict, Any
from stock_trading_game import StockTradingGame, next_trading_day, handle_trade, render_portfolio, get_unrealized_pnl_percent

class AIStrategyGenerator(ABC):
    """AI策略生成器抽象基类"""
    
    @abstractmethod
    def generate_strategy(self, portfolio_result: str, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据投资组合分析生成交易策略
        
        Args:
            portfolio_result: render_portfolio()的返回值
            game_state: 当前游戏状态
            
        Returns:
            Dict: 交易策略，包含decision, tradePrice, tradeQuantity, confidence
        """
        pass

class MockAIStrategyGenerator(AIStrategyGenerator):
    """模拟AI策略生成器（用于测试）"""
    
    def generate_strategy(self, portfolio_result: str, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """生成模拟交易策略"""
        return {
            "decision": "不建仓",
            "tradePrice": "0.00",
            "tradeQuantity": "0",
            "confidence": "中"
        }

class HookBasedAIStrategyGenerator(AIStrategyGenerator):
    """基于Hook的AI策略生成器"""
    
    def __init__(self, hook_system=None):
        """
        初始化Hook-based AI策略生成器
        
        Args:
            hook_system: Hook系统实例（如果可用）
        """
        self.hook_system = hook_system
    
    def generate_strategy(self, portfolio_result: str, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        通过Hook系统生成交易策略
        
        Args:
            portfolio_result: render_portfolio()的返回值
            game_state: 当前游戏状态
            
        Returns:
            Dict: 交易策略
        """
        # 构建hook上下文
        hook_context = {
            "portfolio_result": portfolio_result,
            "game_state": game_state,
            "request_type": "generate_trading_strategy"
        }
        
        # 如果hook系统可用，调用hook
        if self.hook_system:
            try:
                # 调用hook系统
                result = self.hook_system.call_hook("generate_trading_strategy", hook_context)
                
                # 解析hook返回的策略
                if result and "strategy" in result:
                    return result["strategy"]
            except Exception as e:
                print(f"Hook调用失败: {e}")
        
        # 如果hook不可用或失败，返回默认策略
        return {
            "decision": "不建仓",
            "tradePrice": "0.00",
            "tradeQuantity": "0",
            "confidence": "中"
        }

class AITradingLoop:
    """AI驱动的自动交易循环系统"""
    
    def __init__(self, stock_code='sz.002261', initial_cash=100000.0, date_start='2026-02-24', 
                 ai_generator: AIStrategyGenerator = None):
        """
        初始化AI交易循环系统
        
        Args:
            stock_code: 股票代码
            initial_cash: 初始资金
            date_start: 开始日期
            ai_generator: AI策略生成器实例
        """
        self.stock_code = stock_code
        self.initial_cash = initial_cash
        self.date_start = date_start
        self.ai_generator = ai_generator or MockAIStrategyGenerator()
        self.game = None
        self.cycle_count = 0
        self.trading_history = []
        
    def initialize_game(self):
        """创建StockTradingGame实例"""
        print(f"🎮 创建StockTradingGame实例...")
        print(f"股票代码: {self.stock_code}")
        print(f"初始资金: ${self.initial_cash:,.2f}")
        print(f"开始日期: {self.date_start}")
        
        self.game = StockTradingGame(
            stock_code=self.stock_code,
            initial_cash=self.initial_cash,
            date_start=self.date_start
        )
        
        print("✅ StockTradingGame实例创建成功")
        return self.game
    
    def get_portfolio_analysis(self):
        """执行render_portfolio()方法获取投资组合分析"""
        print(f"\n📊 执行render_portfolio()方法...")
        portfolio_result = render_portfolio(self.game)
        print("✅ render_portfolio()执行完成")
        return portfolio_result
    
    def request_ai_strategy(self, portfolio_result):
        """
        请求AI生成交易策略
        
        Args:
            portfolio_result: render_portfolio()的返回值
            
        Returns:
            Dict: AI生成的交易策略
        """
        print(f"\n🧠 请求AI生成交易策略...")
        print("📋 当前投资组合分析:")
        print(portfolio_result)
        
        # 获取当前游戏状态
        game_state = self.game.game_state
        
        # 调用AI策略生成器
        ai_strategy = self.ai_generator.generate_strategy(portfolio_result, game_state)
        
        print(f"📊 AI生成的交易策略:")
        print(f"  决策: {ai_strategy['decision']}")
        print(f"  价格: ${ai_strategy['tradePrice']}")
        print(f"  数量: {ai_strategy['tradeQuantity']}股")
        print(f"  信心度: {ai_strategy['confidence']}")
        
        return ai_strategy
    
    def execute_trade(self, strategy):
        """根据AI策略执行handle_trade()"""
        print(f"\n💼 执行handle_trade()...")
        strategy_str = json.dumps(strategy)
        trade_result = handle_trade(self.game, strategy_str)
        print(f"✅ handle_trade()执行结果: {trade_result}")
        return trade_result
    
    def get_current_pnl(self):
        """获取当前收益率"""
        print(f"\n📈 获取当前收益率...")
        try:
            pnl_percent = get_unrealized_pnl_percent(self.game)
            print(f"当前收益率: {pnl_percent:.2f}%")
            return pnl_percent
        except Exception as e:
            print(f"获取收益率失败: {e}")
            return 0.0
    
    def advance_to_next_day(self):
        """执行next_trading_day()推进到下一个交易日"""
        print(f"\n⏰ 执行next_trading_day()...")
        next_result = next_trading_day(self.game)
        print(f"✅ next_trading_day()执行结果: {next_result}")
        return next_result
    
    def save_cycle_state(self):
        """保存当前循环状态"""
        print(f"\n💾 保存第 {self.cycle_count} 轮状态...")
        self.game.save_game_state(f'ai_trading_cycle_{self.cycle_count}')
        print("✅ 状态保存完成")
    
    def display_current_status(self):
        """显示当前状态"""
        state = self.game.game_state
        print(f"\n📋 当前状态:")
        print(f"  日期: {state['current_date']}")
        print(f"  现金: ${state['cash_balance']:,.2f}")
        print(f"  总资产: ${state.get('total_assets', state['cash_balance']):,.2f}")
        
        holdings = state.get('holdings', {})
        if holdings:
            print(f"  持仓: {len(holdings)}只股票")
            for stock_code, holding in holdings.items():
                print(f"    📈 {stock_code}: {holding['quantity']}股 @ ${holding['cost_price']:.3f}")
        else:
            print(f"  持仓: 无")
    
    def run_single_cycle(self):
        """执行单轮完整交易循环"""
        self.cycle_count += 1
        print(f"\n{'='*60}")
        print(f"🔄 第 {self.cycle_count} 轮循环开始")
        print(f"{'='*60}")
        
        # 1. 执行render_portfolio()方法
        portfolio_result = self.get_portfolio_analysis()
        
        # 2. 请求AI生成交易策略
        strategy = self.request_ai_strategy(portfolio_result)
        
        # 3. 执行handle_trade()
        trade_result = self.execute_trade(strategy)
        
        # 4. 获取当前收益率
        pnl_percent = self.get_current_pnl()
        
        # 5. 执行next_trading_day()
        next_result = self.advance_to_next_day()
        
        # 6. 显示当前状态
        self.display_current_status()
        
        # 7. 保存当前状态
        self.save_cycle_state()
        
        # 记录交易历史
        self.trading_history.append({
            'cycle': self.cycle_count,
            'strategy': strategy,
            'trade_result': trade_result,
            'pnl_percent': pnl_percent,
            'date': self.game.game_state['current_date']
        })
        
        print(f"\n📊 第 {self.cycle_count} 轮循环完成")
        print(f"进度: {self.cycle_count}")
        print(f"{'-'*60}")
        
        return {
            'cycle': self.cycle_count,
            'strategy': strategy,
            'pnl_percent': pnl_percent,
            'date': self.game.game_state['current_date']
        }
    
    def run_auto_loop(self, max_cycles=10):
        """运行自动交易循环"""
        print(f"\n🎮 启动AI驱动的自动交易循环系统 v2.0")
        print(f"股票代码: {self.stock_code}")
        print(f"初始资金: ${self.initial_cash:,.2f}")
        print(f"开始日期: {self.date_start}")
        print(f"最大循环次数: {max_cycles}")
        print(f"AI策略生成器: {self.ai_generator.__class__.__name__}")
        print(f"{'='*60}")
        
        # 初始化游戏
        self.initialize_game()
        
        # 执行循环
        for cycle in range(max_cycles):
            try:
                result = self.run_single_cycle()
                
                # 短暂暂停，避免过快循环
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ 第 {cycle + 1} 轮循环执行失败: {e}")
                import traceback
                traceback.print_exc()
                break
        
        # 最终状态
        print(f"\n🎉 自动交易循环完成！共执行 {self.cycle_count} 轮")
        
        # 显示最终投资组合状态
        print("\n📊 最终投资组合状态:")
        final_portfolio = render_portfolio(self.game)
        print(final_portfolio)
        
        # 显示交易历史摘要
        print("\n📋 交易历史摘要:")
        for history in self.trading_history:
            print(f"  第{history['cycle']}轮: {history['strategy']['decision']} @ ${history['strategy']['tradePrice']}, 收益率: {history['pnl_percent']:.2f}%")
        
        return self.game

def create_trading_loop_with_hook(hook_system=None):
    """
    创建基于Hook的AI交易循环系统
    
    Args:
        hook_system: Hook系统实例
        
    Returns:
        AITradingLoop: 配置了Hook-based AI策略生成器的交易循环系统
    """
    ai_generator = HookBasedAIStrategyGenerator(hook_system)
    return AITradingLoop(ai_generator=ai_generator)

if __name__ == "__main__":
    # 使用模拟AI策略生成器测试
    print("🧪 测试模式：使用模拟AI策略生成器")
    ai_generator = MockAIStrategyGenerator()
    
    ai_trading = AITradingLoop(
        stock_code='sz.002261',
        initial_cash=100000.0,
        date_start='2026-02-24',
        ai_generator=ai_generator
    )
    
    # 运行自动交易循环
    game = ai_trading.run_auto_loop(max_cycles=2)
    
    print("\n✅ AI驱动的自动交易循环系统 v2.0 执行完成！")
    print("\n📋 系统架构:")
    print("  1. ✅ 创建StockTradingGame实例")
    print("  2. ✅ 执行render_portfolio()方法")
    print("  3. ✅ 根据render_portfolio返回值请求AI生成交易策略")
    print("  4. ✅ 根据AI回答执行handle_trade()")
    print("  5. ✅ get_unrealized_pnl_percent()获取当前收益率")
    print("  6. ✅ 执行next_trading_day()")
    print("  7. ✅ 循环执行")
    print("\n🔧 AI策略生成器:")
    print("  - 当前使用: MockAIStrategyGenerator（模拟）")
    print("  - 可切换为: HookBasedAIStrategyGenerator（基于Hook）")
    print("  - 支持扩展: 自定义AIStrategyGenerator实现")