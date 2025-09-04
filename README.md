# 🛠️ Network Config Parser & Renderer

A **multi-vendor network automation demo** that parses raw device configs (Cisco, FortiGate), exports them into a normalized inventory (`YAML`/`JSON`), and generates golden configs via **Jinja2 templates**.

This project shows the full **NetDevOps flow**:


---

## ✨ Features
- 🔍 **Parse** Cisco & FortiGate configs into structured JSON/YAML
- 📦 **Normalize** into a vendor-neutral `inventory.yaml` (source of truth)
- 🏗️ **Render** golden configs using Jinja2 templates
- 🎭 **Multi-vendor support**: Cisco IOS, FortiGate (extensible to Juniper, Arista, etc.)
- 🔄 **Cross-vendor migration**: take Cisco inventory → render FortiGate configs

---

## 📂 Project Structure
network-config-parser/
├── sample-configs/ # Example raw device configs
│ ├── cisco.txt
│ └── fortigate.txt
├── templates/ # Jinja2 templates
│ ├── cisco_svi.j2
│ └── fortigate_svi.j2
├── parser.py # Parse raw configs → JSON/YAML
├── render.py # Render inventory.yaml → configs
├── requirements.txt # Python dependencies
└── inventory.yaml # Vendor-neutral source of truth

---

## 🚀 Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/zakariapast/network-config-parser.git
cd network-config-parser

### 2. Set up virtual environment
python -m venv .venv
.\.venv\Scripts\activate   # (Windows PowerShell)
pip install -r requirements.txt

### 3. Parse raw configs
python parser.py sample-configs/cisco.txt sample-configs/fortigate.txt --yaml
➡️ Outputs parsed_output.json and parsed_output.yaml.

### 4. Export to inventory
python parser.py sample-configs/*.txt --export-inventory inventory.yaml

### 5. Render configs
Cisco:
python render.py inventory.yaml templates/cisco_svi.j2 build
FortiGate:
python render.py inventory.yaml templates/fortigate_svi.j2 build
➡️ Generated configs will be saved in build/.

🖼️ Example

Cisco Output

hostname EDGE-ROUTER-1
!
vlan 10
 name VLAN_10
!
interface GigabitEthernet0/1
 description Auto-generated
 ip address 10.0.10.1 255.255.255.0
!
ip route 0.0.0.0 0.0.0.0 192.168.1.254


FortiGate Output

config system interface
    edit "VLAN10"
        set ip 10.10.10.254 255.255.255.0
        set allowaccess ping https ssh
    next
end

config router static
    edit 0
        set dst 0.0.0.0 0.0.0.0
        set gateway 10.1.1.254
    next
end

