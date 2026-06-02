"""
NSE Data Fetcher
Fetches indices, F&O OI, circuit filters and market breadth from NSE public APIs.
No API key required. Returns JSON for Qt/C++ integration.

Usage:
    python nse_data.py indices
    python nse_data.py index <SYMBOL>        e.g. NIFTY 50
    python nse_data.py fo_oi <SYMBOL>        e.g. NIFTY
    python nse_data.py circuit_filters
    python nse_data.py market_breadth
    python nse_data.py most_active_fo
    python nse_data.py option_chain <SYMBOL> e.g. NIFTY
"""

import sys
import json
import requests

BASE_URL = "https://www.nseindia.com/api"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "X-Requested-With": "XMLHttpRequest",
}

# NSE requires a session cookie from the homepage before API calls work.
_session = requests.Session()
_session_initialized = False

NSE_INDICES = {
    "NIFTY 50":       "NIFTY%2050",
    "NIFTY BANK":     "NIFTY%20BANK",
    "NIFTY IT":       "NIFTY%20IT",
    "NIFTY MIDCAP 100": "NIFTY%20MIDCAP%20100",
    "NIFTY SMALLCAP 100": "NIFTY%20SMALLCAP%20100",
    "NIFTY FMCG":     "NIFTY%20FMCG",
    "NIFTY AUTO":     "NIFTY%20AUTO",
    "NIFTY PHARMA":   "NIFTY%20PHARMA",
    "NIFTY METAL":    "NIFTY%20METAL",
    "NIFTY REALTY":   "NIFTY%20REALTY",
    "INDIA VIX":      "INDIA%20VIX",
}


def _init_session():
    global _session_initialized
    if _session_initialized:
        return
    try:
        _session.get("https://www.nseindia.com/", headers=HEADERS, timeout=10)
        _session_initialized = True
    except Exception:
        pass


