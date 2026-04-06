import yfinance as yf
import pandas as pd
import numpy as np

TICKERS = ["SPY", "QQQ", "DIA", "XLK", "XLF"]
INITIAL_CAPITAL = 1000

TOP_N_LIST = [1, 2, 3]
EARLY_WINDOWS = [3, 4]
LATE_WINDOWS = [3, 4]

def get_data():

    all_data = {}

    for t in TICKERS:
        data = yf.download(
            t,
            interval="15m",
            period="30d"
        )

        data = data.dropna()

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        data.index = data.index.tz_localize(None)

        all_data[t] = data

    return all_data

def run_strategy(all_data, top_n, early_n, late_n):

    returns = []

    dates = set()
    for data in all_data.values():
        dates.update(data.index.date)
    dates = sorted(list(dates))

    for date in dates:

        signals = []
        future_returns = []

        for ticker, data in all_data.items():

            day = data[data.index.date == date]

            if len(day) < max(early_n, late_n) + 2:
                continue

            open_price = day["Open"].iloc[0]
            early_price = day["Close"].iloc[early_n - 1]

            late_open = day["Open"].iloc[-late_n]
            close_price = day["Close"].iloc[-1]

            early_return = early_price / open_price - 1
            late_return = close_price / late_open - 1

            signals.append((ticker, early_return))
            future_returns.append((ticker, late_return))

        if len(signals) < top_n:
            continue

        sig_df = pd.DataFrame(signals, columns=["ticker", "signal"])
        ret_df = pd.DataFrame(future_returns, columns=["ticker", "ret"])

        merged = sig_df.merge(ret_df, on="ticker")
        merged["abs_signal"] = merged["signal"].abs()

        top = merged.nlargest(top_n, "abs_signal")

        daily_returns = []

        for _, row in top.iterrows():
            if row["signal"] < 0:
                r = row["ret"]
            else:
                r = -row["ret"]

            r -= 0.0002
            daily_returns.append(r)

        if len(daily_returns) > 0:
            returns.append(np.mean(daily_returns))

    return pd.Series(returns)

def run():

    all_data = get_data()

    results = []

    for top_n in TOP_N_LIST:
        for early_n in EARLY_WINDOWS:
            for late_n in LATE_WINDOWS:

                returns = run_strategy(all_data, top_n, early_n, late_n)

                if len(returns) == 0:
                    continue

                avg = returns.mean()
                win = (returns > 0).mean()

                results.append({
                    "top_n": top_n,
                    "early": early_n,
                    "late": late_n,
                    "trades": len(returns),
                    "avg_return": avg,
                    "win_rate": win
                })

    df = pd.DataFrame(results)

    print("\n========== EDGE #2 V3.7 ROBUSTNESS ==========\n")
    print(df)
    print("\n============================================\n")

if __name__ == "__main__":
    run()
