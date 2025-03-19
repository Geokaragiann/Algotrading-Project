import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

class BreakoutStrategy:
    def __init__(self):
        """Initialize the strategy with an empty list to store trade results."""
        self.trades = []
        
    def analyze_day(self, day_data, opening_time):
        """
        Analyze a single day's 15-minute candle data to determine trade outcomes.
        
        Args:
            day_data (pd.DataFrame): 15-minute OHLC data for a single trading day.
            opening_time (str): Time of the opening candle in 'HH:MM' format (e.g., '14:45').
        """
        # Identify the opening 15-minute candle based on the provided opening time
        # CAREFUL! ADJUST FOR TIMEZONE OR DAYLIGHT SAVING TIME IF NECESSARY!
        opening_candle_time = pd.to_datetime(opening_time).time()
        opening_candle = day_data[day_data.index.time == opening_candle_time]
        
        if opening_candle.empty:
            return
        
        # Extract OHLC prices from the opening candle
        opening_open = float(opening_candle['Open'].iloc[0])
        opening_high = float(opening_candle['High'].iloc[0])
        opening_low = float(opening_candle['Low'].iloc[0])
        opening_close = float(opening_candle['Close'].iloc[0])
        
        # Determine candle color and set stop loss levels
        if opening_close > opening_open:
            candle_color = 'green'
            long_sl = opening_low - 8    # Long SL 8 points below low
            short_sl = opening_high + 8  # Short SL 8 points above high
        elif opening_close < opening_open:
            candle_color = 'red'
            long_sl = opening_low - 8    # Long SL 8 points below low
            short_sl = opening_high + 8  # Short SL 8 points above high
        else:
            return
        
        # Get price action after the opening candle
        later_data = day_data[day_data.index > opening_candle.index[0]]
        
        if later_data.empty:
            return
        
        # Get the day's closing price (or last available if today)
        day_close = float(day_data['Close'].iloc[-1])
        
        # Calculate risk and take profit levels
        risk = opening_high - opening_low
        long_tp = opening_high + (risk * 0.8)
        short_tp = opening_low - (risk * 0.8)
        
        # Initialize trade result dictionary
        trade_result = {
            'Date': opening_candle.index[0].date(),
            'Candle_Color': candle_color,
            'Opening_High': opening_high,
            'Opening_Low': opening_low,
            'Long_SL': long_sl,
            'Long_TP': long_tp,
            'Short_SL': short_sl,
            'Short_TP': short_tp,
            'Long_Result': 'Not Triggered',
            'Long_Points': 0,
            'Short_Result': 'Not Triggered',
            'Short_Points': 0
        }
        
        # Trade variables
        trade_type = None
        entry_price = None
        sl_price = None
        tp_price = None
        
        # Debug for March 5, 2025
        if trade_result['Date'] == datetime(2025, 3, 5).date():
            print(f"Debugging March 5, 2025:")
            print(f"Open: {opening_open}, High: {opening_high}, Low: {opening_low}, Close: {opening_close}")
            print(f"Long SL: {long_sl}, Long TP: {long_tp}, Short SL: {short_sl}, Short TP: {short_tp}")
        
        # Iterate through subsequent candles
        for timestamp, candle in later_data.iterrows():
            high = float(candle['High'])
            low = float(candle['Low'])
            
            if trade_result['Date'] == datetime(2025, 3, 5).date():
                print(f"Candle at {timestamp}: High={high}, Low={low}")
            
            # Check for trade trigger
            if trade_type is None:
                if high > opening_high:
                    trade_type = 'long'
                    entry_price = opening_high
                    sl_price = long_sl
                    tp_price = long_tp
                elif low < opening_low:
                    trade_type = 'short'
                    entry_price = opening_low
                    sl_price = short_sl
                    tp_price = short_tp
            
            # Monitor active trade
            if trade_type == 'long':
                if low <= sl_price:
                    trade_result['Long_Result'] = 'SL Hit'
                    trade_result['Long_Points'] = sl_price - entry_price
                    if trade_result['Date'] == datetime(2025, 3, 5).date():
                        print(f"Long SL Hit at {low}, below {sl_price}")
                    break
                elif high >= tp_price:
                    trade_result['Long_Result'] = 'TP Hit'
                    trade_result['Long_Points'] = tp_price - entry_price
                    break
            elif trade_type == 'short':
                if high >= sl_price:
                    trade_result['Short_Result'] = 'SL Hit'
                    trade_result['Short_Points'] = entry_price - sl_price
                    break
                elif low <= tp_price:
                    trade_result['Short_Result'] = 'TP Hit'
                    trade_result['Short_Points'] = entry_price - tp_price
                    break
        
        # If trade triggered but unresolved, close at EOD
        else:
            if trade_type == 'long':
                trade_result['Long_Result'] = 'EOD'
                trade_result['Long_Points'] = day_close - entry_price
            elif trade_type == 'short':
                trade_result['Short_Result'] = 'EOD'
                trade_result['Short_Points'] = entry_price - day_close
        
        self.trades.append(trade_result)

