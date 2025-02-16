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
# This function requests the live bid and ask price and returns them. It also returns the status code (error or success)
def get_price(ticker):
    url = f"https://testnet.binance.vision/api/v3/ticker/bookTicker?symbol={ticker.upper()}USDT"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        bid_price = float(data['bidPrice'])
        ask_price = float(data['askPrice'])
        return bid_price, ask_price, response.status_code
    
    else:
        print(f"Failed to retrieve data: {response.status_code}")
        return None, None, response.status_code


# This function makes sure requests the minimum USD amount allowed for orders
def get_min_notional(ticker):
    exchange_info = client.get_symbol_info(f"{ticker.upper()}USDT")
    for filter in exchange_info['filters']:
        if filter['filterType'] == 'MIN_NOTIONAL':
            return float(filter['minNotional'])
    return 10  # default minimum notional in USDT

# This function asks for quantity and executes buy orders
def buy_order(ticker):
    quantity = input("Input quantity: ")
    symbol = f"{ticker.strip().upper()}USDT"
    # Get current price
    bid_price, ask_price, _ = get_price(ticker)
    if bid_price is None:
        print("Could not get current price")
        return
    
    # Check minimum notional
    order_value = float(quantity) * ask_price
    min_notional = get_min_notional(ticker)
    
    if order_value < min_notional:
        print(f"Order value ({order_value:.2f} USDT) is less than minimum required ({min_notional} USDT)")
        return
    
    try:
        order = client.order_market_buy(symbol=symbol, quantity=quantity,test=True)
        print(f"Buy order done: {order}")
    except Exception as e:
        print(f"Order failed: {str(e)}")

# This function asks for quantity and executes sell orders
def sell_order(ticker):
    quantity = input("Input quantity: ")
    symbol = f"{ticker.strip().upper()}USDT"
    # Get current price
    bid_price, ask_price, _ = get_price(ticker)
    if bid_price is None:
        print("Could not get current price")
        return
    
    # Check minimum notional
    order_value = float(quantity) * bid_price
    min_notional = get_min_notional(ticker)
    
    if order_value < min_notional:
        print(f"Order value ({order_value:.2f} USDT) is less than minimum required ({min_notional} USDT)")
        return
    
    try:
        order = client.order_market_sell(symbol=symbol, quantity=quantity,test=True)
        print(f"Sell order done: {order}")
    except Exception as e:
        print(f"Order failed: {str(e)}")


# This function outputs available quantity and quantity locked in orders, for both USDT and the Selected Asset.
def get_current_positions(ticker):
    try:
        account = client.get_account()
        ticker_free = 0.0
        ticker_locked = 0.0
        usdt_free = 0.0
        usdt_locked = 0.0
        
        for balance in account['balances']:
            if balance['asset'] == ticker.upper():
                ticker_free = float(balance['free'])
                ticker_locked = float(balance['locked'])
            elif balance['asset'] == 'USDT':
                usdt_free = float(balance['free'])
                usdt_locked = float(balance['locked'])
                
        return ticker_free, ticker_locked, usdt_free, usdt_locked
    except Exception as e:
        print(f"Error getting positions: {str(e)}")
        return 0.0, 0.0, 0.0, 0.0

# This function cancels all open orders
def cancel_open_orders(ticker):
    symbol = f"{ticker.strip().upper()}USDT"
    try:
        open_orders = client.get_open_orders(symbol=symbol)
        if not open_orders:
            print("No open orders to cancel")
            return
        
        for order in open_orders:
            result = client.cancel_order(symbol=symbol, orderId=order['orderId'], test=True)
            print(f"Cancelled order: {result}")
        print("All open orders cancelled")
    except Exception as e:
        print(f"Error cancelling orders: {str(e)}")

"""Main"""
import time, math, requests, config #file containing the API keys
from binance.client import Client

"""
API_KEY = 'your_test_api_key'
API_SECRET = 'your_test_api_secret'
"""
client = Client(config.API_KEY,config.API_SECRET, testnet=True)
ticker = input("Input ticker: ")

bid, ask, status = get_price(ticker)
print(f"Bid: {bid} | Ask: {ask}")
ans = 0
while ans!="1" and ans!="2":      
    ticker_free, ticker_locked, usdt_free, usdt_locked = get_current_positions(ticker)
    bid, ask, _ = get_price(ticker)
    
    print(f"\nCurrent positions:")
    print(f"{ticker.upper()} Available: {ticker_free:.8f} (${ticker_free * bid:.2f})")
    print(f"{ticker.upper()} Locked in orders: {ticker_locked:.8f} (${ticker_locked * bid:.2f})")
    print(f"USDT Available: ${usdt_free:.2f}")
    print(f"USDT Locked in orders: ${usdt_locked:.2f}\n")
    
    ans = input("1 - Buy Order\n2 - Sell Order\n3 - Cancel Open Orders\n")
    if ans == "1":
        buy_order(ticker)
    elif ans == "2":
        sell_order(ticker)
    elif ans == "3":
        cancel_open_orders(ticker)
    else:
        print("Enter 1, 2, or 3")









# while True:
#     bid_price, ask_price, status = get_price(ticker)
#     if status == 400:
#         break
#     print(f"Bid: {bid_price} | Ask: {ask_price}")
#     time.sleep(1)


