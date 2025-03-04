import pandas as pd
import yfinance as yf
import vectorbt as vbt
from datetime import datetime, timedelta

# Configuration - Limited to last 60 days for 15m data
START_DATE = (datetime.now() - timedelta(days=59)).strftime('%Y-%m-%d')
END_DATE = datetime.now().strftime('%Y-%m-%d')

# Fetch historical data
dax_data = yf.download(
    '^GDAXI',
    start=START_DATE,
    end=END_DATE,
    interval='15m',
    progress=False,
    auto_adjust=False
).tz_convert('Europe/Berlin')

# Clean data
dax_data = dax_data[~dax_data.index.duplicated(keep='first')]

# Strategy implementation
class DaxBreakoutStrategy(vbt.IndicatorFactory):
    # Define custom parameters
    opening_time = '09:00'
    tp_multiplier = 0.5
    
    def pre_compute(self, high, low, close, **kwargs):
        # Find opening candles (09:00 CET)
        opening_mask = (high.index.time == pd.to_datetime(self.opening_time).time())
        self.opening_highs = high[opening_mask].resample('D').first()
        self.opening_lows = low[opening_mask].resample('D').first()
        
    def compute(self, close, high, low):
        # Merge with close prices
        merged = vbt.merge(
            close, 
            self.opening_highs.rename('opening_high'), 
            self.opening_lows.rename('opening_low'), 
            left_index=True, 
            right_index=True
        ).ffill()
        
        # Calculate risk and TP levels
        risk = merged['opening_high'] - merged['opening_low']
        long_tp = merged['opening_high'] + (risk * self.tp_multiplier)
        short_tp = merged['opening_low'] - (risk * self.tp_multiplier)
        
        # Generate signals
        long_entry = merged['close'].vbt.crossed_above(merged['opening_high'])
        short_entry = merged['close'].vbt.crossed_below(merged['opening_low'])
        
        return (
            long_entry.rename('long_entry'),
            short_entry.rename('short_entry'),
            merged['opening_high'].rename('long_stop'),
            merged['opening_low'].rename('short_stop'),
            long_tp.rename('long_tp'),
            short_tp.rename('short_tp')
        )

# PROPERLY instantiate the strategy using class method
strategy = DaxBreakoutStrategy.run(
    high=dax_data.High,
    low=dax_data.Low,
    close=dax_data.Close
)

# Create portfolio with proper stop management
pf = vbt.Portfolio.from_signals(
    dax_data.Close,
    entries=strategy.long_entry,
    short_entries=strategy.short_entry,
    sl_stop=0.5,  # Stop loss at 50% of risk
    tp_stop=0.5,   # Take profit at 50% of risk
    stop_exit_price='close',  # Exit on next bar's close
    freq='15T'
)

# Display results
print("Backtest Results:")
print(pf.stats())

pf.plot().show()