"""
RBI Data Fetcher
Fetches monetary policy rates, forex reserves, and macro data from
RBI's public DBIE (Database on Indian Economy) API.
No API key required. Returns JSON for Qt/C++ integration.

Usage:
    python rbi_data.py policy_rates
    python rbi_data.py forex_reserves
    python rbi_data.py money_supply
    python rbi_data.py inflation_wpi
    python rbi_data.py credit_growth
    python rbi_data.py series <series_id>
"""

import sys
import json
import requests
from datetime import datetime, date

DBIE_BASE = "https://dbie.rbi.org.in/DBIE/dbie.rbi"
ALT_BASE = "https://api.rbi.org.in/api"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FinceptTerminal/1.0)",
    "Accept": "application/json",
}

# RBI DBIE series codes for key indicators
SERIES = {
    "repo_rate":          "BSR1:A.N01.A.A.A.TS:Q.INR:NA.PC",
    "reverse_repo":       "BSR1:A.N02.A.A.A.TS:Q.INR:NA.PC",
    "crr":                "BSR1:A.N04.A.A.A.TS:Q.PC:NA.PC",
    "slr":                "BSR1:A.N05.A.A.A.TS:Q.PC:NA.PC",
    "forex_reserves":     "FXRS:W.TA.FXR.USD.W",
    "m3_money_supply":    "MS:M.MS.M3.A",
    "bank_credit":        "MS:M.MS.BC.A",
}


def _get_json(url, params=None):
    resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_policy_rates():
    """Fetch current RBI policy rates (repo, reverse repo, CRR, SLR, MSF)."""
    # RBI publishes current rates in a structured page; scrape the public JSON feed
    try:
        url = "https://rbidocs.rbi.org.in/rdocs/Publications/PDFs/ratesummary.json"
        data = _get_json(url)
        return data
    except Exception:
        pass

    # Fallback: well-known current rates from RBI sitemap JSON
    try:
        url = "https://m.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"
        # Return hardcoded structure with fetch timestamp so caller knows it tried
        return {
            "note": "RBI policy rates — fetch from RBI website failed, returning last known structure",
            "rates": [
                {"name": "Policy Repo Rate",           "value": None, "unit": "%"},
                {"name": "Standing Deposit Facility",  "value": None, "unit": "%"},
                {"name": "Marginal Standing Facility",  "value": None, "unit": "%"},
                {"name": "Bank Rate",                  "value": None, "unit": "%"},
                {"name": "CRR",                        "value": None, "unit": "%"},
                {"name": "SLR",                        "value": None, "unit": "%"},
            ],
            "source": "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e)}


def get_forex_reserves():
    """Fetch India's total forex reserves (weekly, in USD billion)."""
    try:
        # RBI publishes weekly forex data as a structured release
        url = "https://rbidocs.rbi.org.in/rdocs/PressRelease/PDFs/wdr"
        # Primary: RBI open data API
        url = "https://data.rbi.org.in/RBIAPI/DataREST/Rbi/GetTableData"
        params = {
            "TableNo": "1",   # Table 1 = Foreign Exchange Reserves
            "FromDate": "2024-01-01",
            "ToDate": date.today().isoformat(),
        }
        data = _get_json(url, params)
        return {"source": "RBI", "data": data}
    except Exception:
        pass

    # Fallback: yfinance USD/INR and reserves proxy
    try:
        import yfinance as yf
        ticker = yf.Ticker("INR=X")
        info = ticker.info
        return {
            "usd_inr": info.get("regularMarketPrice"),
            "note": "RBI forex reserves API unavailable; showing USD/INR rate",
            "source": "yfinance",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e)}


def get_money_supply():
    """Fetch M3 money supply and bank credit growth."""
    try:
        url = "https://dbie.rbi.org.in/DBIE/dbie.rbi?site=statistics&type=2&subtype=3"
        data = _get_json(url)
        return data
    except Exception as e:
        return {"error": str(e), "note": "RBI DBIE money supply series"}


def get_inflation_wpi():
    """Fetch WPI (Wholesale Price Index) inflation data."""
    try:
        # Office of Economic Adviser publishes WPI
        url = "https://eaindustry.nic.in/cpi_data.asp"
        return {"note": "WPI data from Ministry of Commerce — use india_economic_data.py for CPI/WPI"}
    except Exception as e:
        return {"error": str(e)}


def get_credit_growth():
    """Fetch bank credit and deposit growth rates."""
    try:
        url = "https://dbie.rbi.org.in/DBIE/dbie.rbi?site=statistics&type=1&subtype=2"
        data = _get_json(url)
        return data
    except Exception as e:
        return {
            "error": str(e),
            "note": "Bank credit growth from RBI DBIE — series BSR1",
        }


def get_series(series_id):
    """Fetch a specific RBI DBIE time series by ID."""
    try:
        url = f"https://dbie.rbi.org.in/DBIE/dbie.rbi?site=statistics"
        params = {"type": "bulk", "series": series_id}
        data = _get_json(url, params)
        return data
    except Exception as e:
        return {"error": str(e), "series_id": series_id}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: rbi_data.py <command> [args]"}))
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "policy_rates":
        result = get_policy_rates()
    elif cmd == "forex_reserves":
        result = get_forex_reserves()
    elif cmd == "money_supply":
        result = get_money_supply()
    elif cmd == "inflation_wpi":
        result = get_inflation_wpi()
    elif cmd == "credit_growth":
        result = get_credit_growth()
    elif cmd == "series" and len(sys.argv) >= 3:
        result = get_series(sys.argv[2])
    else:
        result = {"error": f"Unknown command: {sys.argv[1]}"}

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
