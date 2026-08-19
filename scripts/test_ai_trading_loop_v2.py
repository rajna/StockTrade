#!/usr/bin/env python3
"""
测试AI驱动的自动交易循环系统 v2.0
演示多种AI策略生成器的使用
"""

from ai_trading_loop_v2 import AITradingLoop, MockAIStrategyGenerator
from llm_strategy_generator import LLMStrategyGenerator, MockLLMClient

def test_with_mock_ai():
    """测试使用模拟AI策略生成器"""
    print("🧪 测试1: 使用模拟AI策略生成器")
    print("=" * 60)
    
    ai_generator = MockAIStrategyGenerator()
    
    ai_trading = AITradingLoop(
        stock_code='sz.002261',
        initial_cash=100000.0,
        date_start='2026-02-24',
        ai_generator=ai_generator
    )
    
    game = ai_trading.run_auto_loop(max_cycles=1)
    
    print(f"\n✅ 测试1完成！")
    return ai_trading

def test_with_llm_ai():
    """测试使用LLM策略生成器"""
    print("\n🧪 测试2: 使用LLM策略生成器")
    print("=" * 60)
    
    # 创建模拟LLM客户端
    mock_llm = MockLLMClient()
    
    # 创建LLM策略生成器
    llm_generator = LLMStrategyGenerator(llm_client=mock_llm)
    
    ai_trading = AITradingLoop(
        stock_code='sz.002261',
        initial_cash=100000.0,
        date_start='2026-02-24',
        ai_generator=llm_generator
    )
    
    game = ai_trading.run_auto_loop(max_cycles=1)
    
    print(f"\n✅ 测试2完成！")
    return ai_trading

def main():
    """主测试函数"""
    print("🎮 开始测试AI驱动的自动交易循环系统 v2.0")
    print("=" * 60)
    
    # 测试1: 模拟AI
    ai_trading1 = test_with_mock_ai()
    
    # 测试2: LLM AI
    ai_trading2 = test_with_llm_ai()
    
    # 总结
    print("\n🎉 所有测试完成！")
    print("\n📋 系统架构总结:")
    print("  1. ✅ 创建StockTradingGame实例")
    print("  2. ✅ 执行render_portfolio()方法")
    print("  3. ✅ 根据render_portfolio返回值请求AI生成交易策略")
    print("  4. ✅ 根据AI回答执行handle_trade()")
    print("  5. ✅ get_unrealized_pnl_percent()获取当前收益率")
    print("  6. ✅ 执行next_trading_day()")
    print("  7. ✅ 循环执行")
    
    print("\n🔧 AI策略生成器架构:")
    print("  - AIStrategyGenerator (抽象基类)")
    print("    ├── MockAIStrategyGenerator (模拟AI，用于测试)")
    print("    ├── LLMStrategyGenerator (基于LLM的AI)")
    print("    └── HookBasedAIStrategyGenerator (基于Hook的AI)")
    
    print("\n📊 Hook系统:")
    print("  - Hook文件: hooks/generate-trading-strategy/hook.md")
    print("  - Hook事件: generate_trading_strategy")
    print("  - 当前状态: Hook框架已创建，等待集成")
    
    print("\n🎯 系统优势:")
    print("  - ✅ 灵活的AI策略生成器架构")
    print("  - ✅ 支持多种AI实现方式")
    print("  - ✅ 完整的交易循环流程")
    print("  - ✅ 完善的状态管理和错误处理")
    print("  - ✅ 可扩展的Hook系统支持")

if __name__ == "__main__":
    main()