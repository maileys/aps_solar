# APS Microinverter Data Tools

Scripts for reading power data from an **Altenergy Power System (APS / APsystems)** microinverter gateway and optionally publishing it to [PVOutput.org](https://pvoutput.org).

---

## 📁 Repository Contents

| File | Description |
|------|--------------|
| **`aps_read.py`** | Fetches and displays inverter table data from the APS gateway (no external dependencies other than `requests`). |
| **`aps_read_publish_pvoutput.py`** | Reads inverter data and, if configured, publishes the total instantaneous power (W) to PVOutput using your API key and system ID. |

---

## ⚙️ Configuration

Both scripts read their settings from a simple **JSON config file**.

### Example `config.json`

```json
{
  "host": "192.168.1.102",
  "path": "/cgi-bin/parameters",
  "publish": "yes",
  "pvoutput": {
    "api_key": "YOUR_API_KEY",
    "system_id": "YOUR_SYSTEM_ID",
    "send_voltage_v6": true,
    "send_temp_v5": true
  }
}
```

### Config Fields

| Key | Description | Required | Default |
|-----|-------------|----------|---------|
| `host` | IP or hostname of the APS web interface | ✅ | — |
| `path` | Path to inverter data page | ❌ | `/cgi-bin/parameters` |
| `publish` | `"yes"` to publish to PVOutput, otherwise prints locally | ❌ | `"no"` |
| `pvoutput.api_key` | PVOutput API key | Only if publishing | — |
| `pvoutput.system_id` | PVOutput system ID | Only if publishing | — |
| `pvoutput.send_voltage_v6` | Include average grid voltage when publishing | ❌ | `true` |
| `pvoutput.send_temp_v5` | Include average temperature when publishing | ❌ | `true` |

> 💡 If `publish` is absent or set to `"no"`, readings are printed to the console only — no data is sent to PVOutput.

Save this file as `config.json` in the same folder as the scripts, or specify a custom path using the `--config` flag.

---

## 🧩 Requirements

Both scripts only require one dependency:

```bash
pip install requests
```

Everything else uses Python’s built-in libraries (`html.parser`, `re`, `json`, etc.).  
They run fine on Python **3.7+**.

---

## 🖥️ `aps_read.py`

### Description
Reads the APS inverter table and prints a summary of per-panel power output and total system power.  
No upload functionality — this is for local inspection or diagnostics.

### Usage
```bash
python aps_read.py --config config.json
```

To get JSON-formatted output:
```bash
python aps_read.py --config config.json --json
```

### Example Output
```text
Data source: http://192.168.1.102/cgi-bin/parameters

  INV-XXXX-A: 2 W
  INV-XXXX-B: 1 W
  INV-YYYY-A: 2 W
  INV-YYYY-B: 2 W

Total power: 7 W
```

### Example JSON
```json
{
  "source": "http://192.168.1.102/cgi-bin/parameters",
  "total_watts": 7,
  "panels": {
    "INV-XXXX-A": 2,
    "INV-XXXX-B": 1,
    "INV-YYYY-A": 2,
    "INV-YYYY-B": 2
  }
}
```

---

## ☀️ `aps_read_publish_pvoutput.py`

### Description
Fetches inverter readings, displays them locally, and optionally **publishes to PVOutput.org** if `"publish": "yes"` is set in your `config.json`.

### Usage
```bash
python aps_read_publish_pvoutput.py --config config.json
```

To get JSON-formatted output:
```bash
python aps_read_publish_pvoutput.py --config config.json --json
```

### Example Output (Publish Enabled)
```text
Data source: http://192.168.1.102/cgi-bin/parameters

  INV-XXXX-A: 2 W
  INV-XXXX-B: 1 W
  INV-YYYY-A: 2 W
  INV-YYYY-B: 2 W

Total power: 7 W
Avg voltage: 229 V
Avg temp: 21 °C
PVOutput response: OK 200
```

### Example Output (Publish Disabled)
```text
Data source: http://192.168.1.102/cgi-bin/parameters

  INV-XXXX-A: 2 W
  INV-XXXX-B: 1 W
  INV-YYYY-A: 2 W
  INV-YYYY-B: 2 W

Total power: 7 W
Avg voltage: 229 V
Avg temp: 21 °C
Publishing skipped (publish=no).
```

### Example JSON
```json
{
  "source": "http://192.168.1.102/cgi-bin/parameters",
  "timestamp": "2025-10-20T15:38:22",
  "total_watts": 7,
  "avg_temp_c": 21,
  "avg_volt_v": 229,
  "panels": {
    "INV-XXXX-A": 2,
    "INV-XXXX-B": 1,
    "INV-YYYY-A": 2,
    "INV-YYYY-B": 2
  }
}
```

---

## 🕒 Scheduling (optional)

You can add either script to cron for automatic operation.

Example — run every 5 minutes and append to a log file:
```bash
*/5 * * * * /usr/bin/env bash -lc 'python /home/pi/aps_read_publish_pvoutput.py --config /home/pi/config.json >>/home/pi/aps.log 2>&1'
```

---

## 🧾 License

Released under the **MIT License** — free to use, modify, and distribute with attribution.

---

## 🙋‍♂️ Credits

Developed for home solar monitoring with **Altenergy Power System (APsystems)** microinverters and **PVOutput.org** integration.

---

### Example Hardware Setup
- **APS ECU / Gateway:** serving `/cgi-bin/parameters`
- **Panels:** microinverters reporting power (W), grid voltage (V), and temperature (°C)
- **Host System:** Raspberry Pi / Linux / macOS / Windows  
  (anything that can run Python 3 and has network access to the APS device)

---

### Quick Summary

| Feature | `aps_read.py` | `aps_read_publish_pvoutput.py` |
|----------|---------------|--------------------------------|
| Reads inverter table | ✅ | ✅ |
| Prints per-panel watts | ✅ | ✅ |
| Calculates total watts | ✅ | ✅ |
| JSON output option | ✅ | ✅ |
| PVOutput upload | ❌ | ✅ (if `"publish":"yes"`) |
| Safe to run standalone | ✅ | ✅ |

---

**Happy monitoring!**
