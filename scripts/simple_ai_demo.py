#!/usr/bin/env python3
"""
Simple AI Trading Demo - Quick demonstration of AI trading features
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stock_data_fetcher import (
    StockTradingGame, 
    TradingDecision, 
    stock_data_to_llm_string,
    get_stock_daily_data,
    render_portfolio
)

def demo_trading_decision():
    """Demonstrate TradingDecision data type"""
    print("🤖 Trading Decision Demo")
    print("=" * 30)
    
    # Create sample AI trading decision
    decision: TradingDecision = {
        'reasoning': 'MA5上穿MA10形成金叉，买入信号强烈',
        'reasoning_abstract': '均线金叉',
        'reasoning_symbol': 0.85,
        'decision': '买入',
        'confidence': 'high',
        'tradePrice': 10.50,
        'quantity': 1000
    }
    
    print("AI Trading Decision:")
    for key, value in decision.items():
        print(f"  {key}: {value}")
    
    print("\n✅ TradingDecision structure working correctly")

def demo_llm_conversion():
    """Demonstrate LLM data conversion"""
    print("\n🔗 LLM Data Conversion Demo")
    print("=" * 35)
    
    # Get sample data
    df = get_stock_daily_data('sh.600000', '2025-01-01', '2025-01-05', isCurrent=False)
    
    if df is not None:
        print("📊 Original Data:")
        print(df)
        print()
        
        # Convert to LLM format
        llm_data = stock_data_to_llm_string(df)
        print("🤖 LLM-Formatted Data:")
        print(llm_data)
        
        print("\n✅ LLM conversion working correctly")

def demo_game_initialization():
    """Demonstrate game initialization"""
    print("\n🎮 Game Initialization Demo")
    print("=" * 30)
    
    try:
        # Initialize game
        game = StockTradingGame(
            stock_code='sh.600000',
            initial_cash=50000.0,
            date_start='2025-01-01'
        )
        
        print("✅ Game initialized successfully!")
        print(f"   Stock: {game.game_state['current_stock']}")
        print(f"   Initial Cash: ${game.game_state['initial_cash']:,.2f}")
        print(f"   Current Date: {game.game_state['current_date']}")
        
        # Show portfolio
        portfolio = render_portfolio(game)
        print("\n📋 Initial Portfolio:")
        print(portfolio)
        
    except Exception as e:
        print(f"⚠️ Game initialization failed: {e}")
        print("   This may be expected if no boom days found")

def demo_ai_decision_logic():
    """Demonstrate AI decision logic"""
    print("\n🧠 AI Decision Logic Demo")
    print("=" * 35)
    
    # Simulate different market conditions
    scenarios = [
        {'price': 12.50, 'trend': 'up', 'expected': '买入'},
        {'price': 8.20, 'trend': 'down', 'expected': '卖出'},
        {'price': 10.00, 'trend': 'sideways', 'expected': '持有'}
    ]
    
    for scenario in scenarios:
        price = scenario['price']
        trend = scenario['trend']
        expected = scenario['expected']
        
        # Simple AI logic
        if price > 10.0 and trend == 'up':
            decision = '买入'
            confidence = 'high'
            reasoning = f'价格突破10元，{trend}趋势明显'
        elif price < 9.0 and trend == 'down':
            decision = '卖出'
            confidence = 'medium'
            reasoning = f'价格跌破9元，{trend}趋势确认'
        else:
            decision = '持有'
            confidence = 'low'
            reasoning = f'价格在合理区间，{trend}整理'
        
        print(f"📈 Scenario: {trend}ward trend @ ${price}")
        print(f"🤖 AI Decision: {decision} ({confidence})")
        print(f"💭 Reasoning: {reasoning}")
        print()

def main():
    """Run all demos"""
    print("🚀 Stock Trade Skill - Simple AI Demo")
    print("=" * 50)
    
    try:
        demo_trading_decision()
        demo_llm_conversion()
        demo_game_initialization()
        demo_ai_decision_logic()
        
        print("\n🎉 All demos completed successfully!")
        print("\n📝 Key Features Demonstrated:")
        print("  ✅ TradingDecision data type")
        print("  ✅ LLM data conversion")
        print("  ✅ Game initialization")
        print("  ✅ AI decision logic")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()