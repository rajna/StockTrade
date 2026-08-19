#!/usr/bin/env python3
"""
Test script for Stock Data Fetcher skill
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stock_data_fetcher import (
    get_all_stocks,
    get_stock_daily_data,
    detect_boom_day,
    check_price_near_ma_safe,
    is_within_n_days,
    analyze_stock
)


def test_get_all_stocks():
    """Test get_all_stocks function"""
    print("\n" + "=" * 70)
    print("Test 1: Get All Stocks")
    print("=" * 70)
    
    stocks = get_all_stocks()
    
    if stocks is not None:
        print(f"✅ Success: Found {len(stocks)} stocks")
        print(f"\nFirst 5 stocks:")
        print(stocks.head())
        return True
    else:
        print("❌ Failed: Could not fetch stock list")
        return False


def test_get_stock_daily_data():
    """Test get_stock_daily_data function"""
    print("\n" + "=" * 70)
    print("Test 2: Get Historical Data")
    print("=" * 70)
    
    df = get_stock_daily_data(
        stock_code='sh.600000',
        start_date='2026-01-01',
        end_date='2026-03-12',
        k_type='d',
        isCurrent=False
    )
    
    if df is not None and len(df) > 0:
        print(f"✅ Success: Got {len(df)} days of data")
        print(f"\nLast 5 days:")
        print(df.tail())
        return True, df
    else:
        print("❌ Failed: Could not fetch historical data")
        return False, None


def test_detect_boom_day(df):
    """Test detect_boom_day function"""
    print("\n" + "=" * 70)
    print("Test 3: Detect Boom Days")
    print("=" * 70)
    
    if df is None:
        print("⚠️  Skipped: No historical data available")
        return None
    
    boom_days = detect_boom_day(df)
    
    if len(boom_days) > 0:
        print(f"✅ Success: Found {len(boom_days)} boom days")
        print(f"\nBoom days:")
        print(boom_days)
        return True
    else:
        print("⚠️  No boom days found in the data")
        return True  # Not an error, just no boom days


def test_check_price_near_ma_safe(df):
    """Test check_price_near_ma_safe function"""
    print("\n" + "=" * 70)
    print("Test 4: Check Price Near MA")
    print("=" * 70)
    
    if df is None or len(df) < 20:
        print("⚠️  Skipped: Insufficient data")
        return None
    
    near_ma20 = check_price_near_ma_safe(df, 20, 2.0)
    print(f"✅ Success: Near MA20 = {near_ma20}")
    
    if len(df) >= 60:
        near_ma60 = check_price_near_ma_safe(df, 60, 2.0)
        print(f"✅ Success: Near MA60 = {near_ma60}")
    
    return True


def test_is_within_n_days():
    """Test is_within_n_days function"""
    print("\n" + "=" * 70)
    print("Test 5: Is Within N Days")
    print("=" * 70)
    
    # Test with current date
    result1 = is_within_n_days('2026-03-10', 7)
    print(f"✅ Success: 2026-03-10 within 7 days of today = {result1}")
    
    # Test with specific reference date
    result2 = is_within_n_days('2026-03-10', 7, '2026-03-15')
    print(f"✅ Success: 2026-03-10 within 7 days of 2026-03-15 = {result2}")
    
    return True


def test_analyze_stock():
    """Test analyze_stock function"""
    print("\n" + "=" * 70)
    print("Test 6: Complete Stock Analysis")
    print("=" * 70)
    
    results = analyze_stock(
        stock_code='sh.600000',
        start_date='2026-01-01',
        end_date='2026-03-12',
        include_current=False
    )
    
    if results['error']:
        print(f"❌ Failed: {results['error']}")
        return False
    
    print(f"✅ Success: Analysis complete")
    print(f"   - Historical data: {len(results['historical_data'])} days")
    print(f"   - Boom days: {len(results['boom_days'])} days")
    print(f"   - Near MA20: {results['near_ma20']}")
    print(f"   - Near MA60: {results['near_ma60']}")
    
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("Stock Data Fetcher - Test Suite")
    print("=" * 70)
    
    results = []
    
    # Test 1: Get all stocks
    results.append(("Get All Stocks", test_get_all_stocks()))
    
    # Test 2: Get historical data
    success, df = test_get_stock_daily_data()
    results.append(("Get Historical Data", success))
    
    # Test 3: Detect boom days
    results.append(("Detect Boom Days", test_detect_boom_day(df)))
    
    # Test 4: Check price near MA
    results.append(("Check Price Near MA", test_check_price_near_ma_safe(df)))
    
    # Test 5: Is within N days
    results.append(("Is Within N Days", test_is_within_n_days()))
    
    # Test 6: Complete analysis
    results.append(("Complete Analysis", test_analyze_stock()))
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)
    
    for name, result in results:
        status = "✅ PASS" if result is True else "❌ FAIL" if result is False else "⚠️  SKIP"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    
    if failed > 0:
        print("\n❌ Some tests failed. Please check the errors above.")
        return 1
    else:
        print("\n✅ All tests passed!")
        return 0


if __name__ == '__main__':
    sys.exit(main())
