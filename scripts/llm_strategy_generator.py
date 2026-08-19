#!/usr/bin/env python3
"""
LLM策略生成器 - 直接调用LLM生成交易策略
"""

import json
import re
from typing import Dict, Any

class LLMStrategyGenerator:
    """基于LLM的AI策略生成器"""
    
    def __init__(self, llm_client=None):
        """
        初始化LLM策略生成器
        
        Args:
            llm_client: LLM客户端实例（如果可用）
        """
        self.llm_client = llm_client
    
    def generate_strategy(self, portfolio_result: str, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用LLM生成交易策略
        
        Args:
            portfolio_result: render_portfolio()的返回值
            game_state: 当前游戏状态
            
        Returns:
            Dict: 交易策略
        """
        # 构建提示词
        prompt = self._build_prompt(portfolio_result, game_state)
        
        # 如果LLM客户端可用，调用LLM
        if self.llm_client:
            try:
                response = self.llm_client.generate(prompt)
                strategy = self._parse_strategy(response)
                return strategy
            except Exception as e:
                print(f"LLM调用失败: {e}")
        
        # 如果LLM不可用或失败，返回默认策略
        return self._get_default_strategy()
    
    def _build_prompt(self, portfolio_result: str, game_state: Dict[str, Any]) -> str:
        """构建LLM提示词"""
        prompt = f"""
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
"""
        return prompt
    
    def _parse_strategy(self, response: str) -> Dict[str, Any]:
        """
        解析LLM响应，提取交易策略
        
        Args:
            response: LLM的响应文本
            
        Returns:
            Dict: 解析后的交易策略
        """
        try:
            # 尝试从响应中提取JSON
            json_match = re.search(r'\{[^{}]*"decision"[^{}]*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                strategy = json.loads(json_str)
                
                # 验证必需字段
                required_fields = ['decision', 'tradePrice', 'tradeQuantity', 'confidence']
                if all(field in strategy for field in required_fields):
                    return strategy
            
            # 如果JSON解析失败，返回默认策略
            print("⚠️ 无法从LLM响应中解析出有效的交易策略，使用默认策略")
            return self._get_default_strategy()
            
        except Exception as e:
            print(f"⚠️ 解析LLM响应失败: {e}，使用默认策略")
            return self._get_default_strategy()
    
    def _get_default_strategy(self) -> Dict[str, Any]:
        """获取默认交易策略"""
        return {
            "decision": "不建仓",
            "tradePrice": "0.00",
            "tradeQuantity": "0",
            "confidence": "中"
        }

class MockLLMClient:
    """模拟LLM客户端（用于测试）"""
    
    def generate(self, prompt: str) -> str:
        """生成模拟LLM响应"""
        return """
<reasoning>基于当前投资组合分析，现金余额$100,000.00，总资产$100,000.00，当前无持仓。根据量价关系分析，建议观望等待明确信号。</reasoning>
<reasoningAbstract>现金观望策略</reasoningAbstract>
<reasoningSymbol>现金观望</reasoningSymbol>
<functionAbstract>def check_volume_trend(data): return 'wait'</functionAbstract>
<functionSymbol>volume_checker</functionSymbol>
{
"decision": "不建仓",
"tradePrice": "0.00",
"tradeQuantity": "0",
"confidence": "中"
}
"""

if __name__ == "__main__":
    # 测试LLM策略生成器
    print("🧪 测试LLM策略生成器")
    
    # 创建模拟LLM客户端
    mock_llm = MockLLMClient()
    
    # 创建LLM策略生成器
    generator = LLMStrategyGenerator(llm_client=mock_llm)
    
    # 测试生成策略
    portfolio_result = "当前日期: 2026-03-03\n当前股票: sz.002261\n现金余额: $100,000.00\n当前无持仓"
    game_state = {
        "current_date": "2026-03-03",
        "cash_balance": 100000.00,
        "holdings": {}
    }
    
    strategy = generator.generate_strategy(portfolio_result, game_state)
    
    print("📊 生成的交易策略:")
    print(f"  决策: {strategy['decision']}")
    print(f"  价格: ${strategy['tradePrice']}")
    print(f"  数量: {strategy['tradeQuantity']}股")
    print(f"  信心度: {strategy['confidence']}")
    
    print("\n✅ LLM策略生成器测试完成！")