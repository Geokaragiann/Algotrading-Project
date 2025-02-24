import pandas as pd
import numpy as np

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
    # Load BTC OHLC data (ensure the CSV has columns: Date, Open, High, Low, Close)
    df = pd.read_csv('BTC_daily.csv', parse_dates=['Date'])
    df.sort_values('Date', inplace=True)  # Ensure data is sorted by date
    
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
