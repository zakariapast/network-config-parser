import re
import json
import argparse
from typing import Dict, Any, List, Optional

try:
    import yaml
except Exception:
    yaml = None


# ---------- Helpers ----------
def mask_to_prefix(mask: str) -> int:
    try:
        parts = [int(p) for p in mask.split(".")]
        bits = "".join(f"{p:08b}" for p in parts)
        if "01" in bits:
            # non-contiguous mask fallback: count ones anyway
            return sum(bin(p).count("1") for p in parts)
        return bits.count("1")
    except Exception:
        return 0


def ip_mask_to_cidr(ip: str, mask: str) -> str:
    return f"{ip}/{mask_to_prefix(mask)}"


def first_or_none(seq):
    return seq[0] if seq else None


# ---------- Cisco parser ----------
def parse_cisco(text: str) -> Dict[str, Any]:
    interfaces, seen_ips, seen_vlans = [], set(), set()

    # hostname
    m_host = re.search(r"(?m)^hostname\s+(\S+)", text)
    hostname = m_host.group(1) if m_host else None

    # interface blocks
    for m in re.finditer(r"(?m)^interface\s+([^\n]+)\n(.*?)(?=^\S|\Z)", text, flags=re.S):
        name = m.group(1).strip()
        body = m.group(2)

        # ip address lines
        ips = []
        for ip, mask in re.findall(
            r"^\s*ip address\s+(\d{1,3}(?:\.\d{1,3}){3})\s+(\d{1,3}(?:\.\d{1,3}){3})", body, flags=re.M
        ):
            ips.append({"ip": ip, "mask": mask, "cidr": f"/{mask_to_prefix(mask)}"})
            seen_ips.add(ip)

        # vlan detection
        vlan = None
        m_vlan_if = re.search(r"[Vv]lan(\d+)$", name)
        if m_vlan_if:
            vlan = int(m_vlan_if.group(1))
            seen_vlans.add(vlan)
        else:
            m_vlan_sw = re.search(r"^\s*switchport\s+access\s+vlan\s+(\d+)", body, flags=re.M)
            if m_vlan_sw:
                vlan = int(m_vlan_sw.group(1))
                seen_vlans.add(vlan)

        interfaces.append({"name": name, "ips": ips, "vlan": vlan})

    # static routes
    routes = []
    for m in re.finditer(
        r"(?m)^ip route\s+(\d{1,3}(?:\.\d{1,3}){3})\s+(\d{1,3}(?:\.\d{1,3}){3})\s+(\d{1,3}(?:\.\d{1,3}){3})", text
    ):
        dst, mask, gw = m.groups()
        routes.append({"dst": f"{dst}/{mask_to_prefix(mask)}", "gateway": gw})

    # acl lines
    acls = [line.strip() for line in re.findall(r"(?m)^access-list\s+.+$", text)]

    return {
        "vendor": "cisco",
        "hostname": hostname,
        "interfaces": interfaces,
        "routes": routes,
        "acls": acls,
        "all_ips": sorted(seen_ips),
        "vlans": sorted(seen_vlans),
    }


# ---------- FortiGate parser ----------
def parse_fortigate(text: str) -> Dict[str, Any]:
    interfaces, seen_ips, seen_vlans = [], set(), set()

    # hostname (optional)
    m_host = re.search(r'(?m)^\s*set\s+hostname\s+"?([^\n"]+)"?', text)
    hostname = m_host.group(1) if m_host else None

    # interface blocks (config system interface ... edit NAME ... next)
    for blk in re.finditer(r'edit\s+"?([^\n"]+)"?\s*(.*?)\s*next', text, flags=re.S):
        name = blk.group(1).strip()
        body = blk.group(2)

        ips = []
        for ip, mask in re.findall(
            r"\bset\s+ip\s+(\d{1,3}(?:\.\d{1,3}){3})\s+(\d{1,3}(?:\.\d{1,3}){3})", body
        ):
            ips.append({"ip": ip, "mask": mask, "cidr": f"/{mask_to_prefix(mask)}"})
            seen_ips.add(ip)

        vlan = None
        m_vlan = re.search(r"\bset\s+vlanid\s+(\d+)", body)
        if m_vlan:
            vlan = int(m_vlan.group(1))
            seen_vlans.add(vlan)

        interfaces.append({"name": name, "ips": ips, "vlan": vlan})

    # static routes (config router static ... set dst + set gateway)
    routes = []
    for block in re.finditer(r"config router static(.*?)end", text, flags=re.S):
        body = block.group(1)
        for r in re.finditer(
            r"\bset\s+dst\s+(\d{1,3}(?:\.\d{1,3}){3})\s+(\d{1,3}(?:\.\d{1,3}){3}).*?\bset\s+gateway\s+(\d{1,3}(?:\.\d{1,3}){3})",
            body,
            flags=re.S,
        ):
            dst, mask, gw = r.groups()
            routes.append({"dst": f"{dst}/{mask_to_prefix(mask)}", "gateway": gw})

    return {
        "vendor": "fortigate",
        "hostname": hostname,
        "interfaces": interfaces,
        "routes": routes,
        "policies": [],  # (we can add later)
        "all_ips": sorted(seen_ips),
        "vlans": sorted(seen_vlans),
    }


