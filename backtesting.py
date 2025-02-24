import pandas as pd
import numpy as np
import trading2

class Backtester:
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = 0
        self.trades = []
        
    def backtest(self, data, signals):
        """
        Backtest trading signals against historical price data.
        
        Parameters:
        data (pd.DataFrame): DataFrame with columns 'date', 'open', 'high', 'low', 'close', 'volume'
        signals (pd.Series): Series with same index as data, containing 1 (buy), -1 (sell), or 0 (hold)
        
        Returns:
        dict: Performance metrics including returns, sharpe ratio, max drawdown
        """
        # Initialize tracking variables
        portfolio_value = []
        current_capital = self.initial_capital
        position = 0
        trades = []
        
        for i in range(len(data)):
            date = data.index[i]
            close_price = data['Close'].iloc[i]
            signal = signals.iloc[i]
            
            # Process signals
            if signal == 1 and position == 0:  # Buy signal
                shares = current_capital // close_price
                cost = shares * close_price
                current_capital -= cost
                position = shares
                trades.append({
                    'date': date,
                    'type': 'buy',
                    'price': close_price,
                    'shares': shares,
                    'cost': cost
                })
                
            elif signal == -1 and position > 0:  # Sell signal
                proceeds = position * close_price
                current_capital += proceeds
                trades.append({
                    'date': date,
                    'type': 'sell',
                    'price': close_price,
                    'shares': position,
                    'proceeds': proceeds
                })
                position = 0
            
            # Calculate portfolio value
            portfolio_value.append(current_capital + (position * close_price))
        
        # Calculate performance metrics
        portfolio_value = pd.Series(portfolio_value, index=data.index)
        returns = portfolio_value.pct_change().dropna()
        
        metrics = {
            'total_return': (portfolio_value.iloc[-1] - self.initial_capital) / self.initial_capital * 100,
            'sharpe_ratio': self._calculate_sharpe_ratio(returns),
            'max_drawdown': self._calculate_max_drawdown(portfolio_value),
            'number_of_trades': len(trades),
            'final_value': portfolio_value.iloc[-1],
            'trades': trades
        }
        
        return metrics, portfolio_value
    
    def _calculate_sharpe_ratio(self, returns, risk_free_rate=0.01):
        """Calculate annualized Sharpe ratio"""
        excess_returns = returns - risk_free_rate/252
        return np.sqrt(252) * excess_returns.mean() / returns.std()
    
    def _calculate_max_drawdown(self, portfolio_value):
        """Calculate maximum drawdown"""
        rolling_max = portfolio_value.expanding().max()
        drawdowns = (portfolio_value - rolling_max) / rolling_max
        return drawdowns.min() * 100

def plot_results(data, portfolio_value):
    """
    Plot the equity curve and original price data
    Requires matplotlib
    """
    import matplotlib.pyplot as plt
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # Plot price data
    ax1.plot(data.index, data['Close'], label='Price')
    ax1.set_title('Price History')
    ax1.legend()
    
    # Plot equity curve
    ax2.plot(portfolio_value.index, portfolio_value, label='Portfolio Value')
    ax2.set_title('Equity Curve')
    ax2.legend()
    
    plt.tight_layout()
    return fig

def main():
    # Fetch data and generate signals
    data = trading2.fetch_ohlcv_data()
    signals = trading2.generate_fib_signals(data)
    
    # Run backtest
    backtester = Backtester()
    metrics, portfolio_value = backtester.backtest(data, signals)
    
    # Print results
    print("\nBacktest Results:")
    print(f"Total Return: {metrics['total_return']:.2f}%")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {metrics['max_drawdown']:.2f}%")
    print(f"Number of Trades: {metrics['number_of_trades']}")
    print(f"Final Portfolio Value: ${metrics['final_value']:,.2f}")
    
    # Plot results
    plot_results(data, portfolio_value)

if __name__ == "__main__":
    main()
