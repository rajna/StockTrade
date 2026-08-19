---
name: stock-trade
description: Comprehensive A-share stock data fetching, analysis, and trading simulation tool with real-time quotes, historical K-lines, technical pattern detection, professional K-line chart visualization, and AI-powered trading game. Use when the user needs to (1) Get real-time stock quotes, (2) Fetch historical K-line data, (3) Analyze stock patterns like boom days (放量阳线), (4) Check price position relative to moving averages, (5) Get complete stock list, (6) Perform technical analysis on Chinese A-share stocks, (7) Create professional K-line charts with volume indicators and moving averages, (8) Run AI-powered trading simulations, or (9) Convert stock data to LLM-friendly formats.
---

# Stock Trade

A comprehensive tool for fetching, analyzing, and simulating Chinese A-share stock market data with AI-powered trading capabilities.

## Core Capabilities

### 1. Real-time Stock Quotes
Fetch current stock prices and trading data from Sina Finance.

### 2. Historical K-line Data
Retrieve historical daily/weekly/monthly K-line data with adjustable date ranges.

### 3. Technical Pattern Detection
Identify significant trading patterns like boom days (启动放量阳线).

### 4. Moving Average Analysis
Check price position relative to moving averages.

### 5. Stock List Management
Get complete A-share stock list with codes and names.

### 6. AI Trading Simulation
Run AI-powered trading simulations with realistic market conditions.

### 7. LLM Data Conversion
Convert stock data to LLM-friendly string formats for AI analysis.

## Quick Start

### Get Real-time Quote

```python
from scripts.stock_data_fetcher import get_current

# Get real-time data for a stock
data = get_current('sh.600000')  # Shanghai stock
data = get_current('sz.000001')  # Shenzhen stock

# Returns: [date, open, high, low, close, volume]
```

### Get Historical K-line Data

```python
from scripts.stock_data_fetcher import get_stock_daily_data

# Get daily K-line data
df = get_stock_daily_data(
    stock_code='sh.600000',
    start_date='2026-01-01',
    end_date='2026-03-12',
    k_type='d',  # 'd'=daily, 'w'=weekly, 'm'=monthly
    isCurrent=True  # Include real-time data
)

# Returns DataFrame with columns: date, open, high, low, close, volume, pctChg
```

### Detect Boom Days (放量阳线)

```python
from scripts.stock_data_fetcher import detect_boom_day

# Identify significant upward momentum days
boom_days = detect_boom_day(df)

# Returns DataFrame with boom day details
```

### Check Price Near Moving Average

```python
from scripts.stock_data_fetcher import check_price_near_ma_safe

# Check if price is within 2% of 20-day MA
is_near = check_price_near_ma_safe(df, rolling_number=20, threshold=2.0)
```

### Get All A-share Stocks

```python
from scripts.stock_data_fetcher import get_all_stocks

# Get complete stock list
stocks = get_all_stocks()

# Returns DataFrame with columns: code, name
```

### Draw K-line Charts

```python
from scripts.stock_data_fetcher import get_stock_daily_data, drawK

# Get historical data
df = get_stock_daily_data('sh.600000', '2026-01-01', '2026-03-12', isCurrent=True)

# Draw K-line chart with optional special date highlighting
drawK(df)  # Basic K-line chart
drawK(df, dateArray='2026-03-01,2026-03-05')  # Highlight specific dates
drawK(df, dateArray=['2026-03-01', '2026-03-05'])  # Highlight specific dates (list format)

# Returns: Displays interactive matplotlib chart with:
# - Candlestick chart with volume bars
# - Moving averages (MA5, MA10, MA18)
# - Special date highlighting (purple color)
# - Professional styling with Chinese font support
```

### Convert Stock Data to LLM Format

```python
from scripts.stock_data_fetcher import stock_data_to_llm_string

# Convert DataFrame to LLM-friendly string format
llm_data = stock_data_to_llm_string(df)

# Returns formatted string suitable for AI analysis
```

### Run AI Trading Simulation

```python
from scripts.stock_data_fetcher import StockTradingGame, TradingDecision

# Initialize trading game
game = StockTradingGame(
    stock_code='sh.600000',
    initial_cash=100000.0,
    date_start='2015-12-03 00:00:00'
)

# Get current market data
market_data = get_current_market_data(game)

# Make trading decision
decision: TradingDecision = {
    'reasoning': 'Based on technical analysis',
    'reasoning_abstract': 'MA crossover pattern detected',
    'reasoning_symbol': 0.8,
    'decision': '买入',
    'confidence': 'high',
    'tradePrice': 10.50,
    'quantity': 1000
}

# Execute trade
handle_trade(game, str(decision))
```

## Advanced Features

### Boom Day Detection Algorithm

The `detect_boom_day()` function identifies significant upward momentum days based on:

