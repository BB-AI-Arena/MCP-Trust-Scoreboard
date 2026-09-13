#!/usr/bin/env python3
"""Create fresh loopback configuration without printing secrets or replacing files."""
import argparse
import os
from pathlib import Path
import secrets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(".env"))
    args = parser.parse_args()
    # O_EXCL through mode x prevents overwriting an operator's existing config.
    with open(args.output, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as handle:
        handle.write("POSTGRES_USER=koi\nPOSTGRES_DB=koi_security\n")
        handle.write(f"POSTGRES_PASSWORD={secrets.token_hex(24)}\n")
        handle.write(f"AGENT_TRUST_API_TOKEN={secrets.token_hex(32)}\n")
        handle.write("AGENT_TRUST_AUTH_MODE=token\nAGENT_TRUST_HOSTED_ANALYSIS=false\n")
        handle.write("GEMINI_API_KEY=\nABUSEIPDB_API_KEY=\nSCAN_MODE=async\n")
    print(f"Created {args.output} with restrictive permissions; no credentials printed.")


if __name__ == "__main__":
    main()
