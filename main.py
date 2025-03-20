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

logging.basicConfig(filename='breakout_trading.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

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
        self.position = None
        self.entry_price = None
        self.sl_price = None
        self.tp_price = None
        self.index_symbol = index_symbol
        self.opening_time = opening_time
        self.data_ready = threading.Event()
        self.trades = []
        self.active_orders = {}

    def nextValidId(self, orderId: int):
        self.nextOrderId = orderId
        logging.info(f"Next valid order ID received: {orderId}")

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
        eastern = pytz.timezone('US/Eastern')
        opening_candle_time = pd.to_datetime(self.opening_time, format='%H:%M').replace(
            year=datetime.now(eastern).year, 
            month=datetime.now(eastern).month, 
            day=datetime.now(eastern).day
        ).tz_localize(eastern).time()
        for bar in self.historical_data:
            if bar['Date'].time() == opening_candle_time:
                self.opening_candle = bar
                logging.info(f"Opening candle set: Open={bar['Open']}, High={bar['High']}, "
                            f"Low={bar['Low']}, Close={bar['Close']}")
                break
        if self.opening_candle:
            self.data_ready.set()
        else:
            logging.warning("Opening candle not found.")

    def tickPrice(self, reqId, tickType, price, attrib):
        logging.info(f"Received tick - Type: {tickType}, Price: {price}")
        if tickType not in [1, 2, 4, 66, 67, 68]:
            return
        self.process_price(price)

    def process_price(self, price):
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
            return

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

        if self.position is None and not self.active_orders:
            if price > opening_high - 5:
                self.enter_trade('long', opening_high, long_sl, long_tp, trade_result)
            elif price < opening_low + 5:
                self.enter_trade('short', opening_low, short_sl, short_tp, trade_result)
        elif self.position == 'long' and len(self.active_orders) < 2:
            if price <= self.sl_price:
                self.exit_trade('long', 'SL Hit', self.sl_price, trade_result)
            elif price >= self.tp_price:
                self.exit_trade('long', 'TP Hit', self.tp_price, trade_result)
            elif now.time() >= dt_time(16, 0):
                self.exit_trade('long', 'EOD', price, trade_result)
        elif self.position == 'short' and len(self.active_orders) < 2:
            if price >= self.sl_price:
                self.exit_trade('short', 'SL Hit', self.sl_price, trade_result)
            elif price <= self.tp_price:
                self.exit_trade('short', 'TP Hit', self.tp_price, trade_result)
            elif now.time() >= dt_time(16, 0):
                self.exit_trade('short', 'EOD', price, trade_result)

    def enter_trade(self, trade_type, entry_price, sl_price, tp_price, trade_result):
        order = Order()
        order.action = "BUY" if trade_type == 'long' else "SELL"
        order.totalQuantity = 1
        order.orderType = "LMT"
        order.lmtPrice = entry_price
        order.eTradeOnly = False  # Explicitly disable unsupported attribute
        order.firmQuoteOnly = False
        orderId = self.nextOrderId
        self.placeOrder(orderId, self.contract, order)
        self.active_orders[orderId] = 'Submitted'
        
        trade_logger.info(f"TRADE ENTRY - Type: {trade_type.upper()}, "
                         f"Entry Price: {entry_price:.2f}, "
                         f"Stop Loss: {sl_price:.2f}, "
                         f"Take Profit: {tp_price:.2f}, "
                         f"Symbol: {self.index_symbol}H5, Order ID: {orderId}")
        print(f"Limit Order Placed: {trade_type.upper()} at {entry_price}, SL={sl_price}, TP={tp_price}, Order ID={orderId}")
        self.nextOrderId += 1
        if trade_type == 'long':
            trade_result['Long_Result'] = 'Triggered'
        else:
            trade_result['Short_Result'] = 'Triggered'

    def exit_trade(self, trade_type, result, exit_price, trade_result):
        if any(status == 'Submitted' for status in self.active_orders.values()):
            return
        order = Order()
        order.action = "SELL" if trade_type == 'long' else "BUY"
        order.totalQuantity = 1
        order.orderType = "LMT"
        order.lmtPrice = exit_price
        order.eTradeOnly = False  # Explicitly disable unsupported attribute
        order.firmQuoteOnly = False
        orderId = self.nextOrderId
        self.placeOrder(orderId, self.contract, order)
        self.active_orders[orderId] = 'Submitted'
        
        trade_logger.info(f"TRADE EXIT - Type: {trade_type.upper()}, "
                         f"Entry Price: {self.entry_price:.2f}, "
                         f"Exit Price: {exit_price:.2f}, "
                         f"Result: {result}, "
                         f"Symbol: {self.index_symbol}H5, Order ID: {orderId}")
        print(f"Limit Order Placed to Exit: {trade_type.upper()} at {exit_price}, Result={result}, Order ID={orderId}")
        self.nextOrderId += 1

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        logging.info(f"Order Status - ID: {orderId}, Status: {status}, Filled: {filled}, Avg Fill Price: {avgFillPrice}")
        if orderId in self.active_orders:
            self.active_orders[orderId] = status
            if status == "Filled" and filled > 0:
                if self.position:
                    entry_order_id = min(self.active_orders.keys())  # First order is entry
                    if orderId == entry_order_id:
                        self.position = 'long' if self.active_orders[orderId] == 'Submitted' else 'short'
                        self.entry_price = lastFillPrice
                        trade_logger.info(f"TRADE EXECUTED - Type: {self.position.upper()}, "
                                         f"Entry Price: {lastFillPrice:.2f}, "
                                         f"Order ID: {orderId}")
                        print(f"Trade Executed: {self.position.upper()} - Entry={lastFillPrice}, Order ID={orderId}")
                    else:
                        points = lastFillPrice - self.entry_price if self.position == 'long' else self.entry_price - lastFillPrice
                        trade_result = {
                            'Date': datetime.now(pytz.timezone('US/Eastern')).date(),
                            'Long_Result': 'SL Hit' if self.position == 'long' and lastFillPrice <= self.sl_price else 'TP Hit',
                            'Short_Result': 'SL Hit' if self.position == 'short' and lastFillPrice >= self.sl_price else 'TP Hit',
                            'Long_Points': points if self.position == 'long' else 0,
                            'Short_Points': points if self.position == 'short' else 0
                        }
                        self.trades.append(trade_result)
                        trade_logger.info(f"TRADE EXECUTED - Type: {self.position.upper()}, "
                                         f"Entry Price: {self.entry_price:.2f}, "
                                         f"Exit Price: {lastFillPrice:.2f}, "
                                         f"Points: {points:.2f}, "
                                         f"Order ID: {orderId}")
                        print(f"Trade Executed: {self.position.upper()} - Entry={self.entry_price}, Exit={lastFillPrice}, Points={points}, Order ID={orderId}")
                        self.position = None
                        self.active_orders.clear()
            elif status in ["Cancelled", "Inactive"]:
                del self.active_orders[orderId]

    def error(self, reqId, errorCode, errorString):
        logging.error(f"Error {errorCode}: {errorString}")

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
        time.sleep(wait_seconds)

def main():
    nyse = xcals.get_calendar("NYSE")
    today = datetime.now().date()
    if not nyse.is_session(today):
        logging.info("Not a trading day. Exiting.")
        return

    logging.info(f"Starting breakout strategy for NASDAQ Futures (NQH5) on {today}")
    app = BreakoutApp(index_symbol="NQ", opening_time="09:30")
    app.connect("127.0.0.1", 7497, clientId=123)
    api_thread = threading.Thread(target=run_loop, args=(app,), daemon=True)
    api_thread.start()
    time.sleep(2)

    app.contract = Contract()
    app.contract.symbol = app.index_symbol
    app.contract.secType = "FUT"
    app.contract.exchange = "CME"
    app.contract.currency = "USD"
    app.contract.lastTradeDateOrContractMonth = "20250321"

    wait_for_opening_candle(app.opening_time)

    logging.info("Requesting historical data for opening candle...")
    eastern = pytz.timezone('US/Eastern')
    utc = pytz.UTC
    now_eastern = datetime.now(eastern)
    target_end = datetime(2025, 3, 20, 9, 45, 0, tzinfo=eastern)
    end_dt = max(now_eastern, target_end).astimezone(utc)
    app.reqHistoricalData(
        reqId=1,
        contract=app.contract,
        endDateTime=end_dt.strftime('%Y%m%d %H:%M:%S UTC'),
        durationStr="3 D",
        barSizeSetting="15 mins",
        whatToShow="TRADES",
        useRTH=0,
        formatDate=1,
        keepUpToDate=False,
        chartOptions=[]
    )

    app.data_ready.wait(timeout=15)
    if not app.opening_candle:
        logging.error("Failed to get opening candle. Exiting.")
        app.disconnect()
        return

    app.reqMarketDataType(3)  # Delayed data
    app.reqMktData(2, app.contract, "233", False, False, [])

    eastern = pytz.timezone('US/Eastern')
    while datetime.now(eastern).time() < dt_time(16, 1):
        time.sleep(1)

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

if __name__ == "__main__":
    main()