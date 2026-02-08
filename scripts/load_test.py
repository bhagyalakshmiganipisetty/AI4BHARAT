"""Run the k6 load test script with sensible defaults."""

from __future__ import annotations

import shutil
import subprocess
import sys


def run():
    if not shutil.which("k6"):
        print(
            "k6 is not installed. Install it from https://k6.io/docs/get-started/installation/"
        )
        sys.exit(1)
    cmd = ["k6", "run", "scripts/load_test.js"]
    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    run()
