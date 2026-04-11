from ib_insync import *
from datetime import datetime
import pytz
import sys

# =========================
# CONFIG
# =========================
SYMBOL = "XLK"
QUANTITY = 1
CLIENT_ID = 10

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
# TIME CHECK
# =========================
sgt = pytz.timezone("Asia/Singapore")
now = datetime.now(sgt)

print(f"[TIME] {now}")

if not (now.hour == 21 and now.minute >= 30):
    print("[ABORT] NOT EXECUTION WINDOW")
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
# CONTRACT
# =========================
contract = Stock(SYMBOL, "SMART", "USD")

# =========================
# ORDER
# =========================
order = MarketOrder("BUY", QUANTITY)
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
# WAIT FOR FILL
# =========================
filled = False
MAX_WAIT = 20

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
# CLEAN EXIT
# =========================
ib.disconnect()
print("[DONE]")
