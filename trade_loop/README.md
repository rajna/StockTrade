# stock-trade 交易循环（Agent A ⇄ Agent B）

双 agent 闭环：**A（主控）管账户与编排，B（决策者）只管出决策和复盘**。

```
┌────────────── Agent A (主控, default项目) ──────────────┐
│ 1. init 账户      python3 orchestrator.py init ...      │
│ 2. 取观察数据      python3 orchestrator.py prompt        │
│ 3. coms_send ──观察数据──▶ B                            │
│    coms_await ◀──决策JSON── B                            │
│ 4. 执行交易       python3 orchestrator.py step --decision 买入 --price 9.18 --qty 1000
│ 5. 算盈亏         python3 orchestrator.py pnl            │
│ 6. coms_send ──盈亏反馈──▶ B  ◀──复盘确认── coms_await   │
│ 7. 按需安排下一轮(回到 2)                                 │
└──────────────────────────────────────────────────────────┘
```

## 前置条件

| 条件 | 状态 |
|---|---|
| stock-trade 服务(7860) | ✅ 运行中 |
| 决策者 B(stock-coder, default项目) | ⚠️ **需终端手动启动**(见下) |
| coms 同 project 命名空间 | ✅ A 当前在 default |

## 启动

### 终端 2：启动决策者 B

```bash
pi -e /Users/rama/.pi/agent/extensions/local-coms.ts \
   --cname stock-coder --project default \
   --purpose "A股交易决策者:接收观察数据prompt输出JSON决策,接收盈亏反馈消化后确认继续"
```

B 启动后第一条消息让它读角色文件：
`请阅读 /Users/rama/Documents/agi_nanobot/nanobot/nanobot/skills/stock-trade/trade_loop/coder_prompt.md 并确认角色。`

### 终端 1（当前 pi = Agent A）：跑一轮

```
1. python3 .../trade_loop/orchestrator.py init --stock sh.301171 --cash 100000 --date 2025-08-14 --hold-period 5
2. python3 .../trade_loop/orchestrator.py prompt        # 复制输出
3. coms_send target=stock-coder prompt=<观察数据文本>    # 用 pi 工具
   coms_await msg_id=...                                 # 得到决策JSON
4. python3 .../trade_loop/orchestrator.py step --decision <买入> --price <p> --qty <q>
5. python3 .../trade_loop/orchestrator.py pnl
6. coms_send target=stock-coder prompt=<盈亏反馈文本>
   coms_await msg_id=...                                 # B 复盘确认
7. 回到 2（下一轮）
```

### 持股周期与股票切换

- 初始化可设 `--hold-period N`（默认 5）：当前股票持有满 N 个交易日后才允许切换
- 查看当前持有进度：`python3 .../orchestrator.py pnl` 返回里带 hold 字段（hold_days/hold_period/can_switch）
- 切换股票（需持有满周期，否则 409 报错）：
  ```
  python3 .../orchestrator.py switch --random                 # 随机选股（默认）
  python3 .../orchestrator.py switch --stock sz.000001        # 指定股票
  python3 .../orchestrator.py switch --random --force         # 跳过周期校验强制切换
  ```
- 切换时自动清仓当前持仓、新股票对齐到当前游戏日期、持股周期重新计算
- `loop_state.json` 记录当前 stock，切换后自动更新

## 盈亏语义（A 反馈给 B 的内容）

- **总资产变化** = step 前后总资产差（含佣金/价差）
- **未实现盈亏** = 当前持仓浮盈（从 portfolio_text 解析）
- B 复盘基于：`决策 → 成交 → 账户变化` 三元组

## 文件

- `orchestrator.py` — A 侧 API 封装（init/prompt/step/pnl）
- `coder_prompt.md` — B 角色提示词
- `loop_state.json` — A 侧会话状态（自动生成）

## 参考

- astro_stock 闭环（textron-agent/workflow.md）：planner→coder 同构，含审计与 Textron 学习接入
- 若需接入 Textron 学习：B 的每轮复盘 HighEntropy 由 hook 自动捕获，A 可在反馈消息中附带 `<HighEntropy>` 结构化复盘
