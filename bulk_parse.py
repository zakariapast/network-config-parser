import pathlib
import subprocess
import sys
import yaml
from collections import Counter

def human_table(rows, headers):
    # compute column widths
    widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(str(cell)))
    # build lines
    def line(parts):
        return "  ".join(str(p).ljust(widths[i]) for i, p in enumerate(parts))
    sep = "  ".join("-" * w for w in widths)
    out = [line(headers), sep]
    out += [line(r) for r in rows]
    return "\n".join(out)

def main(out_path="inventory.yaml"):
    backups = pathlib.Path("backups")
    if not backups.exists():
        print("No backups/ folder found.")
        sys.exit(1)

    files = sorted(backups.glob("*.txt"))
    if not files:
        print("No .txt files in backups/")
        sys.exit(1)

    file_list = [str(f) for f in files]
    cmd = [sys.executable, "parser.py", *file_list, "--export-inventory", out_path]

    print(f"Parsing {len(file_list)} file(s) from backups/ → {out_path}")
    # Show the short list for transparency
    for f in files:
        print(f"  - {f.name}")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nparser.py failed: {e}")
        sys.exit(e.returncode)

    # Load inventory and print a summary
    data = yaml.safe_load(open(out_path, "r", encoding="utf-8")) or {}
    devices = data.get("devices", [])
    if not devices:
        print("\nNo devices found in inventory (parser returned empty).")
        sys.exit(0)

    rows = []
    vendor_counts = Counter()
    for d in devices:
        vendor = d.get("vendor", "?")
        vendor_counts[vendor] += 1
        rows.append([
            d.get("name", "?"),
            vendor,
            str(len(d.get("interfaces", []))),
            str(len(d.get("vlans", []))),
            str(len(d.get("routes", []))),
        ])

    print("\nInventory summary:")
    print(human_table(
        rows,
        headers=["Device", "Vendor", "Interfaces", "VLANs", "Routes"]
    ))

    print("\nBy vendor:")
    for v, c in sorted(vendor_counts.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {v}: {c}")

    print(f"\nWrote {out_path} ✅")

if __name__ == "__main__":
    # allow optional custom output path: python bulk_parse.py my_inventory.yaml
    main(*(sys.argv[1:] or []))
