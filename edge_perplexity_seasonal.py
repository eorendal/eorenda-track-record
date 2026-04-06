import yfinance as yf
import pandas as pd
import numpy as np
import os

TICKERS = ["SPY", "QQQ", "DIA", "XLK", "XLF"]
COST_PER_TRADE = 0.0002

end = pd.Timestamp.today().normalize()
start = end - pd.Timedelta(days=365 * 2 + 40)

px = yf.download(
    TICKERS,
    start=start.strftime("%Y-%m-%d"),
    end=end.strftime("%Y-%m-%d"),
    auto_adjust=True,
    progress=False
)["Close"]

if isinstance(px, pd.Series):
    px = px.to_frame()

def backtest_tuesday(close):
    close = close.dropna()
    ret = close.pct_change()
    signal = close.index.dayofweek == 1  # Tuesday

    trade_rets = ret.shift(-1)[signal].dropna() - COST_PER_TRADE
    equity = (1 + trade_rets).cumprod()
    drawdown = equity / equity.cummax() - 1

    return {
        "Number of trades": int(len(trade_rets)),
        "Average return": float(trade_rets.mean()) if len(trade_rets) else np.nan,
        "Win rate": float((trade_rets > 0).mean()) if len(trade_rets) else np.nan,
        "Max drawdown": float(drawdown.min()) if len(drawdown) else np.nan,
        "Total return": float(equity.iloc[-1] - 1) if len(equity) else np.nan,
    }

rows = []
for ticker in TICKERS:
    r = backtest_tuesday(px[ticker])
    rows.append([
        ticker,
        r["Number of trades"],
        r["Average return"],
        r["Win rate"],
        r["Max drawdown"],
        r["Total return"]
    ])

df = pd.DataFrame(
    rows,
    columns=["Ticker", "Number of trades", "Average return", "Win rate", "Max drawdown", "Total return"]
)

os.makedirs("output", exist_ok=True)
df.to_csv("output/tuesday_strategy_results.csv", index=False)

for _, row in df.iterrows():
    print(row["Ticker"])
    print(f"Number of trades: {int(row['Number of trades'])}")
    print(f"Average return: {row['Average return']:.6f}")
    print(f"Win rate: {row['Win rate']:.4f}")
    print(f"Max drawdown: {row['Max drawdown']:.6f}")
    print(f"Total return: {row['Total return']:.6f}")
    print()

