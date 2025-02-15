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

def get_user_inputs():
    return {
        'ticker': input("Input Ticker: "),
        'pos_size': input("Input position size (in $): "),
        'take_profit': input("Input take profit (in %): "),
        'stop_loss': input("Input stop loss (in %): ")
    }

def execute_trade(inputs):
    client = Client(config.API_KEY, config.API_SECRET, testnet=True)

    try:
        # Get current price to calculate quantity
        ticker_price = float(client.get_symbol_ticker(symbol=f"{inputs['ticker'].upper()}USDT")['price'])
        quantity = float(inputs['pos_size']) / ticker_price
        
        # Get symbol info and find the LOT_SIZE filter
        info = client.get_symbol_info(f"{inputs['ticker'].upper()}USDT")
        lot_size_filter = next(filter(lambda x: x['filterType'] == 'LOT_SIZE', info['filters']))
        price_filter = next(filter(lambda x: x['filterType'] == 'PRICE_FILTER', info['filters']))
        
        # Round quantity according to LOT_SIZE
        quantity = round_step_size(quantity, lot_size_filter['stepSize'])
        
        print(f"\nCalculated quantity: {quantity}")  # Debug print
        
        # Place market buy order
        order = client.create_order(
            symbol=f"{inputs['ticker'].upper()}USDT",
            side='BUY',
            type='MARKET',
            quantity=quantity
        )
        
        # Get fill price from the order
        fill_price = float(order['fills'][0]['price'])
        
        # Calculate and round take profit and stop loss prices
        tp_price = round_step_size(fill_price * (1 + float(inputs['take_profit'])/100), price_filter['tickSize'])
        sl_price = round_step_size(fill_price * (1 - float(inputs['stop_loss'])/100), price_filter['tickSize'])
        
        # Place take profit sell order
        tp_order = client.create_order(
            symbol=f"{inputs['ticker'].upper()}USDT",
            side='SELL',
            type='LIMIT',
            timeInForce='GTC',
            quantity=quantity,
            price=tp_price
        )
        
        # Place stop loss order
        sl_order = client.create_order(
            symbol=f"{inputs['ticker'].upper()}USDT",
            side='SELL',
            type='STOP_LOSS_LIMIT',
            timeInForce='GTC',
            quantity=quantity,
            price=sl_price,
            stopPrice=sl_price
        )
        
        print(f"\nOrders placed successfully:")
        print(f"Entry Price: ${fill_price:.4f}")
        print(f"Take Profit: ${tp_price:.4f}")
        print(f"Stop Loss: ${sl_price:.4f}")
        
        # Show current orders
        open_orders = client.get_open_orders(symbol=f"{inputs['ticker'].upper()}USDT")
        print("\nCurrent Open Orders:")
        for order in open_orders:
            print(f"Order ID: {order['orderId']}")
            print(f"Type: {order['type']}")
            print(f"Side: {order['side']}")
            print(f"Price: ${float(order['price']):.4f}")
            print(f"Quantity: {float(order['origQty']):.8f}")
            print("------------------------")
        
    except Exception as e:
        print(f"\n❌ An error occurred: {str(e)}")
        print("Error details:", type(e).__name__)
        if hasattr(e, 'code') and hasattr(e, 'message'):
            print(f"Code: {e.code}")
            print(f"Message: {e.message}")

def round_step_size(quantity, step_size):
    precision = int(round(-math.log10(float(step_size))))
    return round(quantity, precision)