1. **Volume surge**: Volume > 1.35x 5-day average volume
2. **Price gain**: Daily gain > 3.5% OR limit-up (≥9.9%)
3. **Merge logic**: Consecutive days with new highs are merged into one pattern

This helps identify potential trend initiation points.

### Real-time Data Integration

When `isCurrent=True` in `get_stock_daily_data()`, the function:
1. Fetches historical data from Baostock
2. Appends current real-time quote from Sina Finance
3. Returns complete dataset up to the current moment

### Moving Average Analysis

The `check_price_near_ma_safe()` function checks if current price is within a threshold percentage of a specified moving average, useful for:
- Support/resistance level identification
- Entry/exit timing
- Trend confirmation

### AI Trading Game

The `StockTradingGame` class provides a comprehensive trading simulation environment:

#### Key Features:
- **Historical Data Loading**: Automatically loads K-line data from specified start date
- **Boom Day Detection**: Only starts trading after detecting boom signals
- **Realistic Trading**: Includes commission fees, price limits, and market conditions
- **Portfolio Management**: Tracks positions, cash balance, and transaction history
- **AI Decision Integration**: Supports AI-generated trading decisions
- **Risk Management**: Stops trading when profit > 10% or loss > 5%


#### Trading Operations:
- `buy_stock()`: Execute buy orders with price validation
- `sell_stock()`: Execute sell orders with position validation
- `hold_position()`: Maintain current positions
- `no_position()`: Keep cash position
- `next_trading_day()`: Advance to next trading day
- `check_trade_finished()`: Check if trading should stop based on profit/loss

#### Data Conversion:
- `stock_data_to_llm_string()`: Convert DataFrame to LLM-friendly format
- `render_portfolio()`: Generate human-readable portfolio status
- `get_portfolio_value()`: Calculate portfolio metrics

## Data Types

### TradingDecision
```python
from typing import TypedDict

class TradingDecision(TypedDict):
    reasoning: str          # Detailed reasoning for the decision
    reasoning_abstract: str  # Abstract summary of reasoning
    reasoning_symbol: float # Confidence score (0-1)
    decision: str           # '买入', '卖出', '持有', '不建仓'
    confidence: str        # 'high', 'medium', 'low'
    tradePrice: float      # Target price for trade
    quantity: int          # Number of shares to trade
```

### StockPosition
```python
from typing import TypedDict
from datetime import datetime

class StockPosition(TypedDict):
    symbol: str        # Stock symbol
    quantity: int      # Number of shares
    avg_price: float   # Average purchase price
    timestamp: datetime # Purchase timestamp
```

### TradingGame
```python
from typing import TypedDict, Dict, List
from datetime import datetime

class TradingGame(TypedDict):
    cash_balance: float                    # Available cash
    portfolio: Dict[str, StockPosition]     # Current holdings
    transaction_history: List[Dict]        # Trade history
    current_prices: Dict[str, Dict]        # Current market prices
    pre_prices: Dict[str, float]          # Previous day prices
    current_date: datetime                 # Current trading date
    train_start_date: datetime            # Training start date
    current_stock: str                    # Current trading stock
    current_day_k_observing: str          # Daily K-line data for LLM
    current_week_k_observing: str         # Weekly K-line data for LLM
    current_month_k_observing: str        # Monthly K-line data for LLM
```

## Dependencies

Install required packages:

```bash
pip install akshare baostock selenium webdriver-manager beautifulsoup4 pandas lxml numpy talib matplotlib mplfinance
```

Or use the provided requirements.txt:

```bash
pip install -r scripts/requirements.txt
```

### Optional Dependencies

- **talib**: Technical analysis library for advanced indicators
- **matplotlib**: For K-line chart visualization
- **mplfinance**: For professional financial charting

## K-line Chart Visualization

The `drawK()` function provides professional K-line chart visualization with the following features:

### Features

- **Candlestick Chart**: Traditional OHLC candlesticks with proper coloring
- **Volume Bars**: Volume indicators with color-coded bars (red for up, green for down)
- **Moving Averages**: MA5 (blue), MA10 (red), MA18 (yellow) lines
- **Special Date Highlighting**: Purple coloring for specific dates
- **Professional Styling**: Chinese font support, grid lines, proper scaling
- **Dual Layout**: Main chart with price action, bottom chart with volume

### Usage Examples

```python
from scripts.stock_data_fetcher import get_stock_daily_data, drawK

# Get historical data
df = get_stock_daily_data('sh.600000', '2026-01-01', '2026-03-12', isCurrent=True)

# Basic chart
drawK(df)

# Highlight specific dates (comma-separated string)
drawK(df, dateArray='2026-02-01,2026-02-15,2026-03-01')

# Highlight specific dates (list format)
drawK(df, dateArray=['2026-02-01', '2026-02-15', '2026-03-01'])

# Highlight boom days
from scripts.stock_data_fetcher import detect_boom_day
boom_days = detect_boom_day(df)
if len(boom_days) > 0:
    drawK(df, dateArray=boom_days['date'].tolist())
```

