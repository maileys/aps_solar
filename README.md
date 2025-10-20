# APS Solar – Microinverter Data Reader and PVOutput Publisher

A lightweight Python utility for reading live data from an **Altenergy Power System (APS / APsystems)** microinverter gateway and optionally publishing total generation to [PVOutput.org](https://pvoutput.org).

This script automatically fetches power data from your APS ECU web interface and can optionally publish it to PVOutput.  
It also includes logic to handle communication dropouts by estimating total output when some inverters don’t report.

---

## 📁 Repository Contents

| File | Description |
|------|--------------|
| **`aps_solar.py`** | Reads APS inverter data and, if configured, publishes to PVOutput. Includes optional scaling when panels are missing. |
| **`config.json`** | Configuration file specifying gateway, PVOutput, and scaling settings. |

---

## ⚙️ Configuration

`aps_solar.py` uses a simple JSON configuration file.  
If `"pvoutput.publish"` is `"yes"`, it will push results to PVOutput — otherwise it will just display or return them in JSON.

### Example `config.json`

```json
{
  "host": "192.168.1.102",
  "path": "/cgi-bin/parameters",
  "scale_missing": "yes",
  "expected_count": 20,
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
| `host` | IP or hostname of the APS ECU/gateway | ✅ | — |
| `path` | Path to the inverter data page | ❌ | `/cgi-bin/parameters` |
| `scale_missing` | `"yes"` to estimate total if some inverters don’t report | ❌ | `"no"` |
| `expected_count` | Expected number of inverter/panel readings (only required if scaling is enabled) | ⚠️ | — |
| `pvoutput.publish` | `"yes"` to publish data to PVOutput | ❌ | `"no"` |
| `pvoutput.api_key` | Your PVOutput API key | Required if publishing | — |
| `pvoutput.system_id` | Your PVOutput system ID | Required if publishing | — |
| `pvoutput.send_voltage_v6` | Include average voltage in upload (`v6`) | ❌ | `true` |
| `pvoutput.send_temp_v5` | Include average temperature in upload (`v5`) | ❌ | `true` |

---

## 🧩 Requirements

This script depends only on one external library:

```bash
pip install requests
```

Everything else uses the Python standard library (`html.parser`, `json`, `re`, `datetime`, etc.).  
Tested with **Python 3.7+**.

---

## 🖥️ Usage

### Read inverter data only
```bash
python aps_solar.py --config config.json
```

### Output as JSON
```bash
python aps_solar.py --config config.json --json
```

---

## ⚙️ How Scaling Works

If some inverters fail to report, and `scale_missing` is `"yes"`,  
the script estimates total output as:

```
estimated_total = round((total_raw / received_count) * expected_count)
```

This ensures continuity of total readings during brief communication losses.  
Scaling only occurs if:
- `scale_missing` = `"yes"`, **and**
- `expected_count` is defined and greater than the number of readings received.

---

## 🧾 Example Outputs

### Case 1 – All panels reporting
```text
Data source: http://192.168.1.102/cgi-bin/parameters

  INV-XXXX-A: 2 W
  INV-XXXX-B: 1 W
  INV-YYYY-A: 2 W
  INV-YYYY-B: 2 W

Received panels: 4
Raw total power: 7 W
Total power: 7 W
Avg voltage: 229.0 V
Avg temp: 21.0 °C
Publishing skipped (pvoutput.publish=no).
```

### Case 2 – Some panels missing, scaling enabled
```text
Data source: http://192.168.1.102/cgi-bin/parameters

  INV-XXXX-A: 2 W
  INV-XXXX-B: 1 W
  INV-YYYY-A: 2 W
  INV-YYYY-B: — W

Received panels: 3 / expected 4
Raw total power: 5 W
Estimated total (scaled for missing panels): 7 W
Avg voltage: 229.0 V
Avg temp: 21.0 °C
PVOutput response: OK 200
```

### JSON Output Example
```json
{
  "source": "http://192.168.1.102/cgi-bin/parameters",
  "timestamp": "2025-10-20T16:04:25",
  "received_count": 18,
  "expected_count": 20,
  "total_watts_raw": 630,
  "total_watts_estimated": 700,
  "total_watts_for_output": 700,
  "avg_volt_v": 229.0,
  "avg_temp_c": 21.0,
  "panels": {
    "INV-XXXX-A": 2,
    "INV-XXXX-B": 1,
    "INV-YYYY-A": 2
  },
  "scaled_due_to_missing": true
}
```

---

## ☀️ PVOutput Publishing

When `"pvoutput.publish": "yes"`, the script posts results to:

```
https://pvoutput.org/service/r2/addstatus.jsp
```

Data sent:
| Field | Description |
|--------|-------------|
| `v2` | Instantaneous Power (W) |
| `v5` | Temperature (°C) *(optional)* |
| `v6` | Voltage (V) *(optional)* |

A typical success response from PVOutput is:
```
OK 200
```

---

## 🕒 Scheduling Example (Linux)

Run every 5 minutes and log output:
```bash
*/5 * * * * /usr/bin/env bash -lc 'python /home/pi/aps_solar.py --config /home/pi/config.json >>/home/pi/aps_solar.log 2>&1'
```

---

## 🧾 License

Released under the **MIT License** — free to use, modify, and distribute with attribution.

---

## 🙋‍♂️ Credits

Developed for personal solar monitoring using  
**Altenergy Power System (APsystems)** microinverters  
with optional **PVOutput.org** integration.

---

### 🧠 Summary

| Feature | Supported |
|----------|------------|
| Reads inverter data | ✅ |
| Prints per-panel watts | ✅ |
| Calculates total watts | ✅ |
| Estimates missing panels | ✅ (optional) |
| JSON output option | ✅ |
| PVOutput publishing | ✅ |
| Simple config file | ✅ |
| No heavy dependencies | ✅ |

---

**Happy monitoring!**
