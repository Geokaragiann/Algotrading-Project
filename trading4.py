import pandas as pd
import yfinance as yf
from datetime import datetime

def fetch_and_analyze_dax40_today():
    """
    Fetches today's DAX40 data and analyzes trade setups with detailed explanation
    """
    # Download today's data for the low and subsequent price action
    df = yf.download('^GDAXI', interval='15m', period='1d', progress=False)

    if not df.empty:
        # Convert index to datetime and convert to CET
        df.index = pd.to_datetime(df.index).tz_convert('Europe/Berlin')
        
        # Debug: Print the first few rows to verify time zone
        print("Data with CET Time Zone:")
        print(df.head())
        
        # Get today's 09:00 CET candle
        opening_candle = df[df.index.time == pd.to_datetime('09:00').time()]
        
        if not opening_candle.empty:
            first_candle = opening_candle.iloc[0]
            
            # Get low and high values using MultiIndex
            low = float(first_candle[('Low', '^GDAXI')])
            high = float(first_candle[('High', '^GDAXI')])
            
            # Calculate risk and take profit distances
            risk = high - low
            take_profit_distance = risk * 0.8  # 80% of risk
            
            # Calculate take profit levels
            long_tp = high + take_profit_distance
            short_tp = low - take_profit_distance
            
            # Print initial setup
            print(f"\nOpening Candle (09:00-09:15):")
            print(f"High: {high:.2f}")
            print(f"Low: {low:.2f}")
            print(f"Risk Range: {risk:.2f} points")
            
            # Get subsequent price action
            later_candles = df[df.index > opening_candle.index[0]]
            
            if not later_candles.empty:
                later_high = float(later_candles[('High', '^GDAXI')].max())
                later_low = float(later_candles[('Low', '^GDAXI')].min())
                
                print("\nSubsequent Price Action:")
                print(f"Highest price reached: {later_high:.2f}")
                print(f"Lowest price reached: {later_low:.2f}")
                
                # Check Long Setup
                print("\nLong Trade Analysis:")
                print(f"Entry Level: {high:.2f}")
                print(f"Stop Loss: {low:.2f}")
                print(f"Take Profit: {long_tp:.2f}")
                
                if later_high > high:  # Long entry triggered
                    print("Trade Triggered at:", high)
                    if later_low <= low:  # Stop loss hit
                        print("LOSS - Stop Loss hit at:", low)
                        print(f"Loss amount: {(low - high):.2f} points")
                    elif later_high >= long_tp:  # Take profit hit
                        print("WIN - Take Profit hit at:", long_tp)
                        print(f"Profit amount: {(long_tp - high):.2f} points")
                    else:
                        print("Still Active - Current price within range")
                else:
                    print("Not Triggered - Price never reached entry level")
                
                # Check Short Setup
                print("\nShort Trade Analysis:")
                print(f"Entry Level: {low:.2f}")
                print(f"Stop Loss: {high:.2f}")
                print(f"Take Profit: {short_tp:.2f}")
                
                if later_low < low:  # Short entry triggered
                    print("Trade Triggered at:", low)
                    if later_high >= high:  # Stop loss hit
                        print("LOSS - Stop Loss hit at:", high)
                        print(f"Loss amount: {(high - low):.2f} points")
                    elif later_low <= short_tp:  # Take profit hit
                        print("WIN - Take Profit hit at:", short_tp)
                        print(f"Profit amount: {(low - short_tp):.2f} points")
                    else:
                        print("Still Active - Current price within range")
                else:
                    print("Not Triggered - Price never reached entry level")

if __name__ == "__main__":
    fetch_and_analyze_dax40_today()