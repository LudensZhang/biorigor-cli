#!/usr/bin/env python3
"""Minimal Python integration example for biorigor-cli.

Two options are shown:

  A. shell out to the CLI and parse --json   (simplest, no coupling)
  B. talk to the HTTP API directly           (no CLI dependency)

Both expect BIORIGOR_HOST (and either BIORIGOR_TOKEN or a prior `biorigor login`).

    export BIORIGOR_HOST=https://biorigor.example.org
    python3 python_client.py paper.pdf
"""

import json
import os
import subprocess
import sys
import time
import urllib.request


def cli_json(*args):
    """Run the CLI with --json and return the parsed result."""
    out = subprocess.run(["biorigor", *args, "--json"],
                         check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def via_cli(pdf):
    task = cli_json("submit", pdf)
    tid = task["taskId"]
    print(f"[cli] submitted {tid}")

    # Poll ourselves rather than blocking, so we can do other work in between.
    while True:
        t = cli_json("status", tid)
        if t["status"] in ("done", "error", "canceled"):
            return t
        print(f"[cli] {t['status']}: {t.get('stage', '')}")
        time.sleep(60)


def via_http(pdf):
    host = os.environ["BIORIGOR_HOST"].rstrip("/")
    token = os.environ["BIORIGOR_TOKEN"]     # or read it from ~/.config/biorigor/config.json
    hdr = {"X-BioRigor-Token": token}

    # multipart by hand — no third-party dependency
    boundary = "----example"
    with open(pdf, "rb") as fh:
        data = fh.read()
    body = b"".join([
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"modelId\"\r\n\r\n"
        f"\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"main\"; "
        f"filename=\"{os.path.basename(pdf)}\"\r\n"
        f"Content-Type: application/pdf\r\n\r\n".encode(),
        data, b"\r\n", f"--{boundary}--\r\n".encode(),
    ])
    req = urllib.request.Request(host + "/api/tasks", data=body, headers={
        **hdr, "Content-Type": f"multipart/form-data; boundary={boundary}"})
    tid = json.load(urllib.request.urlopen(req, timeout=600))["taskId"]
    print(f"[http] submitted {tid}")

    while True:
        req = urllib.request.Request(f"{host}/api/tasks/{tid}", headers=hdr)
        t = json.load(urllib.request.urlopen(req, timeout=60))
        if t["status"] in ("done", "error", "canceled"):
            return t
        print(f"[http] {t['status']}: {t.get('stage', '')}")
        time.sleep(60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(f"usage: {sys.argv[0]} <paper.pdf> [--http]")
    result = (via_http if "--http" in sys.argv else via_cli)(sys.argv[1])
    print(json.dumps({k: result.get(k) for k in
                      ("id", "status", "risk", "stage", "error")}, indent=2))