# ---------- Auto-detect & wrapper ----------
def detect_vendor(text: str) -> str:
    if "config system interface" in text or "config firewall policy" in text:
        return "fortigate"
    if re.search(r"(?m)^interface\s+\S+", text):
        return "cisco"
    return "auto"


def parse(text: str, vendor: str = "auto") -> Dict[str, Any]:
    if vendor == "auto":
        vendor = detect_vendor(text)
    if vendor == "cisco":
        return parse_cisco(text)
    if vendor == "fortigate":
        return parse_fortigate(text)
    # fallback try Cisco first
    data = parse_cisco(text)
    if not data.get("interfaces"):
        data = parse_fortigate(text)
    return data


# ---------- Inventory export ----------
def pick_device_name(parsed: Dict[str, Any], fallback_filename: str) -> str:
    return parsed.get("hostname") or fallback_filename


def pick_mgmt_ip(parsed: Dict[str, Any]) -> Optional[str]:
    """
    Very simple heuristic:
    - prefer a /32 (Loopback) if present
    - else first SVI VLAN IP
    - else first interface IP
    """
    # prefer /32
    for intf in parsed.get("interfaces", []):
        for ipobj in intf.get("ips", []):
            if ipobj.get("cidr") == "/32":
                return ipobj["ip"]

    # prefer vlan interfaces
    for intf in parsed.get("interfaces", []):
        if intf.get("vlan") is not None and intf.get("ips"):
            return intf["ips"][0]["ip"]

    # else any ip
    for intf in parsed.get("interfaces", []):
        for ipobj in intf.get("ips", []):
            return ipobj["ip"]

    return None


def normalize_inventory_entry(parsed: Dict[str, Any], filename: str) -> Dict[str, Any]:
    dev = {
        "name": pick_device_name(parsed, filename),
        "vendor": parsed.get("vendor"),
        "mgmt_ip": pick_mgmt_ip(parsed),
        "vlans": parsed.get("vlans", []),
        "interfaces": [],
        "routes": parsed.get("routes", []),
    }

    for intf in parsed.get("interfaces", []):
        # choose first IP if multiple
        ip_cidr = None
        if intf.get("ips"):
            ip = intf["ips"][0]["ip"]
            mask = intf["ips"][0]["mask"]
            ip_cidr = ip_mask_to_cidr(ip, mask)
        dev["interfaces"].append(
            {
                "name": intf.get("name"),
                "ip": ip_cidr,         # e.g., 10.0.10.1/24
                "vlan": intf.get("vlan"),
            }
        )
    return dev


# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser(description="Parse network configs → JSON/YAML and optional inventory export")
    ap.add_argument("files", nargs="+", help="Config files (Cisco/FortiGate)")
    ap.add_argument("--out", default="parsed_output", help="Output filename (without extension)")
    ap.add_argument("--yaml", action="store_true", help="Also write YAML output")
    ap.add_argument("--vendor", choices=["auto", "cisco", "fortigate"], default="auto")
    ap.add_argument("--export-inventory", metavar="PATH", help="Write normalized inventory YAML to PATH")
    args = ap.parse_args()

    results: List[Dict[str, Any]] = []
    inventory: Dict[str, Any] = {"devices": []}

    for path in args.files:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            parsed = parse(text, vendor=args.vendor)
            parsed["file"] = path
            results.append(parsed)

            if args.export_inventory:
                # strip directories from filename
                fname = path.split("\\")[-1].split("/")[-1]
                inventory["devices"].append(normalize_inventory_entry(parsed, fname))
        except FileNotFoundError:
            results.append({"file": path, "error": "File not found"})

    # structured results
    with open(f"{args.out}.json", "w", encoding="utf-8") as j:
        json.dump(results, j, indent=2)

    if args.yaml and yaml is not None:
        with open(f"{args.out}.yaml", "w", encoding="utf-8") as y:
            yaml.safe_dump(results, y, sort_keys=False)

    if args.export_inventory:
        if yaml is None:
            raise RuntimeError("PyYAML not installed: pip install pyyaml")
        with open(args.export_inventory, "w", encoding="utf-8") as inv:
            yaml.safe_dump(inventory, inv, sort_keys=False)

    print(f"Wrote {args.out}.json" + (" and YAML" if args.yaml and yaml else ""))
    if args.export_inventory:
        print(f"Wrote inventory → {args.export_inventory}")


if __name__ == "__main__":
    main()
