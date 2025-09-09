import argparse
import logging
import os
import pathlib
import shutil
import yaml
from dotenv import load_dotenv

# Only import Netmiko when needed (so mock mode works without SSH libs)
def _netmiko():
    from netmiko import ConnectHandler
    return ConnectHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def load_devices(path: str, device_name: str | None):
    data = yaml.safe_load(open(path, "r", encoding="utf-8"))
    devices = [d for d in data.get("devices", []) if d.get("netmiko_type") == "cisco_ios"]
    if device_name:
        devices = [d for d in devices if d.get("name") == device_name]
    return devices

def fetch_one_ssh(dev: dict, password: str, enable_secret: str | None, outdir: pathlib.Path, cmd: str):
    ConnectHandler = _netmiko()
    params = {
        "device_type": "cisco_ios",
        "host": dev["host"],
        "username": dev["username"],
        "password": password,
        "fast_cli": True,
    }
    name = dev["name"]
    logging.info("SSH → %s (%s)", name, dev["host"])

    with ConnectHandler(**params) as conn:
        if enable_secret:
            conn.enable()
        conn.send_command("terminal length 0", expect_string=r"#")
        conn.send_command("terminal width 511", expect_string=r"#")
        run_cmd = dev.get("show_cmd", cmd)
        output = conn.send_command(run_cmd, read_timeout=60)

    outdir.mkdir(exist_ok=True)
    path = outdir / f"{name}.txt"
    path.write_text(output, encoding="utf-8")
    logging.info("Saved config → %s", path)

def fetch_one_mock(dev: dict, src_file: pathlib.Path, outdir: pathlib.Path):
    """Mock mode: just copy a local file and name it like the device."""
    name = dev["name"]
    outdir.mkdir(exist_ok=True)
    dst = outdir / f"{name}.txt"
    shutil.copyfile(src_file, dst)
    logging.info("MOCK copy → %s (from %s)", dst, src_file)

def main():
    load_dotenv()
    ap = argparse.ArgumentParser(description="Backup Cisco IOS configs (SSH or mock)")
    ap.add_argument("--devices", default="devices.yaml", help="YAML device list")
    ap.add_argument("--out", default="backups", help="Output folder")
    ap.add_argument("--cmd", default="show running-config", help="Show command to run (SSH mode)")
    ap.add_argument("--device", help="Backup only this device name")
    ap.add_argument("--mock-from", help="Path to local config to copy instead of SSH")
    args = ap.parse_args()

    devices = load_devices(args.devices, args.device)
    if not devices:
        logging.warning("No matching Cisco IOS devices in %s", args.devices)
        return

    outdir = pathlib.Path(args.out)

    if args["mock_from"] if isinstance(args, dict) else args.mock_from:
        # MOCK MODE
        src = pathlib.Path(args.mock_from).resolve()
        if not src.exists():
            raise SystemExit(f"--mock-from not found: {src}")
        logging.info("Running in MOCK mode using %s", src)
        for d in devices:
            try:
                fetch_one_mock(d, src, outdir)
            except Exception as e:
                logging.exception("Mock copy failed %s: %s", d.get("name"), e)
        return

    # SSH MODE
    password = os.getenv("PASSWORD")
    enable_secret = os.getenv("ENABLE_SECRET")
    if not password:
        raise SystemExit("PASSWORD not set (put it in .env or set $env:PASSWORD)")

    for d in devices:
        try:
            fetch_one_ssh(d, password, enable_secret, outdir, args.cmd)
        except Exception as e:
            logging.exception("SSH backup failed %s: %s", d.get("name"), e)

if __name__ == "__main__":
    main()
