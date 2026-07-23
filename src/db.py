"""Read-only access to the Supabase `core.*` market-data schema.

The market-state layer's index and India-VIX history come from here (official
NSE Nifty via niftyindices.com, FRED S&P 500) rather than a raw web scrape —
better provenance and longer history than yfinance. See ADR-008.

The DB is only touched on ``--refresh``; normal runs read the committed
``data/raw`` cache, so a clean clone needs no credentials.
"""
from __future__ import annotations

import os
from typing import Optional

import pandas as pd
from dotenv import load_dotenv

from .config import ROOT

load_dotenv(ROOT / ".env")


class DBUnavailable(RuntimeError):
    """Raised when a refresh is requested but no DATABASE_URL is configured."""


def _dsn() -> str:
    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn:
        raise DBUnavailable(
            "DATABASE_URL not set. Copy .env.example to .env and fill it in, "
            "or run without --refresh to use the cached data/raw pulls."
        )
    return dsn


def _fetch_series(sql: str, name: str) -> pd.Series:
    """Run a (date, value) query and return a float Series indexed by date."""
    import psycopg2

    conn = psycopg2.connect(_dsn())
    try:
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()
    if not rows:
        return pd.Series(dtype="float64", name=name)
    dates = pd.to_datetime([r[0] for r in rows])
    vals = [float(r[1]) for r in rows]
    return pd.Series(vals, index=dates, name=name)


def fetch_close(table: str, date_col: str = "date", close_col: str = "close") -> pd.Series:
    """Daily close series from a core.* OHLC table, indexed by date."""
    return _fetch_series(
        f"SELECT {date_col}, {close_col} FROM core.{table} "
        f"WHERE {close_col} IS NOT NULL ORDER BY {date_col}",
        table,
    )


def fetch_macro_column(column: str) -> pd.Series:
    """A single daily column from core.macro_daily (e.g. india_vix)."""
    return _fetch_series(
        f"SELECT date, {column} FROM core.macro_daily "
        f"WHERE {column} IS NOT NULL ORDER BY date",
        column,
    )


def fetch_nse_close(symbol: str, start: str) -> pd.Series:
    """Daily close for one NSE symbol from core.nse_daily_prices (2022+).

    Official NSE data (via am-ai-engine). Used for post-listing series of
    India names whose yfinance feed is unreliable (e.g. LIC). Returns an empty
    series if the symbol/date range is absent.
    """
    import psycopg2

    conn = psycopg2.connect(_dsn())
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT date, close FROM core.nse_daily_prices "
            "WHERE symbol = %s AND date >= %s AND close IS NOT NULL ORDER BY date",
            (symbol, start),
        )
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()
    if not rows:
        return pd.Series(dtype="float64", name=symbol)
    return pd.Series(
        [float(r[1]) for r in rows],
        index=pd.to_datetime([r[0] for r in rows]),
        name=symbol,
    )
