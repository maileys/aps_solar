# APS Microinverter Data Tools

Scripts for reading power data from an **Altenergy Power System (APS / APsystems)** microinverter gateway and optionally publishing it to [PVOutput.org](https://pvoutput.org).

---

## 📁 Repository Contents

| File | Description |
|------|--------------|
| **`aps_read.py`** | Fetches and displays inverter table data from the APS gateway (only dependency: `requests`). |
| **`aps_read_publish_pvoutput.py`** | Reads inverter data and pushes total instantaneous power (W) to PVOutput using API key and System ID. |

---

## ⚙️ Configuration

Both scripts read their settings from a simple **JSON config file**.

### Example `config.json`

```json
{
  "host": "192.168.1.102",
  "path": "/cgi-bin/parameters",
  "pvoutput": {
    "api_key": "YOUR_API_KEY",
    "system_id": "YOUR_SYSTEM_ID",
    "send_voltage_v6": true,
    "send_temp_v5": true
  }
}
```

### Config fields

| Key | Description | Required | Default |
|-----|-------------|----------|---------|
| `host` | IP address or hostname of APS web interface | ✅ | — |
| `path` | Path to inverter data page | ❌ | `/cgi-bin/parameters` |
| `pvoutput.api_key` | PVOutput API key | Only for publisher | — |
| `pvoutput.system_id` | PVOutput system ID | Only for publisher | — |
| `pvoutput.send_voltage_v6` | Include average grid voltage in upload (`v6`) | ❌ | `true` |
| `pvoutput.send_temp_v5` | Include average temperature in upload (`v5`) | ❌ | `true` |

> Save this as `config.json` in the same folder as the scripts (or specify with `--config`).

---

## 🧩 Requirements

Both scripts depend on the `requests` library for HTTP. Install once:

```bash
pip install requests
```

Everything else uses Python’s standard library (`html.parser`, `re`, `json`, etc.).

---

## 🖥️ `aps_read.py`

### Description
Reads the APS inverter table and prints a summary of each panel’s power plus total system power. Can also emit JSON.

### Usage
```bash
python aps_read.py --config config.json
```

Optional JSON:
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
Avg voltage: 229 V
Avg temp: 21 °C
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

## ☀️ `aps_read_publish_pvoutput.py`

### Description
Reads the inverter table and sends the **instantaneous total power (W)** to PVOutput via the official API.  
Optionally includes average voltage (`v6`) and temperature (`v5`) if available.

### Usage
```bash
python aps_read_publish_pvoutput.py --config config.json
```

Optional JSON print alongside the push:
```bash
python aps_read_publish_pvoutput.py --config config.json --json
```

### Example Output
```text
Data source: http://192.168.1.102/cgi-bin/parameters

  INV-XXXX-A: 2 W
  INV-XXXX-B: 1 W
  INV-YYYY-A: 2 W
  INV-YYYY-B: 2 W

Total power: 7 W
Avg voltage: 229 V
Avg temp: 21 °C
PVOutput OK | Power=7W | Temp=21°C | Volt=229V
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

Send regular PVOutput updates via cron (every 5 minutes, example):

```bash
*/5 * * * * /usr/bin/env bash -lc 'python /path/aps_read_publish_pvoutput.py --config /path/config.json >>/var/log/aps_to_pvoutput.log 2>&1'
```

---

## 🧾 License

Released under the **MIT License** — free to use, modify, and distribute with attribution.

---

## 🙋‍♂️ Credits

Built for home solar monitoring with **Altenergy Power System (APsystems)** microinverters and **PVOutput.org** integration.
