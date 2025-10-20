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
NUM_RE  = re.compile(r"(-?\d+(?:\.\d+)?)")  # for °C number

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
    Parses all <table> elements into tables -> rows -> cells (plain text).
    Handles odd markup (e.g., stray <center>, &nbsp;, <sup>o</sup>) by collecting text.
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
        elif self._in_table and tag == "tr":
            self._in_tr = True
            self._current_row = []
        elif self._in_tr and tag == "td":
            self._in_td = True
            self._current_cell = []

    def handle_endtag(self, tag):
        if tag == "td" and self._in_td:
            # finalize cell
            text = "".join(self._current_cell).strip().replace("\xa0", " ")
            self._current_row.append(text)
            self._in_td = False
        elif tag == "tr" and self._in_tr:
            # finalize row
            self._current_table.append(self._current_row)
            self._in_tr = False
        elif tag == "table" and self._in_table:
            # finalize table
            self.tables.append(self._current_table)
            self._in_table = False

    def handle_data(self, data):
        if self._in_td:
            self._current_cell.append(data)

def find_inverter_table(tables: List[List[List[str]]]) -> Optional[List[List[str]]]:
    """
    Locate the table whose header row contains 'Current Power'.
    """
    for tbl in tables:
        if not tbl:
            continue
        # Flatten first row cells to check header text
        header = " ".join(tbl[0]).strip()
        if "Current Power" in header:
            return tbl
    return None

def parse_inverter_rows(html: str) -> List[Dict]:
    parser = SimpleTableParser()
    parser.feed(html)
    table = find_inverter_table(parser.tables)
    if not table:
        r
