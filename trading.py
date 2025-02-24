import numpy as np
import pandas as pd

def find_swing_points(data, window=5):
    """
    Identify swing high and low points in price data
    
    Parameters:
    data (pd.Series): Price data
    window (int): Number of periods to look before/after for swing point confirmation
    
    Returns:
    tuple: Arrays of swing high and swing low indices
    """
    highs = []
    lows = []
    
    for i in range(window, len(data) - window):
        # Check if current point is highest/lowest in the window
        left_window = data[i-window:i]
        right_window = data[i:i+window+1]
        
        # Swing high
        if data[i] > max(left_window[:-1]) and data[i] > max(right_window[1:]):
            highs.append(i)
            
        # Swing low
        if data[i] < min(left_window[:-1]) and data[i] < min(right_window[1:]):
            lows.append(i)
            
    return np.array(highs), np.array(lows)

def calculate_fibonacci_levels(high_price, low_price):
    """
    Calculate Fibonacci retracement levels
    
    Parameters:
    high_price (float): Swing high price
    low_price (float): Swing low price
    
    Returns:
    dict: Fibonacci levels
    """
    diff = high_price - low_price
    
    levels = {
        '0.0': low_price,
        '0.236': low_price + 0.236 * diff,
        '0.382': low_price + 0.382 * diff,
        '0.5': low_price + 0.5 * diff,
        '0.618': low_price + 0.618 * diff,
        '0.786': low_price + 0.786 * diff,
        '1.0': high_price
    }
    
    return levels

def trading_strategy(df, window=5, stop_loss_pct=0.02):
    """
    Trading strategy using swing points and Fibonacci retracement
    
    Parameters:
    df (pd.DataFrame): DataFrame with 'close' price column
    window (int): Window size for swing point detection
    stop_loss_pct (float): Stop loss percentage
    
    Returns:
    pd.DataFrame: DataFrame with signals
    """
    df = df.copy()
    
    # Find swing points
    swing_highs, swing_lows = find_swing_points(df['close'], window)
    
    # Initialize signals
    df['signal'] = 0  # 1 for buy, -1 for sell
    df['stop_loss'] = np.nan
    
    for i in range(window*2, len(df)):
        # Find most recent swing points
        prev_highs = swing_highs[swing_highs < i]
        prev_lows = swing_lows[swing_lows < i]
        
        if len(prev_highs) > 0 and len(prev_lows) > 0:
            last_high = df['close'].iloc[prev_highs[-1]]
            last_low = df['close'].iloc[prev_lows[-1]]
            
            # Calculate Fibonacci levels
            fib_levels = calculate_fibonacci_levels(last_high, last_low)
            
            current_price = df['close'].iloc[i]
            
            # Buy signal: Price bounces off 0.618 level
            if (current_price > fib_levels['0.618'] and 
                df['close'].iloc[i-1] <= fib_levels['0.618']):
                df.loc[df.index[i], 'signal'] = 1
                df.loc[df.index[i], 'stop_loss'] = current_price * (1 - stop_loss_pct)
            
            # Sell signal: Price breaks below 0.382 level after uptrend
            elif (current_price < fib_levels['0.382'] and 
                  df['close'].iloc[i-1] >= fib_levels['0.382']):
                df.loc[df.index[i], 'signal'] = -1
    
    return df

# Example usage
if __name__ == "__main__":
    # Sample data
    data = pd.DataFrame({
        'close': [100, 101, 102, 101, 99, 98, 97, 98, 100, 102, 103, 102, 101, 100]
    })
    
    # Apply strategy
    results = trading_strategy(data)
    
    # Print signals
    print("Trading Signals:")
    print(results[results['signal'] != 0])