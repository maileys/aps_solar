# APS Solar – Microinverter Data Reader and PVOutput Publisher

A lightweight Python utility for reading live data from an **Altenergy Power System (APS / APsystems)** microinverter gateway and optionally publishing total generation data to [PVOutput.org](https://pvoutput.org).

This script automatically fetches power data from your APS ECU web interface and can optionally publish it to PVOutput.  
It also includes logic to handle communication dropouts by estimating total output when some inverters don’t report, and can log extra metrics such as voltage, temperature, and grid frequency.

---

## 📁 Repository Contents

| File | Description |
|------|--------------|
| **`aps_solar.py`** | Reads APS inverter data and, if configured, publishes to PVOutput. Includes optional scaling when panels are missing. |
| **`config.json`** | Configuration file specifying gateway, PVOutput, and scaling settings. |

---

## ⚙️ Configuration

`aps_solar.py` uses a simple JSON configuration file.  
If `"pvoutput.publish"` is `true`, it will push results to PVOutput — otherwise it will just display or return them in JSON.

### Example `config.json`

```json
{
  "host": "192.168.1.102",
  "path": "/cgi-bin/parameters",
  "scale_missing": true,
  // Only required if scale_missing is true:
  "expected_count": 20,
  "pvoutput": {
    "publish": true,
    "api_key": "YOUR_API_KEY",
    "system_id": "YOUR_SYSTEM_ID",
    "send_temp": true,
    "send_voltage": true,
    "send_freq": true,
    "send_freq_key": "v11"
  }
}
```

### Config Fields

| Key | Description | Required | Default |
|-----|-------------|----------|---------|
| `host` | IP or hostname of the APS ECU/gateway | ✅ | — |
| `path` | Path to the inverter data page | ❌ | `/cgi-bin/parameters` |
| `scale_missing` | `true` to estimate total if some inverters don’t report | ❌ | `false` |
| `expected_count` | Expected number of inverter/panel readings (only required if scaling is enabled) | ⚠️ | — |
| `pvoutput.publish` | Enables publishing data to PVOutput | ❌ | `false` |
| `pvoutput.api_key` | Your PVOutput API key | Required if publishing | — |
| `pvoutput.system_id` | Your PVOutput system ID | Required if publishing | — |
| `pvoutput.send_temp` | Include average inverter temperature (`v5`) | ❌ | `true` |
| `pvoutput.send_voltage` | Include average grid voltage (`v6`) | ❌ | `true` |
| `pvoutput.send_freq` | Include average grid frequency | ❌ | `false` |
| `pvoutput.send_freq_key` | Extended PVOutput field to use for frequency (e.g. `v7–v12`, default `v11`) | ❌ | `"v11"` |

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
python aps_solar.py --config /path/to/config.json
```

### Output as JSON
```bash
python aps_solar.py --config /path/to/config.json --json
```

---

## ⚙️ How Scaling Works

If some inverters fail to report, and `scale_missing` is `true`,  
the script estimates total output as:

```
estimated_total = round((total_raw / received_count) * expected_count)
```

This ensures continuity of total readings during brief communication losses.  
Scaling only occurs if:
- `scale_missing` = `true`, **and**
- `expected_count` is defined and greater than the number of readings received.

---

## 🧾 Example Outputs

### Case 1 – All panels reporting
```text
Data source: http://192.168.1.102/cgi-bin/parameters

  INV-XXXX-A: 120 W
  INV-XXXX-B: 118 W
  INV-YYYY-A: 117 W
  INV-YYYY-B: 117 W

Received panels: 4
Raw total power: 472 W
Total power: 472 W
Avg voltage: 234.0 V
Avg temp: 50.0 °C
Avg frequency: 50.01 Hz
Publishing skipped (pvoutput.publish=no).
```

### Case 2 – Some panels missing, scaling enabled
```text
Data source: http://192.168.1.102/cgi-bin/parameters

  INV-XXXX-A: 120 W
  INV-XXXX-B: 118 W
  INV-YYYY-A: 117 W
  INV-YYYY-B: — W

Received panels: 3 / expected 4
Raw total power: 355 W
Estimated total (scaled for missing panels): 472 W
Avg voltage: 234.0 V
Avg temp: 50.0 °C
Avg frequency: 50.01 Hz
PVOutput response: OK 200
```

### JSON Output Example
```json
{
  "source": "http://192.168.1.102/cgi-bin/parameters",
  "timestamp": "2025-10-23T11:10:16",
  "received_count": 4,
  "expected_count": 10,
  "total_watts_raw": 472,
  "total_watts_estimated": null,
  "total_watts_for_output": 472,
  "avg_volt_v": 234.0,
  "avg_temp_c": 50.0,
  "avg_freq_hz": 50.01,
  "scaled_due_to_missing": false,
  "panels": {
    "INV-XXXX-A": 120,
    "INV-XXXX-B": 118,
    "INV-YYYY-A": 117,
    "INV-YYYY-B": 117
  }
}
```

---

## ☀️ PVOutput Publishing

When `"pvoutput.publish": true`, the script posts results to:

```
https://pvoutput.org/service/r2/addstatus.jsp
```

### Data sent

| Field | Description |
|--------|-------------|
| `v2` | Instantaneous Power (W) |
| `v5` | Temperature (°C) *(optional, if `send_temp = true`)* |
| `v6` | Voltage (V) *(optional, if `send_voltage = true`)* |
| `v11` | Frequency (Hz) *(optional, if `send_freq = true` and `send_freq_key = "v11"`)* |

> You can change `send_freq_key` to another extended slot (`v7`–`v12`) in your config if your PVOutput system already uses `v11`.

A successful response from PVOutput is:
```
OK 200
```

---

## 🕒 Scheduling Example (Linux)

Run every 5 minutes and log output:

```bash
*/5 * * * * /usr/bin/env bash -lc 'python /opt/aps_solar/aps_solar.py --config /opt/aps_solar/config.json >> /var/log/aps_solar.log 2>&1'
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
| Send voltage & temperature | ✅ |
| Send grid frequency | ✅ |
| Simple config file | ✅ |
| No heavy dependencies | ✅ |

---

**Happy monitoring!**
