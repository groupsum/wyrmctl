from __future__ import annotations

import argparse
import json
from pathlib import Path

from wyrmctl.client import NpmClient


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--identity", required=True)
    parser.add_argument("--secret", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    client = NpmClient(base_url=args.base_url, identity=args.identity, secret=args.secret)
    Path(args.out).write_text(json.dumps(client.openapi_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
