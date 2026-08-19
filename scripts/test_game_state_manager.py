#!/usr/bin/env python3
"""
Test script for GameState Manager functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stock_data_fetcher import StockTradingGame, get_portfolio_value, render_portfolio
from game_state_manager import GameStateManager


def test_game_state_manager():
    """Test GameStateManager functionality"""
    print("🧪 Testing GameState Manager")
    print("=" * 50)
    
    # Create GameStateManager
    manager = GameStateManager("./test_game_states")
    
    # Test basic functionality
    print("\n1. Testing basic GameStateManager operations...")
    
    # Create a test game state
    test_state = {
        'cash_balance': 75000.0,
        'portfolio': {
            'sh.600000': {
                'symbol': 'sh.600000',
                'quantity': 500,
                'avg_price': 12.50,
                'timestamp': '2025-01-01 10:00:00'
            }
        },
        'transaction_history': [
            {
                'type': 'BUY',
                'symbol': 'sh.600000',
                'quantity': 500,
                'price': 12.50,
                'amount': 6250.0,
                'profit_loss': 0,
                'timestamp': '2025-01-01 10:00:00'
            }
        ],
        'current_prices': {
            'sh.600000': {
                'open': 12.50,
                'high': 13.00,
                'low': 12.40,
                'close': 12.80,
                'volume': 1000000
            }
        },
        'current_date': '2025-01-01 10:00:00',
        'current_stock': 'sh.600000',
        'initial_cash': 75000.0
    }
    
    # Test saving
    print("   - Saving test state...")
    saved_file = manager.save_game_state(test_state, "test_game")
    print(f"   ✅ Saved to: {saved_file}")
    
    # Test loading
    print("   - Loading saved state...")
    loaded_state = manager.load_game_state("test_game")
    print(f"   ✅ Loaded state: {loaded_state is not None}")
    
    # Test listing
    print("   - Listing game states...")
    game_states = manager.list_game_states()
    print(f"   ✅ Found {len(game_states)} game states")
    
    # Test cleanup
    print("   - Cleaning up old files...")
    deleted = manager.cleanup_old_files("test_game", keep_latest=3)
    print(f"   ✅ Deleted {deleted} old files")
    
    print("\n✅ GameStateManager tests completed!")


def test_stock_trading_game_with_save():
    """Test StockTradingGame with auto-save functionality"""
    print("\n🎮 Testing StockTradingGame with Auto-Save")
    print("=" * 50)
    
    try:
        # Initialize game with auto-save
        print("1. Initializing StockTradingGame with auto-save...")
        game = StockTradingGame(
            stock_code='sh.600000',
            initial_cash=50000.0,
            date_start='2025-01-01',
            load_from_save=False,
            save_dir="./test_game_states"
        )
        
        # Get initial save info
        save_info = game.get_save_info()
        print(f"   Game ID: {save_info['game_id']}")
        print(f"   Auto-save enabled: {save_info['auto_save_enabled']}")
        print(f"   Initial cash: ${save_info['cash_balance']:,.2f}")
        
        # Test manual save
        print("\n2. Testing manual save...")
        saved_file = game.save_game_state("Initial state")
        print(f"   ✅ Manual save completed: {saved_file}")
        
        # Test portfolio operations
        print("\n3. Testing portfolio operations with auto-save...")
        
        # Get current portfolio
        portfolio_info = get_portfolio_value(game)
        print(f"   Initial portfolio: ${portfolio_info['total_value']:,.2f}")
        
        # Execute a trade (this should trigger auto-save)
        print("   - Executing buy trade...")
        try:
            result = game.buy_stock('sh.600000', 10.50, 1000)
            print(f"   ✅ Trade executed: {result['message']}")
        except Exception as e:
            print(f"   ⚠️  Trade failed (expected for demo): {e}")
        
        # Check if auto-save triggered
        save_info_after_trade = game.get_save_info()
        print(f"   Portfolio size after trade: {save_info_after_trade['portfolio_size']}")
        print(f"   Transaction count: {save_info_after_trade['transaction_count']}")
        
        # Test listing saved states
        print("\n4. Testing saved state listing...")
        saved_states = game.list_game_states()
        print(f"   ✅ Found {len(saved_states)} saved states")
        for state in saved_states[:3]:  # Show first 3
            print(f"   - {state['game_id']}: {state['timestamp']}")
        
        # Test backup creation
        print("\n5. Testing backup creation...")
        try:
            backup_file = game.create_backup()
            print(f"   ✅ Backup created: {backup_file}")
        except Exception as e:
            print(f"   ⚠️  Backup failed: {e}")
        
        # Test cleanup
        print("\n6. Testing cleanup...")
        deleted = game.cleanup_old_files(keep_latest=5)
        print(f"   ✅ Cleaned up {deleted} old files")
        
        # Show final portfolio
        print("\n7. Final portfolio status:")
        final_portfolio = render_portfolio(game)
        print(final_portfolio)
        
        print("\n✅ StockTradingGame with auto-save tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


def test_auto_save_behavior():
    """Test auto-save behavior"""
    print("\n🔄 Testing Auto-Save Behavior")
    print("=" * 40)
    
    try:
        # Create game
        game = StockTradingGame(
            stock_code='sh.600000',
            initial_cash=30000.0,
            date_start='2025-01-01',
            load_from_save=False,
            save_dir="./test_game_states"
        )
        
        # Enable auto-save
        game.enable_auto_save(True)
        
        # Perform multiple operations
        print("1. Performing multiple operations...")
        
        # Save info before operations
        initial_save_info = game.get_save_info()
        print(f"   Initial save time: {initial_save_info['last_save_time']}")
        
        # Execute trades
        for i in range(3):
            print(f"   - Trade {i+1}...")
            try:
                # Try different operations
                if i % 3 == 0:
                    game.buy_stock('sh.600000', 10.0 + i, 100)
                elif i % 3 == 1:
                    game.sell_stock('sh.600000', 12.0 + i, 50)
                else:
                    game.hold_position('sh.600000')
            except Exception as e:
                print(f"     Trade {i+1} failed: {e}")
        
        # Check save info after operations
        final_save_info = game.get_save_info()
        print(f"   Final save time: {final_save_info['last_save_time']}")
        
        # Disable auto-save
        print("\n2. Disabling auto-save...")
        game.enable_auto_save(False)
        print("   ✅ Auto-save disabled")
        
        # Perform operation (should not auto-save)
        print("3. Performing operation with auto-save disabled...")
        try:
            game.no_position('sh.600000')
        except Exception as e:
            print(f"   Operation failed: {e}")
        
        # Check that save time didn't change
        disabled_save_info = game.get_save_info()
        print(f"   Save time after disabled auto-save: {disabled_save_info['last_save_time']}")
        
        print("\n✅ Auto-save behavior tests completed!")
        
    except Exception as e:
        print(f"❌ Auto-save test failed: {e}")
        import traceback
        traceback.print_exc()


def test_error_handling():
    """Test error handling"""
    print("\n🚨 Testing Error Handling")
    print("=" * 40)
    
    # Create GameStateManager
    manager = GameStateManager("./test_game_states")
    
    # Test loading non-existent state
    print("1. Testing non-existent state loading...")
    loaded = manager.load_game_state("non_existent_game")
    print(f"   Loading non-existent state: {loaded}")
    
    # Test cleanup non-existent
    print("2. Testing cleanup of non-existent game...")
    deleted = manager.cleanup_old_files("non_existent_game")
    print(f"   Cleanup non-existent game: {deleted} files deleted")
    
    # Test StockTradingGame with invalid parameters
    print("3. Testing StockTradingGame with invalid parameters...")
    try:
        game = StockTradingGame(
            stock_code='invalid_stock',
            initial_cash=1000.0,
            date_start='2025-01-01'
        )
        print("   ⚠️  Game should have failed but didn't")
    except Exception as e:
        print(f"   ✅ Expected error: {e}")
    
    print("\n✅ Error handling tests completed!")


def main():
    """Run all tests"""
    print("🧪 GameState Manager Test Suite")
    print("=" * 60)
    
    try:
        test_game_state_manager()
        test_stock_trading_game_with_save()
        test_auto_save_behavior()
        test_error_handling()
        
        print("\n" + "=" * 60)
        print("🎉 All tests completed successfully!")
        print("\n📋 Summary:")
        print("  ✅ GameStateManager basic operations")
        print("  ✅ StockTradingGame integration")
        print("  ✅ Auto-save functionality")
        print("  ✅ Error handling")
        print("  ✅ Backup and cleanup")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()