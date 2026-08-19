#!/usr/bin/env python3
"""
测试AI驱动的自动交易循环系统
演示完整的工作流程
"""

from ai_trading_loop import AITradingLoop

def test_ai_trading_loop():
    """
    测试AI交易循环系统
    """
    print("🎮 开始测试AI驱动的自动交易循环系统")
    print("=" * 60)
    
    # 创建AI交易循环系统
    ai_trading = AITradingLoop(
        stock_code='sz.002261',
        initial_cash=100000.0,
        date_start='2026-02-24'
    )
    
    # 运行自动交易循环（2轮测试）
    print("\n📊 开始运行自动交易循环...")
    game = ai_trading.run_auto_loop(max_cycles=2)
    
    # 显示最终结果
    print("\n🎉 测试完成！")
    print(f"总循环次数: {ai_trading.cycle_count}")
    print(f"交易历史记录: {len(ai_trading.trading_history)}条")
    
    # 显示交易历史
    print("\n📋 详细交易历史:")
    for history in ai_trading.trading_history:
        print(f"  第{history['cycle']}轮:")
        print(f"    决策: {history['strategy']['decision']}")
        print(f"    价格: ${history['strategy']['tradePrice']}")
        print(f"    数量: {history['strategy']['tradeQuantity']}股")
        print(f"    收益率: {history['pnl_percent']:.2f}%")
        print(f"    日期: {history['date']}")
    
    return ai_trading

if __name__ == "__main__":
    # 运行测试
    ai_trading = test_ai_trading_loop()
    
    print("\n✅ AI交易循环系统测试完成！")
    print("\n📋 系统说明:")
    print("  1. ✅ 创建StockTradingGame实例")
    print("  2. ✅ 执行render_portfolio()方法")
    print("  3. ⏳ 根据render_portfolio返回值和提示词请求AI生成交易策略")
    print("  4. ✅ 根据AI回答执行handle_trade()")
    print("  5. ✅ 获取当前收益率")
    print("  6. ✅ 执行next_trading_day()")
    print("  7. ✅ 循环执行")
    print("\n🔧 Hook支持:")
    print("  - Hook文件位置: hooks/hook.md")
    print("  - Hook触发时机: request_ai_strategy()方法")
    print("  - 当前状态: Hook框架已创建，等待AI介入")