#!/usr/bin/env python3
"""
Usage Examples for Stock Data Fetcher

This script demonstrates various use cases of the stock-data-fetcher skill.
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


def example_1_get_stock_list():
    """Example 1: Get complete A-share stock list"""
    print("\n" + "=" * 70)
    print("Example 1: Get Complete A-share Stock List")
    print("=" * 70)
    
    stocks = get_all_stocks()
    
    if stocks is not None:
        print(f"\n✅ Found {len(stocks)} stocks")
        print(f"\nFirst 10 stocks:")
        print(stocks.head(10))
        
        # Search for specific stocks
        print(f"\n🔍 Searching for stocks with '平安' in name:")
        pingan = stocks[stocks['name'].str.contains('平安', na=False)]
        print(pingan)
    else:
        print("❌ Failed to get stock list")


def example_2_get_historical_data():
    """Example 2: Get historical K-line data"""
    print("\n" + "=" * 70)
    print("Example 2: Get Historical K-line Data")
    print("=" * 70)
    
    # Get daily data for 浦发银行 (sh.600000)
    df = get_stock_daily_data(
        stock_code='sh.600000',
        start_date='2026-01-01',
        end_date='2026-03-12',
        k_type='d',
        isCurrent=False
    )
    
    if df is not None:
        print(f"\n✅ Got {len(df)} days of data for 浦发银行 (sh.600000)")
        print(f"\nRecent 10 days:")
        print(df.tail(10))
        
        # Calculate basic statistics
        print(f"\n📊 Statistics:")
        print(f"   - Average close: {df['close'].mean():.2f}")
        print(f"   - Max close: {df['close'].max():.2f}")
        print(f"   - Min close: {df['close'].min():.2f}")
        print(f"   - Average volume: {df['volume'].mean():,.0f}")
    else:
        print("❌ Failed to get historical data")


def example_3_detect_boom_days():
    """Example 3: Detect boom days (放量阳线)"""
    print("\n" + "=" * 70)
    print("Example 3: Detect Boom Days (放量阳线)")
    print("=" * 70)
    
    # Get historical data
    df = get_stock_daily_data('sh.600000', '2026-01-01', '2026-03-12')
    
    if df is not None:
        # Detect boom days
        boom_days = detect_boom_day(df)
        
        if len(boom_days) > 0:
            print(f"\n✅ Found {len(boom_days)} boom days")
            print(f"\nBoom days details:")
            print(boom_days)
            
            # Analyze boom days
            print(f"\n📊 Analysis:")
            for idx, row in boom_days.iterrows():
                print(f"   - {row['date']}: {row['merge_count']} days merged, close: {row['close']:.2f}")
        else:
            print("⚠️  No boom days found in the data")
    else:
        print("❌ Failed to get historical data")


def example_4_check_ma_position():
    """Example 4: Check price position relative to moving averages"""
    print("\n" + "=" * 70)
    print("Example 4: Check Price Position Relative to Moving Averages")
    print("=" * 70)
    
    # Get historical data
    df = get_stock_daily_data('sh.600000', '2026-01-01', '2026-03-12')
    
    if df is not None and len(df) >= 20:
        # Check various MAs
        ma_periods = [5, 10, 20, 60]
        
        print(f"\n📊 Price position relative to moving averages:")
        for period in ma_periods:
            if len(df) >= period:
                is_near = check_price_near_ma_safe(df, period, threshold=2.0)
                latest_close = df.iloc[-1]['close']
                ma_value = df['close'].rolling(period).mean().iloc[-1]
                distance = ((latest_close - ma_value) / ma_value) * 100
                
                print(f"   - MA{period}: {ma_value:.2f} (distance: {distance:+.2f}%) - {'✅ Near' if is_near else '❌ Not near'}")
    else:
        print("❌ Insufficient data")


def example_5_complete_analysis():
    """Example 5: Complete stock analysis in one call"""
    print("\n" + "=" * 70)
    print("Example 5: Complete Stock Analysis")
    print("=" * 70)
    
    # Analyze multiple stocks
    stocks_to_analyze = ['sh.600000', 'sh.600519', 'sz.000001']
    
    for stock_code in stocks_to_analyze:
        print(f"\n📈 Analyzing {stock_code}...")
        
        results = analyze_stock(
            stock_code=stock_code,
            start_date='2026-01-01',
            end_date='2026-03-12',
            include_current=False
        )
        
        if results['error']:
            print(f"   ❌ Error: {results['error']}")
        else:
            print(f"   ✅ Analysis complete:")
            print(f"      - Historical data: {len(results['historical_data'])} days")
            print(f"      - Boom days: {len(results['boom_days'])} days")
            print(f"      - Near MA20: {results['near_ma20']}")
            print(f"      - Near MA60: {results['near_ma60']}")


def example_6_date_utilities():
    """Example 6: Date utility functions"""
    print("\n" + "=" * 70)
    print("Example 6: Date Utility Functions")
    print("=" * 70)
    
    # Check if dates are within N days
    test_dates = ['2026-03-10', '2026-03-05', '2026-03-20']
    
    print(f"\n📅 Checking if dates are within 7 days of today:")
    for date in test_dates:
        is_recent = is_within_n_days(date, 7)
        print(f"   - {date}: {'✅ Yes' if is_recent else '❌ No'}")
    
    # Check relative to specific date
    print(f"\n📅 Checking if dates are within 7 days of 2026-03-15:")
    for date in test_dates:
        is_recent = is_within_n_days(date, 7, '2026-03-15')
        print(f"   - {date}: {'✅ Yes' if is_recent else '❌ No'}")


def example_7_custom_analysis():
    """Example 7: Custom analysis workflow"""
    print("\n" + "=" * 70)
    print("Example 7: Custom Analysis Workflow")
    print("=" * 70)
    
    # Step 1: Get stock list
    print("\nStep 1: Getting stock list...")
    stocks = get_all_stocks()
    
    if stocks is None:
        print("❌ Failed to get stock list")
        return
    
    # Step 2: Find stocks with specific criteria
    print("\nStep 2: Finding stocks with '银行' in name...")
    bank_stocks = stocks[stocks['name'].str.contains('银行', na=False)]
    print(f"Found {len(bank_stocks)} bank stocks")
    print(bank_stocks.head(5))
    
    # Step 3: Analyze first bank stock
    if len(bank_stocks) > 0:
        first_bank = bank_stocks.iloc[0]
        stock_code = f"sz.{first_bank['code']}"
        
        print(f"\nStep 3: Analyzing {first_bank['name']} ({stock_code})...")
        
        df = get_stock_daily_data(stock_code, '2026-01-01', '2026-03-12')
        
        if df is not None:
            # Detect boom days
            boom_days = detect_boom_day(df)
            
            # Check MA position
            near_ma20 = check_price_near_ma_safe(df, 20, 2.0) if len(df) >= 20 else None
            
            print(f"\n📊 Analysis Results:")
            print(f"   - Data range: {df.iloc[0]['date']} to {df.iloc[-1]['date']}")
            print(f"   - Latest close: {df.iloc[-1]['close']:.2f}")
            print(f"   - Boom days: {len(boom_days)}")
            print(f"   - Near MA20: {near_ma20}")
            
            if len(boom_days) > 0:
                print(f"\n🔥 Recent boom days:")
                print(boom_days.tail(3))


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("Stock Data Fetcher - Usage Examples")
    print("=" * 70)
    
    examples = [
        ("Get Stock List", example_1_get_stock_list),
        ("Get Historical Data", example_2_get_historical_data),
        ("Detect Boom Days", example_3_detect_boom_days),
        ("Check MA Position", example_4_check_ma_position),
        ("Complete Analysis", example_5_complete_analysis),
        ("Date Utilities", example_6_date_utilities),
        ("Custom Analysis", example_7_custom_analysis),
    ]
    
    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
    
    print("\n" + "=" * 70)
    print("✅ All examples completed!")
    print("=" * 70)


if __name__ == '__main__':
    main()
