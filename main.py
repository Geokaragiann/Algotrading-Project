import pandas as pd
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
import threading
import time
from datetime import datetime, timedelta, time as dt_time
import pytz
import exchange_calendars as xcals
import logging

# General logging setup
logging.basicConfig(filename='breakout_trading.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Trade-specific logging setup
trade_logger = logging.getLogger('trade_logger')
trade_handler = logging.FileHandler('trade_execution.log')
trade_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
trade_logger.addHandler(trade_handler)
trade_logger.setLevel(logging.INFO)

class BreakoutApp(EWrapper, EClient):
    def __init__(self, index_symbol="NQ", opening_time="09:30"):
        EClient.__init__(self, self)
        self.nextOrderId = None
        self.historical_data = []
        self.opening_candle = None
        self.position = None  # None, 'long', or 'short'
        self.entry_price = None
        self.sl_price = None
        self.tp_price = None
        self.index_symbol = index_symbol
        self.opening_time = opening_time
        self.data_ready = threading.Event()
        self.trades = []

    def nextValidId(self, orderId: int):
        self.nextOrderId = orderId
        logging.info(f"Next valid order ID received: {orderId}")
        print(f"Connected to IBKR. Next order ID: {orderId}")

    def historicalData(self, reqId, bar):
        self.historical_data.append({
            'Open': bar.open,
            'High': bar.high,
            'Low': bar.low,
            'Close': bar.close,
            'Date': pd.to_datetime(bar.date, format='%Y%m%d %H:%M:%S')
        })

    def historicalDataEnd(self, reqId, start, end):
        logging.info("Historical data retrieval complete")
        print("Historical data retrieved.")
        opening_candle_time = pd.to_datetime(self.opening_time).time()
        for bar in self.historical_data:
            if bar['Date'].time() == opening_candle_time:
                self.opening_candle = bar
                logging.info(f"Opening candle set: Open={bar['Open']}, High={bar['High']}, "
                            f"Low={bar['Low']}, Close={bar['Close']}")
                print(f"Opening candle set at {self.opening_time}: Open={bar['Open']}, "
                      f"High={bar['High']}, Low={bar['Low']}, Close={bar['Close']}")
                break
        if self.opening_candle:
            self.data_ready.set()
        else:
            logging.warning("Opening candle not found.")
            print("Warning: Opening candle not found. Check time or data availability.")

    def tickPrice(self, reqId, tickType, price, attrib):
        if tickType != 4:  # 4 = Last price
            return
        if not self.opening_candle:
            return

        now = datetime.now(pytz.timezone('US/Eastern'))
        opening_open = self.opening_candle['Open']
        opening_high = self.opening_candle['High']
        opening_low = self.opening_candle['Low']
        opening_close = self.opening_candle['Close']

        if opening_close > opening_open:
            candle_color = 'green'
            long_sl = opening_low - 8
            short_sl = opening_high + 8
        elif opening_close < opening_open:
            candle_color = 'red'
            long_sl = opening_low - 8
            short_sl = opening_high + 8
        else:
            return  # Skip neutral candles

        risk = opening_high - opening_low
        long_tp = opening_high + (risk * 0.8)
        short_tp = opening_low - (risk * 0.8)

        trade_result = {
            'Date': now.date(),
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

        if self.position is None:
            if price > opening_high:
                self.enter_trade('long', opening_high, long_sl, long_tp, trade_result)
            elif price < opening_low:
                self.enter_trade('short', opening_low, short_sl, short_tp, trade_result)
        elif self.position == 'long':
            if price <= self.sl_price:
                self.exit_trade('long', 'SL Hit', self.sl_price, trade_result)
            elif price >= self.tp_price:
                self.exit_trade('long', 'TP Hit', self.tp_price, trade_result)
            elif now.time() >= dt_time(16, 0):
                self.exit_trade('long', 'EOD', price, trade_result)
        elif self.position == 'short':
            if price >= self.sl_price:
                self.exit_trade('short', 'SL Hit', self.sl_price, trade_result)
            elif price <= self.tp_price:
                self.exit_trade('short', 'TP Hit', self.tp_price, trade_result)
            elif now.time() >= dt_time(16, 0):
                self.exit_trade('short', 'EOD', price, trade_result)

    def enter_trade(self, trade_type, entry_price, sl_price, tp_price, trade_result):
        order = Order()
        order.action = "BUY" if trade_type == 'long' else "SELL"
        order.totalQuantity = 1  # 1 E-mini NQ contract
        order.orderType = "MKT"
        self.placeOrder(self.nextOrderId, self.contract, order)
        self.position = trade_type
        self.entry_price = entry_price
        self.sl_price = sl_price
        self.tp_price = tp_price
        
        trade_logger.info(f"TRADE ENTRY - Type: {trade_type.upper()}, "
                         f"Entry Price: {entry_price:.2f}, "
                         f"Stop Loss: {sl_price:.2f}, "
                         f"Take Profit: {tp_price:.2f}, "
                         f"Symbol: {self.index_symbol}M5")
        
        logging.info(f"Entered {trade_type.upper()} at {entry_price}, SL={sl_price}, TP={tp_price}")
        print(f"Trade Entered: {trade_type.upper()} at {entry_price}, SL={sl_price}, TP={tp_price}")
        self.nextOrderId += 1
        if trade_type == 'long':
            trade_result['Long_Result'] = 'Triggered'
        else:
            trade_result['Short_Result'] = 'Triggered'

    def exit_trade(self, trade_type, result, exit_price, trade_result):
        order = Order()
        order.action = "SELL" if trade_type == 'long' else "BUY"
        order.totalQuantity = 1
        order.orderType = "MKT"
        self.placeOrder(self.nextOrderId, self.contract, order)
        points = exit_price - self.entry_price if trade_type == 'long' else self.entry_price - exit_price
        
        trade_logger.info(f"TRADE EXIT - Type: {trade_type.upper()}, "
                         f"Entry Price: {self.entry_price:.2f}, "
                         f"Exit Price: {exit_price:.2f}, "
                         f"Result: {result}, "
                         f"Points: {points:.2f}, "
                         f"Symbol: {self.index_symbol}M5")
        
        if trade_type == 'long':
            trade_result['Long_Result'] = result
            trade_result['Long_Points'] = points
        else:
            trade_result['Short_Result'] = result
            trade_result['Short_Points'] = points
        self.trades.append(trade_result)
        logging.info(f"Exited {trade_type.upper()}: {result}, Points={points}")
        print(f"Trade Exited: {trade_type.upper()} - {result}, Points={points}")
        self.position = None
        self.nextOrderId += 1

    def error(self, reqId, errorCode, errorString):
        logging.error(f"Error {errorCode}: {errorString}")
        print(f"IBKR Error {errorCode}: {errorString}")

def run_loop(app):
    app.run()

def wait_for_opening_candle(opening_time="09:30"):
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    opening_hour, opening_minute = map(int, opening_time.split(":"))
    target_time = now.replace(hour=opening_hour, minute=opening_minute + 15, second=0, microsecond=0)
    if now < target_time:
        wait_seconds = (target_time - now).total_seconds()
        logging.info(f"Waiting {wait_seconds / 60:.1f} minutes until {opening_time} +15 minutes...")
        print(f"Current time: {now.strftime('%H:%M:%S %Z')}. Waiting {wait_seconds / 60:.1f} minutes until {opening_time} +15 minutes...")
        time.sleep(wait_seconds)
    else:
        print(f"Past {opening_time} +15 minutes. Checking for opening candle now.")

def main():
    nyse = xcals.get_calendar("NYSE")
    today = datetime.now().date()
    if not nyse.is_session(today):
        logging.info("Not a trading day. Exiting.")
        print(f"Today ({today}) is not a trading day (e.g., weekend or holiday). Exiting.")
        return

    print(f"Starting breakout strategy for NASDAQ Futures (NQM5) on {today}...")
    logging.info(f"Starting breakout strategy for NASDAQ Futures (NQM5) on {today}")

    app = BreakoutApp(index_symbol="NQ", opening_time="09:30")
    app.connect("127.0.0.1", 7497, clientId=123)
    api_thread = threading.Thread(target=run_loop, args=(app,), daemon=True)
    api_thread.start()
    time.sleep(2)

    # Define NASDAQ 100 Futures contract (NQM5 - June 2025)
    app.contract = Contract()
    app.contract.symbol = app.index_symbol  # "NQ"
    app.contract.secType = "FUT"
    app.contract.exchange = "CME"
    app.contract.currency = "USD"
    app.contract.lastTradeDateOrContractMonth = "20250620"  # June 20, 2025 expiration

    wait_for_opening_candle(app.opening_time)

    print("Requesting historical data for opening candle...")
    app.reqHistoricalData(
        reqId=1,
        contract=app.contract,
        endDateTime="",
        durationStr="1 D",
        barSizeSetting="15 mins",
        whatToShow="TRADES",
        useRTH=1,
        formatDate=1,
        keepUpToDate=False,
        chartOptions=[]
    )

    app.data_ready.wait(timeout=10)
    if not app.opening_candle:
        logging.error("Failed to get opening candle. Exiting.")
        print("Error: Failed to get opening candle. Check IBKR connection or timing. Exiting.")
        app.disconnect()
        return

    print("Subscribing to real-time market data...")
    app.reqMarketDataType(3)  # Delayed data for paper trading
    app.reqMktData(2, app.contract, "", False, False, [])

    eastern = pytz.timezone('US/Eastern')
    print("Monitoring NASDAQ Futures (NQM5) for breakouts until 4:01 PM ET...")
    while datetime.now(eastern).time() < dt_time(16, 1):
        time.sleep(1)

    # Allow time for EOD processing
    time.sleep(10)

    if app.position:
        logging.warning("Position still open after EOD. Closing manually.")
        print("Warning: Position still open after EOD. Please close manually.")

    results_df = pd.DataFrame(app.trades)
    if not results_df.empty:
        results_df.to_csv('trade_results.csv', index=False)
        logging.info("Trade results saved to 'trade_results.csv'")
        print("Trading session complete. Results saved to 'trade_results.csv'")
    else:
        print("No trades executed today.")

    app.disconnect()
    logging.info("Market closed. Disconnected.")
    print("Disconnected from IBKR. Strategy stopped.")

if __name__ == "__main__":
    main()