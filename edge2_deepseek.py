import yfinance as yf
import pandas as pd
import numpy as np

INITIAL_CAPITAL = 1000
TICKERS = ["SPY", "QQQ", "DIA", "XLK", "XLF"]

LONG_THRESHOLD = -0.02
SHORT_THRESHOLD = 0.02
COST = 0.0002

def get_data():

    data = yf.download(
        TICKERS,
        period="2y",
        interval="1d",
        group_by="ticker"
    )

    open_ = pd.DataFrame()
    close = pd.DataFrame()

    for t in TICKERS:
        open_[t] = data[t]["Open"]
        close[t] = data[t]["Close"]

    return open_, close


def build_strategy(open_, close):

    daily_returns = close.pct_change().dropna()

    returns = []
    dates = []

    for i in range(len(daily_returns) - 1):

        today = daily_returns.iloc[i]
        next_day_open = open_.iloc[i+1]
        next_day_close = close.iloc[i+1]

        trades = []

        # LONG worst performer
        worst_ticker = today.idxmin()
        worst_return = today.min()

        if worst_return < LONG_THRESHOLD:
            entry = next_day_open[worst_ticker]
            exit_ = next_day_close[worst_ticker]

            r = (exit_ / entry - 1) - COST
            trades.append(r)

        # SHORT best performer
        best_ticker = today.idxmax()
        best_return = today.max()

        if best_return > SHORT_THRESHOLD:
            entry = next_day_open[best_ticker]
            exit_ = next_day_close[best_ticker]

            r = (entry / exit_ - 1) - COST
            trades.append(r)

        if len(trades) > 0:
            returns.append(np.mean(trades))
        else:
            returns.append(0)

        dates.append(daily_returns.index[i+1])

    return pd.Series(returns, index=dates)


def simulate(returns):

    capital = INITIAL_CAPITAL
    equity = []

    for r in returns:
        capital *= (1 + r)
        equity.append(capital)

    return np.array(equity)


def run():

    open_, close = get_data()

    returns = build_strategy(open_, close)

    equity = simulate(returns)

    print("\n========== EORENDA EDGE #2 (MEAN REVERSION V1) ==========")
    print("Total Return:", equity[-1] / INITIAL_CAPITAL - 1)
    print("Avg Return:", returns.mean())
    print("Win Rate:", (returns > 0).mean())
    print("Max Drawdown:",
          (equity / np.maximum.accumulate(equity) - 1).min())
    print("Trades:", (returns != 0).sum())
    print("========================================================\n")


if __name__ == "__main__":
    run()
