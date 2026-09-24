"""Print normalized endpoints from a spec URL or file.

Example::

    python -m sentinel_core --spec http://127.0.0.1:8000/openapi.json
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sentinel_core.spec_parser import SpecParser


def main() -> None:
    """CLI entry: load a spec and print METHOD / path with BOLA flags."""
    parser = argparse.ArgumentParser(description="Normalize an OpenAPI spec for SentinelAPI")
    parser.add_argument(
        "--spec",
        default="http://127.0.0.1:8000/openapi.json",
        help="Spec URL or file path",
    )
    args = parser.parse_args()
    spec_parser = SpecParser()
    source = args.spec
    if source.startswith(("http://", "https://")):
        endpoints = spec_parser.load_from_url(source)
    else:
        endpoints = spec_parser.load_from_file(Path(source))

    print(f"{len(endpoints)} endpoints from {source}")
    print(f"{'flag':<6} {'method':<7} {'path':<28} {'auth':<6} object_id_params")
    print("-" * 72)
    for endpoint in endpoints:
        flag = "BOLA" if endpoint.is_bola_candidate else ""
        auth = "yes" if endpoint.auth_required else "no"
        ids = ",".join(endpoint.object_id_params) if endpoint.object_id_params else "-"
        print(f"{flag:<6} {endpoint.method:<7} {endpoint.path:<28} {auth:<6} {ids}")


if __name__ == "__main__":
    main()
