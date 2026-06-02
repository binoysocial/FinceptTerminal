"""
India Economic Data Fetcher
Fetches GDP, CPI, WPI, IIP, PMI, fiscal data and other macro indicators
for India from public sources (MOSPI, RBI, World Bank, IMF, S&P Global PMI).
No API key required for most sources. Returns JSON for Qt/C++ integration.

Usage:
    python india_economic_data.py gdp
    python india_economic_data.py cpi
    python india_economic_data.py wpi
    python india_economic_data.py iip
    python india_economic_data.py pmi
    python india_economic_data.py fiscal
    python india_economic_data.py trade_balance
    python india_economic_data.py all_indicators
"""

import sys
import json
import requests
from datetime import datetime

WB_BASE = "https://api.worldbank.org/v2"
IMF_BASE = "https://www.imf.org/external/datamapper/api/v1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FinceptTerminal/1.0)",
    "Accept": "application/json",
}

# World Bank indicator codes for India
WB_INDICATORS = {
    "gdp_growth":     "NY.GDP.MKTP.KD.ZG",   # GDP growth (annual %)
    "gdp_usd":        "NY.GDP.MKTP.CD",        # GDP current USD
    "gdp_per_capita": "NY.GDP.PCAP.CD",        # GDP per capita current USD
    "cpi_inflation":  "FP.CPI.TOTL.ZG",        # CPI inflation (annual %)
    "unemployment":   "SL.UEM.TOTL.ZS",        # Unemployment (% of labor force)
    "fdi_inflows":    "BX.KLT.DINV.CD.WD",     # FDI net inflows (BoP, USD)
    "exports":        "NE.EXP.GNFS.CD",         # Exports of goods/services (USD)
    "imports":        "NE.IMP.GNFS.CD",         # Imports of goods/services (USD)
    "current_account": "BN.CAB.XOKA.CD",       # Current account balance (USD)
    "gross_savings":  "NY.GNS.ICTR.ZS",        # Gross savings (% of GDP)
}

IMF_INDICATORS = {
    "gdp_ppp":        "PPPGDP",   # GDP PPP (Int'l $)
    "inflation":      "PCPIPCH",  # Inflation (avg consumer prices, %)
    "current_account_pct": "BCA_NGDPDZ", # Current account (% of GDP)
    "govt_debt":      "GGXWDG_NGDP",    # Govt debt (% of GDP)
    "fiscal_balance": "GGXCNL_NGDP",    # Fiscal balance (% of GDP)
}


def _wb_get(indicator, country="IN", mrv=10):
    """Fetch World Bank indicator for India, most recent N values."""
    url = f"{WB_BASE}/country/{country}/indicator/{indicator}"
    params = {"format": "json", "mrv": mrv, "per_page": mrv}
    resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    meta, data = resp.json()
    return [
        {"year": str(row.get("date", "")), "value": row.get("value")}
        for row in (data or [])
        if row.get("value") is not None
    ]


def _imf_get(indicator, country="IND"):
    """Fetch IMF DataMapper indicator for India."""
    url = f"{IMF_BASE}/{indicator}/{country}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    values = data.get("values", {}).get(indicator, {}).get(country, {})
    return [{"year": str(k), "value": v} for k, v in sorted(values.items()) if v is not None]


def get_gdp():
    """Fetch India GDP growth rate and nominal GDP."""
    try:
        growth = _wb_get(WB_INDICATORS["gdp_growth"])
        nominal = _wb_get(WB_INDICATORS["gdp_usd"])
        per_capita = _wb_get(WB_INDICATORS["gdp_per_capita"])
        return {
            "country": "India",
            "gdp_growth_pct": growth,
            "gdp_nominal_usd": nominal,
            "gdp_per_capita_usd": per_capita,
            "source": "World Bank",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "indicator": "GDP"}


def get_cpi():
    """Fetch India CPI inflation from World Bank and IMF."""
    try:
        wb_cpi = _wb_get(WB_INDICATORS["cpi_inflation"])
        imf_cpi = _imf_get(IMF_INDICATORS["inflation"])
        return {
            "country": "India",
            "cpi_inflation_pct": wb_cpi,
            "imf_avg_consumer_prices": imf_cpi,
            "note": "For monthly CPI, see MOSPI: https://mospi.gov.in/consumer-price-index",
            "source": "World Bank / IMF",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "indicator": "CPI"}