def _get(path, params=None):
    _init_session()
    url = f"{BASE_URL}{path}"
    resp = _session.get(url, headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_all_indices():
    """Fetch summary of all NSE indices."""
    try:
        data = _get("/allIndices")
        results = []
        for idx in data.get("data", []):
            results.append({
                "symbol": idx.get("indexSymbol", ""),
                "name": idx.get("index", ""),
                "last": idx.get("last", 0),
                "change": idx.get("change", 0),
                "change_pct": idx.get("percentChange", 0),
                "open": idx.get("open", 0),
                "high": idx.get("high", 0),
                "low": idx.get("low", 0),
                "prev_close": idx.get("previousClose", 0),
                "year_high": idx.get("yearHigh", 0),
                "year_low": idx.get("yearLow", 0),
                "advances": idx.get("advances", 0),
                "declines": idx.get("declines", 0),
                "unchanged": idx.get("unchanged", 0),
                "time_val": idx.get("timeVal", ""),
            })
        return results
    except Exception as e:
        return {"error": str(e)}


def get_index_data(index_name):
    """Fetch detailed data for a single index."""
    try:
        encoded = index_name.replace(" ", "%20")
        data = _get(f"/equity-stockIndices", params={"index": index_name.upper()})
        metadata = data.get("metadata", {})
        return {
            "symbol": metadata.get("indexSymbol", index_name),
            "name": metadata.get("index", index_name),
            "open": metadata.get("open", 0),
            "high": metadata.get("high", 0),
            "low": metadata.get("low", 0),
            "prev_close": metadata.get("previousClose", 0),
            "last": metadata.get("last", 0),
            "change": metadata.get("change", 0),
            "change_pct": metadata.get("percentChange", 0),
            "advances": metadata.get("advances", 0),
            "declines": metadata.get("declines", 0),
            "unchanged": metadata.get("unchanged", 0),
            "constituents": len(data.get("data", [])),
        }
    except Exception as e:
        return {"error": str(e), "symbol": index_name}


def get_fo_oi(symbol):
    """Fetch F&O open interest summary for a symbol (e.g. NIFTY, BANKNIFTY)."""
    try:
        data = _get("/equity-stockIndices", params={"index": symbol.upper()})
        return data
    except Exception:
        pass

    # Fallback: participant-wise OI
    try:
        data = _get("/participant-wise-open-interest")
        return data
    except Exception as e:
        return {"error": str(e), "symbol": symbol}


def get_option_chain(symbol):
    """Fetch full option chain for an index or stock."""
    try:
        data = _get("/option-chain-indices", params={"symbol": symbol.upper()})
        oc = data.get("records", {})
        expiry_dates = oc.get("expiryDates", [])
        underlying = oc.get("underlyingValue", 0)

        # Summarise by expiry: total CE OI, PE OI, PCR
        expiry_summary = {}
        for item in oc.get("data", []):
            exp = item.get("expiryDate", "")
            if exp not in expiry_summary:
                expiry_summary[exp] = {"ce_oi": 0, "pe_oi": 0, "ce_vol": 0, "pe_vol": 0}
            if "CE" in item:
                expiry_summary[exp]["ce_oi"] += item["CE"].get("openInterest", 0)
                expiry_summary[exp]["ce_vol"] += item["CE"].get("totalTradedVolume", 0)
            if "PE" in item:
                expiry_summary[exp]["pe_oi"] += item["PE"].get("openInterest", 0)
                expiry_summary[exp]["pe_vol"] += item["PE"].get("totalTradedVolume", 0)

        for k, v in expiry_summary.items():
            total_oi = v["ce_oi"] + v["pe_oi"]
            v["pcr"] = round(v["pe_oi"] / v["ce_oi"], 2) if v["ce_oi"] > 0 else 0
            v["total_oi"] = total_oi

        return {
            "symbol": symbol,
            "underlying": underlying,
            "expiry_dates": expiry_dates,
            "expiry_summary": expiry_summary,
        }
    except Exception as e:
        return {"error": str(e), "symbol": symbol}


def get_circuit_filters():
    """Fetch securities hitting upper/lower circuit limits."""
    try:
        data = _get("/live-analysis-variations", params={"index": "circulars"})
        return data
    except Exception:
        pass
    try:
        # Alternative: price band hitters
        data = _get("/live-analysis-data", params={"index": "UCC"})
        return data
    except Exception as e:
        return {"error": str(e)}


def get_market_breadth():
    """Fetch advances/declines across NSE segments."""
    try:
        indices = get_all_indices()
        if isinstance(indices, dict) and "error" in indices:
            return indices
        total_advances = sum(i.get("advances", 0) for i in indices if isinstance(i, dict))
        total_declines = sum(i.get("declines", 0) for i in indices if isinstance(i, dict))
        total_unchanged = sum(i.get("unchanged", 0) for i in indices if isinstance(i, dict))
        return {
            "advances": total_advances,
            "declines": total_declines,
            "unchanged": total_unchanged,
            "advance_decline_ratio": round(total_advances / total_declines, 2) if total_declines > 0 else 0,
        }
    except Exception as e:
        return {"error": str(e)}


def get_most_active_fo():
    """Fetch most active F&O contracts by OI and volume."""
    try:
        data = _get("/live-analysis-oi-spurts-underlyings")
        return data
    except Exception as e:
        return {"error": str(e)}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: nse_data.py <command> [args]"}))
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "indices":
        result = get_all_indices()
    elif cmd == "index" and len(sys.argv) >= 3:
        result = get_index_data(" ".join(sys.argv[2:]).upper())
    elif cmd == "fo_oi" and len(sys.argv) >= 3:
        result = get_fo_oi(sys.argv[2].upper())
    elif cmd == "option_chain" and len(sys.argv) >= 3:
        result = get_option_chain(sys.argv[2].upper())
    elif cmd == "circuit_filters":
        result = get_circuit_filters()
    elif cmd == "market_breadth":
        result = get_market_breadth()
    elif cmd == "most_active_fo":
        result = get_most_active_fo()
    else:
        result = {"error": f"Unknown command: {cmd}"}

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
