#!/usr/bin/env python3
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests
from html.parser import HTMLParser

# ======================================
# Constants
# ======================================
PROTOCOL = "http"
DEFAULT_PATH = "/cgi-bin/parameters"
TIMEOUT = 5.0
DEFAULT_CONFIG_FILE = "config.json"

# Regex helpers
WATT_RE = re.compile(r"(\d+)\s*W\b", re.IGNORECASE)
VOLT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*V\b", re.IGNORECASE)
TEMP_RE = re.compile(r"(\d+)\s*°?\s*C", re.IGNORECASE)


# ======================================
# Config handling
# ======================================
def load_config(path: str) -> Dict:
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(cfg_path, "r") as f:
        cfg = json.load(f)
    if "host" not in cfg:
        raise KeyError("Config must contain 'host'.")
    if "path" not in cfg:
        cfg["path"] = DEFAULT_PATH
    return cfg


# ======================================
# HTML table parser
# ======================================
class SimpleTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables: List[List[List[str]]] = []
        self._in_table = self._in_tr = self._in_td = False
        self._current_table: List[List[str]] = []
        self._current_row: List[str] = []
        self._current_cell: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self._in_table = True
            self._current_table = []
        elif tag == "tr" and self._in_table:
            self._in_tr = True
            self._current_row = []
        elif tag == "td" and self._in_tr:
            self._in_td = True
            self._current_cell = []

    def handle_endtag(self, tag):
        if tag == "td" and self._in_td:
            text = "".join(self._current_cell).strip().replace("\xa0", " ")
            self._current_row.append(text)
            self._in_td = False
        elif tag == "tr" and self._in_tr:
            self._current_table.append(self._current_row)
            self._in_tr = False
        elif tag == "table" and self._in_table:
            self.tables.append(self._current_table)
            self._in_table = False

    def handle_data(self, data):
        if self._in_td:
            self._current_cell.append(data)


# ======================================
# Core parsing logic
# ======================================
def find_inverter_table(tables: List[List[List[str]]]) -> Optional[List[List[str]]]:
    for tbl in tables:
        if tbl and "Current Power" in " ".join(tbl[0]):
            return tbl
    return None


def extract_first_int(text: str) -> Optional[int]:
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else None


def extract_first_float(text: str) -> Optional[float]:
    m = re.search(r"(\d+(?:\.\d+)?)", text)
    return float(m.group(1)) if m else None


def parse_inverter_data(html: str) -> List[Dict]:
    parser = SimpleTableParser()
    parser.feed(html)
    table = find_inverter_table(parser.tables)
    if not table:
        raise ValueError("Could not find inverter data table.")
    rows = table[1:]  # skip header
    results = []
    for r in rows:
        if len(r) < 2:
            continue
        inv = r[0].strip()
        watts = extract_first_int(r[1])
        volt = extract_first_float(r[3]) if len(r) > 3 else None
        temp = extract_first_int(r[4]) if len(r) > 4 else None
        results.append({"id": inv, "watts": watts, "volt": volt, "temp": temp})
    return results


# ======================================
# PVOutput Publishing
# ======================================
def send_to_pvoutput(api_key: str, system_id: str, watts: int, avg_temp: Optional[float], avg_volt: Optional[float]):
    now = datetime.now()
    headers = {
        "X-Pvoutput-Apikey": api_key,
        "X-Pvoutput-SystemId": system_id,
    }
    data = {
        "d": now.strftime("%Y%m%d"),
        "t": now.strftime("%H:%M"),
        "v2": watts,
    }
    if avg_temp is not None:
        data["v5"] = round(avg_temp)
    if avg_volt is not None:
        data["v6"] = round(avg_volt, 1)

    r = requests.post("https://pvoutput.org/service/r2/addstatus.jsp", headers=headers, data=data, timeout=10)
    r.raise_for_status()
    return r.text.strip()


# ======================================
# Main
# ======================================
def build_url(host: str, path: str) -> str:
    return f"{PROTOCOL}://{host}{path}"


def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


def main():
    parser = argparse.ArgumentParser(description="Read APS inverter data and optionally publish to PVOutput.")
    parser.add_argument("--config", default=DEFAULT_CONFIG_FILE, help=f"Path to config file (default: {DEFAULT_CONFIG_FILE})")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of text.")
    args = parser.parse_args()

    try:
        cfg = load_config(args.config)
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)

    url = build_url(cfg["host"], cfg["path"])
    pv_cfg = cfg.get("pvoutput", {})
    publish = str(pv_cfg.get("publish", "no")).lower() in ("yes", "true", "1")

    try:
        html = fetch_html(url)
        readings = parse_inverter_data(html)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    total = sum(r["watts"] or 0 for r in readings)
    avg_volt = sum(r["volt"] for r in readings if r["volt"]) / len([r for r in readings if r["volt"]]) if any(r["volt"] for r in readings) else None
    avg_temp = sum(r["temp"] for r in readings if r["temp"]) / len([r for r in readings if r["temp"]]) if any(r["temp"] for r in readings) else None

    result = {
        "source": url,
        "timestamp": datetime.now().isoformat(),
        "total_watts": total,
        "avg_volt_v": avg_volt,
        "avg_temp_c": avg_temp,
        "panels": {r["id"]: r["watts"] for r in readings},
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Data source: {url}\n")
        for r in readings:
            print(f"  {r['id']}: {r['watts']} W")
        print(f"\nTotal power: {total} W")
        if avg_volt is not None:
            print(f"Avg voltage: {avg_volt:.1f} V")
        if avg_temp is not None:
            print(f"Avg temp: {avg_temp:.1f} °C")

    if publish:
        try:
            api_key = pv_cfg.get("api_key")
            system_id = pv_cfg.get("system_id")
            if not api_key or not system_id:
                raise KeyError("Missing PVOutput credentials (api_key, system_id).")
            result_txt = send_to_pvoutput(api_key, system_id, total, avg_temp, avg_volt)
            print(f"\nPVOutput response: {result_txt}")
        except Exception as e:
            print(f"Error publishing to PVOutput: {e}", file=sys.stderr)
            sys.exit(4)
    else:
        print("\nPublishing skipped (pvoutput.publish=no).")


if __name__ == "__main__":
    main()
