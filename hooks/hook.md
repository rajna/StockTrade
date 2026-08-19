# Stock Trading AI Hook

## Hook: ai_trading_strategy_generator

### 触发时机
当`ai_trading_loop.py`执行到`request_ai_strategy()`方法时触发

### 输入数据
```json
{
  "portfolio_result": "render_portfolio()的完整返回值",
  "stock_code": "sz.002261",
  "current_date": "2026-03-03",
  "cash_balance": 100000.00,
  "holdings": {}
}
```

### 期望输出
```json
{
  "decision": "买入/卖出/持有/不建仓",
  "tradePrice": "35.83",
  "tradeQuantity": "1000",
  "confidence": "高/中/低"
}
```

### 提示词模板
```
根据以下股票投资组合分析，生成交易策略：

{portfolio_result}

请严格按照以下格式要求组织你的回答，用中文回答：
你必须将推理思考方法等放到reasoning,reasoningAbstract,reasoningSymbol标签中
<reasoning>详细推理过程(或交易策略)</reasoning>
<reasoningAbstract>用简短文字抽象类似问题(或股票走势)的推理过程(或交易策略)</reasoningAbstract>
<reasoningSymbol>推理过程(或交易策略)的内容要被或摘要或抽象或符号化为少于7个词组成的记号</reasoningSymbol>
<functionAbstract>交易策略或信号捕捉的 Python code </functionAbstract>
<functionSymbol>Python program name</functionSymbol>
最终决策和关键信息用以下JSON格式输出，确保无需额外处理即可被程序解析：
{{
"decision": "买入/卖出/持有/不建仓",
"tradePrice": "买入/卖出的精确价格，不是价格范围",
"tradeQuantity":"买入/卖出的股票精确数量，不是范围",
"confidence": "高/中/低"
}}
```

### Hook处理流程
1. 接收`portfolio_result`数据
2. 使用提示词模板生成完整提示词
3. 调用AI生成交易策略
4. 解析AI返回的JSON格式交易决策
5. 返回标准化的交易策略对象

### 错误处理
- 如果AI返回格式错误，使用默认策略"不建仓"
- 如果AI返回价格或数量无效，使用0值
- 记录所有AI生成的策略用于后续分析