"""Download a fresh S&P 500 snapshot and update the local data files."""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

PATH_TO_CSV = Path("data/spx.csv")
PATH_TO_DAILY_CSV = Path("data/spx_day.csv")
DAILY_START = pd.Timestamp(1885, 2, 2)
SYMBOL = "%5EGSPC"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def download_yahoo(symbol: str = SYMBOL) -> pd.DataFrame:
    """Download the full daily price history from the Yahoo Finance chart API."""
    period2 = int(datetime.now(timezone.utc).timestamp()) + 86_400
    params = {
        "period1": 0,
        "period2": period2,
        "interval": "1d",
        "events": "div,splits",
    }
    last_error = None
    for host in ("query2.finance.yahoo.com", "query1.finance.yahoo.com"):
        url = f"https://{host}/v8/finance/chart/{symbol}"
        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=60)
            response.raise_for_status()
            result = response.json()["chart"]["result"][0]
            quotes = result["indicators"]["quote"][0]
            data = pd.DataFrame(
                {
                    "Date": pd.to_datetime(result["timestamp"], unit="s", utc=True)
                    .tz_convert("America/New_York")
                    .normalize()
                    .tz_localize(None),
                    "Open": quotes["open"],
                    "High": quotes["high"],
                    "Low": quotes["low"],
                    "Close": quotes["close"],
                    "Volume": quotes["volume"],
                }
            )
            data = data.dropna(subset=["Close"]).drop_duplicates("Date")
            return data.sort_values("Date").reset_index(drop=True)
        except (KeyError, IndexError, requests.RequestException, ValueError) as error:
            last_error = error
    raise RuntimeError(f"Could not download {symbol} from Yahoo Finance") from last_error


def load_local_history() -> pd.DataFrame:
    """Load the previously stored history, if there is any."""
    if not PATH_TO_CSV.exists():
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    return pd.read_csv(PATH_TO_CSV, sep=";")


def update_snapshot() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Merge the fresh download with the pre-1970 local history (Yahoo starts in 1970)."""
    fresh = download_yahoo()
    local = load_local_history()
    local["Date"] = pd.to_datetime(local["Date"])
    history = local[local["Date"] < fresh["Date"].min()]
    snapshot = pd.concat([history, fresh], ignore_index=True).sort_values("Date")

    PATH_TO_CSV.parent.mkdir(parents=True, exist_ok=True)
    snapshot.to_csv(PATH_TO_CSV, sep=";", index=False, date_format="%Y-%m-%d")

    daily = snapshot[snapshot["Date"] >= DAILY_START]
    daily.to_csv(PATH_TO_DAILY_CSV, sep=";", index=False, date_format="%Y-%m-%d")
    return snapshot, daily


if __name__ == "__main__":
    snapshot, daily = update_snapshot()
    print(
        f"Saved {len(snapshot):,} rows to {PATH_TO_CSV} "
        f"({snapshot['Date'].min():%Y-%m-%d} to {snapshot['Date'].max():%Y-%m-%d})"
    )
    print(
        f"Saved {len(daily):,} rows to {PATH_TO_DAILY_CSV} "
        f"({daily['Date'].min():%Y-%m-%d} to {daily['Date'].max():%Y-%m-%d})"
    )
