import pandas as pd
import pandas_ta as ta
import ccxt
import time

def detect_candlestick_patterns(df):
    """
    Detects key candlestick reversal patterns using pandas_ta.
    """
    patterns = {
        "Engulfing": ta.cdl_engulfing(df['Open'], df['High'], df['Low'], df['Close']),
        "Hammer": ta.cdl_hammer(df['Open'], df['High'], df['Low'], df['Close']),
        "Inverted Hammer": ta.cdl_inverted_hammer(df['Open'], df['High'], df['Low'], df['Close']),
        "Shooting Star": ta.cdl_shooting_star(df['Open'], df['High'], df['Low'], df['Close']),
        "Doji": ta.cdl_doji(df['Open'], df['High'], df['Low'], df['Close']),
        "Morning Star": ta.cdl_morning_star(df['Open'], df['High'], df['Low'], df['Close']),
        "Evening Star": ta.cdl_evening_star(df['Open'], df['High'], df['Low'], df['Close']),
        "Three White Soldiers": ta.cdl_three_white_soldiers(df['Open'], df['High'], df['Low'], df['Close']),
        "Three Black Crows": ta.cdl_three_black_crows(df['Open'], df['High'], df['Low'], df['Close']),
    }

    for pattern, values in patterns.items():
        df[pattern] = values

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
