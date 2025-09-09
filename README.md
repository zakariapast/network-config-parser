# Network Config Parser & Generator

This project is a **mini network automation toolkit** that demonstrates how to:

* Collect (backup) device configurations
* Parse raw configs into structured inventory (YAML/JSON)
* Render configs back using Jinja2 templates
* Support vendor migration (e.g., Cisco → FortiGate)

It’s designed as a **portfolio-ready lab project** showing scripting, parsing, and automation workflows commonly expected in Network Engineer / Network Automation roles.

---

## 🚀 Features

### 🔹 Backup

* `backup_cisco.py`

  * **SSH mode**: Connects to Cisco IOS devices using Netmiko and saves running-config
  * **Mock mode**: Copies configs from `sample-configs/` (no hardware required)

### 🔹 Parsing

* `parser.py`: Converts raw configs into structured data (YAML/JSON)
* `bulk_parse.py`: Automatically parses all configs in `backups/` and builds a unified `inventory.yaml`
* Produces a summary table (device, vendor, interfaces, VLANs, routes)

### 🔹 Rendering

* `render.py`: Uses Jinja2 templates to generate device configs from `inventory.yaml`
* Example template: `templates/cisco_svi.j2` for Cisco SVIs, VLANs, and routes

---

## 📂 Project Structure

```
network-config-parser/
├── backups/              # Saved device configs (real or mock)
├── build/                # Generated configs from templates
├── sample-configs/       # Example configs for mock mode
├── templates/            # Jinja2 templates (per vendor)
├── backup_cisco.py       # Cisco backup script (SSH + mock)
├── bulk_parse.py         # Helper to parse all backups at once
├── parser.py             # Parse configs → JSON/YAML
├── render.py             # Render configs from inventory + templates
├── inventory.yaml        # Auto-generated device inventory
├── requirements.txt      # Python dependencies
├── .env.example          # Example credentials file
└── README.md             # Project documentation
```

---

## ⚡ Quickstart

### 1. Clone repo

```bash
git clone https://github.com/zakariapast/network-config-parser.git
cd network-config-parser
```

### 2. Create virtual environment & install dependencies

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Prepare `.env`

Create a local `.env` (never commit real secrets!)

```ini
PASSWORD=YourPasswordHere
ENABLE_SECRET=OptionalEnable
```

### 4. Run mock backup

```bash
python backup_cisco.py --mock-from sample-configs\cisco.txt --out backups
```

### 5. Parse configs

```bash
python bulk_parse.py
```

### 6. Render configs

```bash
python render.py inventory.yaml templates\cisco_svi.j2 build
```

---

## ✅ Example Workflow

```bash
# Backup (mock)
python backup_cisco.py --mock-from sample-configs\cisco.txt --out backups

# Parse all backups → inventory
python bulk_parse.py

# Render configs from inventory
python render.py inventory.yaml templates\cisco_svi.j2 build
```

Output:

* `backups/` → raw configs
* `inventory.yaml` → structured device model
* `build/` → generated configs

---

## 🔐 Security Notes

* `.env` is ignored by git (credentials stay local)
* Use `.env.example` for safe sharing
* Rotate/change any test credentials before pushing to GitHub

---

## 🎯 Why This Project

This repo demonstrates **scripting + automation thinking**:

* SSH automation with Netmiko
* Parsing unstructured text into data models
* Jinja2 templating for repeatable configs
* Vendor migration workflows (Cisco → FortiGate, etc.)
* Clean GitOps-style workflow with backups, inventory, and builds

It’s a solid foundation for:

* Interview coding challenges
* Personal learning labs
* Extending into CI/CD pipelines

---

## 🛠️ Next Steps

* Add vendor filters (`--vendor cisco|fortigate`) in bulk parser
* Add validation checks (e.g., duplicate IPs)
* Add GitHub Actions CI to auto-parse + render on push
* Extend templates for FortiGate, Arista, etc.

---

## 📜 License

MIT License (see `LICENSE`).
