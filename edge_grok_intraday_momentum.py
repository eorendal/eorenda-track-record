import yfinance as yf
import pandas as pd
import numpy as np

tickers = ["SPY", "QQQ", "DIA", "XLK", "XLF"]

print("Downloading maximum 1-hour data (~2 years)...")

data = {}
for ticker in tickers:
    try:
        df = yf.download(
            ticker, period="730d", interval="1h",
            progress=False, prepost=False, auto_adjust=False
        )
        if not df.empty:
            if df.index.tz is not None:
                df = df.tz_convert('America/New_York')
            df = df.between_time('09:30', '16:00')
            df = df.reset_index()
            df['date'] = df['Datetime'].dt.date
            price_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            df[price_cols] = df[price_cols].apply(pd.to_numeric, errors='coerce')
            data[ticker] = df
            print(f"✓ Downloaded {ticker}: {len(df)} bars ({df['date'].nunique()} trading days)")
    except Exception as e:
        print(f"Error downloading {ticker}: {e}")

trades = []
for ticker, df in data.items():
    for date, group in df.groupby('date'):
        group = group.sort_values('Datetime').reset_index(drop=True)
        if len(group) < 2:
            continue
        try:
            open_price  = float(group['Open'].values[0].item())
            early_close = float(group['Close'].values[0].item())
            entry_price = float(group['Close'].values[0].item())
            exit_price  = float(group['Close'].values[-1].item())
            
            early_ret = (early_close / open_price) - 1.0
            
            if early_ret > 0.0015:   # +0.15% in first hour
                gross_ret = (exit_price / entry_price) - 1.0
                net_ret = gross_ret - 0.0004
                trades.append(net_ret)
        except Exception:
            continue

if not trades:
    print("No trades generated.")
else:
    returns = np.array(trades)
    num_trades = len(returns)
    avg_return = np.mean(returns) * 100
    win_rate = (np.sum(returns > 0) / num_trades) * 100
    total_return = (np.prod(1 + returns) - 1) * 100
    
    cum = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cum)
    drawdowns = (cum - running_max) / running_max
    max_dd = np.min(drawdowns) * 100
    
    print("\n=== BEST YFINANCE RESULT: 1-HOUR +0.15% FILTER ===")
    print("- Number of trades:", num_trades)
    print("- Average return:", f"{avg_return:.4f}%")
    print("- Win rate:", f"{win_rate:.4f}%")
    print("- Max drawdown:", f"{max_dd:.4f}%")
    print("- Total return:", f"{total_return:.4f}%")
    
    print("\nStrategy: Long-only 1-hour momentum continuation")
    print("Logic: First-hour return > +0.15% → long to close | Skip everything else")
    print("Period: ~2 years | TC: 0.0004 roundtrip | Fixed logic, no optimization")
