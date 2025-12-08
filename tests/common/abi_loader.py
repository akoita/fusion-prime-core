"""
ABI Loader Utilities

This module provides utilities for loading contract ABIs from files
instead of storing them inline in environment variables.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_abi_from_env(
    env_var_name: str, project_root: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Load ABI from a file path specified in an environment variable.

    Args:
        env_var_name: Name of the environment variable containing the ABI file path
        project_root: Optional project root path. If not provided, uses current working directory

    Returns:
        List of ABI function/event definitions

    Raises:
        FileNotFoundError: If the ABI file doesn't exist
        ValueError: If the environment variable is not set
        json.JSONDecodeError: If the ABI file contains invalid JSON
    """
    abi_path = os.getenv(env_var_name)
    if not abi_path:
        raise ValueError(f"Environment variable {env_var_name} is not set")

    # If path is relative, make it relative to project root
    if not os.path.isabs(abi_path):
        if project_root is None:
            project_root = os.getcwd()
        abi_path = os.path.join(project_root, abi_path)

    if not os.path.exists(abi_path):
        raise FileNotFoundError(f"ABI file not found: {abi_path}")

    with open(abi_path, "r") as f:
        abi_data = json.load(f)

    # Handle both direct ABI arrays and wrapped ABI objects
    if isinstance(abi_data, list):
        return abi_data
    elif isinstance(abi_data, dict) and "abi" in abi_data:
        return abi_data["abi"]
    else:
        raise ValueError(f"Invalid ABI format in {abi_path}")


def load_escrow_factory_abi(project_root: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load the EscrowFactory contract ABI.

    Args:
        project_root: Optional project root path

    Returns:
        EscrowFactory ABI as a list of function/event definitions
    """
    return load_abi_from_env("ESCROW_FACTORY_ABI_PATH", project_root)


def load_contract_abi(
    contract_name: str, project_root: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Load a contract ABI by name.

    Args:
        contract_name: Name of the contract (e.g., 'EscrowFactory')
        project_root: Optional project root path

    Returns:
        Contract ABI as a list of function/event definitions
    """
    abi_path = os.path.join(
        project_root or os.getcwd(), "contracts", "abis", f"{contract_name}.json"
    )
    return load_abi_from_file(abi_path)


def load_abi_from_file(abi_path: str) -> List[Dict[str, Any]]:
    """
    Load ABI from a specific file path.

    Args:
        abi_path: Path to the ABI JSON file

    Returns:
        ABI as a list of function/event definitions
    """
    if not os.path.exists(abi_path):
        raise FileNotFoundError(f"ABI file not found: {abi_path}")

    with open(abi_path, "r") as f:
        abi_data = json.load(f)

    # Handle both direct ABI arrays and wrapped ABI objects
    if isinstance(abi_data, list):
        return abi_data
    elif isinstance(abi_data, dict) and "abi" in abi_data:
        return abi_data["abi"]
    else:
        raise ValueError(f"Invalid ABI format in {abi_path}")


def load_escrow_abi(project_root: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load Escrow contract ABI.

    Args:
        project_root: Optional project root path. If not provided, uses current working directory

    Returns:
        List of ABI dictionaries for the Escrow contract
    """
    if project_root is None:
        project_root = os.getcwd()

    abi_path = os.path.join(project_root, "contracts", "abi", "Escrow.json")
    return load_abi_from_file(abi_path)
