import pandas as pd
import yfinance as yf
from datetime import datetime

# =========================
# CONFIG
# =========================
TICKERS = ["SPY", "QQQ", "XLK", "XLF", "DIA"]
OUTPUT_FILE = "eorenda_signal.csv"

# =========================
# SIGNAL LOGIC (EDGE #1)
# =========================
def generate_signal():
    try:
        data = yf.download(TICKERS, period="5d", interval="1d", auto_adjust=True)

        if data is None or data.empty:
            print("[WARNING] No data returned from yfinance")
            return None

        # Use Close prices
        close = data["Close"]

        if close.empty:
            print("[WARNING] Close data empty")
            return None

        # Simple momentum: last day return
        returns = close.pct_change().iloc[-1]

        if returns is None or returns.isnull().all():
            print("[WARNING] Returns invalid")
            return None

        # Pick best performing ETF
        best = returns.idxmax()

        print(f"[SIGNAL] Selected: {best}")

        return pd.DataFrame([{
            "timestamp": datetime.now(),
            "ticker": best,
            "action": "BUY",
            "weight": 1.0
        }])

    except Exception as e:
        print(f"[ERROR] SIGNAL GENERATION FAILED: {e}")
        return None

# =========================
# MAIN EXECUTION
# =========================
def run():
    try:
        trades = generate_signal()

        if trades is None or trades.empty:
            print("[INFO] No trades today")

            df = pd.DataFrame([{
                "timestamp": datetime.now(),
                "ticker": "NONE",
                "action": "NONE",
                "weight": 0
            }])
        else:
            df = trades

    except Exception as e:
        print(f"[FATAL] UNEXPECTED ERROR: {e}")

        df = pd.DataFrame([{
            "timestamp": datetime.now(),
            "ticker": "NONE",
            "action": "NONE",
            "weight": 0
        }])

    # 🔴 ALWAYS WRITE FILE (CRITICAL GUARANTEE)
    df.to_csv(OUTPUT_FILE, index=False)

    print("\n========== EORENDA LIVE SIGNAL ==========")
    print(df)
    print("=========================================")
    print("SIGNAL FILE WRITTEN\n")

# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    print(f"RUN TIME: {datetime.now()}")
    run()