### Chart Customization

The `drawK()` function automatically handles:
- Date formatting and scaling
- Color coding for price movements
- Moving average calculations
- Volume bar positioning
- Legend and axis labels
- Layout optimization

For advanced customization, you can access the underlying matplotlib objects and modify them as needed.

## Important Notes

### Stock Code Format

- Shanghai stocks: `sh.XXXXXX` (e.g., `sh.600000`)
- Shenzhen stocks: `sz.XXXXXX` (e.g., `sz.000001`)

### Data Sources

- **Real-time quotes**: Sina Finance (web scraping with Selenium)
- **Historical data**: Baostock API
- **Stock list**: Akshare API

### Rate Limiting

- Sina Finance: Add delays between requests to avoid blocking
- Baostock: Free API with rate limits, use responsibly

### Browser Requirements

Real-time quote fetching requires Chrome/Chromium browser and ChromeDriver, automatically managed by webdriver-manager.

## Error Handling

All functions include comprehensive error handling:
- Network errors: Retry with exponential backoff
- Missing data: Return None or empty DataFrame
- Invalid codes: Print error message and return None

## Example Workflow

### Basic Stock Analysis

```python
# 1. Get stock list
stocks = get_all_stocks()

# 2. Get historical data
df = get_stock_daily_data('sh.600000', '2026-01-01', '2026-03-12', isCurrent=True)

# 3. Detect boom days
boom_days = detect_boom_day(df)

# 4. Check MA position
is_near_ma20 = check_price_near_ma_safe(df, 20, 2.0)

# 5. Draw K-line chart
drawK(df)

# 6. Draw K-line chart with boom days highlighted
if len(boom_days) > 0:
    drawK(df, dateArray=boom_days['date'].tolist())

# 7. Analyze results
if len(boom_days) > 0:
    print(f"Found {len(boom_days)} boom days")
    print(boom_days[['date', 'close', 'volume', 'merge_count']])
```

### AI Trading Simulation

```python
from scripts.stock_data_fetcher import StockTradingGame, TradingDecision

# 1. Initialize trading game
game = StockTradingGame(
    stock_code='sh.600000',
    initial_cash=100000.0,
    date_start='2015-12-03 00:00:00'
)

# 2. Run trading simulation
while not check_trade_finished(game, 1):
    # Get current market data
    market_data = get_current_market_data(game)
    
    # Generate AI decision (example)
    decision: TradingDecision = {
        'reasoning': 'MA crossover pattern detected',
        'reasoning_abstract': 'Bullish signal',
        'reasoning_symbol': 0.8,
        'decision': '买入',
        'confidence': 'high',
        'tradePrice': 10.50,
        'quantity': 1000
    }
    
    # Execute trade
    handle_trade(game, str(decision))
    
    # Advance to next trading day
    next_trading_day(game)
    
    # Display portfolio status
    print(render_portfolio(game))

# 3. Get final results
final_portfolio = get_portfolio_value(game)
print(f"Final portfolio value: {final_portfolio['total_value']:.2f}")
print(f"Total P&L: {final_portfolio['unrealized_pnl']:.2f} ({final_portfolio['unrealized_pnl_percent']:.2f}%)")
```

### LLM Data Integration

```python
from scripts.stock_data_fetcher import get_stock_daily_data, stock_data_to_llm_string

# Get historical data
df = get_stock_daily_data('sh.600000', '2026-01-01', '2026-03-12', isCurrent=True)

# Convert to LLM-friendly format
llm_data = stock_data_to_llm_string(df)

# Use with AI models
response = ai_model.analyze_stock_data(llm_data)
```

## Testing

### Run Tests

```bash
# Test basic functionality
python scripts/test_kline.py

# Test K-line chart examples
python scripts/kline_example.py

# Test trading game
python scripts/test_trading_game.py
```

### Test Coverage

The test suite covers:
- Data retrieval from multiple sources
- Boom day detection algorithms
- K-line chart drawing functionality
- Error handling and edge cases
- Trading simulation mechanics
- LLM data conversion

## References

For detailed API documentation, see [references/API_REFERENCE.md].

## Version History

### v2.0.0 - Stock Trade
- Added comprehensive AI trading simulation capabilities
- Added LLM data conversion functions
- Added TradingDecision, StockPosition, TradingGame data types
- Enhanced StockTradingGame class with full trading functionality
- Added portfolio management and risk management features
- Improved error handling and validation

### v1.0.0 - Stock Data Fetcher
- Initial release with basic data fetching and analysis capabilities
- K-line chart visualization
- Technical pattern detection
- Real-time quote integration