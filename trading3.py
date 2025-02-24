import pandas as pd
import talib

def detect_candlestick_patterns(df):
    """
    Detects key candlestick reversal patterns using TA-Lib.
    """
    patterns = {
        "Engulfing": talib.CDLENGULFING(df['Open'], df['High'], df['Low'], df['Close']),
        "Hammer": talib.CDLHAMMER(df['Open'], df['High'], df['Low'], df['Close']),
        "Inverted Hammer": talib.CDLINVERTEDHAMMER(df['Open'], df['High'], df['Low'], df['Close']),
        "Shooting Star": talib.CDLSHOOTINGSTAR(df['Open'], df['High'], df['Low'], df['Close']),
        "Doji": talib.CDLDOJI(df['Open'], df['High'], df['Low'], df['Close']),
        "Morning Star": talib.CDLMORNINGSTAR(df['Open'], df['High'], df['Low'], df['Close']),
        "Evening Star": talib.CDLEVENINGSTAR(df['Open'], df['High'], df['Low'], df['Close']),
        "Three White Soldiers": talib.CDL3WHITESOLDIERS(df['Open'], df['High'], df['Low'], df['Close']),
        "Three Black Crows": talib.CDL3BLACKCROWS(df['Open'], df['High'], df['Low'], df['Close']),
    }

    for pattern, values in patterns.items():
        df[pattern] = values

    return df

def calculate_rsi(df, period=14):
    """
    Calculates the RSI (Relative Strength Index).
    """
    df['RSI'] = talib.RSI(df['Close'], timeperiod=period)
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

def main():
    # Load BTC OHLC daily data (ensure it has 'Date', 'Open', 'High', 'Low', 'Close' columns)
    df = pd.read_csv("BTC_daily.csv", parse_dates=['Date'])
    df.sort_values("Date", inplace=True)

    # Keep only the last 100 days
    df = df.tail(100).reset_index(drop=True)

    # Detect candlestick patterns
    df = detect_candlestick_patterns(df)

    # Calculate RSI
    df = calculate_rsi(df)

    # Filter signals based on RSI confirmation
    df = filter_signals(df)

    # Print the last 100 days with confirmed signals
    latest_signals = df[['Date', 'Close', 'RSI', 'Bullish Confirmation', 'Bearish Confirmation']]
    
    print("Confirmed Trading Signals (Last 100 Days):")
    print(latest_signals[latest_signals[['Bullish Confirmation', 'Bearish Confirmation']].any(axis=1)])

if __name__ == "__main__":
    main()
