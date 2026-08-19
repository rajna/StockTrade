# Stock Trade Skill - Usage Examples

## 🚀 Quick Start Examples

### Example 1: Basic Stock Analysis
```python
from scripts.stock_data_fetcher import get_stock_daily_data, detect_boom_day, drawK

# Get historical data
df = get_stock_daily_data('sh.600000', '2025-01-01', '2025-03-12', isCurrent=True)

# Detect boom days
boom_days = detect_boom_day(df)
print(f"Found {len(boom_days)} boom days")

# Draw K-line chart
drawK(df, dateArray=boom_days['date'].tolist())
```

### Example 2: AI Trading Simulation
```python
from scripts.stock_data_fetcher import StockTradingGame, TradingDecision, handle_trade

# Initialize trading game
game = StockTradingGame(
    stock_code='sh.600000',
    initial_cash=100000.0,
    date_start='2025-01-01'
)

# AI trading decision
decision: TradingDecision = {
    'reasoning': 'MA5上穿MA10形成金叉，买入信号强烈',
    'reasoning_abstract': '均线金叉',
    'reasoning_symbol': 0.85,
    'decision': '买入',
    'confidence': 'high',
    'tradePrice': 10.50,
    'quantity': 1000
}

# Execute trade
handle_trade(game, str(decision))
```

### Example 3: LLM Data Integration
```python
from scripts.stock_data_fetcher import stock_data_to_llm_string, get_stock_daily_data

# Get historical data
df = get_stock_daily_data('sh.600000', '2025-01-01', '2025-03-12')

# Convert to LLM-friendly format
llm_data = stock_data_to_llm_string(df)

# Send to AI model for analysis
# response = ai_model.analyze_stock_data(llm_data)
```

## 🎮 Advanced Trading Examples

### Example 4: Complete Trading Workflow
```python
from scripts.stock_data_fetcher import (
    StockTradingGame, TradingDecision, handle_trade, 
    next_trading_day, check_trade_finished, render_portfolio
)

# Initialize game
game = StockTradingGame('sh.600000', 100000.0, '2025-01-01')

# Run trading simulation
trade_count = 0
max_trades = 10

while not check_trade_finished(game, trade_count) and trade_count < max_trades:
    # AI makes decision
    decision = make_ai_decision(game)
    
    # Execute trade
    handle_trade(game, str(decision))
    trade_count += 1
    
    # Show portfolio
    print(render_portfolio(game))
    
    # Advance to next day
    if not next_trading_day(game):
        break

# Show final results
final_portfolio = get_portfolio_value(game)
print(f"Final P&L: ${final_portfolio['unrealized_pnl']:,.2f}")
```

### Example 5: Portfolio Management
```python
from scripts.stock_data_fetcher import get_portfolio_value, render_portfolio

# Get portfolio metrics
portfolio_info = get_portfolio_value(game)
print(f"Total Value: ${portfolio_info['total_value']:,.2f}")
print(f"Cash Balance: ${portfolio_info['cash_balance']:,.2f}")
print(f"Portfolio Value: ${portfolio_info['portfolio_value']:,.2f}")
print(f"P&L: ${portfolio_info['unrealized_pnl']:,.2f} ({portfolio_info['unrealized_pnl_percent']:+.2f}%)")

# Render detailed portfolio
portfolio_status = render_portfolio(game)
print(portfolio_status)
```

## 🤖 AI Decision Examples

