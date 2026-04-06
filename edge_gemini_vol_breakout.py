import yfinance as yf
import pandas as pd
import numpy as np

# 1. Institutional Parameters & Uncorrelated Macro Universe
# Equities, Real Estate, Gold, Bonds, Oil, Emerging Markets, Dollar
trade_tickers = ["SPY", "QQQ", "IWM", "EEM", "VNQ", "GLD", "SLV", "USO", "TLT", "UUP", "XLF", "XLE"]
macro_tickers = ["^VIX", "^VIX3M"]
cash_proxy = "BIL" # 1-3 Month T-Bill ETF for Cash Sweep
all_tickers = trade_tickers + macro_tickers + [cash_proxy]

cost = 0.0002
target_risk_per_trade = 0.02 # Target risk: 2%

# Fetch 3 years of data for indicator burn-in
print("Fetching institutional data pipeline...")
data = yf.download(all_tickers, period="3y", progress=False)

# Process Macro Regime (VIX Term Structure)
if isinstance(data.columns, pd.MultiIndex):
    vix_close = data['Close']['^VIX']
    vix3m_close = data['Close']['^VIX3M']
    bil_returns = data['Close']['BIL'].pct_change()
else:
    vix_close = yf.download("^VIX", period="3y", progress=False)['Close']
    vix3m_close = yf.download("^VIX3M", period="3y", progress=False)['Close']
    bil_returns = yf.download("BIL", period="3y", progress=False)['Close'].pct_change()

vix_ratio = vix_close / vix3m_close
vix_contango = vix_ratio < 1.0 

trade_list = []
daily_returns_list = []
active_weights_list = []

# 2. Strategy Logic per Asset
for ticker in trade_tickers:
    df = pd.DataFrame()
    if isinstance(data.columns, pd.MultiIndex):
        df['Close'] = data['Close'][ticker]
        df['High'] = data['High'][ticker]
        df['Low'] = data['Low'][ticker]
        df['Volume'] = data['Volume'][ticker]
    else:
        df['Close'] = data['Close']
        df['High'] = data['High']
        df['Low'] = data['Low']
        df['Volume'] = data['Volume']
        
    df.dropna(inplace=True)
        
    # Volatility Squeeze & Volume Confirmation
    df['Returns'] = df['Close'].pct_change()
    df['Vol_20'] = df['Returns'].rolling(window=20).std()
    df['Vol_Quantile'] = df['Vol_20'].rolling(window=100).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)
    df['Low_Vol'] = df['Vol_Quantile'] < 0.25
    df['Vol_SMA_20'] = df['Volume'].rolling(window=20).mean()
    
    # Macro Trend & Breakout Levels
    df['SMA_100'] = df['Close'].rolling(window=100).mean()
    df['High_20'] = df['High'].rolling(window=20).max().shift(1)
    
    # ATR for Position Sizing and Trailing Stop
    df['Prev_Close'] = df['Close'].shift(1)
    df['TR'] = np.maximum(df['High'] - df['Low'], np.maximum(abs(df['High'] - df['Prev_Close']), abs(df['Low'] - df['Prev_Close'])))
    df['ATR_14'] = df['TR'].rolling(window=14).mean().shift(1)
    
    df['VIX_Contango'] = vix_contango
    
    # Isolate exactly the last 504 trading days (2 years)
    df = df.tail(504).copy()
    
    position = 0
    entry_price = 0
    highest_high = 0
    active_weight = 0
    
    closes = df['Close'].values
    highs = df['High'].values
    volumes = df['Volume'].values
    highs_20 = df['High_20'].values
    smas_100 = df['SMA_100'].values
    vol_smas_20 = df['Vol_SMA_20'].values
    low_vols = df['Low_Vol'].values
    atrs = df['ATR_14'].values
    contango_regime = df['VIX_Contango'].values
    
    strat_returns = np.zeros(len(df))
    daily_weights = np.zeros(len(df))
    
    # 3. Execution Loop
    for i in range(1, len(df)):
        if position == 1:
            strat_returns[i] = active_weight * (closes[i] - closes[i-1]) / closes[i-1]
            daily_weights[i] = active_weight
            highest_high = max(highest_high, highs[i])
            trailing_stop = highest_high - (2 * atrs[i])
            
            if closes[i] < trailing_stop:
                trade_ret = (closes[i] - entry_price) / entry_price - (cost * 2) 
                trade_list.append(trade_ret * active_weight) 
                position = 0
                strat_returns[i] -= cost * active_weight
                active_weight = 0
                
        if position == 0 and low_vols[i] and contango_regime[i]:
            if closes[i] > highs_20[i] and closes[i] > smas_100[i] and volumes[i] > vol_smas_20[i]:
                stop_distance_pct = (2 * atrs[i]) / closes[i]
                if stop_distance_pct > 0:
                    calculated_weight = target_risk_per_trade / stop_distance_pct
                    active_weight = min(calculated_weight, 0.25) # Max 25% portfolio allocation per trade
                    
                    position = 1
                    entry_price = closes[i]
                    highest_high = highs[i]
                    strat_returns[i] -= cost * active_weight
                    daily_weights[i] = active_weight
                
    if position == 1:
        trade_ret = (closes[-1] - entry_price) / entry_price - (cost * 2)
        trade_list.append(trade_ret * active_weight)
        strat_returns[-1] -= cost * active_weight
                
    daily_returns_list.append(pd.Series(strat_returns, index=df.index))
    active_weights_list.append(pd.Series(daily_weights, index=df.index))

# 4. Institutional Portfolio Aggregation with Cash Sweep
strategy_returns = pd.concat(daily_returns_list, axis=1).sum(axis=1)
total_active_weight = pd.concat(active_weights_list, axis=1).sum(axis=1)

# Ensure we don't leverage past 100% total portfolio allocation
total_active_weight = total_active_weight.clip(upper=1.0)

# Calculate idle cash (1 - total active weight)
idle_cash_weight = 1.0 - total_active_weight

# Isolate the exact 504 days for the T-Bill returns to match
bil_returns_aligned = bil_returns.reindex(strategy_returns.index).fillna(0)

# Final Portfolio Return = Active Edge + Yield on Idle Cash
port_returns = strategy_returns + (idle_cash_weight * bil_returns_aligned)
port_cum_returns = (1 + port_returns).cumprod()

num_trades = len(trade_list)
avg_return = np.mean(trade_list) if num_trades > 0 else 0
win_rate = sum(1 for t in trade_list if t > 0) / num_trades if num_trades > 0 else 0

roll_max = port_cum_returns.cummax()
drawdown = (port_cum_returns - roll_max) / roll_max
max_dd = drawdown.min() if not pd.isna(drawdown.min()) else 0

total_return = port_cum_returns.iloc[-1] - 1 if len(port_cum_returns) > 0 else 0

# 5. Output EXACTLY per directive
print(f"- Number of trades: {num_trades}")
print(f"- Average return: {avg_return:.4%}")
print(f"- Win rate: {win_rate:.4%}")
print(f"- Max drawdown: {max_dd:.4%}")
print(f"- Total return: {total_return:.4%}")
