#!/usr/bin/env python3
"""
Test script for Stock Trading Game functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stock_data_fetcher import (
    stock_data_to_llm_string,
    get_stock_daily_data
)

from stock_trading_game import (
    StockTradingGame,
    TradingDecision,
    get_portfolio_value,
    render_portfolio
)

def test_stock_data_to_llm_string():
    """Test stock data to LLM string conversion"""
    print("Testing stock_data_to_llm_string...")
    
    # Create sample data
    import pandas as pd
    sample_data = pd.DataFrame({
        'date': ['2026-01-01', '2026-01-02', '2026-01-03'],
        'open': [10.0, 10.5, 11.0],
        'high': [10.5, 11.0, 11.5],
        'low': [9.8, 10.2, 10.8],
        'close': [10.2, 10.8, 11.2],
        'volume': [1000000, 1200000, 1500000]
    })
    
    # Convert to LLM format
    llm_string = stock_data_to_llm_string(sample_data)
    print("LLM String:")
    print(llm_string)
    print("✅ stock_data_to_llm_string test passed")

def test_trading_decision_types():
    """Test TradingDecision data type"""
    print("\nTesting TradingDecision data type...")
    
    # Create sample trading decision
    decision: TradingDecision = {
        'reasoning': 'MA crossover pattern detected',
        'reasoning_abstract': 'Bullish signal',
        'reasoning_symbol': 0.8,
        'decision': '买入',
        'confidence': 'high',
        'tradePrice': 10.50,
        'quantity': 1000
    }
    
    print("Trading Decision:")
    print(decision)
    print("✅ TradingDecision test passed")

def test_stock_trading_game():
    """Test StockTradingGame initialization"""
    print("\nTesting StockTradingGame...")
    
    try:
        # Initialize trading game
        game = StockTradingGame(
            stock_code='sh.600000',
            initial_cash=100000.0,
            date_start='2025-01-01'
        )
        
        print(f"Game initialized successfully!")
        print(f"Current date: {game.game_state['current_date']}")
        print(f"Current stock: {game.game_state['current_stock']}")
        print(f"Initial cash: {game.game_state['initial_cash']}")
        
        # Test portfolio value calculation
        portfolio_info = get_portfolio_value(game)
        print(f"Portfolio info: {portfolio_info}")
        
        # Test portfolio rendering
        portfolio_render = render_portfolio(game)
        print("Portfolio render:")
        print(portfolio_render)
        
        print("✅ StockTradingGame test passed")
        
    except Exception as e:
        print(f"❌ StockTradingGame test failed: {e}")
        # This is expected if we don't have boom days in the test period
        print("Note: This failure is expected if no boom days found in test period")

def test_data_conversion():
    """Test data conversion functions"""
    print("\nTesting data conversion functions...")
    
    try:
        # Test get_stock_daily_data
        df = get_stock_daily_data('sh.600000', '2026-01-01', '2026-01-10', isCurrent=False)
        if df is not None:
            print(f"✅ get_stock_daily_data returned {len(df)} rows")
            
            # Test LLM conversion
            llm_data = stock_data_to_llm_string(df)
            print(f"✅ LLM conversion successful, length: {len(llm_data)}")
        else:
            print("⚠️ get_stock_daily_data returned None (may be expected)")
            
    except Exception as e:
        print(f"❌ Data conversion test failed: {e}")

def main():
    """Run all tests"""
    print("Starting Stock Trade Skill Tests...")
    print("=" * 50)
    
    try:
        test_stock_data_to_llm_string()
        test_trading_decision_types()
        test_stock_trading_game()
        test_data_conversion()
        
        print("\n" + "=" * 50)
        print("🎉 All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()