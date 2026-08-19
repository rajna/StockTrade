---
name: stock-trade-ai-strategy
description: 根据股票投资组合分析生成AI交易策略
trigger:
  event: generate_trading_strategy
  priority: 100
---

# Generate Trading Strategy Hook

在AI交易循环中触发，用于生成交易策略：

1. 接收投资组合分析结果
2. 使用AI分析量价关系和技术指标
3. 生成交易决策（买入/卖出/持有/不建仓）
4. 返回JSON格式的交易策略

## 输入数据

```json
{
  "portfolio_result": "render_portfolio()的完整返回值",
  "game_state": {
    "current_date": "2026-03-03",
    "cash_balance": 100000.00,
    "holdings": {}
  },
  "request_type": "generate_trading_strategy"
}
```

## 输出数据

```json
{
  "strategy": {
    "decision": "买入/卖出/持有/不建仓",
    "tradePrice": "35.83",
    "tradeQuantity": "1000",
    "confidence": "高/中/低"
  }
}
```

## AI提示词模板

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