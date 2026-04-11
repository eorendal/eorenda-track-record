from ib_insync import *
from datetime import datetime
import pytz

# CONNECT
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=10)

# TIME CHECK
sgt = pytz.timezone("Asia/Singapore")
now = datetime.now(sgt)

print("TIME:", now)

if not (now.hour == 21 and now.minute >= 30):
    print("ABORT: NOT EXECUTION TIME")
    ib.disconnect()
    exit()

# CONTRACT
contract = Stock("XLK", "SMART", "USD")

# ORDER
quantity = 1
order = MarketOrder("BUY", quantity)
order.outsideRth = False
order.tif = "DAY"

# PLACE ORDER
trade = ib.placeOrder(contract, order)

print("ORDER ID:", trade.order.orderId)

# WAIT FOR FILL
filled = False

for _ in range(20):
    ib.sleep(1)
    status = trade.orderStatus.status
    print("STATUS:", status)

    if status == "Filled":
        filled = True
        break

# RESULT
if filled:
    print("SUCCESS: FILLED")
else:
    ib.cancelOrder(order)
    print("FAILED: NOT FILLED")

ib.disconnect()
