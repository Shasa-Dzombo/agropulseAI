"""
Pulls new photos off a DJI remote controller over adb into a local folder -
the "first half" that scripts/watch_and_upload_dji_images.py already assumes
someone has done by hand ("e.g. where `adb pull` lands photos copied off a
DJI remote controller mid-flight").

Run this alongside watch_and_upload_dji_images.py, both pointed at the same
folder, and the whole chain runs unattended:

    RC storage --(this script)--> local folder --(watcher)--> POST /drones/flights/{id}/images

adb is the same transport scrcpy uses, so if scrcpy can already see your RC,
so can this. No new Python dependency - it shells out to the system `adb`.

IMPORTANT - confirm your real remote path first. The DCIM layout differs by
RC model and DJI app version, so --remote-dir is required rather than
guessed:

    adb devices                  # confirm the RC is listed and authorized
    adb shell ls /sdcard/DCIM/   # find the real folder your photos land in

Usage:
    python scripts/adb_pull_dji_images.py \\
        --remote-dir /sdcard/DCIM/100MEDIA \\
        --local-folder "C:\\Users\\you\\dji_pulls" \\
        [--poll-interval 5.0] \\
        [--adb-binary adb] \\
        [--serial <device-serial>]     # only needed with several devices attached

Ctrl-C to stop. Safe to re-run: pulled filenames are recorded in
<local-folder>/.pulled_files.txt so nothing is re-downloaded on restart.
"""

import argparse
import os
import subprocess
import sys
import time

_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".dng")
_MARKER_FILENAME = ".pulled_files.txt"


def build_adb_command(adb_binary: str, serial: str, *args: str) -> list:
    """`-s <serial>` must come before the subcommand, hence assembling the
    command rather than appending."""
    command = [adb_binary]
    if serial:
        command += ["-s", serial]
    return command + list(args)


def run_adb(adb_binary: str, serial: str, *args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        build_adb_command(adb_binary, serial, *args),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def check_device_available(adb_binary: str, serial: str) -> None:
    """Fails loudly and early with actionable guidance - a silent empty poll
    loop against a disconnected/unauthorized RC is the worst outcome here."""
    try:
        result = run_adb(adb_binary, serial, "devices", timeout=30)
    except FileNotFoundError:
        sys.exit(
            f"'{adb_binary}' not found. Install Android platform-tools (the same adb scrcpy uses) "
            "or pass --adb-binary with its full path."
        )
    except subprocess.TimeoutExpired:
        sys.exit("adb devices timed out - is the adb server wedged? Try 'adb kill-server' and retry.")

    if result.returncode != 0:
        sys.exit(f"adb devices failed: {result.stderr.strip()}")

    # Skip the "List of devices attached" header; a device line is
    # "<serial>\t<state>", where state must be "device" (not "unauthorized"
    # or "offline").
    attached = [
        line.split("\t")
        for line in result.stdout.splitlines()[1:]
        if "\t" in line
    ]
    ready = [serial_no for serial_no, state in attached if state.strip() == "device"]

    if not ready:
        detail = "; ".join(f"{s}={state.strip()}" for s, state in attached) or "none attached"
        sys.exit(
            f"No adb device ready ({detail}). Connect the RC, set USB mode to file transfer, "
            "and accept the 'Allow USB debugging' prompt on its screen."
        )
    if serial and serial not in ready:
        sys.exit(f"Device '{serial}' is not ready. Ready devices: {', '.join(ready)}")


def list_remote_images(adb_binary: str, serial: str, remote_dir: str) -> list:
    result = run_adb(adb_binary, serial, "shell", "ls", remote_dir)
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        print(f"  ! could not list {remote_dir}: {stderr}")
        return []

    names = []
    for line in result.stdout.splitlines():
        name = line.strip()
        if name and name.lower().endswith(_IMAGE_EXTENSIONS):
            names.append(name)
    return names


def pull_file(adb_binary: str, serial: str, remote_dir: str, name: str, local_folder: str) -> bool:
    # Remote paths are POSIX regardless of the host OS, so they're joined
    # with "/" explicitly rather than os.path.join (which would emit "\" on
    # Windows and break on the device).
    remote_path = f"{remote_dir.rstrip('/')}/{name}"
    result = run_adb(adb_binary, serial, "pull", remote_path, local_folder)
    if result.returncode != 0:
        print(f"  FAILED to pull {name}: {result.stderr.strip() or result.stdout.strip()}")
        return False
    return True


def load_pulled(marker_path: str) -> set:
    if not os.path.exists(marker_path):
        return set()
    with open(marker_path) as f:
        return {line.strip() for line in f if line.strip()}


def mark_pulled(marker_path: str, name: str) -> None:
    with open(marker_path, "a") as f:
        f.write(name + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--remote-dir", required=True, help="Folder on the RC, e.g. /sdcard/DCIM/100MEDIA")
    parser.add_argument("--local-folder", required=True, help="Where to put pulled files (point the watcher here too)")
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--adb-binary", default="adb")
    parser.add_argument("--serial", default="", help="Only needed when several devices are attached")
    args = parser.parse_args()

    check_device_available(args.adb_binary, args.serial)
    os.makedirs(args.local_folder, exist_ok=True)

    marker_path = os.path.join(args.local_folder, _MARKER_FILENAME)
    pulled = load_pulled(marker_path)

    print(f"Pulling new images from {args.remote_dir} -> {args.local_folder} - Ctrl-C to stop.")
    if pulled:
        print(f"({len(pulled)} file(s) already pulled previously, skipping those)")

    try:
        while True:
            for name in list_remote_images(args.adb_binary, args.serial, args.remote_dir):
                if name in pulled:
                    continue

                print(f"New file on RC: {name}")
                try:
                    if not pull_file(args.adb_binary, args.serial, args.remote_dir, name, args.local_folder):
                        continue  # transient failure - retry on the next poll
                except subprocess.TimeoutExpired:
                    print(f"  timed out pulling {name} - will retry next poll")
                    continue

                # Only recorded after a confirmed-successful pull, so an
                # interrupted transfer is retried rather than skipped.
                mark_pulled(marker_path, name)
                pulled.add(name)
                print(f"  pulled -> {os.path.join(args.local_folder, name)}")

            time.sleep(args.poll_interval)
    except KeyboardInterrupt:
        print("Stopped.")


if __name__ == "__main__":
    main()
