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

# Regex patterns
WATT_RE = re.compile(r"(\d+)\s*W\b", re.IGNORECASE)
VOLT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*V\b", re.IGNORECASE)
TEMP_RE = re.compile(r"(\d+)\s*°?\s*C", re.IGNORECASE)


# ======================================
# Config loading
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
# HTML table parser (stdlib)
# ======================================
class SimpleTableParser(HTMLParser):
    """
    Parses <table> → <tr> → <td> hierarchy into a list of tables.
    Each table is a list of rows; each row is a list of text cells.
    """

    def __init__(self):
        super().__init__()
        self.tables: List[List[List[str]]] = []
        self._in_table = False
        self._in_tr = False
        self._in_td = False

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


def find_inverter_table(tables: List[List[List[str]]]) -> Optional[List[List[str]]]:
    """Locate the table whose header row contains 'Current Power'."""
    for tbl in tables:
        if not tbl:
            continue
        header = " ".join(tbl[0])
        if "Current Power" in header:
            return tbl
    return None


# ======================================
# Core parsing logic
# ======================================
def parse_inverter_rows(html: str) -> List[Dict]:
    parser = SimpleTableParser()
    parser.feed(html)
    table = find_inverter_table(parser.tables)
    if not table:
        raise ValueError("Could not find inverter data table.")

    rows = table[1:]  # skip header
    readings = []
    for row in rows:
        if len(row) < 2:
            continue
        inv = row[0].strip()
        power = extract_first_int(row[1])
        volt = extract_first_float(row[3]) if len(row) > 3 else None
        temp = extract_first_int(row[4]) if len(row) > 4 else None
        readings.append({"id": inv, "watts": power, "volt": volt, "temp": temp})
    return readings


def extract_first_int(text: str) -> Optional[int]:
    m = WATT_RE.search(text)
    if m:
        return int(m.group(1))
    m2 = re.search(r"(\d+)", text)
    return int(m2.group(1)) if m2 else None


def extract_first_float(text: str) -> Optional[float]:
    m = VOLT_RE.search(text)
    if m:
        return float(m.group(1))
    m2 = re.search(r"(\d+(?:\.\d+)?)", text)
    return float(m2.group(1)) if m2 else None


# ======================================
# HTTP fetch and PVOutput push
# ======================================
def build_url(host: str, path: str) -> str:
    return f"{
