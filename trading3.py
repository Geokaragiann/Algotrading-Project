import pandas as pd
import pandas_ta as ta
import ccxt
import time

def detect_candlestick_patterns(df):
    """
    Detects key candlestick reversal patterns using pure price data.
    """
    # Initialize pattern columns
    patterns = pd.DataFrame(index=df.index)
    
    # Helper functions
    def is_bullish(open, close):
        return close > open
    
    def is_bearish(open, close):
        return close < open
    
    def body_size(open, close):
        return abs(close - open)
    
    def upper_shadow(high, open, close):
        return high - max(open, close)
    
    def lower_shadow(low, open, close):
        return min(open, close) - low
    
    # Detect patterns
    for i in range(1, len(df)-1):
        prev = df.iloc[i-1]
        curr = df.iloc[i]
        next = df.iloc[i+1]
        
        # Engulfing
        patterns.at[curr.name, 'Engulfing'] = int(
            (is_bullish(curr['Open'], curr['Close']) and 
             is_bearish(prev['Open'], prev['Close']) and
             curr['Close'] > prev['Open'] and
             curr['Open'] < prev['Close']) or
            (is_bearish(curr['Open'], curr['Close']) and 
             is_bullish(prev['Open'], prev['Close']) and
             curr['Close'] < prev['Open'] and
             curr['Open'] > prev['Close'])
        )
        
        # Hammer
        patterns.at[curr.name, 'Hammer'] = int(
            is_bullish(curr['Open'], curr['Close']) and
            lower_shadow(curr['Low'], curr['Open'], curr['Close']) >= 2 * body_size(curr['Open'], curr['Close']) and
            upper_shadow(curr['High'], curr['Open'], curr['Close']) <= 0.1 * body_size(curr['Open'], curr['Close'])
        )
        
        # Inverted Hammer
        patterns.at[curr.name, 'Inverted Hammer'] = int(
            is_bullish(curr['Open'], curr['Close']) and
            upper_shadow(curr['High'], curr['Open'], curr['Close']) >= 2 * body_size(curr['Open'], curr['Close']) and
            lower_shadow(curr['Low'], curr['Open'], curr['Close']) <= 0.1 * body_size(curr['Open'], curr['Close'])
        )
        
        # Shooting Star
        patterns.at[curr.name, 'Shooting Star'] = int(
            is_bearish(curr['Open'], curr['Close']) and
            upper_shadow(curr['High'], curr['Open'], curr['Close']) >= 2 * body_size(curr['Open'], curr['Close']) and
            lower_shadow(curr['Low'], curr['Open'], curr['Close']) <= 0.1 * body_size(curr['Open'], curr['Close'])
        )
        
        # Doji
        patterns.at[curr.name, 'Doji'] = int(
            body_size(curr['Open'], curr['Close']) <= 0.01 * curr['Close'] and  # Very small body
            (upper_shadow(curr['High'], curr['Open'], curr['Close']) > 0.01 * curr['Close'] or
             lower_shadow(curr['Low'], curr['Open'], curr['Close']) > 0.01 * curr['Close'])  # At least one shadow
        )
        
        # Morning Star
        patterns.at[curr.name, 'Morning Star'] = int(
            is_bearish(prev['Open'], prev['Close']) and
            body_size(curr['Open'], curr['Close']) <= 0.01 * curr['Close'] and  # Small body (star)
            is_bullish(next['Open'], next['Close']) and
            next['Close'] > prev['Close']
        )
        
        # Evening Star
        patterns.at[curr.name, 'Evening Star'] = int(
            is_bullish(prev['Open'], prev['Close']) and
            body_size(curr['Open'], curr['Close']) <= 0.01 * curr['Close'] and  # Small body (star)
            is_bearish(next['Open'], next['Close']) and
            next['Close'] < prev['Close']
        )
        
        # Three White Soldiers
        patterns.at[curr.name, 'Three White Soldiers'] = int(
            i >= 2 and
            all(is_bullish(df.iloc[j]['Open'], df.iloc[j]['Close']) for j in range(i-2, i+1)) and
            all(df.iloc[j]['Close'] > df.iloc[j-1]['Close'] for j in range(i-1, i+1)) and
            all(df.iloc[j]['Open'] > df.iloc[j-1]['Open'] for j in range(i-1, i+1))
        )
        
        # Three Black Crows
        patterns.at[curr.name, 'Three Black Crows'] = int(
            i >= 2 and
            all(is_bearish(df.iloc[j]['Open'], df.iloc[j]['Close']) for j in range(i-2, i+1)) and
            all(df.iloc[j]['Close'] < df.iloc[j-1]['Close'] for j in range(i-1, i+1)) and
            all(df.iloc[j]['Open'] < df.iloc[j-1]['Open'] for j in range(i-1, i+1))
        )
    
    # Merge patterns with original dataframe
    df = pd.concat([df, patterns], axis=1)
    
    return df

def calculate_rsi(df, period=14):
    """
    Calculates the RSI (Relative Strength Index) using pandas_ta.
    """
    df['RSI'] = ta.rsi(df['Close'], length=period)
    return df

def filter_signals(df):
    """
    Filters the signals where RSI confirms a reversal.
    - Bullish confirmation: RSI < 30
    - Bearish confirmation: RSI > 70
    """
    bullish_reversals = ['Engulfing', 'Hammer', 'Inverted Hammer', 'Morning Star', 'Three White Soldiers']
    bearish_reversals = ['Engulfing', 'Shooting Star', 'Evening Star', 'Three Black Crows']

    df['Bullish Signal'] = df[bullish_reversals].sum(axis=1) > 0  # If any bullish pattern is detected
    df['Bearish Signal'] = df[bearish_reversals].sum(axis=1) > 0  # If any bearish pattern is detected

    df['Bullish Confirmation'] = df['Bullish Signal'] & (df['RSI'] < 30)
    df['Bearish Confirmation'] = df['Bearish Signal'] & (df['RSI'] > 70)

    return df

def fetch_binance_data():
    """
    Fetches the last 100 days of OHLCV data from Binance using ccxt.
    """
    exchange = ccxt.binance()
    symbol = 'BTC/USDT'  # Symbol for BTC in USDT
    timeframe = '1d'  # Daily timeframe
    limit = 100  # Last 100 days of data

    # Fetch historical OHLCV data (Open, High, Low, Close, Volume)
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    
    # Convert the OHLCV data into a pandas DataFrame
    ohlcv_df = pd.DataFrame(ohlcv, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
    ohlcv_df['Date'] = pd.to_datetime(ohlcv_df['Date'], unit='ms')  # Convert timestamp to datetime
    ohlcv_df.set_index('Date', inplace=True)

    return ohlcv_df

def main():
    # Fetch BTC data from Binance
    df = fetch_binance_data()

    # Detect candlestick patterns
    df = detect_candlestick_patterns(df)

    # Calculate RSI
    df = calculate_rsi(df)

    # Filter signals based on RSI confirmation
    df = filter_signals(df)

    # Print the last 100 days with confirmed signals
    latest_signals = df[['Close', 'RSI', 'Bullish Confirmation', 'Bearish Confirmation']]

    print("Confirmed Trading Signals (Last 100 Days):")
    print(latest_signals[latest_signals[['Bullish Confirmation', 'Bearish Confirmation']].any(axis=1)])

if __name__ == "__main__":
    main()
