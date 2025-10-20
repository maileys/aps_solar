#!/usr/bin/env python3
import argparse
import json
import re
import sys
from typing import List, Tuple, Dict
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# =======================================
# Constants
# =======================================
PROTOCOL = "http"
DEFAULT_PATH = "/cgi-bin/parameters"
TIMEOUT = 5  # seconds
DEFAULT_CONFIG_FILE = "config.json"

WATT_RE = re.compile(r"(\d+)\s*W\b", re.IGNORECASE)


def load_config(path: str) -> Dict[str, str]:
    """Load host/path settings from a JSON config file."""
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(cfg_path, "r") as f:
        config = json.load(f)

    if "host" not in config:
        raise KeyError("Config file must contain a 'host' field.")
    if "path" not in config:
        config["path"] = DEFAULT_PATH  # apply fallback
    return config


def build_url(host: str, path: str) -> str:
    return f"{PROTOCOL}://{host}{path}"


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
    if len(rows) < 2:
        raise ValueError("No data rows found in the inverter table")

    results: List[Tuple[str, int]] = []
    for tr in rows[1:]:
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        inverter_id = tds[0].get_text(strip=True)
        power_cell = tds[1].get_text(" ", strip=True)
        m = WATT_RE.search(power_cell.replace("\xa0", " "))
        if m:
            watts = int(m.group(1))
            results.append((inverter_id, watts))
    return results


def to_json(readings: List[Tuple[str, int]], url: str) -> str:
    data = {
        "source": url,
        "total_watts": sum(w for _, w in readings),
        "panels": {inv: w for inv, w in readings},
    }
    return json.dumps(data, separators=(",", ":"))


def main():
    parser = argparse.ArgumentParser(
        description="Scrape APS inverter data using a JSON config file."
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG_FILE,
        help=f"Path to config file containing 'host' (and optional 'path'). Default: {DEFAULT_CONFIG_FILE}",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON instead of human-readable text.",
    )
    args = parser.parse_args()

    # Load configuration
    try:
        cfg = load_config(args.config)
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)

    host = cfg["host"]
    path = cfg["path"]
    url = build_url(host, path)

    # Fetch and parse
    try:
        html = fetch_html(url)
        readings = parse_watts(html)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    if not readings:
        print("No inverter watt readings found.", file=sys.stderr)
        sys.exit(3)

    # Output
    if args.json:
        print(to_json(readings, url))
        return

    total = sum(w for _, w in readings)
    print(f"Data source: {url}\n")
    print("Panel readings:")
    for inv, w in readings:
        print(f"  {inv}: {w} W")
    print(f"\nTotal power: {total} W")


if __name__ == "__main__":
    main()
