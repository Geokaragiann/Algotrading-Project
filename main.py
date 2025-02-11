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
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={ticker}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return float(data['price'])
    else:
        print(f"Failed to retrieve data: {response.status_code}")


"""Main"""
import time
import requests
ticker = input("Input Ticker: ").upper()
while True:
    price = get_price(ticker)
    print(price)
    time.sleep(1)