### Example 6: AI Trading Decision Logic
```python
def make_ai_decision(game):
    """AI trading decision function"""
    current_price = game.game_state['current_prices'][game.game_state['current_stock']]['close']
    portfolio_info = get_portfolio_value(game)
    
    # AI logic based on market conditions
    if current_price > 10.0 and portfolio_info['unrealized_pnl_percent'] > 5:
        return TradingDecision(
            reasoning='价格突破10元且盈利超过5%，加仓买入',
            reasoning_abstract='突破加仓',
            reasoning_symbol=0.9,
            decision='买入',
            confidence='high',
            tradePrice=current_price * 1.01,
            quantity=500
        )
    elif current_price < 9.0 and portfolio_info['unrealized_pnl_percent'] < -3:
        return TradingDecision(
            reasoning='价格跌破9元且亏损超过3%，止损卖出',
            reasoning_abstract='止损',
            reasoning_symbol=0.8,
            decision='卖出',
            confidence='high',
            tradePrice=current_price * 0.99,
            quantity=1000
        )
    else:
        return TradingDecision(
            reasoning='价格在合理区间内，持有观望',
            reasoning_abstract='区间震荡',
            reasoning_symbol=0.5,
            decision='持有',
            confidence='medium',
            tradePrice=0,
            quantity=0
        )
```

### Example 7: Multi-Stock Trading
```python
def multi_stock_trading():
    """Trade multiple stocks"""
    stocks = ['sh.600000', 'sz.000001', 'sh.600036']
    
    for stock in stocks:
        try:
            game = StockTradingGame(stock, 50000.0, '2025-01-01')
            
            # AI decision for this stock
            decision = make_ai_decision(game)
            
            # Execute trade
            handle_trade(game, str(decision))
            
            # Show results
            print(f"{stock}: {decision['decision']} {decision['quantity']} shares")
            
        except Exception as e:
            print(f"Error trading {stock}: {e}")
```

## 📊 Data Analysis Examples

### Example 8: Technical Analysis
```python
from scripts.stock_data_fetcher import detect_boom_day, check_price_near_ma_safe

# Get historical data
df = get_stock_daily_data('sh.600000', '2025-01-01', '2025-03-12')

# Detect boom days
boom_days = detect_boom_day(df)
print(f"Boom days: {len(boom_days)}")

# Check MA positions
near_ma20 = check_price_near_ma_safe(df, 20, 2.0)
near_ma60 = check_price_near_ma_safe(df, 60, 2.0)

print(f"Near MA20: {near_ma20}")
print(f"Near MA60: {near_ma60}")

# Analyze boom day patterns
if len(boom_days) > 0:
    print("Boom day analysis:")
    print(boom_days[['date', 'close', 'volume', 'merge_count']])
```

### Example 9: Market Data Integration
```python
from scripts.stock_data_fetcher import get_current, get_stock_daily_data

# Get real-time quote
current_data = get_current('sh.600000')
if current_data:
    print(f"Current price: {current_data[4]}")

# Get historical data with real-time integration
df = get_stock_daily_data('sh.600000', '2025-01-01', '2025-03-12', isCurrent=True)
print(f"Latest data point: {df.iloc[-1]}")
```

## 🔗 LLM Integration Examples

### Example 10: LLM Stock Analysis
```python
from scripts.stock_data_fetcher import stock_data_to_llm_string, get_stock_daily_data

# Get data
df = get_stock_daily_data('sh.600000', '2025-01-01', '2025-03-12')

# Convert to LLM format
llm_data = stock_data_to_llm_string(df)

# Prepare prompt for AI model
prompt = f"""
请分析以下股票数据，并提供投资建议：

{llm_data}

请分析：
1. 价格趋势
2. 成交量变化
3. 技术指标
4. 投资建议
"""

# Send to AI model
# response = ai_model.generate_response(prompt)
```