def run_backtest(index_symbol='^IXIC', opening_time='14:45'):
    """
    Run the backtest for a given index and opening time.
    
    Args:
        index_symbol (str): The ticker symbol for the index (e.g., '^IXIC' for NASDAQ).
        opening_time (str): Time of the opening candle in 'HH:MM' format (e.g., '14:45').
    """
    # Set date range to include recent data
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    print(f"Fetching data for {index_symbol} from {start_date} to {end_date}...")
    try:
        index_data = yf.download(
            index_symbol,
            start=start_date,
            end=end_date,
            interval='15m',
            progress=False
        )
    except Exception as e:
        print(f"Error downloading data: {e}")
        return
    
    if index_data.empty:
        print("No data downloaded. Possible reasons:")
        print("- Market might be closed (e.g., weekend or holiday)")
        print("- Data not yet available for today")
        print("- Internet connection issue")
        print(f"Last index timestamp: {index_data.index[-1] if not index_data.empty else 'N/A'}")
        return
    
    # Remove timezone for consistency
    index_data.index = index_data.index.tz_localize(None)
    print(f"Data retrieved. Last timestamp: {index_data.index[-1]}")
    
    print("Running strategy analysis...")
    strategy = BreakoutStrategy()
    
    for date, day_data in index_data.groupby(index_data.index.date):
        strategy.analyze_day(day_data, opening_time)
    
    results_df = pd.DataFrame(strategy.trades)
    
    if not results_df.empty:
        print("\nBacktest Results:")
        print("================")
        print(f"Total Days Analyzed: {len(results_df)}")
        
        # Long trade statistics
        long_sl_hit = len(results_df[results_df['Long_Result'] == 'SL Hit'])
        long_tp_hit = len(results_df[results_df['Long_Result'] == 'TP Hit'])
        long_eod = len(results_df[results_df['Long_Result'] == 'EOD'])
        long_not_triggered = len(results_df[results_df['Long_Result'] == 'Not Triggered'])
        long_total_points = results_df['Long_Points'].sum()
        
        print("\nLong Trades:")
        print(f"SL Hit: {long_sl_hit}")
        print(f"TP Hit: {long_tp_hit}")
        print(f"EOD (Closed at End of Day): {long_eod}")
        print(f"Not Triggered: {long_not_triggered}")
        print(f"Total Points: {long_total_points:.2f}")
        
        # Short trade statistics
        short_sl_hit = len(results_df[results_df['Short_Result'] == 'SL Hit'])
        short_tp_hit = len(results_df[results_df['Short_Result'] == 'TP Hit'])
        short_eod = len(results_df[results_df['Short_Result'] == 'EOD'])
        short_not_triggered = len(results_df[results_df['Short_Result'] == 'Not Triggered'])
        short_total_points = results_df['Short_Points'].sum()
        
        print("\nShort Trades:")
        print(f"SL Hit: {short_sl_hit}")
        print(f"TP Hit: {short_tp_hit}")
        print(f"EOD (Closed at End of Day): {short_eod}")
        print(f"Not Triggered: {short_not_triggered}")
        print(f"Total Points: {short_total_points:.2f}")
        
        print(f"\nOverall Total Points: {(long_total_points + short_total_points):.2f}")
        
        # Calculate additional metrics
        long_triggered = results_df[results_df['Long_Result'] != 'Not Triggered']
        short_triggered = results_df[results_df['Short_Result'] != 'Not Triggered']
        
        total_trades = len(long_triggered) + len(short_triggered)
        wins = len(long_triggered[long_triggered['Long_Result'] == 'TP Hit']) + len(short_triggered[short_triggered['Short_Result'] == 'TP Hit'])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        all_points = pd.concat([long_triggered['Long_Points'], short_triggered['Short_Points']])
        gross_profits = all_points[all_points > 0].sum()
        gross_losses = abs(all_points[all_points < 0].sum())
        profit_factor = gross_profits / gross_losses if gross_losses > 0 else float('inf')
        
        avg_win = all_points[all_points > 0].mean() if wins > 0 else 0
        avg_loss = abs(all_points[all_points < 0].mean()) if (total_trades - wins) > 0 else 0
        expectancy = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * avg_loss)
        
        print("\nAdditional Metrics:")
        print(f"Total Trades: {total_trades}")
        print(f"Win Rate: {win_rate:.2f}% (>55% preferably)")
        print(f"Profit Factor: {profit_factor:.2f} (>1.5 preferably)")
        print(f"Expectancy (Points per Trade): {expectancy:.2f} (>5 points preferably)")
        
        results_df.to_csv('backtest_results.csv', index=False)
        print("\nDetailed results saved to 'backtest_results.csv'")
    else:
        print("No trades were executed in the backtest period.")

if __name__ == "__main__":
    # Example: Customize index_symbol and opening_time as needed
    run_backtest(index_symbol='^IXIC', opening_time='14:45')  # NASDAQ, 14:45 opening
    # run_backtest(index_symbol='^GSPC', opening_time='09:30')  # S&P 500, 09:30 opening