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
    url = f"https://api.binance.com/api/v3/ticker/bookTicker?symbol={ticker.upper()}USDT"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        bid_price = float(data['bidPrice'])
        ask_price = float(data['askPrice'])
        return bid_price, ask_price, response.status_code
    
    else:
        print(f"Failed to retrieve data: {response.status_code}")
        return None, None, response.status_code


"""Main"""
import time
import requests
import config

"""
API_KEY = 'your_test_api_key'
API_SECRET = 'your_test_api_secret'
"""

ticker = input("Input Ticker: ").upper()
while True:
    bid_price, ask_price, status = get_price(ticker)
    if status == 400:
        break
    print(f"Bid: {bid_price} | Ask: {ask_price}")
    time.sleep(2)
    
"""test test test"""

"""test test"""

