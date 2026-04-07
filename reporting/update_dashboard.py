import pandas as pd
from datetime import datetime

# Load data
equity = pd.read_csv("storage/equity_curve.csv")
trades = pd.read_csv("storage/trades_log.csv")

# Compute cumulative return
equity["cum_return"] = equity["nav"] - 1

# Compute drawdown
equity["peak"] = equity["nav"].cummax()
equity["drawdown"] = (equity["nav"] - equity["peak"]) / equity["peak"]

# Save processed outputs
equity.to_csv("reporting/performance_clean.csv", index=False)
trades.to_csv("reporting/trades_clean.csv", index=False)

print("Dashboard data updated:", datetime.now())
