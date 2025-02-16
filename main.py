# Copyright (C) 2025 The Repository Collaborators

# This program is free software: you can redistribute it and/or modify  
# it under the terms of the GNU Affero General Public License as published by  
# the Free Software Foundation, either version 3 of the License, or  
# (at your option) any later version.  

# This program is distributed in the hope that it will be useful,  
# but WITHOUT ANY WARRANTY; without even the implied warranty of  
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the  
# GNU Affero General Public License for more details.  

# You should have received a copy of the GNU Affero General Public License  
# along with this program. If not, see <https://www.gnu.org/licenses/>.
"""Functions"""
from binance.um_futures import UMFutures
import math

def get_price(ticker):
    try:
        symbol = f"{ticker.upper()}USDT"
        ticker_price = client.book_ticker(symbol=symbol)
        bid_price = float(ticker_price['bidPrice'])
        ask_price = float(ticker_price['askPrice'])
        return bid_price, ask_price, 200
    except Exception as e:
        print(f"Failed to retrieve data: {str(e)}")
        return None, None, 400

def get_quantity_precision(ticker):
    try:
        symbol = f"{ticker.upper()}USDT"
        exchange_info = client.exchange_info()
        for sym in exchange_info['symbols']:
            if sym['symbol'] == symbol:
                for filt in sym['filters']:
                    if filt['filterType'] == 'LOT_SIZE':
                        return int(round(-math.log10(float(filt['stepSize']))))
        return 4  # default precision
    except Exception as e:
        print(f"Error getting precision: {str(e)}")
        return 4

def get_min_notional(ticker):
    try:
        symbol = f"{ticker.upper()}USDT"
        exchange_info = client.exchange_info()
        for sym in exchange_info['symbols']:
            if sym['symbol'] == symbol:
                for filt in sym['filters']:
                    if filt['filterType'] == 'MIN_NOTIONAL':
                        return float(filt['notional'])
        return 5.0  # default minimum notional
    except Exception as e:
        print(f"Error getting min notional: {str(e)}")
        return 5.0

def buy_order(ticker):
    try:
        symbol = f"{ticker.strip().upper()}USDT"
        bid_price, ask_price, _ = get_price(ticker)
        if bid_price is None:
            return

        qty_precision = get_quantity_precision(ticker)
        quantity = input(f"Input quantity (precision {qty_precision}): ")
        
        # Validate quantity format
        try:
            quantity = float(quantity)
            quantity = round(quantity, qty_precision)
        except ValueError:
            print("Invalid quantity format")
            return

        order_value = quantity * ask_price
        min_notional = get_min_notional(ticker)
        
        if order_value < min_notional:
            print(f"Order value ({order_value:.2f} USDT) < min ({min_notional} USDT)")
            return

        # Send futures order
        order = client.new_order(
            symbol=symbol,
            side='BUY',
            type='MARKET',
            quantity=quantity
        )
        print(f"Long position opened: {order}")
    except Exception as e:
        print(f"Order failed: {str(e)}")

def sell_order(ticker):
    try:
        symbol = f"{ticker.strip().upper()}USDT"
        bid_price, ask_price, _ = get_price(ticker)
        if bid_price is None:
            return

        qty_precision = get_quantity_precision(ticker)
        quantity = input(f"Input quantity (precision {qty_precision}): ")
        
        try:
            quantity = float(quantity)
            quantity = round(quantity, qty_precision)
        except ValueError:
            print("Invalid quantity format")
            return

        order_value = quantity * bid_price
        min_notional = get_min_notional(ticker)
        
        if order_value < min_notional:
            print(f"Order value ({order_value:.2f} USDT) < min ({min_notional} USDT)")
            return

        order = client.new_order(
            symbol=symbol,
            side='SELL',
            type='MARKET',
            quantity=quantity
        )
        print(f"Position closed: {order}")
    except Exception as e:
        print(f"Order failed: {str(e)}")

def get_current_positions(ticker):
    try:
        account_info = client.account()
        positions = account_info['positions']
        symbol = f"{ticker.upper()}USDT"
        
        ticker_free = 0.0
        ticker_locked = 0.0
        usdt_free = float(account_info['availableBalance'])
        usdt_locked = 0.0

        for position in positions:
            if position['symbol'] == symbol:
                ticker_free = float(position['positionAmt'])
                ticker_locked = (float(position['initialMargin']) + 
                                float(position['maintMargin']))
        
        # Calculate USDT locked
        usdt_locked = sum(
            float(pos['initialMargin']) + float(pos['maintMargin'])
            for pos in positions
        )
        
        return ticker_free, ticker_locked, usdt_free, usdt_locked
    except Exception as e:
        print(f"Error getting positions: {str(e)}")
        return 0.0, 0.0, 0.0, 0.0

def cancel_open_orders(ticker):
    try:
        symbol = f"{ticker.strip().upper()}USDT"
        result = client.cancel_open_orders(symbol=symbol)
        print(f"Cancelled orders for {symbol}: {result}")
    except Exception as e:
        print(f"Error cancelling orders: {str(e)}")

"""Main"""
import time, config

client = UMFutures(
    key=config.API_KEY,
    secret=config.API_SECRET,
    base_url="https://testnet.binancefuture.com"
)

if __name__ == "__main__":
    ticker = input("Input ticker (e.g. BTC): ").strip().upper()
    
    while True:
        bid, ask, status = get_price(ticker)
        if status != 200:
            time.sleep(1)
            continue
            
        ticker_free, ticker_locked, usdt_free, usdt_locked = get_current_positions(ticker)
        
        print("\n" + "="*40)
        print(f"{ticker}USDT Trading Interface")
        print(f"Bid: {bid:.8f} | Ask: {ask:.8f}")
        print(f"\n{ticker} Position:")
        print(f"Available: {ticker_free:.8f} (${ticker_free * bid:.2f})")
        print(f"Locked: {ticker_locked:.8f} (${ticker_locked * bid:.2f})")
        print(f"\nUSDT Balance:")
        print(f"Available: ${usdt_free:.2f}")
        print(f"Locked: ${usdt_locked:.2f}")
        print("="*40 + "\n")
        
        action = input("1 - Buy/Long\n2 - Sell/Close\n3 - Cancel Orders\n4 - Refresh\nQ - Quit\n> ")
        
        if action == "1":
            buy_order(ticker)
        elif action == "2":
            sell_order(ticker)
        elif action == "3":
            cancel_open_orders(ticker)
        elif action.upper() == "Q":
            break
        elif action == "4":
            continue
        else:
            print("Invalid selection")
        
        time.sleep(1)  # Rate limit protection








# while True:
#     bid_price, ask_price, status = get_price(ticker)
#     if status == 400:
#         break
#     print(f"Bid: {bid_price} | Ask: {ask_price}")
#     time.sleep(1)


