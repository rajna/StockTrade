# Stock Trading Game Web UI

这是 `scripts/stock_trading_game.py` 的 Web 界面与 Flask 服务封装。

## 启动

```bash
cd /Users/rama/Documents/agi_nanobot/nanobot/nanobot/skills/stock-trade/UI
python3 app.py
```

浏览器打开：

```text
http://127.0.0.1:7860
```

如需指定端口：

```bash
PORT=8080 python3 app.py
```

## 功能

- 初始化一次股票交易模拟
- 执行一次模拟：按买入/卖出/持有/不建仓决策调用 `handle_trade()`，随后调用 `next_trading_day()`
- 查看每一步模拟交易轨迹
- 查看当前交易账户：现金、持仓、市值、总资产、收益率
- 查看当前股票 K 线图以及 `render_portfolio()` 输出的日/周/月 K 线观察文本

## API

- `GET /api/health`
- `POST /api/init`
- `GET /api/state`
- `POST /api/step`
- `POST /api/advance`
- `GET /api/trajectory`
- `GET /api/kline`

## 说明

界面基于 `/Users/rama/Desktop/index2.html` 的交易面板模板改造，当前会话存储在 Flask 进程内存中，重启服务后需要重新初始化。
