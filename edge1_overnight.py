import yfinance as yf
import pandas as pd
import numpy as np

TICKERS = [
    "SPY", "QQQ", "DIA",
    "XLF", "XLE", "XLK",
    "XLV", "XLY", "XLI"
]

INITIAL_CAPITAL = 1000
TOP_N = 3

def get_data():
    data = yf.download(TICKERS, interval="1d", period="10y", group_by="ticker")

    close = pd.DataFrame()
    open_ = pd.DataFrame()

    for t in TICKERS:
        try:
            close[t] = data[t]["Close"]
            open_[t] = data[t]["Open"]
        except:
            pass

    return close.dropna(), open_.dropna()

def compute_overnight(close, open_):
    return (open_ / close.shift(1) - 1).dropna()

def build_returns(overnight):

    strategy_returns = []

    for i in range(1, len(overnight)):

        signal = overnight.iloc[i-1]

        top_assets = signal.nlargest(TOP_N)

        # FIX: only positive signals
        positive = top_assets[top_assets > 0]

        if len(positive) == 0:
            strategy_returns.append(0)
            continue

        weights = positive / positive.sum()

        today = overnight.iloc[i][positive.index]

        weighted_return = (today * weights).sum()

        strategy_returns.append(weighted_return)

    return pd.Series(strategy_returns)

def apply_costs(returns):
    return returns - 0.0002

def simulate(returns):

    capital = INITIAL_CAPITAL
    equity = []

    for r in returns:
        capital *= (1 + r)
        equity.append(capital)

    return np.array(equity)

def run():

    close, open_ = get_data()

    overnight = compute_overnight(close, open_)

    returns = build_returns(overnight)

    returns = apply_costs(returns)

    equity = simulate(returns)

    print("\n========== EORENDA V2.5 ==========")
    print("Total Return:", equity[-1] / INITIAL_CAPITAL - 1)
    print("Avg Return:", returns.mean())
    print("Win Rate:", (returns > 0).mean())
    print("Max Drawdown:",
          (equity / np.maximum.accumulate(equity) - 1).min())
    print("================================\n")

if __name__ == "__main__":
    run()
