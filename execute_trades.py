from ib_insync import *
import pandas as pd
from datetime import datetime
import os

# ==============================
# CONFIG
# ==============================

HOST = "127.0.0.1"
PORT = 7496   # LIVE account
CLIENT_ID = 1

CAPITAL = 1500
ALLOCATION_BUFFER = 0.9   # safety buffer

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
# IBKR PRICE FETCH
# ==============================

def get_price_ibkr(ib, contract):
    try:
        data = ib.reqMktData(contract, "", False, False)
        ib.sleep(3)

        if data.last and data.last > 0:
            return float(data.last)

        elif data.bid and data.ask and data.bid > 0 and data.ask > 0:
            return float((data.bid + data.ask) / 2)

        elif data.close and data.close > 0:
            return float(data.close)

        else:
            return None

    except Exception as e:
        print(f"IBKR price error: {e}")
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

    new_row = pd.DataFrame([{
        "date": datetime.today().date(),
        "nav": last_nav,
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

    # Sync account (important)
    ib.reqAccountSummary()

    positions = get_positions(ib)

    for s in signals:
        ticker = s["ticker"]
        weight = float(s["weight"])

        if ticker in positions and positions[ticker] > 0:
            print(f"Skipping {ticker} (already held)")
            continue

        allocation = CAPITAL * weight * ALLOCATION_BUFFER

        contract = Stock(ticker, "SMART", "USD")
        ib.qualifyContracts(contract)

        price = get_price_ibkr(ib, contract)

        if price is None or price == 0:
            print(f"Skipping {ticker} (no price)")
            continue

        quantity = int(allocation / price)

        if quantity <= 0:
            print(f"Skipping {ticker} (size too small)")
            continue

        # ==============================
        # ORDER (CASH SAFE)
        # ==============================

        order = MarketOrder("BUY", quantity)
        order.tif = "DAY"
        order.outsideRth = False

        trade = ib.placeOrder(contract, order)

        ib.sleep(5)

        status = trade.orderStatus.status

        if status in ["PreSubmitted", "Submitted", "Filled"]:
            print(f"ORDER ACCEPTED {ticker} | Qty: {quantity} | Price: ~{price} | Status: {status}")
            log_trade(ticker, quantity, price)
        else:
            print(f"FAILED {ticker} | Status: {status}")

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
