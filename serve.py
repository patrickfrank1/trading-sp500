import time
import requests
from datetime import datetime
import http.server
import socketserver
from threading import Thread

import pandas as pd

from util_kelly import simulate_kelly_strategy, StockMarketData

PATH_TO_CSV = 'data/spx_day.csv'
PATH_TO_CALCULATION = 'kelly_fractions.txt'
DATE_MIN_BLOG = pd.Timestamp(2021, 3, 1).to_pydatetime()
DATE_MAX_BLOG = (pd.Timestamp.today() + pd.Timedelta(days=1)).to_pydatetime()
REBALANCING_INTERVAL = 1
KELLY_FRACTION = 1.0
WINDOW = 252
MIN_KELLY = -5.0
MAX_KELLY = 5.0
SELECT_COLUMNS = ['Date', 'Close', 'kelly_factor', 'strategy_cum_returns', 'cum_returns']
SELECT_ROWS = [-1*i for i in range(1, 254)]
REFRESH_INTERVAL = 86400
PORT = 9009
DIRECTORY = "."


def download_data() -> None:
    url = 'https://stooq.com/q/d/l/?s=^spx&i=d&c=1'
    headers = {
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.87 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Sec-GPC': '1',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        'Accept-Language': 'en-US,en;q=0.9,de-DE;q=0.8,de;q=0.7'
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        with open(PATH_TO_CSV, 'wb') as f:
            f.write(response.content)
        print('File downloaded successfully as spx_day.csv')
    else:
        print('Failed to download file:', response.status_code, response.reason)
    return


def calculate_kelly_fractions() -> pd.DataFrame:
    simulation_data = StockMarketData(PATH_TO_CSV, delimiter=";", parse_dates=['Date'], infer_datetime_format=True)
    simulation_data.restrict_date(DATE_MIN_BLOG, DATE_MAX_BLOG)
    k_cap = simulate_kelly_strategy(
        simulation_data.get_data(),
        rebalancing_interval=REBALANCING_INTERVAL,
        kelly_fraction=KELLY_FRACTION,
        window=WINDOW,
        min_kelly=MIN_KELLY,
        max_kelly=MAX_KELLY
    )
    select_rows = [len(k_cap) - 1] + SELECT_ROWS
    selected_data = k_cap.iloc[select_rows, k_cap.columns.get_indexer(SELECT_COLUMNS)]
    return selected_data


def refresh_data() -> None:
    while True:
        print(f"Updated kelly fractions at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        download_data()
        kelly_factors = calculate_kelly_fractions()
        kelly_factors.to_csv(PATH_TO_CALCULATION, sep='\t', index=False, float_format='%.2f')
        time.sleep(REFRESH_INTERVAL)
    return


class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = PATH_TO_CALCULATION
        return http.server.SimpleHTTPRequestHandler.do_GET(self)


if __name__ == "__main__":
    updater_thread = Thread(target=refresh_data)
    updater_thread.start()

    handler = SimpleHTTPRequestHandler
    handler.extensions_map.update({
        ".txt": "text/plain",
    })

    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print("Serving at port", PORT)
        httpd.serve_forever()