def check_orders(ticker):
    client = Client(config.API_KEY, config.API_SECRET, testnet=True)
    
    open_orders = client.get_open_orders(symbol=f"{ticker.upper()}USDT")
    print(f"\n=== Current Open Orders for {ticker.upper()} ===")
    
    if not open_orders:
        print("No open orders found.")
    else:
        for order in open_orders:
            print("\n📊 Order Details:")
            print(f"Type: {'🛑 Stop Loss' if order['type'] == 'STOP_LOSS_LIMIT' else '🎯 Take Profit' if order['type'] == 'LIMIT' else order['type']}")
            print(f"Side: {'🔴 SELL' if order['side'] == 'SELL' else '🟢 BUY'}")
            print(f"Price: ${float(order['price']):.4f}")
            print(f"Quantity: {float(order['origQty']):.8f} {ticker.upper()}")
            if order['type'] == 'STOP_LOSS_LIMIT':
                print(f"Stop Trigger: ${float(order['stopPrice']):.4f}")
            print("------------------------")
    
    # Get current balance
    balance = client.get_asset_balance(asset=ticker.upper())
    print(f"\n💰 Current {ticker.upper()} Balance:")
    print(f"Available: {float(balance['free']):.8f}")
    print(f"In Orders: {float(balance['locked']):.8f}")
    
    # Get current market price
    current_price = float(client.get_symbol_ticker(symbol=f"{ticker.upper()}USDT")['price'])
    print(f"\n📈 Current Market Price: ${current_price:.4f}")

def close_position(ticker):
    client = Client(config.API_KEY, config.API_SECRET, testnet=True)
    symbol = f"{ticker.upper()}USDT"
    
    try:
        # First cancel all open orders
        result = client.cancel_all_open_orders(symbol=symbol)
        print("\n🚫 Cancelled all open orders")
        
        # Get current balance
        balance = client.get_asset_balance(asset=ticker.upper())
        quantity = float(balance['free'])
        
        if quantity > 0:
            # Get symbol info for LOT_SIZE filter
            info = client.get_symbol_info(symbol)
            lot_size_filter = next(filter(lambda x: x['filterType'] == 'LOT_SIZE', info['filters']))
            # Round quantity according to LOT_SIZE
            quantity = round_step_size(quantity, lot_size_filter['stepSize'])
            
            # Place market sell order for entire balance
            order = client.create_order(
                symbol=symbol,
                side='SELL',
                type='MARKET',
                quantity=quantity
            )
            print(f"✅ Sold {quantity} {ticker.upper()} at market price")
        else:
            print(f"No {ticker.upper()} balance to sell")
            
        # Show final balance
        final_balance = client.get_asset_balance(asset=ticker.upper())
        print(f"\n💰 Final {ticker.upper()} Balance: {float(final_balance['free']):.8f}")
        
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")

"""Main"""
import time, math, requests, config #file containing the API keys
from binance.client import Client

"""
API_KEY = 'your_test_api_key'
API_SECRET = 'your_test_api_secret'
"""

while True:
    print("\n=== Trading Menu ===")
    print("1. 📈 Execute new trade")
    print("2. 📊 Check existing orders")
    print("3. 📉 Close position")
    print("4. 🚪 Exit")
    
    choice = input("\nEnter your choice (1-4): ")
    
    if choice == "1":
        inputs = get_user_inputs()
        while True:
            ans = input("\nStart trade? (y/N): ")
            
            if ans.lower() == 'y':
                execute_trade(inputs)
                break
            elif ans.lower() == 'n' or ans == '':
                break
            else:
                print("Invalid input. Please enter 'y', 'N', or nothing.")
    
    elif choice == "2":
        ticker = input("\nEnter ticker to check (e.g., BTC): ")
        check_orders(ticker)
    
    elif choice == "3":
        ticker = input("\nEnter ticker to close position (e.g., BTC): ")
        print(f"\n⚠️ This will cancel all open orders and sell all {ticker.upper()}")
        confirm = input("Are you sure? (y/N): ")
        if confirm.lower() == 'y':
            close_position(ticker)
        else:
            print("Position close cancelled")
    
    elif choice == "4":
        print("\nExiting program... Goodbye! 👋")
        break
    
    else:
        print("\n❌ Invalid choice. Please enter 1, 2, 3, or 4.")









# while True:
#     bid_price, ask_price, status = get_price(ticker)
#     if status == 400:
#         break
#     print(f"Bid: {bid_price} | Ask: {ask_price}")
#     time.sleep(1)


