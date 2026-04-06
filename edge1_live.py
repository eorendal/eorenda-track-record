import os
os.chdir("/Users/whizmindsacademy/quant_lab")

import yfinance as yf
import pandas as pd
from datetime import datetime

TICKERS = ["SPY", "QQQ", "DIA", "XLK", "XLF"]

def generate_signal():

    data = yf.download(TICKERS, period="5d", interval="1d", group_by="ticker")

    close = pd.DataFrame()
    open_ = pd.DataFrame()

    for t in TICKERS:
        close[t] = data[t]["Close"]
        open_[t] = data[t]["Open"]

    overnight = open_ / close.shift(1) - 1
    overnight = overnight.dropna()

    # latest signal
    signal = overnight.iloc[-1]

    # rank
    top_assets = signal.nlargest(3)
    positive = top_assets[top_assets > 0]

    if len(positive) == 0:
        return []

    weights = positive / positive.sum()

    trades = []

    for ticker, weight in weights.items():
        trades.append({
            "timestamp": datetime.now(),
            "ticker": ticker,
            "action": "BUY",
            "weight": round(weight, 4)
        })

    return trades

def save_trades(trades):

    if len(trades) == 0:
        df = pd.DataFrame([{
            "timestamp": datetime.now(),
            "ticker": "NONE",
            "action": "NONE",
            "weight": 0
        }])
    else:
        df = pd.DataFrame(trades)

    df.to_csv("eorenda_signal.csv", index=False)

def run():

    print("RUN TIME:", datetime.now())
    
    trades = generate_signal()

    print("\n========== EORENDA LIVE SIGNAL ==========")

    if len(trades) == 0:
        print("No trades today.")
    else:
        for t in trades:
            print(t)

    save_trades(trades)

    print("========================================\n")

if __name__ == "__main__":
    run()
