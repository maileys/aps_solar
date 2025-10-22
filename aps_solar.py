#!/usr/bin/env python3
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from html.parser import HTMLParser

# ======================================
# Constants
# ======================================
PROTOCOL = "http"
DEFAULT_PATH = "/cgi-bin/parameters"
TIMEOUT = 5.0
DEFAULT_CONFIG_FILE = "config.json"

# Regex helpers (strict, unit-specific, with tolerant temp)
WATT_RE = re.compile(r"(-?\d+)\s*W\b", re.IGNORECASE)
VOLT_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*V\b", re.IGNORECASE)
# Accept degree as '°', 'º', HTML '&deg;', or plain 'o' (from <sup>o</sup>)
TEMP_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*(?:°|º|&deg;|o)?\s*C\b", re.IGNORECASE)
# Optional numeric fallback
NUM_RE  = re.compile(r"(-?\d+(?:\.\d+)?)")

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

def extract_watts(text: str) -> Optional[int]:
    m = WATT_RE.search(text)
    return int(m.group(1)) if m else None

def extract_volts(text: str) -> Optional[float]:
    m = VOLT_RE.search(text)
    if m:
        return float(m.group(1))
    m2 = NUM_RE.search(text)
    return float(m2.group(1)) if m2 else None

def extract_temp(text: str) -> Optional[float]:
    m = TEMP_RE.search(text)
    if m:
        return float(m.group(1))
    m2 = NUM_RE.search(text)
    return float(m2.group(1)) if m2 else None

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
        watts = extract_watts(r[1])
        volt = extract_volts(r[3]) if len(r) > 3 else None    # "Grid Voltage"
        temp = extract_temp(r[4]) if len(r) > 4 else None     # "Temperature"
        results.append({"id": inv, "watts": watts, "volt": volt, "temp": temp})
    return results

# ======================================
# PVOutput Publishing
# ======================================
def send_to_pvoutput(api_key: str, system_id: str, watts: int,
                     avg_temp: Optional[float], avg_volt: Optional[float]) -> str:
    now = datetime.now()
    headers = {
        "X-Pvoutput-Apikey": api_key,
        "X-Pvoutput-SystemId": system_id,
    }
    data = {
        "d": now.strftime("%Y%m%d"),
        "t": now.strftime("%H:%M"),
        "v2": watts,  # power (W)
    }
    # v5 = temperature (°C), v6 = voltage (V)
    if avg_temp is not None:
        data["v5"] = int(round(avg_temp))
    if avg_volt is not None:
        data["v6"] = f"{avg_volt:.1f}"

    r = requests.post("https://pvoutput.org/service/r2/addstatus.jsp",
                      headers=headers, data=data, timeout=10)
    r.raise_for_status()
    return r.text.strip()

# ======================================
# Helpers
# ======================================
def average(values: List[Optional[float]]) -> Optional[float]:
    nums = [v for v in values if isinstance(v, (int, float))]
    return (sum(nums) / len(nums)) if nums else None

def scale_total_if_missing(
    total_raw: int,
    received_count: int,
    expected_count: Optional[int],
    scale_missing: bool
) -> Tuple[int, Optional[int]]:
    """
    Returns (chosen_total, estimated_total_or_none).
    If scaling is enabled and we received fewer than expected (but >0),
    compute: estimated_total = round(total_raw * expected/received)
    """
    if (scale_missing and isinstance(expected_count, int) and expected_count > 0
            and received_count > 0 and expected_count > received_count):
        estimated = int(round(total_raw * (expected_count / received_count)))
        return estimated, estimated
    return total_raw, None

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
    parser = argparse.ArgumentParser(
        description="Read APS inverter data and optionally publish to PVOutput (with comms-loss scaling)."
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG_FILE,
                        help=f"Path to config file (default: {DEFAULT_CONFIG_FILE})")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of text.")
    args = parser.parse_args()

    # Load config
    try:
        cfg = load_config(args.config)
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)

    url = build_url(cfg["host"], cfg["path"])
    pv_cfg = cfg.get("pvoutput", {})
    publish = str(pv_cfg.get("publish", "no")).lower() in ("yes", "true", "1")

    # Scaling logic
    scale_missing = str(cfg.get("scale_missing", "no")).lower() in ("yes", "true", "1")
    expected_count = None
    if scale_missing:
        expected_count = cfg.get("expected_count")
        if not isinstance(expected_count, int) or expected_count <= 0:
            raise ValueError("'expected_count' must be a positive integer when scale_missing is enabled.")

    # Read data
    try:
        html = fetch_html(url)
        readings = parse_inverter_data(html)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    # Compute totals & averages
    valid_watts = [r["watts"] for r in readings if isinstance(r["watts"], int)]
    received_count = len(valid_watts)
    total_raw = sum(valid_watts)
    avg_volt = average([r["volt"] for r in readings])
    avg_temp = average([r["temp"] for r in readings])

    # Scale if configured and missing some readings
    total_scaled, estimated_value = scale_total_if_missing(
        total_raw=total_raw,
        received_count=received_count,
        expected_count=expected_count,
        scale_missing=scale_missing
    )

    # Prepare JSON payload for --json or for logging
    payload = {
        "source": url,
        "timestamp": datetime.now().isoformat(),
        "received_count": received_count,
        "expected_count": expected_count,
        "total_watts_raw": total_raw,
        "total_watts_estimated": estimated_value,  # may be None
        "total_watts_for_output": total_scaled,
        "avg_volt_v": round(avg_volt, 1) if isinstance(avg_volt, (int, float)) else None,
        "avg_temp_c": round(avg_temp, 1) if isinstance(avg_temp, (int, float)) else None,
        "panels": {r["id"]: r["watts"] for r in readings},
        "scaled_due_to_missing": bool(estimated_value is not None),
    }

    # Output
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Data source: {url}\n")
        for r in readings:
            watts_display = r['watts'] if r['watts'] is not None else 'N/A'
            print(f"  {r['id']}: {watts_display} W")
        if scale_missing and expected_count is not None:
            print(f"\nReceived panels: {received_count} / expected {expected_count}")
        else:
            print(f"\nReceived panels: {received_count}")
        print(f"Raw total power: {total_raw} W")
        if estimated_value is not None:
            print(f"Estimated total (scaled for missing panels): {total_scaled} W")
        else:
            print(f"Total power: {total_scaled} W")
        if avg_volt is not None:
            print(f"Avg voltage: {avg_volt:.1f} V")
        if avg_temp is not None:
            print(f"Avg temp: {avg_temp:.1f} °C")

    # Publish (uses scaled total if present)
    if publish:
        try:
            api_key = pv_cfg.get("api_key")
            system_id = pv_cfg.get("system_id")
            if not api_key or not system_id:
                raise KeyError("Missing PVOutput credentials (api_key, system_id).")
            resp_text = send_to_pvoutput(api_key, system_id, total_scaled, avg_temp, avg_volt)
            print(f"\nPVOutput response: {resp_text}")
        except Exception as e:
            print(f"Error publishing to PVOutput: {e}", file=sys.stderr)
            sys.exit(4)
    else:
        print("\nPublishing skipped (pvoutput.publish=no).")

if __name__ == "__main__":
    main()
