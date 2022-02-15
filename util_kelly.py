from typing import Union
from datetime import datetime, date
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def string_padding(string, width):
	"""
	Pads a string with spaces to the specified width.
	"""
	filler = '.' * (width - len(string))
	return string + filler

def daily_risk_free_rate(r, period=252):
	"""
	Calculates the daily risk-free rate for a given risk-free rate of the specified period.
	"""
	return (1 + r)**(1/period)

def kelly_factor(mean, std, r):
	"""
	Calculates the Kelly factor for a given mean, standard deviation, and risk-free rate.
	"""
	return (mean - r) / std**2

def capped_kelly_factor(kelly_factor, minimum, maximum):
	"""
	Capped Kelly factor.
	"""
	kelly_factor = np.where(np.isnan(kelly_factor), 0, kelly_factor)
	kelly_factor = np.where(kelly_factor < minimum, minimum, kelly_factor)
	kelly_factor = np.where(kelly_factor > maximum, maximum, kelly_factor)
	return kelly_factor

def calculate_kelly_factor(returns, risk_free_rate, window=252, minimum=0, maximum=3):
	"""
	Calculates the Kelly factor for a given returns dataframe and risk-free rate.
	"""
	mean = returns.rolling(window).mean()
	std = returns.rolling(window).std()
	r = np.log(daily_risk_free_rate(risk_free_rate)) # why log of daily risk free rate?
	k = kelly_factor(mean, std, r)
	k = capped_kelly_factor(k, minimum, maximum)
	return k

def simulate_kelly_strategy(market_data, rebalancing_interval, \
	annual_risk_free_rate=0.01, window=252, kelly_fraction=1.0, min_kelly=0.0, max_kelly=100.0):

	market_data['returns'] = market_data['Close'] / market_data['Close'].shift(1)
	market_data['log_returns'] = np.log(market_data["returns"])
	market_data['kelly_factor'] = calculate_kelly_factor(market_data['log_returns'], window=window, \
		risk_free_rate=annual_risk_free_rate, minimum=min_kelly, maximum=max_kelly)
	market_data['kelly_fraction'] = market_data['kelly_factor'] * kelly_fraction

	r_daily = daily_risk_free_rate(annual_risk_free_rate)
	
	# Allocate space
	portfolio = np.zeros(len(market_data))
	equity = np.zeros(len(market_data))
	cash = np.zeros(len(market_data))

	for i, _row in enumerate(market_data.iterrows()):
		row = _row[1]
		if i == 0:
			portfolio[0] = 1
			cash[0] = 1
			equity[0] = 0
		else:
			portfolio[i] = cash[i-1] * r_daily + equity[i-1] * row['returns']
			if i % rebalancing_interval == 0:
				equity[i] = portfolio[i] * row['kelly_fraction']
				cash[i] = portfolio[i] * (1 - row['kelly_fraction'])
			else:
				equity[i] = equity[i-1]
				cash[i] = cash[i-1]

	# Collect results
	market_data['portfolio'] = portfolio
	market_data['equity'] = equity
	market_data['cash'] = cash
	market_data['strategy_returns'] = market_data['portfolio'] / market_data['portfolio'].shift(1)
	market_data['strategy_log_returns'] = np.log(market_data['strategy_returns'])
	market_data['strategy_cum_returns'] = market_data['strategy_log_returns'].cumsum()
	market_data['cum_returns'] = market_data['log_returns'].cumsum()
	
	return market_data

def plot_strategy(dataset, ablation, label_return="", \
	title_return="Buy-and-hold and Long-Only Strategy with Kelly Sizing" ,title_kelly="Factor", logplot=False):

	fig, ax = plt.subplots(2, figsize=(12, 8), sharex=True)
	ax[0].plot(np.exp(dataset['cum_returns']) * 100, label='Buy and Hold', linewidth=3)

	for i, factor in enumerate(ablation):
		if logplot:
			ax[0].semilogy(np.exp(dataset[f"strategy_cum_returns_{i}"]) * 100, label=f"{label_return} {factor}", linewidth=0.9)
		else:
			ax[0].plot(np.exp(dataset[f"strategy_cum_returns_{i}"]) * 100, label=f"{label_return} {factor}", linewidth=0.9)

		ax[1].plot(dataset[f"kelly_factor_{i}"])

	ax[0].set_ylabel('Returns (%)')
	ax[0].set_title(title_return)
	ax[0].legend()
	ax[1].set_ylabel('Leverage')
	ax[1].set_xlabel('Date')
	ax[1].set_title(title_kelly)
	plt.tight_layout()
	plt.show()

class StockMarketData():
	original_data: pd.DataFrame
	data: pd.DataFrame

	def __init__(self, path_to_csv: str, **kwargs):
		self.original_data = pd.read_csv(path_to_csv, **kwargs)
		self.data = self.original_data.copy()

	def restrict_date(self, start_date: Union[datetime,date], end_date: Union[datetime,date]) -> None:
		"""
		Restricts the data to the specified date range.
		"""
		start_timestamp = start_date
		end_timestamp = end_date

		if (isinstance(start_date, (datetime,date)) and isinstance(end_date, (datetime,date))):
			start_timestamp = pd.Timestamp(datetime.combine(start_date, datetime.min.time()).timestamp(), unit='s')
			end_timestamp = pd.Timestamp(datetime.combine(end_date, datetime.min.time()).timestamp(), unit='s')

		data = self.original_data.copy()
		data = data[data['Date'] >= start_timestamp]
		data = data[data['Date'] <= end_timestamp]
		self.data = data
		
	def get_data(self) -> pd.DataFrame:
		return self.data.copy()