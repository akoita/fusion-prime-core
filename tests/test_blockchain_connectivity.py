"""
Blockchain Connectivity Test

Tests basic blockchain connectivity and contract verification.
"""

from tests.base_integration_test import BaseIntegrationTest


class TestBlockchainConnectivity(BaseIntegrationTest):
    """Test blockchain connectivity and basic operations."""

    def test_blockchain_connectivity(self):
        """Test blockchain connectivity and basic operations."""
        print("🔄 Testing blockchain connectivity...")

        # Test basic connectivity
        latest_block = self.web3.eth.block_number
        assert latest_block > 0, "Cannot get latest block number"
        print(f"✅ Connected to blockchain, latest block: {latest_block}")
        print(f"✅ Chain ID: {self.chain_id}")

        # Test contract interaction (if factory address is set)
        if self.factory_address:
            code = self.web3.eth.get_code(self.factory_address)
            assert len(code) > 0, "Factory contract not found at address"
            print(f"✅ Factory contract verified at {self.factory_address}")
        else:
            print("ℹ️  Factory address not set, skipping contract verification")
