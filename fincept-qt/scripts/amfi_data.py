"""
AMFI / Mutual Fund Data Fetcher
Fetches NAVs, fund details, AUM, and SIP statistics from AMFI India.
No API key required. Returns JSON for Qt/C++ integration.

Sources:
  - mfapi.in   — clean REST API wrapping AMFI data
  - amfiindia.com — official NAV flat files

Usage:
    python amfi_data.py nav <scheme_code>        e.g. 120503 (Axis Bluechip)
    python amfi_data.py search <query>           e.g. "hdfc"
    python amfi_data.py categories
    python amfi_data.py top_funds <category>     e.g. "Equity"
    python amfi_data.py aum_summary
    python amfi_data.py sip_stats
    python amfi_data.py nav_history <scheme_code> [days]
"""

import sys
import json
import requests
from datetime import datetime, date, timedelta

MFAPI_BASE = "https://api.mfapi.in/mf"
AMFI_NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
AMFI_AUM_URL = "https://www.amfiindia.com/modules/AumReport"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FinceptTerminal/1.0)",
    "Accept": "application/json, text/plain, */*",
}


def _get(url, params=None):
    resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def get_nav(scheme_code):
    """Fetch latest NAV and fund metadata for a scheme."""
    try:
        data = _get(f"{MFAPI_BASE}/{scheme_code}")
        meta = data.get("meta", {})
        nav_data = data.get("data", [])
        latest = nav_data[0] if nav_data else {}
        return {
            "scheme_code": scheme_code,
            "scheme_name": meta.get("scheme_name", ""),
            "fund_house": meta.get("fund_house", ""),
            "scheme_type": meta.get("scheme_type", ""),
            "scheme_category": meta.get("scheme_category", ""),
            "scheme_sub_category": meta.get("scheme_sub_category", ""),
            "nav": float(latest.get("nav", 0)),
            "nav_date": latest.get("date", ""),
            "prev_nav": float(nav_data[1].get("nav", 0)) if len(nav_data) > 1 else 0,
        }
    except Exception as e:
        return {"error": str(e), "scheme_code": scheme_code}


def get_nav_history(scheme_code, days=30):
    """Fetch historical NAV data for a scheme."""
    try:
        data = _get(f"{MFAPI_BASE}/{scheme_code}")
        nav_data = data.get("data", [])
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        history = [
            {"date": row["date"], "nav": float(row["nav"])}
            for row in nav_data
            if row.get("date", "") >= cutoff
        ]
        return {
            "scheme_code": scheme_code,
            "scheme_name": data.get("meta", {}).get("scheme_name", ""),
            "history": history,
        }
    except Exception as e:
        return {"error": str(e), "scheme_code": scheme_code}


def search_funds(query):
    """Search for mutual fund schemes by name or AMC."""
    try:
        data = _get(f"{MFAPI_BASE}/search", params={"q": query})
        return [
            {
                "scheme_code": str(f.get("schemeCode", "")),
                "scheme_name": f.get("schemeName", ""),
            }
            for f in (data if isinstance(data, list) else [])
        ]
    except Exception as e:
        return {"error": str(e), "query": query}


def get_categories():
    """List all AMFI scheme categories."""
    # Parse the official AMFI NAV flat file to extract categories
    try:
        resp = requests.get(AMFI_NAV_URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        categories = set()
        for line in resp.text.splitlines():
            parts = line.split(";")
            if len(parts) >= 6:
                # AMFI NAV format: SchemeCode;ISINDivPayoutGrowth;ISIN;SchemeName;NAV;Date
                # Category lines have no numeric scheme code
                if not parts[0].strip().isdigit() and parts[0].strip():
                    categories.add(parts[0].strip())
        return sorted(categories)
    except Exception as e:
        return {"error": str(e)}


def get_top_funds(category="Equity"):
    """Fetch list of funds in a category (from mfapi search)."""
    try:
        data = _get(f"{MFAPI_BASE}/search", params={"q": category})
        return [
            {
                "scheme_code": str(f.get("schemeCode", "")),
                "scheme_name": f.get("schemeName", ""),
            }
            for f in (data if isinstance(data, list) else [])
        ][:50]
    except Exception as e:
        return {"error": str(e), "category": category}


def get_aum_summary():
    """
    Fetch industry-level AUM summary from AMFI.
    AMFI publishes monthly AUM by category.
    """
    try:
        resp = requests.get(
            "https://www.amfiindia.com/modules/AumReport",
            headers={**HEADERS, "Referer": "https://www.amfiindia.com/"},
            timeout=20,
        )
        # AMFI AUM page is HTML — return structured metadata
        return {
            "source": "https://www.amfiindia.com/modules/AumReport",
            "note": "AMFI publishes AUM as HTML/PDF; parse the page for detailed breakdown",
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "status": resp.status_code,
        }
    except Exception as e:
        return {"error": str(e)}


def get_sip_stats():
    """Fetch SIP (Systematic Investment Plan) industry statistics."""
    # AMFI publishes monthly SIP data via press releases
    return {
        "source": "https://www.amfiindia.com/indian-mutual",
        "note": "AMFI SIP data published monthly as press release. "
                "Key metrics: SIP accounts, monthly SIP amount (₹Cr), SIP AUM.",
        "data_url": "https://www.amfiindia.com/modules/SIPReport",
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: amfi_data.py <command> [args]"}))
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "nav" and len(sys.argv) >= 3:
        result = get_nav(sys.argv[2])
    elif cmd == "nav_history" and len(sys.argv) >= 3:
        days = int(sys.argv[3]) if len(sys.argv) >= 4 else 30
        result = get_nav_history(sys.argv[2], days)
    elif cmd == "search" and len(sys.argv) >= 3:
        result = search_funds(" ".join(sys.argv[2:]))
    elif cmd == "categories":
        result = get_categories()
    elif cmd == "top_funds":
        category = " ".join(sys.argv[2:]) if len(sys.argv) >= 3 else "Equity"
        result = get_top_funds(category)
    elif cmd == "aum_summary":
        result = get_aum_summary()
    elif cmd == "sip_stats":
        result = get_sip_stats()
    else:
        result = {"error": f"Unknown command: {sys.argv[1]}"}

    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
