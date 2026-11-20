The analyses in this repository are based on historical S&P 500 data. The original long history was retrieved from https://stooq.com/q/d/?s=^spx&c=1 and contains daily prices from 1885 onwards.

Refresh the local snapshot with the latest daily prices from Yahoo Finance (`^GSPC`) at any time:

```bash
python update_data.py
```

This keeps the pre-1970 history and replaces all later rows with a fresh download. The script writes `data/spx.csv` (full history) and `data/spx_day.csv` (daily data since 1885), both separated by semicolons.
