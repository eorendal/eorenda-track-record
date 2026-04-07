from ib_insync import *
import pandas as pd
from datetime import datetime
import os

# ==============================
# CONFIG
# ==============================

HOST = "127.0.0.1"
PORT = 7496
CLIENT_ID = 1

CAPITAL = 1500
ALLOCATION_BUFFER = 0.9
MAX_SHARES = 2

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
# FAIL-SAFE SIGNAL LOADER
# ==============================

def load_signals():
    try:
        if not os.path.exists("eorenda_signal.csv"):
            print("Signal file missing. Skipping.")
            return []

        df = pd.read_csv("eorenda_signal.csv")

        if df.empty:
            print("Signal file empty. Skipping.")
            return []

        required_cols = {"ticker", "weight"}
        if not required_cols.issubset(df.columns):
            print("Invalid signal format. Skipping.")
            return []

        if df.iloc[0]["ticker"] == "NONE":
            return []

        return df.to_dict("records")

    except Exception as e:
        print(f"Signal load failure: {e}")
        return []

# ==============================
# LOCK CONTROL
# ==============================

def already_ran_today():
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, "r") as f:
            if f.read().strip() == str(datetime.today().date()):
                return True
    return False

def write_lock():
    with open(LOCK_FILE, "w") as f:
        f.write(str(datetime.today().date()))

# ==============================
# POSITION CHECK
# ==============================

def get_positions(ib):
    pos = {}
    for p in ib.positions():
        pos[p.contract.symbol] = p.position
    return pos

# ==============================
# PRICE FETCH (SAFE)
# ==============================

def get_price_ibkr(ib, contract):
    try:
        data = ib.reqMktData(contract, "", False, False)
        ib.sleep(2)

        if data.last and data.last > 0:
            return float(data.last)

        if data.close and data.close > 0:
            return float(data.close)

        return None

    except Exception as e:
        print(f"Price fetch failure: {e}")
        return None

# ==============================
# LOGGING (STRICT FORMAT)
# ==============================

def log_trade(ticker, qty, price):
    file_path = "storage/trades_log.csv"

    new_row = pd.DataFrame([{
        "date": str(datetime.today().date()),
        "ticker": ticker,
        "quantity": int(qty),
        "price": float(price)
    }])

    if not os.path.exists(file_path):
        new_row.to_csv(file_path, index=False)
    else:
        new_row.to_csv(file_path, mode="a", header=False, index=False)

def update_equity_curve():
    file_path = "storage/equity_curve.csv"

    today = str(datetime.today().date())

    if not os.path.exists(file_path):
        df = pd.DataFrame([{
            "date": today,
            "nav": 1.0,
            "return": 0.0
        }])
        df.to_csv(file_path, index=False)
        return

    df = pd.read_csv(file_path)

    if today in df["date"].values:
        return  # prevent duplicates

    last_nav = df.iloc[-1]["nav"]

    new_row = pd.DataFrame([{
        "date": today,
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
    positions = get_positions(ib)

    for s in signals:
        try:
            ticker = s["ticker"]
            weight = float(s["weight"])

            if ticker in positions and positions[ticker] > 0:
                print(f"Skipping {ticker} (already held)")
                continue

            allocation = CAPITAL * weight * ALLOCATION_BUFFER

            contract = Stock(ticker, "SMART", "USD")
            ib.qualifyContracts(contract)

            price = get_price_ibkr(ib, contract)

            if price is None:
                print(f"Skipping {ticker} (no price)")
                continue

            calculated_qty = int(allocation / price)
            quantity = min(calculated_qty, MAX_SHARES)

            if quantity <= 0:
                print(f"Skipping {ticker} (size too small)")
                continue

            order = MarketOrder("BUY", quantity)
            order.tif = "DAY"
            order.outsideRth = False

            trade = ib.placeOrder(contract, order)
            ib.sleep(3)

            status = trade.orderStatus.status

            if status in ["PreSubmitted", "Submitted", "Filled"]:
                print(f"ORDER ACCEPTED {ticker} | Qty: {quantity} | Price: ~{price} | Status: {status}")
                log_trade(ticker, quantity, price)
            else:
                print(f"FAILED {ticker} | Status: {status}")

        except Exception as e:
            print(f"Execution failure for {s}: {e}")
            continue

    ib.disconnect()
    update_equity_curve()
    write_lock()

    print("=====================================\n")

# ==============================
# MAIN
# ==============================

if __name__ == "__main__":
    execute()
