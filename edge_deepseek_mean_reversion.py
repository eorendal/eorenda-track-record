import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

TICKERS = ["SPY", "QQQ", "DIA", "XLK", "XLF"]
TRANSACTION_COST = 0.0002
BACKTEST_YEARS = 2
LONG_THRESHOLD = -0.02
SHORT_THRESHOLD = 0.02

end_date = datetime.today()
start_date = end_date - timedelta(days=BACKTEST_YEARS * 365)

data = yf.download(
    tickers=TICKERS,
    start=start_date,
    end=end_date,
    group_by='ticker',
    auto_adjust=True,
    progress=False
)

open_df = pd.DataFrame()
close_df = pd.DataFrame()
for ticker in TICKERS:
    if ticker in data.columns.levels[0]:
        open_df[ticker] = data[ticker]['Open']
        close_df[ticker] = data[ticker]['Close']
    else:
        open_df[ticker] = data[ticker].Open
        close_df[ticker] = data[ticker].Close

open_df = open_df.dropna()
close_df = close_df.dropna()

daily_returns = close_df.pct_change().dropna()

trade_returns = []
daily_portfolio_returns = []

dates = daily_returns.index
for i in range(len(dates) - 1):
    t = dates[i]
    next_day = dates[i+1]
    
    rets_t = daily_returns.loc[t]
    worst_ticker = rets_t.idxmin()
    worst_return = rets_t.min()
    best_ticker = rets_t.idxmax()
    best_return = rets_t.max()
    
    trades_this_day = []
    
    if worst_return < LONG_THRESHOLD:
        open_price = open_df.loc[next_day, worst_ticker]
        close_price = close_df.loc[next_day, worst_ticker]
        raw_return = (close_price - open_price) / open_price
        net_return = raw_return - TRANSACTION_COST
        trades_this_day.append(net_return)
        trade_returns.append(net_return)
    
    if best_return > SHORT_THRESHOLD:
        open_price = open_df.loc[next_day, best_ticker]
        close_price = close_df.loc[next_day, best_ticker]
        raw_return = (open_price - close_price) / open_price
        net_return = raw_return - TRANSACTION_COST
        trades_this_day.append(net_return)
        trade_returns.append(net_return)
    
    if len(trades_this_day) > 0:
        daily_return = sum(trades_this_day) / len(trades_this_day)
    else:
        daily_return = 0.0
    daily_portfolio_returns.append(daily_return)

equity_curve = np.cumprod(1 + np.array(daily_portfolio_returns))
total_return = equity_curve[-1] - 1

running_peak = np.maximum.accumulate(equity_curve)
drawdowns = (running_peak - equity_curve) / running_peak
max_drawdown = np.max(drawdowns)

num_trades = len(trade_returns)
if num_trades > 0:
    avg_return = np.mean(trade_returns)
    win_rate = np.sum(np.array(trade_returns) > 0) / num_trades
else:
    avg_return = 0.0
    win_rate = 0.0

print(f"Number of trades: {num_trades}")
print(f"Average return: {avg_return:.6f}")
print(f"Win rate: {win_rate:.2%}")
print(f"Max drawdown: {max_drawdown:.2%}")
print(f"Total return: {total_return:.2%}")
