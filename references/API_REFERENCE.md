# API Reference

Complete API documentation for Stock Data Fetcher.

## Table of Contents

1. [Real-time Data](#real-time-data)
2. [Historical Data](#historical-data)
3. [Pattern Detection](#pattern-detection)
4. [Technical Analysis](#technical-analysis)
5. [Stock List](#stock-list)
6. [Utility Functions](#utility-functions)

---

## Real-time Data

### `get_current(stock_code)`

Fetch real-time stock quote from Sina Finance.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| stock_code | str | Yes | Stock code with exchange prefix (e.g., 'sh.600000', 'sz.000001') |

**Returns:**

- `List[str]`: `[date, open, high, low, close, volume]`
- `None`: If error occurs

**Example:**

```python
from scripts.stock_data_fetcher import get_current

# Shanghai stock
data = get_current('sh.600000')
# Returns: ['2026-03-12', '10.5000000000', '10.8000000000', '10.4000000000', '10.7500000000', '12345678']

# Shenzhen stock
data = get_current('sz.000001')
```

**Notes:**

- Requires Chrome/Chromium browser and ChromeDriver
- Automatically managed by webdriver-manager
- Adds 5-second delay for page loading
- Volume is converted to shares (1 lot = 100 shares)

**Error Handling:**

- Returns `None` if:
  - selenium not installed
  - Stock code invalid
  - Network error
  - Page structure changed

---

## Historical Data

### `get_stock_daily_data(stock_code, start_date, end_date, k_type, isCurrent)`

Fetch historical K-line data from Baostock.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| stock_code | str | Yes | - | Stock code with exchange prefix |
| start_date | str | No | '2026-01-01' | Start date in 'YYYY-MM-DD' format |
| end_date | str | No | '2026-03-12' | End date in 'YYYY-MM-DD' format |
| k_type | str | No | 'd' | K-line type: 'd'=daily, 'w'=weekly, 'm'=monthly |
| isCurrent | bool | No | False | Whether to append real-time data |

**Returns:**

- `pd.DataFrame`: With columns `[date, open, high, low, close, volume, pctChg]`
- `None`: If error occurs

**Example:**

```python
from scripts.stock_data_fetcher import get_stock_daily_data

# Get daily data
df = get_stock_daily_data(
    stock_code='sh.600000',
    start_date='2026-01-01',
    end_date='2026-03-12',
    k_type='d',
    isCurrent=True  # Include today's real-time data
)

print(df.head())
#         date   open   high    low  close    volume  pctChg
# 0  2026-01-02  10.50  10.80  10.40  10.75  12345678    2.5
# 1  2026-01-03  10.75  11.00  10.60  10.90   9876543    1.4
```

**Notes:**

- Uses Baostock free API
- No adjustment by default (adjustflag="2")
- When `isCurrent=True`, appends real-time quote from Sina Finance
- Numeric columns are automatically converted from strings

**Error Handling:**

- Returns `None` if:
  - baostock not installed
  - Invalid stock code
  - Network error
  - No data available

---

## Pattern Detection

### `detect_boom_day(data)`

Identify significant upward momentum days (启动放量阳线).

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| data | pd.DataFrame | Yes | DataFrame with columns `[date, open, high, low, close, volume]` |

**Returns:**

- `pd.DataFrame`: With columns:
  - `date`: Boom day date
  - `high`: Merged high price
  - `low`: Merged low price
  - `close`: Merged close price
  - `volume`: Maximum volume during merge
  - `merged`: Always True
  - `merge_count`: Number of days merged
  - `original_dates`: Comma-separated list of merged dates

**Example:**

```python
from scripts.stock_data_fetcher import get_stock_daily_data, detect_boom_day

# Get historical data
df = get_stock_daily_data('sh.600000', '2026-01-01', '2026-03-12')

# Detect boom days
boom_days = detect_boom_day(df)

print(boom_days)
#          date   high    low  close    volume  merged  merge_count    original_dates
# 0  2026-02-15  11.50  10.80  11.45  25678901    True            1        2026-02-15
# 1  2026-03-05  12.30  11.60  12.25  34567890    True            3  2026-03-05,2026-03-06,2026-03-07
```

**Algorithm:**

1. **Volume surge**: Volume > 1.35x 5-day average volume
2. **Price gain**: Daily gain > 3.5% OR limit-up (≥9.9%)
3. **Merge logic**: Consecutive days with new highs are merged into one pattern

**Use Cases:**

- Identify trend initiation points
- Find strong momentum stocks
- Detect potential breakouts

---

## Technical Analysis

### `check_price_near_ma_safe(df, rolling_number, threshold)`

Check if current price is near a moving average.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| df | pd.DataFrame | Yes | - | DataFrame with 'close' column |
| rolling_number | int | Yes | - | Moving average period |
| threshold | float | No | 2.0 | Percentage threshold |

**Returns:**

- `bool`: True if price is within threshold of MA, False otherwise

**Example:**

```python
from scripts.stock_data_fetcher import get_stock_daily_data, check_price_near_ma_safe

df = get_stock_daily_data('sh.600000', '2026-01-01', '2026-03-12')

# Check if price is within 2% of 20-day MA
is_near_ma20 = check_price_near_ma_safe(df, 20, 2.0)
print(f"Near MA20: {is_near_ma20}")

# Check if price is within 1% of 60-day MA
is_near_ma60 = check_price_near_ma_safe(df, 60, 1.0)
print(f"Near MA60: {is_near_ma60}")
```

**Notes:**

- Does not modify the input DataFrame
- Returns False if MA cannot be calculated (insufficient data)
- Useful for support/resistance identification

---

## Stock List

### `get_all_stocks()`

Get complete A-share stock list with codes and names.

**Parameters:**

None

**Returns:**

- `pd.DataFrame`: With columns `[code, name]`
- `None`: If error occurs

**Example:**

```python
from scripts.stock_data_fetcher import get_all_stocks

stocks = get_all_stocks()
print(f"Total stocks: {len(stocks)}")
print(stocks.head())
#      code    name
# 0  000001  平安银行
# 1  000002  万科A
# 2  000004  国华网安
# 3  000005  ST星源
# 4  000006  深振业A
```

**Notes:**

- Uses Akshare API
- Automatically saves to 'A股股票列表.csv'
- Includes both Shanghai and Shenzhen stocks

---

## Utility Functions

### `is_within_n_days(target_date_str, count, reference_date_str)`

Check if target date is within N days of reference date.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| target_date_str | str | Yes | - | Target date in 'YYYY-MM-DD' format |
| count | int | Yes | - | Number of days |
| reference_date_str | str | No | Current date | Reference date in 'YYYY-MM-DD' format |

**Returns:**

- `bool`: True if within N days (past or future), False otherwise

**Example:**

```python
from scripts.stock_data_fetcher import is_within_n_days

# Check if date is within 7 days of today
is_recent = is_within_n_days('2026-03-10', 7)
print(f"Is recent: {is_recent}")

# Check if date is within 7 days of specific date
is_recent = is_within_n_days('2026-03-10', 7, '2026-03-15')
print(f"Is recent: {is_recent}")
```

---

### `analyze_stock(stock_code, start_date, end_date, include_current)`

Perform complete stock analysis in one call.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| stock_code | str | Yes | - | Stock code with exchange prefix |
| start_date | str | No | '2026-01-01' | Start date for historical data |
| end_date | str | No | '2026-03-12' | End date for historical data |
| include_current | bool | No | True | Whether to include real-time data |

**Returns:**

- `Dict[str, Any]`: With keys:
  - `stock_code`: Stock code
  - `historical_data`: DataFrame or None
  - `boom_days`: DataFrame or None
  - `near_ma20`: bool or None
  - `near_ma60`: bool or None
  - `error`: str or None

**Example:**

```python
from scripts.stock_data_fetcher import analyze_stock

results = analyze_stock('sh.600000', '2026-01-01', '2026-03-12', True)

if results['error']:
    print(f"Error: {results['error']}")
else:
    print(f"Historical data: {len(results['historical_data'])} days")
    print(f"Boom days: {len(results['boom_days'])} days")
    print(f"Near MA20: {results['near_ma20']}")
    print(f"Near MA60: {results['near_ma60']}")
```

---

## Data Sources

### Sina Finance

- **URL**: https://finance.sina.com.cn
- **Data**: Real-time quotes
- **Method**: Web scraping with Selenium
- **Rate Limit**: Add delays between requests

### Baostock

- **URL**: http://baostock.com
- **Data**: Historical K-line data
- **Method**: API calls
- **Rate Limit**: Free API with rate limits

### Akshare

- **URL**: https://akshare.akfamily.xyz
- **Data**: Stock list, market data
- **Method**: API calls
- **Rate Limit**: Free API with rate limits

---

## Error Handling

All functions include comprehensive error handling:

1. **Import errors**: Check if required packages are installed
2. **Network errors**: Print error message and return None
3. **Data errors**: Return None or empty DataFrame
4. **Invalid inputs**: Print error message and return None

**Best Practices:**

- Always check return values for None
- Use try-except blocks for critical operations
- Add delays between API calls to avoid rate limiting
- Cache results when possible

---

## Performance Tips

1. **Batch processing**: Process multiple stocks in batches
2. **Caching**: Save results to avoid repeated API calls
3. **Parallel processing**: Use multiprocessing for large datasets
4. **Data filtering**: Filter data early to reduce memory usage

---

## Common Issues

### Issue 1: Chrome/ChromeDriver not found

**Solution**: Install Chrome browser, webdriver-manager will handle the rest

### Issue 2: Baostock connection timeout

**Solution**: Check network connection, retry with exponential backoff

### Issue 3: Sina Finance blocking requests

**Solution**: Add longer delays between requests, use rotating proxies

### Issue 4: Missing data for recent dates

**Solution**: Use `isCurrent=True` to append real-time data

---

## Version History

- **v1.0.0** (2026-03-12): Initial release
  - Real-time quotes from Sina Finance
  - Historical K-line data from Baostock
  - Boom day detection
  - Moving average analysis
  - Stock list management
