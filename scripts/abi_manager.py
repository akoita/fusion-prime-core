#!/usr/bin/env python3
"""
ABI Manager for Fusion Prime

This script helps manage contract ABIs by providing utilities to:
- Extract ABIs from environment variables
- Validate ABI files
- Convert between different ABI formats
"""

import argparse
import json
import os
import sys
from pathlib import Path


def extract_abi_from_env(env_file: str, output_dir: str = "contracts/abis"):
    """Extract ABI from environment file and save as JSON."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("ESCROW_FACTORY_ABI="):
                # Extract the ABI value
                abi_str = line.split("=", 1)[1]
                try:
                    abi_data = json.loads(abi_str)
                    # Save as formatted JSON
                    with open(output_path / "EscrowFactory.json", "w") as abi_file:
                        json.dump(abi_data, abi_file, indent=2)
                    print(f"✅ Extracted ABI to {output_path / 'EscrowFactory.json'}")
                except json.JSONDecodeError as e:
                    print(f"❌ Error parsing ABI: {e}")
                    return False
                break
    return True


def validate_abi_file(abi_path: str):
    """Validate an ABI file."""
    try:
        with open(abi_path, "r") as f:
            abi_data = json.load(f)

        if not isinstance(abi_data, list):
            print(f"❌ ABI file {abi_path} should contain a list of functions/events")
            return False

        # Check for required fields
        for item in abi_data:
            if not isinstance(item, dict):
                print(f"❌ ABI item should be a dictionary")
                return False

            if "type" not in item:
                print(f"❌ ABI item missing 'type' field")
                return False

        print(f"✅ ABI file {abi_path} is valid")
        return True

    except FileNotFoundError:
        print(f"❌ ABI file not found: {abi_path}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in ABI file: {e}")
        return False


def list_abi_files(abi_dir: str = "contracts/abis"):
    """List all ABI files in the directory."""
    abi_path = Path(abi_dir)
    if not abi_path.exists():
        print(f"❌ ABI directory not found: {abi_dir}")
        return

    abi_files = list(abi_path.glob("*.json"))
    if not abi_files:
        print(f"📁 No ABI files found in {abi_dir}")
        return

    print(f"📁 ABI files in {abi_dir}:")
    for abi_file in sorted(abi_files):
        print(f"  - {abi_file.name}")


def main():
    parser = argparse.ArgumentParser(description="Manage contract ABIs")
    parser.add_argument("command", choices=["extract", "validate", "list"], help="Command to run")
    parser.add_argument(
        "--env-file", default=".env.test", help="Environment file to extract ABI from"
    )
    parser.add_argument(
        "--abi-dir", default="contracts/abis", help="Directory containing ABI files"
    )
    parser.add_argument("--abi-file", help="Specific ABI file to validate")

    args = parser.parse_args()

    if args.command == "extract":
        success = extract_abi_from_env(args.env_file, args.abi_dir)
        sys.exit(0 if success else 1)

    elif args.command == "validate":
        if args.abi_file:
            success = validate_abi_file(args.abi_file)
        else:
            # Validate all ABI files in directory
            abi_path = Path(args.abi_dir)
            if not abi_path.exists():
                print(f"❌ ABI directory not found: {args.abi_dir}")
                sys.exit(1)

            abi_files = list(abi_path.glob("*.json"))
            if not abi_files:
                print(f"📁 No ABI files found in {args.abi_dir}")
                sys.exit(0)

            all_valid = True
            for abi_file in abi_files:
                if not validate_abi_file(str(abi_file)):
                    all_valid = False

            success = all_valid
        sys.exit(0 if success else 1)

    elif args.command == "list":
        list_abi_files(args.abi_dir)


if __name__ == "__main__":
    main()
