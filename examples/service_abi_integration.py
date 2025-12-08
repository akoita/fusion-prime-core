"""
Service ABI Integration Examples

This file shows how to integrate the Contract Registry into existing services
to access smart contract ABIs in different environments.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from google.cloud import storage
from web3 import Web3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# METHOD 1: Using Contract Registry Library (Recommended)
# ============================================================================


def example_with_contract_registry():
    """Example using the Contract Registry library."""
    try:
        # Import the contract registry (adjust path as needed)
        from services.shared.contract_registry import ContractRegistry

        # Initialize contract registry
        registry = ContractRegistry()

        # Get contract address and ABI
        factory_address = registry.get_contract_address("EscrowFactory")
        factory_abi = registry.get_contract_abi("EscrowFactory")

        # Create Web3 contract instance
        web3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
        factory_contract = web3.eth.contract(address=factory_address, abi=factory_abi)

        # Use contract
        owner = factory_contract.functions.owner().call()
        logger.info(f"Factory owner: {owner}")

        return factory_contract

    except Exception as e:
        logger.error(f"Contract registry integration failed: {e}")
        raise


# ============================================================================
# METHOD 2: Direct GCS URL Loading (For GCP Environments)
# ============================================================================


def load_abi_from_gcs(gcs_url: str) -> List[Dict[str, Any]]:
    """Load ABI from GCS URL."""
    try:
        # Parse GCS URL: gs://bucket/path/to/file.json
        if not gcs_url.startswith("gs://"):
            raise ValueError(f"Invalid GCS URL: {gcs_url}")

        path_parts = gcs_url[5:].split("/", 1)  # Remove 'gs://' and split
        if len(path_parts) != 2:
            raise ValueError(f"Invalid GCS URL format: {gcs_url}")

        bucket_name, blob_name = path_parts

        # Load from GCS
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        abi_json = blob.download_as_text()
        abi_data = json.loads(abi_json)

        # Handle different ABI formats
        if isinstance(abi_data, list):
            return abi_data
        elif isinstance(abi_data, dict) and "abi" in abi_data:
            return abi_data["abi"]
        else:
            raise ValueError(f"Invalid ABI format in {gcs_url}")

    except Exception as e:
        logger.error(f"Failed to load ABI from {gcs_url}: {e}")
        raise


def example_with_gcs_url():
    """Example using GCS URL for ABI loading."""
    try:
        # Get contract address
        factory_address = os.getenv("ESCROW_FACTORY_ADDRESS")
        if not factory_address:
            raise ValueError("ESCROW_FACTORY_ADDRESS not set")

        # Try GCS URL first
        factory_abi_url = os.getenv("ESCROW_FACTORY_ABI_URL")
        if factory_abi_url:
            factory_abi = load_abi_from_gcs(factory_abi_url)
            logger.info("Loaded ABI from GCS")
        else:
            # Fallback to local file
            factory_abi_path = os.getenv("ESCROW_FACTORY_ABI_PATH")
            if not factory_abi_path:
                raise ValueError("No ABI source available")

            with open(factory_abi_path, "r") as f:
                abi_data = json.load(f)
                factory_abi = abi_data.get("abi", abi_data)
            logger.info("Loaded ABI from local file")

        # Create Web3 contract instance
        web3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
        factory_contract = web3.eth.contract(address=factory_address, abi=factory_abi)

        # Use contract
        owner = factory_contract.functions.owner().call()
        logger.info(f"Factory owner: {owner}")

        return factory_contract

    except Exception as e:
        logger.error(f"GCS URL integration failed: {e}")
        raise


# ============================================================================
# METHOD 3: Hybrid Approach with Fallbacks
# ============================================================================


def load_contract_abi_with_fallback(contract_name: str) -> List[Dict[str, Any]]:
    """Load contract ABI with multiple fallback methods."""

    # Method 1: Try GCS URL
    abi_url = os.getenv(f"{contract_name.upper()}_ABI_URL")
    if abi_url:
        try:
            return load_abi_from_gcs(abi_url)
        except Exception as e:
            logger.warning(f"GCS ABI loading failed: {e}")

    # Method 2: Try local file path
    abi_path = os.getenv(f"{contract_name.upper()}_ABI_PATH")
    if abi_path and os.path.exists(abi_path):
        try:
            with open(abi_path, "r") as f:
                abi_data = json.load(f)
                return abi_data.get("abi", abi_data)
        except Exception as e:
            logger.warning(f"Local file ABI loading failed: {e}")

    # Method 3: Try contract registry
    try:
        from services.shared.contract_registry import ContractRegistry

        registry = ContractRegistry()
        return registry.get_contract_abi(contract_name)
    except Exception as e:
        logger.warning(f"Contract registry ABI loading failed: {e}")

    # All methods failed
    raise ValueError(f"Could not load ABI for {contract_name} using any method")


def example_hybrid_approach():
    """Example using hybrid approach with multiple fallbacks."""
    try:
        # Get contract address
        factory_address = os.getenv("ESCROW_FACTORY_ADDRESS")
        if not factory_address:
            raise ValueError("ESCROW_FACTORY_ADDRESS not set")

        # Load ABI with fallbacks
        factory_abi = load_contract_abi_with_fallback("EscrowFactory")

        # Create Web3 contract instance
        web3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
        factory_contract = web3.eth.contract(address=factory_address, abi=factory_abi)

        # Use contract
        owner = factory_contract.functions.owner().call()
        logger.info(f"Factory owner: {owner}")

        return factory_contract

    except Exception as e:
        logger.error(f"Hybrid approach failed: {e}")
        raise


# ============================================================================
# SERVICE INTEGRATION EXAMPLES
# ============================================================================


class SettlementService:
    """Example settlement service with contract integration."""

    def __init__(self):
        self.web3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
        self.factory_contract = self._load_factory_contract()

    def _load_factory_contract(self):
        """Load the factory contract using contract registry."""
        try:
            from services.shared.contract_registry import ContractRegistry

            registry = ContractRegistry()
            factory_address = registry.get_contract_address("EscrowFactory")
            factory_abi = registry.get_contract_abi("EscrowFactory")

            return self.web3.eth.contract(address=factory_address, abi=factory_abi)
        except Exception as e:
            logger.error(f"Failed to load factory contract: {e}")
            raise

    def create_escrow(self, payer: str, payee: str, amount: int) -> Dict[str, Any]:
        """Create a new escrow contract."""
        try:
            # Build transaction
            tx = self.factory_contract.functions.createEscrow(
                payer, payee, amount
            ).build_transaction({"from": payer, "gas": 200000, "gasPrice": self.web3.eth.gas_price})

            return {
                "status": "success",
                "transaction": tx,
                "factory_address": self.factory_contract.address,
            }
        except Exception as e:
            logger.error(f"Failed to create escrow: {e}")
            return {"status": "error", "error": str(e)}


class RiskEngineService:
    """Example risk engine service with contract monitoring."""

    def __init__(self):
        self.web3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
        self.factory_contract = self._load_factory_contract()

    def _load_factory_contract(self):
        """Load the factory contract using hybrid approach."""
        factory_address = os.getenv("ESCROW_FACTORY_ADDRESS")
        if not factory_address:
            raise ValueError("ESCROW_FACTORY_ADDRESS not set")

        factory_abi = load_contract_abi_with_fallback("EscrowFactory")

        return self.web3.eth.contract(address=factory_address, abi=factory_abi)

    def monitor_escrow_events(self, from_block: int = None):
        """Monitor escrow deployment events."""
        try:
            if from_block is None:
                from_block = self.web3.eth.block_number - 100

            # Get EscrowDeployed events
            event_filter = self.factory_contract.events.EscrowDeployed.create_filter(
                fromBlock=from_block
            )

            events = event_filter.get_all_entries()
            logger.info(f"Found {len(events)} escrow deployment events")

            return events
        except Exception as e:
            logger.error(f"Failed to monitor events: {e}")
            return []


# ============================================================================
# HEALTH CHECK EXAMPLES
# ============================================================================


def contract_health_check() -> Dict[str, Any]:
    """Comprehensive contract health check."""
    health = {"status": "healthy", "contracts": {}, "errors": []}

    try:
        # Check factory contract
        factory_address = os.getenv("ESCROW_FACTORY_ADDRESS")
        if not factory_address:
            health["errors"].append("ESCROW_FACTORY_ADDRESS not set")
            health["status"] = "unhealthy"
            return health

        # Load contract
        factory_abi = load_contract_abi_with_fallback("EscrowFactory")
        web3 = Web3(Web3.HTTPProvider(os.getenv("RPC_URL")))
        factory_contract = web3.eth.contract(address=factory_address, abi=factory_abi)

        # Test contract call
        owner = factory_contract.functions.owner().call()

        health["contracts"]["EscrowFactory"] = {
            "address": factory_address,
            "owner": owner,
            "status": "healthy",
        }

    except Exception as e:
        health["contracts"]["EscrowFactory"] = {"status": "unhealthy", "error": str(e)}
        health["errors"].append(f"EscrowFactory: {e}")
        health["status"] = "unhealthy"

    return health


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    """Run examples."""

    print("=== Service ABI Integration Examples ===\n")

    # Example 1: Contract Registry
    print("1. Contract Registry Integration:")
    try:
        contract = example_with_contract_registry()
        print("✅ Contract registry integration successful")
    except Exception as e:
        print(f"❌ Contract registry integration failed: {e}")

    print()

    # Example 2: GCS URL
    print("2. GCS URL Integration:")
    try:
        contract = example_with_gcs_url()
        print("✅ GCS URL integration successful")
    except Exception as e:
        print(f"❌ GCS URL integration failed: {e}")

    print()

    # Example 3: Hybrid Approach
    print("3. Hybrid Approach:")
    try:
        contract = example_hybrid_approach()
        print("✅ Hybrid approach successful")
    except Exception as e:
        print(f"❌ Hybrid approach failed: {e}")

    print()

    # Example 4: Health Check
    print("4. Health Check:")
    health = contract_health_check()
    print(f"Status: {health['status']}")
    if health["errors"]:
        print(f"Errors: {health['errors']}")

    print()

    # Example 5: Service Integration
    print("5. Service Integration:")
    try:
        settlement = SettlementService()
        print("✅ Settlement service initialized")

        risk_engine = RiskEngineService()
        print("✅ Risk engine service initialized")

    except Exception as e:
        print(f"❌ Service integration failed: {e}")