def get_wpi():
    """
    Fetch Wholesale Price Index (WPI) data.
    MOSPI publishes monthly WPI; primary source is DBIE RBI.
    """
    try:
        # Try World Bank proxy (producer prices)
        url = f"{WB_BASE}/country/IN/indicator/FP.WPI.TOTL.ZG"
        params = {"format": "json", "mrv": 10}
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if resp.status_code == 200:
            meta, data = resp.json()
            if data:
                return {
                    "country": "India",
                    "wpi_pct": [
                        {"year": str(r.get("date")), "value": r.get("value")}
                        for r in data if r.get("value") is not None
                    ],
                    "source": "World Bank",
                }
    except Exception:
        pass

    return {
        "note": "Monthly WPI published by MOSPI — https://mospi.gov.in/web/mospi/wholesale-price-index",
        "dbie_series": "RBI DBIE series for WPI: available at https://dbie.rbi.org.in",
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }


def get_iip():
    """
    Fetch Index of Industrial Production (IIP) data.
    Published monthly by MOSPI.
    """
    try:
        # World Bank manufacturing value added as proxy
        url = f"{WB_BASE}/country/IN/indicator/NV.IND.MANF.KD.ZG"
        params = {"format": "json", "mrv": 10}
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if resp.status_code == 200:
            _, data = resp.json()
            return {
                "country": "India",
                "manufacturing_growth_pct": [
                    {"year": str(r.get("date")), "value": r.get("value")}
                    for r in (data or []) if r.get("value") is not None
                ],
                "source": "World Bank (annual proxy for IIP)",
                "official_source": "https://mospi.gov.in/index-industrial-production",
                "fetched_at": datetime.utcnow().isoformat() + "Z",
            }
    except Exception as e:
        return {"error": str(e), "indicator": "IIP"}


def get_pmi():
    """
    Fetch PMI data for India.
    S&P Global (formerly IHS Markit) publishes India Manufacturing and Services PMI.
    Free historical summary available via Trading Economics.
    """
    try:
        # Trading Economics has a free JSON endpoint for India PMI
        url = "https://tradingeconomics.com/india/manufacturing-pmi"
        # TE blocks scraping; return metadata with source links
        return {
            "country": "India",
            "note": "PMI published monthly by S&P Global / HSBC",
            "manufacturing_pmi_source": "https://tradingeconomics.com/india/manufacturing-pmi",
            "services_pmi_source": "https://tradingeconomics.com/india/services-pmi",
            "composite_pmi_source": "https://tradingeconomics.com/india/composite-pmi",
            "api_note": "Use trading_economics_data.py with a TE API key for live PMI values",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "indicator": "PMI"}


def get_fiscal():
    """Fetch India fiscal deficit, government debt, and revenue data."""
    try:
        debt = _imf_get(IMF_INDICATORS["govt_debt"])
        balance = _imf_get(IMF_INDICATORS["fiscal_balance"])
        return {
            "country": "India",
            "govt_debt_pct_gdp": debt,
            "fiscal_balance_pct_gdp": balance,
            "note": "Monthly fiscal data: https://www.cga.nic.in/",
            "source": "IMF World Economic Outlook",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "indicator": "Fiscal"}


def get_trade_balance():
    """Fetch India trade balance, exports, and imports."""
    try:
        exports = _wb_get(WB_INDICATORS["exports"])
        imports = _wb_get(WB_INDICATORS["imports"])
        current_acct = _wb_get(WB_INDICATORS["current_account"])
        return {
            "country": "India",
            "exports_usd": exports,
            "imports_usd": imports,
            "current_account_usd": current_acct,
            "source": "World Bank",
            "monthly_source": "https://commerce.gov.in/trade-statistics/",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e), "indicator": "Trade"}


def get_all_indicators():
    """Fetch a summary of key India macro indicators."""
    try:
        results = {}
        for name, code in WB_INDICATORS.items():
            try:
                data = _wb_get(code, mrv=3)
                results[name] = data[0] if data else None
            except Exception:
                results[name] = None

        return {
            "country": "India",
            "latest_indicators": results,
            "source": "World Bank",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: india_economic_data.py <command>"}))
        sys.exit(1)

    cmd = sys.argv[1].lower()
    dispatch = {
        "gdp":            get_gdp,
        "cpi":            get_cpi,
        "wpi":            get_wpi,
        "iip":            get_iip,
        "pmi":            get_pmi,
        "fiscal":         get_fiscal,
        "trade_balance":  get_trade_balance,
        "all_indicators": get_all_indicators,
    }

    fn = dispatch.get(cmd)
    if fn:
        result = fn()
    else:
        result = {"error": f"Unknown command: {cmd}", "available": list(dispatch.keys())}

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
