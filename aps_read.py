#!/usr/bin/env python3
import re
import sys
from typing import List, Tuple

import requests
from bs4 import BeautifulSoup

# =======================================
# Configuration Constants
# =======================================
PROTOCOL = "http"
PATH = "/cgi-bin/parameters"
TIMEOUT = 5  # seconds

# Regex to extract integer watt values like " 2 W" (including &nbsp;)
WATT_RE = re.compile(r"(\d+)\s*W\b", re.IGNORECASE)


def build_url(host: str) -> str:
    """Build the full URL from protocol, host, and path."""
    return f"{PROTOCOL}://{host}{PATH}"


def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


def parse_watts(html: str) -> List[Tuple[str, int]]:
    """Returns a list of (inverter_id, watts)."""
    soup = BeautifulSoup(html, "html.parser")

    # Find the main table with header "Current Power"
    table = None
    for t in soup.find_all("table"):
        header_cells = [c.get_text(strip=True) for c in t.find_all("td")]
        if any("Current Power" in txt for txt in header_cells):
            table = t
            break

    if table is None:
        raise ValueError("Could not find the inverter table with 'Current Power' header")

    rows = table.find_all("tr")
    if not rows or len(rows) < 2:
        raise ValueError("No data rows found in the inverter table")

    results: List[Tuple[str, int]] = []
    for tr in rows[1:]:
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        inverter_id = tds[0].get_text(strip=True)
        power_cell = tds[1].get_text(" ", strip=True)
        m = WATT_RE.search(power_cell.replace("\xa0", " "))
        if not m:
            continue
        watts = int(m.group(1))
        results.append((inverter_id, watts))
    return results


def main():
    # Require host argument
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <host>", file=sys.stderr)
        print("Example: aps_scrape.py 192.168.1.102", file=sys.stderr)
        sys.exit(1)

    host = sys.argv[1]
    url = build_url(host)

    try:
        html = fetch_html(url)
        readings = parse_watts(html)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    if not readings:
        print("No inverter watt readings found.")
        sys.exit(3)

    total = sum(w for _, w in readings)
    print(f"Data source: {url}\n")
    print("Panel readings:")
    for inv, w in readings:
        print(f"  {inv}: {w} W")
    print(f"\nTotal power: {total} W")


if __name__ == "__main__":
    main()
