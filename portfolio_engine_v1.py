import yfinance as yf
import pandas as pd
import numpy as np

INITIAL_CAPITAL = 1000
TICKERS = ["SPY", "QQQ", "DIA", "XLK", "XLF"]

THRESHOLD = 0.002  # 🔥 gating threshold

# ======================
# EDGE #1
# ======================
def edge1():

    data = yf.download(TICKERS, period="60d", interval="1d", group_by="ticker")

    close = pd.DataFrame()
    open_ = pd.DataFrame()

    for t in TICKERS:
        close[t] = data[t]["Close"]
        open_[t] = data[t]["Open"]

    overnight = open_ / close.shift(1) - 1
    overnight = overnight.dropna()

    returns = {}

    for i in range(1, len(overnight)):

        signal = overnight.iloc[i-1]

        top_assets = signal.nlargest(3)
        positive = top_assets[top_assets > 0]

        if len(positive) == 0:
            returns[overnight.index[i]] = 0
            continue

        weights = positive / positive.sum()
        today = overnight.iloc[i][positive.index]

        r = (today * weights).sum() - 0.0002
        returns[overnight.index[i]] = r

    return pd.Series(returns)

# ======================
# EDGE #2 (WITH STRENGTH)
# ======================
def edge2():

    all_data = {}

    for t in TICKERS:
        data = yf.download(t, interval="15m", period="30d")

        data = data.dropna()

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        data.index = data.index.tz_localize(None)

        all_data[t] = data

    returns = {}

    dates = set()
    for d in all_data.values():
        dates.update(d.index.date)

    dates = sorted(list(dates))

    for date in dates:

        signals = []
        future_returns = []

        for ticker, data in all_data.items():

            day = data[data.index.date == date]

            if len(day) < 10:
                continue

            open_price = day["Open"].iloc[0]
            early_price = day["Close"].iloc[3]

            late_open = day["Open"].iloc[-4]
            close_price = day["Close"].iloc[-1]

            early_return = early_price / open_price - 1
            late_return = close_price / late_open - 1

            signals.append(early_return)
            future_returns.append(late_return)

        if len(signals) < 2:
            continue

        strength = np.mean(np.abs(signals))

        r = np.mean([-ret for ret in future_returns]) - 0.0002

        returns[pd.Timestamp(date)] = (r, strength)

    return returns

# ======================
# GATED ENGINE
# ======================
def run():

    print("Running components...")

    e1 = edge1()
    e2 = edge2()

    common_dates = sorted(set(e1.index).intersection(set(e2.keys())))

    capital = INITIAL_CAPITAL
    equity = []

    for date in common_dates:

        r1 = e1.loc[date]
        r2, strength = e2[date]

        # 🔥 GATING LOGIC
        if strength > THRESHOLD:
            r = r2
        else:
            r = r1

        capital *= (1 + r)
        equity.append(capital)

    equity = np.array(equity)

    returns = pd.Series(np.diff(np.insert(equity, 0, INITIAL_CAPITAL)) / INITIAL_CAPITAL)

    print("\n========== PORTFOLIO ENGINE V7 (GATED) ==========")
    print("Total Return:", equity[-1] / INITIAL_CAPITAL - 1)
    print("Avg Return:", returns.mean())
    print("Win Rate:", (returns > 0).mean())
    print("Max Drawdown:",
          (equity / np.maximum.accumulate(equity) - 1).min())
    print("Observations:", len(equity))
    print("================================================\n")

if __name__ == "__main__":
    run()
