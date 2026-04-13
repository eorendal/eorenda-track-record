from ib_insync import *
from datetime import datetime, timedelta
import pytz
import pandas as pd
import sys
import csv

# =========================
# CONFIG
# =========================
CLIENT_ID = 10
SIGNAL_FILE = "eorenda_signal.csv"
TRADE_LOG = "storage/trades_log.csv"
EQUITY_LOG = "storage/equity_curve.csv"

# =========================
# CONNECT
# =========================
ib = IB()

try:
    ib.connect('127.0.0.1', 7497, clientId=CLIENT_ID)
except:
    print("[ERROR] IBKR CONNECTION FAILED")
    sys.exit()

if not ib.isConnected():
    print("[ERROR] NOT CONNECTED TO IBKR")
    sys.exit()

# =========================
# TIME CHECK (04:50 CLOSE EXECUTION)
# =========================
sgt = pytz.timezone("Asia/Singapore")
now = datetime.now(sgt)

print(f"[TIME] {now}")

if not (now.hour == 4 and now.minute >= 50):
    print("[ABORT] NOT CLOSE EXECUTION WINDOW")
    ib.disconnect()
    sys.exit()

# =========================
# POSITION CHECK
# =========================
positions = ib.positions()

if positions:
    print("[SKIP] EXISTING POSITION DETECTED")
    for p in positions:
        print(f" - {p.contract.symbol}: {p.position}")
    ib.disconnect()
    sys.exit()

# =========================
# READ SIGNAL
# =========================
try:
    signal_df = pd.read_csv(SIGNAL_FILE)
except:
    print("[ERROR] SIGNAL FILE NOT FOUND")
    ib.disconnect()
    sys.exit()

if signal_df.empty:
    print("[ERROR] SIGNAL FILE EMPTY")
    ib.disconnect()
    sys.exit()

signal = signal_df.iloc[-1]

ticker = signal["ticker"]
action = signal["action"]
weight = float(signal["weight"])
timestamp_str = signal["timestamp"]

print(f"[SIGNAL] {action} {ticker} weight={weight}")

# =========================
# STALE SIGNAL CHECK (CRITICAL)
# =========================
try:
    signal_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S.%f")
except:
    print("[ERROR] INVALID SIGNAL TIMESTAMP FORMAT")
    ib.disconnect()
    sys.exit()

# convert signal_time to SGT timezone
signal_time = sgt.localize(signal_time)

if now - signal_time > timedelta(minutes=10):
    print("[ABORT] STALE SIGNAL")
    ib.disconnect()
    sys.exit()

# =========================
# ACTION CHECK
# =========================
if action != "BUY":
    print("[NO TRADE] ACTION NOT BUY")
    ib.disconnect()
    sys.exit()

# =========================
# CONTRACT
# =========================
contract = Stock(ticker, "SMART", "USD")

# =========================
# POSITION SIZING
# =========================
quantity = 1  # can upgrade later

if quantity <= 0:
    print("[ERROR] INVALID QUANTITY")
    ib.disconnect()
    sys.exit()

# =========================
# ORDER
# =========================
order = MarketOrder("BUY", quantity)
order.outsideRth = False
order.tif = "DAY"

# =========================
# PLACE ORDER
# =========================
trade = ib.placeOrder(contract, order)

if not trade:
    print("[ERROR] ORDER OBJECT NOT CREATED")
    ib.disconnect()
    sys.exit()

print(f"[ORDER] ID={trade.order.orderId}")

# =========================
# WAIT FOR FILL (STRICT CLOSE WINDOW)
# =========================
filled = False
MAX_WAIT = 10

for i in range(MAX_WAIT):
    ib.sleep(1)
    status = trade.orderStatus.status
    print(f"[STATUS] {status}")

    if status == "Filled":
        filled = True
        break

# =========================
# RESULT HANDLING
# =========================
if filled:
    print("[SUCCESS] ORDER FILLED")
else:
    ib.cancelOrder(order)
    print("[FAILED] NOT FILLED - ORDER CANCELLED")

# =========================
# LOG TRADE
# =========================
try:
    with open(TRADE_LOG, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now(),
            ticker,
            action,
            quantity,
            trade.orderStatus.status
        ])
except:
    print("[WARNING] FAILED TO LOG TRADE")

# =========================
# LOG EQUITY
# =========================
try:
    account = ib.accountSummary()
    equity = [x.value for x in account if x.tag == "NetLiquidation"]

    if equity:
        with open(EQUITY_LOG, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([datetime.now(), equity[0]])
except:
    print("[WARNING] FAILED TO LOG EQUITY")

# =========================
# CLEAN EXIT
# =========================
ib.disconnect()
print("[DONE]")

