#!/usr/bin/env python3
"""
AI Trading Example - Demonstrate AI-powered stock trading simulation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stock_data_fetcher import (
    StockTradingGame, 
    TradingDecision, 
    handle_trade,
    next_trading_day,
    check_trade_finished,
    render_portfolio,
    get_portfolio_value
)

def ai_trading_decision(game, market_data):
    """
    AI trading decision function (simplified example)
    
    In a real implementation, this would use an AI model to make decisions
    """
    current_price = game.game_state['current_prices'][game.game_state['current_stock']]['close']
    
    # Simple AI logic based on price movement
    if current_price > 10.0:
        return TradingDecision(
            reasoning='价格突破10元阻力位，买入信号',
            reasoning_abstract='突破阻力',
            reasoning_symbol=0.8,
            decision='买入',
            confidence='high',
            tradePrice=current_price * 1.01,  # 略高于当前价
            quantity=500
        )
    elif current_price < 9.5:
        return TradingDecision(
            reasoning='价格跌破9.5元支撑位，卖出信号',
            reasoning_abstract='跌破支撑',
            reasoning_symbol=0.7,
            decision='卖出',
            confidence='medium',
            tradePrice=current_price * 0.99,  # 略低于当前价
            quantity=300
        )
    else:
        return TradingDecision(
            reasoning='价格在合理区间内，持有观望',
            reasoning_abstract='区间震荡',
            reasoning_symbol=0.5,
            decision='持有',
            confidence='low',
            tradePrice=0,
            quantity=0
        )

def run_ai_trading_simulation():
    """Run AI-powered trading simulation"""
    print("🤖 AI Trading Simulation")
    print("=" * 50)
    
    # Initialize trading game
    game = StockTradingGame(
        stock_code='sh.600000',
        initial_cash=100000.0,
        date_start='2025-01-01'
    )
    
    print(f"📊 Starting simulation for {game.game_state['current_stock']}")
    print(f"💰 Initial cash: ${game.game_state['initial_cash']:,.2f}")
    print(f"📅 Start date: {game.game_state['current_date']}")
    print()
    
    trade_count = 0
    max_trades = 5  # Limit number of trades for demo
    
    while not check_trade_finished(game, trade_count) and trade_count < max_trades:
        # Get current market data
        market_data = game.game_state['current_prices'][game.game_state['current_stock']]
        current_price = market_data['close']
        
        print(f"📈 Day {trade_count + 1} - {game.game_state['current_date']}")
        print(f"💵 Current price: ${current_price:.2f}")
        
        # AI makes trading decision
        decision = ai_trading_decision(game, market_data)
        
        print(f"🧠 AI Decision:")
        print(f"   Reasoning: {decision['reasoning']}")
        print(f"   Decision: {decision['decision']}")
        print(f"   Confidence: {decision['confidence']}")
        
        # Execute trade
        try:
            handle_trade(game, str(decision))
            trade_count += 1
        except Exception as e:
            print(f"❌ Trade execution failed: {e}")
        
        # Show portfolio status
        portfolio_info = get_portfolio_value(game)
        print(f"💼 Portfolio: ${portfolio_info['total_value']:,.2f}")
        print(f"📊 P&L: ${portfolio_info['unrealized_pnl']:,.2f} ({portfolio_info['unrealized_pnl_percent']:+.2f}%)")
        print()
        
        # Advance to next trading day
        if not next_trading_day(game):
            print("🏁 No more trading days available")
            break
    
    # Final results
    print("🎯 Simulation Results")
    print("=" * 50)
    final_portfolio = get_portfolio_value(game)
    
    print(f"📊 Final Portfolio Value: ${final_portfolio['total_value']:,.2f}")
    print(f"💰 Initial Investment: ${game.game_state['initial_cash']:,.2f}")
    print(f"📈 Total P&L: ${final_portfolio['unrealized_pnl']:,.2f}")
    print(f"📊 P&L Percentage: {final_portfolio['unrealized_pnl_percent']:+.2f}%")
    print(f"🔄 Total Trades: {trade_count}")
    
    # Show final portfolio details
    print("\n📋 Final Portfolio Details:")
    print(render_portfolio(game))
    
    # Performance summary
    if final_portfolio['unrealized_pnl_percent'] > 0:
        print("🎉 Profitable simulation!")
    elif final_portfolio['unrealized_pnl_percent'] < 0:
        print("📉 Loss-making simulation")
    else:
        print("➖ Break-even simulation")

def demonstrate_llm_integration():
    """Demonstrate LLM data integration"""
    print("\n🔗 LLM Data Integration Demo")
    print("=" * 50)
    
    from stock_data_fetcher import get_stock_daily_data, stock_data_to_llm_string
    
    # Get historical data
    df = get_stock_daily_data('sh.600000', '2025-01-01', '2025-01-31', isCurrent=False)
    
    if df is not None:
        print("📊 Historical Data Sample:")
        print(df.head())
        print()
        
        # Convert to LLM format
        llm_data = stock_data_to_llm_string(df)
        print("🤖 LLM-Formatted Data:")
        print(llm_data[:500] + "..." if len(llm_data) > 500 else llm_data)
        print()
        
        print("✅ LLM integration successful!")
        print("📝 This formatted data can be sent to AI models for analysis")

def main():
    """Main function to run all demonstrations"""
    print("🚀 Stock Trade Skill - AI Trading Demo")
    print("=" * 60)
    
    try:
        # Run AI trading simulation
        run_ai_trading_simulation()
        
        # Demonstrate LLM integration
        demonstrate_llm_integration()
        
        print("\n🎉 All demonstrations completed successfully!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()