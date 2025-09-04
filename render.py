import sys
import pathlib
import ipaddress
import yaml
from copy import deepcopy
from jinja2 import Environment, FileSystemLoader, ChoiceLoader

def enrich_device(dev: dict) -> dict:
    """Return a copy of the device with computed fields for the template."""
    d = deepcopy(dev)
    # add split ip/netmask on each interface
    for intf in d.get("interfaces", []):
        ip_cidr = intf.get("ip")
        if not ip_cidr:
            intf["ip_addr"] = None
            intf["netmask"] = None
            continue
        if "/" not in ip_cidr:
            # handle weird case; treat like host /32
            ip_cidr = ip_cidr + "/32"
        ipi = ipaddress.ip_interface(ip_cidr)
        intf["ip_addr"] = str(ipi.ip)           # e.g. 10.0.10.1
        intf["netmask"] = str(ipi.network.netmask)  # e.g. 255.255.255.0

    # add expanded route fields
    for r in d.get("routes", []):
        prefix = r.get("dst")
        if prefix:
            net = ipaddress.ip_network(prefix, strict=False)
            r["dst_network"] = str(net.network_address)   # e.g. 0.0.0.0
            r["dst_netmask"] = str(net.netmask)           # e.g. 0.0.0.0
    return d

def main(inventory_path="inventory.yaml", template_path="templates/cisco_svi.j2", outdir="build", device_name=None):
    template_path = template_path.replace("\\", "/")
    cwd = pathlib.Path.cwd()

    env = Environment(
        loader=ChoiceLoader([
            FileSystemLoader(str(cwd)),
            FileSystemLoader(str(cwd / "templates")),
            FileSystemLoader(str(pathlib.Path(template_path).parent or ".")),
        ]),
        trim_blocks=True, lstrip_blocks=True
    )

    tpl_name = pathlib.Path(template_path).name
    data = yaml.safe_load(open(inventory_path, "r", encoding="utf-8"))
    out = pathlib.Path(outdir)
    out.mkdir(exist_ok=True)
    tpl = env.get_template(tpl_name)

    # 🔹 filter device if --device is used
    devices = data.get("devices", [])
    if device_name:
        devices = [d for d in devices if d.get("name") == device_name]
        if not devices:
            print(f"[WARN] Device '{device_name}' not found in {inventory_path}")
            return

    for dev in devices:
        edev = enrich_device(dev)
        text = tpl.render(device=edev)
        (out / f"{edev['name']}.cfg").write_text(text, encoding="utf-8")

    print(f"Rendered {len(devices)} config(s) → {out.resolve()}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) >= 4:
        main(args[0], args[1], args[2], args[3])
    elif len(args) == 3:
        main(args[0], args[1], args[2])
    elif len(args) == 2:
        main(args[0], args[1])
    elif len(args) == 1:
        main(args[0])
    else:
        main()

