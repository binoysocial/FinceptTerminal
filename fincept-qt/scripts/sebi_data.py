"""
SEBI / NSE Data Fetcher
Fetches FII/DII flows, bulk deals, block deals, IPO filings, and
market participation data from SEBI and NSE public APIs.
No API key required. Returns JSON for Qt/C++ integration.

Usage:
    python sebi_data.py fii_dii
    python sebi_data.py fii_dii_monthly
    python sebi_data.py bulk_deals
    python sebi_data.py block_deals
    python sebi_data.py ipo_list
    python sebi_data.py short_selling
"""

import sys
import json
import requests
from datetime import datetime, date, timedelta

NSE_BASE = "https://www.nseindia.com/api"
SEBI_BASE = "https://www.sebi.gov.in"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

_session = requests.Session()
_session_ready = False


def _init_session():
    global _session_ready
    if _session_ready:
        return
    try:
        _session.get("https://www.nseindia.com/", headers=HEADERS, timeout=10)
        _session_ready = True
    except Exception:
        pass


def _nse_get(path, params=None):
    _init_session()
    resp = _session.get(f"{NSE_BASE}{path}", headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_fii_dii():
    """
    Fetch today's FII/DII activity (cash market net buy/sell).
    NSE publishes this as a daily settlement figure.
    """
    try:
        data = _nse_get("/fiidiidata")
        results = []
        for row in data if isinstance(data, list) else data.get("data", []):
            results.append({
                "date": row.get("date", ""),
                "fii_net_purchase": row.get("netPurchase_FII_FPI", 0),
                "dii_net_purchase": row.get("netPurchase_DII", 0),
                "fii_gross_buy": row.get("grossPurchase_FII_FPI", 0),
                "fii_gross_sell": row.get("grossSale_FII_FPI", 0),
                "dii_gross_buy": row.get("grossPurchase_DII", 0),
                "dii_gross_sell": row.get("grossSale_DII", 0),
            })
        return results
    except Exception as e:
        return {"error": str(e)}


def get_fii_dii_monthly():
    """Fetch monthly FII/DII aggregated data."""
    try:
        today = date.today()
        from_date = (today - timedelta(days=180)).strftime("%d-%m-%Y")
        to_date = today.strftime("%d-%m-%Y")
        data = _nse_get("/fiidiidata", params={"type": "fii", "from": from_date, "to": to_date})
        return data
    except Exception as e:
        return {"error": str(e)}


def get_bulk_deals():
    """Fetch bulk deal disclosures from NSE (>= 0.5% of listed shares)."""
    try:
        data = _nse_get("/bulk-deals")
        results = []
        for row in data if isinstance(data, list) else data.get("data", []):
            results.append({
                "date": row.get("bdDt", ""),
                "symbol": row.get("symbol", ""),
                "company": row.get("mktCapInCr", ""),
                "client_name": row.get("clientName", ""),
                "buy_sell": row.get("buySell", ""),
                "quantity": row.get("bdQty", 0),
                "trade_price": row.get("bdTrdPrc", 0),
                "remarks": row.get("remarks", ""),
            })
        return results
    except Exception as e:
        return {"error": str(e)}


def get_block_deals():
    """Fetch block deal disclosures from NSE (large off-market trades)."""
    try:
        data = _nse_get("/block-deals")
        results = []
        for row in data if isinstance(data, list) else data.get("data", []):
            results.append({
                "date": row.get("bdDt", ""),
                "symbol": row.get("symbol", ""),
                "client_name": row.get("clientName", ""),
                "buy_sell": row.get("buySell", ""),
                "quantity": row.get("bdQty", 0),
                "trade_price": row.get("bdTrdPrc", 0),
            })
        return results
    except Exception as e:
        return {"error": str(e)}


def get_ipo_list():
    """Fetch upcoming and recent IPO listings from NSE."""
    try:
        data = _nse_get("/all-upcoming-issues", params={"issueType": "ipo"})
        upcoming = []
        for row in data if isinstance(data, list) else data.get("data", []):
            upcoming.append({
                "company": row.get("companyName", ""),
                "symbol": row.get("symbol", ""),
                "issue_open": row.get("issueOpenDate", ""),
                "issue_close": row.get("issueCloseDate", ""),
                "issue_size_cr": row.get("issueSize", 0),
                "price_band": row.get("priceBand", ""),
                "lot_size": row.get("lotSize", 0),
                "status": row.get("issueStatus", ""),
            })
        return upcoming
    except Exception as e:
        return {"error": str(e)}


def get_short_selling():
    """Fetch short-selling data (Securities Lending and Borrowing)."""
    try:
        data = _nse_get("/slb-securities")
        return data
    except Exception as e:
        return {"error": str(e)}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: sebi_data.py <command>"}))
        sys.exit(1)

    cmd = sys.argv[1].lower()
    dispatch = {
        "fii_dii":         get_fii_dii,
        "fii_dii_monthly": get_fii_dii_monthly,
        "bulk_deals":      get_bulk_deals,
        "block_deals":     get_block_deals,
        "ipo_list":        get_ipo_list,
        "short_selling":   get_short_selling,
    }

    fn = dispatch.get(cmd)
    if fn:
        result = fn()
    else:
        result = {"error": f"Unknown command: {cmd}", "available": list(dispatch.keys())}

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
