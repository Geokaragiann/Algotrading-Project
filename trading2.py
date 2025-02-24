import pandas as pd
import numpy as np
import ccxt

def generate_fib_signals(data, window=2, threshold=0.01):
    """
    Generate trading signals based on Fibonacci retracement levels
    Returns a Series with 1 (buy), -1 (sell), or 0 (hold)
    """
    # Detect swings
    data_with_swings = detect_swings(data.copy(), window)
    signals = pd.Series(0, index=data.index)
    
    for i in range(window, len(data) - 1):
        if data_with_swings['SwingHigh'].iloc[i]:
            swing_high = data_with_swings['High'].iloc[i]
            # Find the next swing low
            next_lows = data_with_swings.iloc[i:][data_with_swings['SwingLow']]
            if not next_lows.empty:
                swing_low = next_lows['Low'].iloc[0]
                fib_levels = calculate_fib_levels(swing_high, swing_low)
                
                # Generate signals based on price crossing Fibonacci levels
                current_price = data['Close'].iloc[i]
                for level, price in fib_levels.items():
                    if abs(current_price - price) / price < threshold:
                        signals.iloc[i] = 1  # Buy signal at support levels
                        
    return signals


def fetch_ohlcv_data(symbol='BTC/USDT', timeframe='1d', limit=100):
    """
    Fetches OHLCV data from Binance using CCXT.
    """
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['Date'] = pd.to_datetime(df['Date'], unit='ms')
    return df

def detect_swings(data, window=2):
    """
    Detects swing highs and lows in the OHLC data.
    A swing high occurs when the high is the highest in the given window.
    A swing low occurs when the low is the lowest in the given window.
    """
    highs = data['High'].values
    lows = data['Low'].values
    
    swing_highs = np.full(len(data), False)
    swing_lows = np.full(len(data), False)
    
    for i in range(window, len(data) - window):
        if highs[i] == max(highs[i-window:i+window+1]):
            swing_highs[i] = True
        if lows[i] == min(lows[i-window:i+window+1]):
            swing_lows[i] = True
    
    data['SwingHigh'] = swing_highs
    data['SwingLow'] = swing_lows
    return data

def calculate_fib_levels(swing_high, swing_low, levels=[0.236, 0.382, 0.5, 0.618, 0.764]):
    """
    Calculates Fibonacci retracement levels between a given swing high and swing low.
    """
    diff = swing_high - swing_low
    fib_levels = {f"{level*100:.1f}%": swing_high - diff * level for level in levels}
    return fib_levels

def main():
    # Fetch OHLCV data from Binance
    df = fetch_ohlcv_data(symbol='BTC/USDT', timeframe='1d', limit=100)

    # Detect swing highs/lows
    df = detect_swings(df, window=2)

    # Identify the most recent significant swing high and low
    swing_highs = df[df['SwingHigh']]
    swing_lows = df[df['SwingLow']]
    
    if swing_highs.empty or swing_lows.empty:
        print("No significant swing points found.")
        return
    
    swing_high_val = swing_highs['High'].max()
    swing_low_val = swing_lows['Low'].min()

    # Calculate Fibonacci retracement levels
    fib_levels = calculate_fib_levels(swing_high_val, swing_low_val)
    
    # Get the most recent closing price
    current_price = df.iloc[-1]['Close']
    
    # Print Fibonacci levels
    print(f"Swing High: {swing_high_val}, Swing Low: {swing_low_val}")
    print("Fibonacci Retracement Levels:")
    for level, price in fib_levels.items():
        print(f"{level}: {price:.2f}")

    # Check if the current price is near any Fibonacci levels
    for level, price in fib_levels.items():
        if abs(current_price - price) / price < 0.01:  # Within 1% of a Fibonacci level
            print(f"ALERT: Current price ({current_price:.2f}) is near Fibonacci level {level}: {price:.2f}")

if __name__ == "__main__":
    main()