### Example 11: AI-Powered Trading Assistant
```python
class AITradingAssistant:
    def __init__(self):
        self.game = None
        self.decision_history = []
    
    def analyze_stock(self, stock_code, start_date='2025-01-01'):
        """Analyze stock and provide AI recommendations"""
        # Initialize game
        self.game = StockTradingGame(stock_code, 100000.0, start_date)
        
        # Get market data
        market_data = self.game.game_state['current_prices'][stock_code]
        
        # AI analysis
        analysis = {
            'stock_code': stock_code,
            'current_price': market_data['close'],
            'recommendation': self.get_ai_recommendation(),
            'confidence': self.calculate_confidence(),
            'risk_level': self.assess_risk()
        }
        
        return analysis
    
    def get_ai_recommendation(self):
        """Get AI trading recommendation"""
        # AI logic here
        return '买入'
    
    def calculate_confidence(self):
        """Calculate confidence score"""
        return 0.85
    
    def assess_risk(self):
        """Assess risk level"""
        return 'medium'
```

## 🎯 Real-World Use Cases

### Example 12: Backtesting Strategy
```python
def backtest_strategy(stock_code, start_date, end_date, strategy_func):
    """Backtest a trading strategy"""
    game = StockTradingGame(stock_code, 100000.0, start_date)
    
    while game.game_state['current_date'] <= end_date:
        # Apply strategy
        decision = strategy_func(game)
        
        # Execute trade
        handle_trade(game, str(decision))
        
        # Advance to next day
        if not next_trading_day(game):
            break
    
    # Calculate performance
    final_portfolio = get_portfolio_value(game)
    return {
        'total_return': final_portfolio['unrealized_pnl_percent'],
        'final_value': final_portfolio['total_value'],
        'trades_executed': len(game.game_state['transaction_history'])
    }
```

### Example 13: Risk Management
```python
def risk_management_game():
    """Game with risk management rules"""
    game = StockTradingGame('sh.600000', 100000.0, '2025-01-01')
    
    max_loss = -0.05  # 5% maximum loss
    max_profit = 0.10  # 10% maximum profit
    
    while True:
        # Check risk limits
        portfolio_info = get_portfolio_value(game)
        
        if portfolio_info['unrealized_pnl_percent'] <= max_loss:
            print(f"Stop loss triggered at {portfolio_info['unrealized_pnl_percent']:.2f}%")
            break
            
        if portfolio_info['unrealized_pnl_percent'] >= max_profit:
            print(f"Take profit triggered at {portfolio_info['unrealized_pnl_percent']:.2f}%")
            break
        
        # AI decision
        decision = make_ai_decision(game)
        handle_trade(game, str(decision))
        
        # Advance
        if not next_trading_day(game):
            break
    
    return game
```

## 🚨 Error Handling Examples

### Example 14: Robust Trading
```python
def robust_trading():
    """Trading with comprehensive error handling"""
    try:
        game = StockTradingGame('sh.600000', 100000.0, '2025-01-01')
        
        while True:
            try:
                # AI decision
                decision = make_ai_decision(game)
                
                # Execute trade with error handling
                try:
                    result = handle_trade(game, str(decision))
                    print(f"Trade executed: {result['message']}")
                except ValueError as e:
                    print(f"Trade failed: {e}")
                
                # Advance day
                if not next_trading_day(game):
                    break
                    
            except Exception as e:
                print(f"Day processing error: {e}")
                break
                
    except Exception as e:
        print(f"Game initialization error: {e}")
    
    return game
```

## 📈 Performance Monitoring

### Example 15: Performance Tracking
```python
def track_performance(game):
    """Track and display performance metrics"""
    portfolio_info = get_portfolio_value(game)
    
    metrics = {
        'total_return': portfolio_info['unrealized_pnl_percent'],
        'sharpe_ratio': calculate_sharpe_ratio(game),
        'max_drawdown': calculate_max_drawdown(game),
        'win_rate': calculate_win_rate(game),
        'trade_frequency': len(game.game_state['transaction_history'])
    }
    
    print("Performance Metrics:")
    for key, value in metrics.items():
        print(f"{key}: {value}")
    
    return metrics
```

---

These examples demonstrate the comprehensive capabilities of the Stock Trade skill, from basic data analysis to advanced AI-powered trading simulations. Each example can be adapted for specific use cases and integrated into larger trading systems.