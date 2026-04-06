import yfinance as yf
import pandas as pd
import numpy as np
import time

print("SCRIPT STARTED")

# -----------------------------
# CONFIG
# -----------------------------
tickers = [
    "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA",
    "UNH","XOM","JNJ","JPM","V","PG","MA","HD",
    "CVX","ABBV","MRK","PEP","KO","COST","AVGO","ADBE",
    "WMT","MCD","CSCO","ACN","DHR","VZ","NFLX",
    "LIN","NKE","AMD","CRM","TXN","PM","INTC","HON",
    "NEE","UNP","LOW","UPS","ORCL","QCOM","RTX","IBM",
    "AMGN","CAT","INTU","SPGI","GE","PLD","MDT","ISRG",
    "BKNG","NOW","BLK","AXP","GS","MS","DE","ADI","MU"
]

start = "2005-01-01"
end   = "2026-01-01"

# -----------------------------
# DOWNLOAD (BATCHED)
# -----------------------------
def download_batch(tickers):
    return yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=False,
        progress=False,
        threads=False
    )

chunks = [tickers[i:i+10] for i in range(0, len(tickers), 10)]
data_list = []

for chunk in chunks:
    df = download_batch(chunk)

    if isinstance(df.columns, pd.MultiIndex):
        if "Adj Close" in df.columns.get_level_values(0):
            df = df["Adj Close"]
        else:
            df = df["Close"]

    data_list.append(df)
    time.sleep(1)

data = pd.concat(data_list, axis=1)
data = data.loc[:, ~data.columns.duplicated()]
data = data.dropna(how="all")

print("DATA SHAPE:", data.shape)

# -----------------------------
# RETURNS
# -----------------------------
returns = data.pct_change()

# -----------------------------
# MOMENTUM (12–1)
# -----------------------------
momentum = (data.shift(21) / data.shift(252)) - 1

# -----------------------------
# VOLATILITY (FOR WEIGHTING)
# -----------------------------
vol = returns.rolling(20).std()

# -----------------------------
# MONTHLY REBALANCE DATES
# -----------------------------
monthly_dates = data.resample("M").last().index
monthly_dates = [d for d in monthly_dates if d in data.index]

# -----------------------------
# BACKTEST
# -----------------------------
portfolio_returns = []

for i in range(len(monthly_dates) - 1):

    date = monthly_dates[i]
    next_date = monthly_dates[i + 1]

    signal = momentum.loc[date].dropna()

    # need enough cross-section
    if len(signal) < 40:
        continue

    ranked = signal.sort_values(ascending=False)

    long_assets = ranked.head(20).index
    short_assets = ranked.tail(20).index

    vol_long = vol.loc[date, long_assets]
    vol_short = vol.loc[date, short_assets]

    if vol_long.isna().any() or vol_short.isna().any():
        continue

    # inverse vol weights
    w_long = 1 / vol_long
    w_long = w_long / w_long.sum()

    w_short = 1 / vol_short
    w_short = w_short / w_short.sum()

    price_today_long = data.loc[date, long_assets]
    price_next_long  = data.loc[next_date, long_assets]

    price_today_short = data.loc[date, short_assets]
    price_next_short  = data.loc[next_date, short_assets]

    ret_long = (price_next_long / price_today_long) - 1
    ret_short = (price_next_short / price_today_short) - 1

    # market neutral return
    portfolio_return = (w_long * ret_long).sum() - (w_short * ret_short).sum()

    portfolio_returns.append(portfolio_return)

returns_series = pd.Series(portfolio_returns)

# -----------------------------
# METRICS
# -----------------------------
if len(returns_series) == 0:
    print("❌ NO TRADES GENERATED")
else:
    periods_per_year = 12

    cagr = (1 + returns_series).prod() ** (periods_per_year / len(returns_series)) - 1
    volatility = returns_series.std() * np.sqrt(periods_per_year)
    sharpe = cagr / volatility if volatility != 0 else 0

    cum = (1 + returns_series).cumprod()
    peak = cum.cummax()
    drawdown = (cum - peak) / peak
    max_dd = drawdown.min()

    print("\nRESULTS:")
    print("CAGR:", round(cagr, 4))
    print("VOL:", round(volatility, 4))
    print("SHARPE:", round(sharpe, 4))
    print("MAX DRAWDOWN:", round(max_dd, 4))

print("SCRIPT COMPLETED")
