#!/usr/bin/env python3
"""
K-line Chart Drawing Example

This example demonstrates how to use the drawK function to create
professional K-line charts with volume indicators and moving averages.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stock_data_fetcher import get_stock_daily_data, drawK, detect_boom_day

def main():
    """Example usage of drawK function"""
    
    print("K-line Chart Drawing Example")
    print("=" * 50)
    
    # Example 1: Basic K-line chart
    print("\n1. Drawing basic K-line chart for Shanghai Composite (000001)")
    try:
        df = get_stock_daily_data('sz.000001', '2026-01-01', '2026-03-12', isCurrent=True)
        if df is not None and len(df) > 0:
            print(f"Retrieved {len(df)} days of data")
            drawK(df)
        else:
            print("No data available for Shanghai Composite")
    except Exception as e:
        print(f"Error drawing basic chart: {e}")
    
    # Example 2: K-line chart with boom days highlighted
    print("\n2. Drawing K-line chart with boom days highlighted")
    try:
        df = get_stock_daily_data('sh.600000', '2026-01-01', '2026-03-12', isCurrent=True)
        if df is not None and len(df) > 0:
            # Detect boom days
            boom_days = detect_boom_day(df)
            if len(boom_days) > 0:
                # Format boom dates for highlighting
                boom_dates = boom_days['date'].tolist()
                print(f"Found {len(boom_days)} boom days to highlight")
                drawK(df, dateArray=boom_dates)
            else:
                print("No boom days found, drawing basic chart")
                drawK(df)
        else:
            print("No data available for 600000")
    except Exception as e:
        print(f"Error drawing boom days chart: {e}")
    
    # Example 3: K-line chart with specific dates highlighted
    print("\n3. Drawing K-line chart with specific dates highlighted")
    try:
        df = get_stock_daily_data('sz.000002', '2026-01-01', '2026-03-12', isCurrent=True)
        if df is not None and len(df) > 0:
            # Highlight specific dates (comma-separated string)
            special_dates = '2026-02-01,2026-02-15,2026-03-01'
            print(f"Highlighting specific dates: {special_dates}")
            drawK(df, dateArray=special_dates)
        else:
            print("No data available for 000002")
    except Exception as e:
        print(f"Error drawing specific dates chart: {e}")
    
    print("\n✅ K-line chart examples completed!")

if __name__ == "__main__":
    main()