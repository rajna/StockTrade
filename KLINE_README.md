# K-line Chart Visualization Guide

## Overview

The stock-data-fetcher skill now includes professional K-line chart visualization capabilities through the `drawK()` function. This feature allows you to create detailed financial charts with volume indicators, moving averages, and special date highlighting.

## Features

### 📊 Professional K-line Charts
- **Candlestick visualization** with proper OHLC representation
- **Volume bars** with color coding (red for up days, green for down days)
- **Moving averages**: MA5 (blue), MA10 (red), MA18 (yellow)
- **Special date highlighting** with purple coloring
- **Professional styling** with Chinese font support

### 🎯 Key Components
1. **Main Chart Area**: Price action with candlesticks and moving averages
2. **Volume Chart**: Volume bars below the main chart
3. **Date Axis**: Properly formatted date labels
4. **Legend**: Clear identification of moving averages
5. **Grid Lines**: For better readability

## Usage Examples

### Basic Chart
```python
from scripts.stock_data_fetcher import get_stock_daily_data, drawK

# Get historical data
df = get_stock_daily_data('sh.600000', '2026-01-01', '2026-03-12', isCurrent=True)

# Draw basic K-line chart
drawK(df)
```

### Highlight Specific Dates
```python
# Using comma-separated string
drawK(df, dateArray='2026-02-01,2026-02-15,2026-03-01')

# Using list format
drawK(df, dateArray=['2026-02-01', '2026-02-15', '2026-03-01'])
```

### Highlight Boom Days
```python
from scripts.stock_data_fetcher import detect_boom_day

# Detect boom days
boom_days = detect_boom_day(df)

# Highlight boom days in the chart
if len(boom_days) > 0:
    drawK(df, dateArray=boom_days['date'].tolist())
```

## Chart Customization

### Date Format Support
The `drawK()` function accepts multiple date formats:
- **String**: `'2026-02-01,2026-02-15,2026-03-01'`
- **List**: `['2026-02-01', '2026-02-15', '2026-03-01']`
- **DataFrame column**: Automatically detects 'date' column

### Color Scheme
- **Red candles**: Up days (close >= open)
- **Green candles**: Down days (close < open)
- **Purple highlights**: Special dates
- **Blue line**: MA5
- **Red line**: MA10
- **Yellow line**: MA18

## Integration with Existing Functions

The `drawK()` function integrates seamlessly with existing stock analysis functions:

```python
# Complete analysis workflow
from scripts.stock_data_fetcher import (
    get_stock_daily_data, 
    detect_boom_day, 
    check_price_near_ma_safe,
    drawK
)

# 1. Get data
df = get_stock_daily_data('sh.600000', '2026-01-01', '2026-03-12', isCurrent=True)

# 2. Analyze patterns
boom_days = detect_boom_day(df)
near_ma20 = check_price_near_ma_safe(df, 20, 2.0)

# 3. Visualize results
if len(boom_days) > 0:
    drawK(df, dateArray=boom_days['date'].tolist())
else:
    drawK(df)
```

## Technical Requirements

### Dependencies
- `matplotlib>=3.7.0`
- `numpy>=1.24.0`
- `pandas>=2.0.0`

### Installation
```bash
pip install matplotlib numpy mplfinance
```

Or use the provided requirements file:
```bash
pip install -r scripts/requirements.txt
```

## Error Handling

The function includes comprehensive error handling:
- **Missing dependencies**: Clear error messages if matplotlib is not installed
- **Invalid data**: Graceful handling of missing or malformed data
- **Date parsing**: Automatic conversion of various date formats

## Performance Considerations

- **Large datasets**: For datasets with >1000 data points, consider using weekly or monthly data
- **Real-time updates**: Charts may take longer to render with real-time data included
- **Memory usage**: Each chart creates new matplotlib figures, close them when done

## Troubleshooting

### Common Issues

1. **Font not found**: Ensure Chinese fonts are installed on your system
2. **Chart not displaying**: Check if matplotlib backend is properly configured
3. **Date parsing errors**: Ensure dates are in YYYY-MM-DD format

### Debug Mode
```python
# Enable verbose output
import matplotlib.pyplot as plt
plt.ion()  # Turn on interactive mode
```

## Advanced Usage

### Custom Styling
```python
# Access underlying matplotlib objects for customization
fig, axes = plt.subplots(2, 1, figsize=(20, 10))
# Modify axes properties as needed
axes[0].set_title('Custom Chart Title')
axes[0].grid(True, alpha=0.3)
```

### Export Charts
```python
# Save chart to file
fig = drawK(df, return_figure=True)  # If modified to return figure
fig.savefig('kline_chart.png', dpi=300, bbox_inches='tight')
```

## Examples

See `scripts/kline_example.py` for comprehensive usage examples and `scripts/test_kline.py` for testing functionality.