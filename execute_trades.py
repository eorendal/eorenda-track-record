from ib_insync import *
import pandas as pd
from datetime import datetime
import os
import yfinance as yf

# ==============================
# CONFIG
# ==============================

HOST = "127.0.0.1"
PORT = 7496
CLIENT_ID = 1

CAPITAL = 1500
LOCK_FILE = "execution.lock"

BASE_DIR = "/Users/whizmindsacademy/quant_lab"
os.chdir(BASE_DIR)

# ==============================
# CONNECTION
# ==============================

def connect_ibkr():
    ib = IB()
    ib.connect(HOST, PORT, clientId=CLIENT_ID)
    return ib

# ==============================
# LOAD SIGNALS
# ==============================

def load_signals():
    df = pd.read_csv("eorenda_signal.csv")

    if df.iloc[0]["ticker"] == "NONE":
        return []

    return df.to_dict("records")

# ==============================
# LOCK CONTROL
# ==============================

def already_ran_today():
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, "r") as f:
            last = f.read().strip()
            if last == str(datetime.today().date()):
                return True
    return False

def write_lock():
    with open(LOCK_FILE, "w") as f:
        f.write(str(datetime.today().date()))

# ==============================
# POSITION CHECK
# ==============================

def get_positions(ib):
    positions = ib.positions()
    pos_dict = {}

    for p in positions:
        pos_dict[p.contract.symbol] = p.position

    return pos_dict

# ==============================
# PRICE FETCH (YFINANCE FALLBACK)
# ==============================

def get_price(ticker):
    try:
        data = yf.download(ticker, period="1d", interval="1m", progress=False)

        if data.empty:
            return None

        return float(data["Close"].iloc[-1])

    except Exception as e:
        print(f"Price fetch error for {ticker}: {e}")
        return None

# ==============================
# LOGGING
# ==============================

def log_trade(ticker, qty, price):
    file_path = "storage/trades_log.csv"

    new_row = pd.DataFrame([{
        "date": datetime.today().date(),
        "ticker": ticker,
        "quantity": qty,
        "price": price
    }])

    if not os.path.exists(file_path):
        new_row.to_csv(file_path, index=False)
    else:
        new_row.to_csv(file_path, mode="a", header=False, index=False)

def update_equity_curve():
    file_path = "storage/equity_curve.csv"

    if not os.path.exists(file_path):
        df = pd.DataFrame([{
            "date": datetime.today().date(),
            "nav": 1.0,
            "return": 0.0
        }])
        df.to_csv(file_path, index=False)
        return

    df = pd.read_csv(file_path)

    last_nav = df.iloc[-1]["nav"]

    # Placeholder: no PnL calc yet
    new_nav = last_nav

    new_row = pd.DataFrame([{
        "date": datetime.today().date(),
        "nav": new_nav,
        "return": 0.0
    }])

    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(file_path, index=False)

# ==============================
# EXECUTION ENGINE
# ==============================

def execute():

    print("\n========== EXECUTION ENGINE ==========")
    print("RUN TIME:", datetime.now())

    if already_ran_today():
        print("Already executed today. Skipping.")
        return

    signals = load_signals()

    if len(signals) == 0:
        print("No trades to execute.")
        write_lock()
        return

    ib = connect_ibkr()

    positions = get_positions(ib)

    for s in signals:
        ticker = s["ticker"]
        weight = float(s["weight"])

        if ticker in positions and positions[ticker] > 0:
            print(f"Skipping {ticker} (already held)")
            continue

        allocation = CAPITAL * weight

        price = get_price(ticker)

        if price is None or price == 0:
            print(f"Skipping {ticker} (no price)")
            continue

        quantity = int(allocation / price)

        if quantity == 0:
            print(f"Skipping {ticker} (size too small)")
            continue

        contract = Stock(ticker, "SMART", "USD")
        ib.qualifyContracts(contract)

        order = MarketOrder("BUY", quantity)
        ib.placeOrder(contract, order)

        print(f"BUY {ticker} | Qty: {quantity} | Price: ~{price}")

        log_trade(ticker, quantity, price)

        ib.sleep(1)

    ib.disconnect()

    update_equity_curve()
    write_lock()

    print("=====================================\n")

# ==============================
# MAIN
# ==============================

if __name__ == "__main__":
    execute()
