# APS Microinverter Data Tools

Scripts for reading power data from an **Altenergy Power System (APS / APsystems)** microinverter gateway and optionally publishing it to [PVOutput.org](https://pvoutput.org).

---

## 📁 Repository Contents

| File | Description |
|------|--------------|
| **`aps_read.py`** | Fetches and displays inverter table data from the APS gateway (no external dependencies other than `requests`). |
| **`aps_read_publish_pvoutput.py`** | Reads inverter data and pushes total instantaneous power (W) to PVOutput using API key and System ID. |

---

## ⚙️ Configuration

Both scripts read their settings from a simple **JSON config file**.

Example:

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
