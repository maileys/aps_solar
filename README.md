# APS Solar – Microinverter Data Reader and PVOutput Publisher

A lightweight Python utility for reading live data from an **Altenergy Power System (APS / APsystems)** microinverter gateway and optionally publishing total generation to [PVOutput.org](https://pvoutput.org).

This script replaces older versions (`aps_read.py`, `aps_read_publish_pvoutput.py`) with a **single unified tool** for both reading and publishing.

---

## 📁 Repository Contents

| File | Description |
|------|--------------|
| **`aps_solar.py`** | Reads power data from the APS web interface and, if configured, publishes it to PVOutput.org. |
| **`config.json`** | Configuration file specifying gateway and PVOutput settings. |

---

## ⚙️ Configuration

`aps_solar.py` uses a simple JSON configuration file.  
If the `publish` flag (inside `pvoutput`) is `"yes"`, data will be pushed to PVOutput — otherwise it’s just printed or returned as JSON.

### Example `config.json`

```json
{
  "host": "192.168.1.102",
  "path": "/cgi-bin/parameters",
  "pvoutput": {
    "publish": "yes",
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
| `host` | IP or hostname of the APS ECU / gateway | ✅ | — |
| `path` | Path to inverter data page | ❌ | `/cgi-bin/parameters` |
| `pvoutput.publish` | `"yes"` to publish to PVOutput; otherwise just print results | ❌ | `"no"` |
| `pvoutput.api_key` | PVOutput API key | Only if publishing | — |
| `pvoutput.system_id` | PVOutput system ID | Only if publishing | — |
| `pvoutput.send_voltage_v6` | Include average voltage in upload (`v6`) | ❌ | `true` |
| `pvoutput.send_temp_v5` | Include average temperature in upload (`v5`) | ❌ | `true` |

> 💡 If `"publish"` is missing or set to `"no"`, readings are displayed locally and **not** uploaded to PVOutput.

Save this file as `config.json` in the same folder as the script (or specify another path with `--config`).

---

## 🧩 Requirements

Only one external library is required:

```bash
pip install requests
```

All other functionality uses Python’s standard library (`html.parser`, `re`, `json`, etc.).  
Tested on **Python 3.7+**.

---

## 🖥️ Usage

### Basic usage
```bash
python aps_solar.py --config config.json
```

### JSON output
```bash
python aps_solar.py --config config.json --json
```

---

## 🧾 Example Outputs

### Console Output (Publish = yes)
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

### Console Output (Publish = no)
```text
Data source: http://192.168.1.102/cgi-bin/parameters

  INV-XXXX-A: 2 W
  INV-XXXX-B: 1 W
  INV-YYYY-A: 2 W
  INV-YYYY-B: 2 W

Total power: 7 W
Avg voltage: 229 V
Avg temp: 21 °C
Publishing skipped (pvoutput.publish=no).
```

### JSON Output Example
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

## ☀️ PVOutput Publishing

If `"pvoutput.publish": "yes"`, the script automatically posts the current total power and optional average voltage/temperature to PVOutput.org using your API key and system ID.

Endpoint used:
```
https://pvoutput.org/service/r2/addstatus.jsp
```

Data fields sent:
- `v2` = Instantaneous Power (W)
- `v5` = Temperature (°C) *(optional)*
- `v6` = Voltage (V) *(optional)*

A typical PVOutput success response is:
```
OK 200
```

---

## 🕒 Scheduling (optional)

You can schedule this script to run automatically using cron or Task Scheduler.

Example — run every 5 minutes and append to a log file:
```bash
*/5 * * * * /usr/bin/env bash -lc 'python /home/pi/aps_solar.py --config /home/pi/config.json >>/home/pi/aps_solar.log 2>&1'
```

---

## 🧾 License

Released under the **MIT License** — free to use, modify, and distribute with attribution.

---

## 🙋‍♂️ Credits

Developed for personal solar monitoring with **Altenergy Power System (APsystems)** microinverters and **PVOutput.org** integration.

---

### 🧠 Summary

| Feature | Supported |
|----------|------------|
| Reads inverter data | ✅ |
| Prints per-panel watts | ✅ |
| Calculates total watts | ✅ |
| JSON output option | ✅ |
| PVOutput publishing | ✅ (if `"pvoutput.publish":"yes"`) |
| Simple config file | ✅ |
| No heavy dependencies | ✅ |

---

**Happy monitoring!**
