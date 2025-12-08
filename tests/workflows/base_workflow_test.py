"""
Base Workflow Test Class

Environment-agnostic base class for workflow tests.
Automatically configures based on TEST_ENVIRONMENT variable.
"""

import os
import time
from typing import Optional

import pytest
import requests
from web3 import Web3
from web3.providers import LegacyWebSocketProvider

from tests.common.abi_loader import load_escrow_abi, load_escrow_factory_abi
from tests.common.environment_manager import Environment, EnvironmentManager


class BaseWorkflowTest:
    """
    Base class for environment-agnostic workflow tests.

    This class automatically adapts to local, testnet, or production environments
    based on the TEST_ENVIRONMENT variable or pytest markers.
    """

    def setup_method(self):
        """
        Setup test environment - works for local, testnet, or production.
        """
        # Determine environment from env var or default to local
        env_name = os.getenv("TEST_ENVIRONMENT", "local").lower()

        try:
            self.environment = Environment(env_name)
        except ValueError:
            pytest.fail(f"Invalid TEST_ENVIRONMENT: {env_name}")

        # Initialize environment manager
        self.env_manager = EnvironmentManager()
        self.config = self.env_manager.set_environment(self.environment)

        print(f"\n🔧 Test Environment: {self.environment.value.upper()}")
        print("=" * 60)

        # Setup blockchain connection
        self._setup_blockchain()

        # Setup service URLs
        self._setup_services()

        # Setup test accounts
        self._setup_test_accounts()

        # Setup GCP configuration (if applicable)
        self._setup_gcp()

        self._print_configuration()

    def _setup_blockchain(self):
        """Setup blockchain connection based on environment."""
        blockchain_config = self.config.blockchain

        self.rpc_url = blockchain_config.rpc_url
        self.chain_id = blockchain_config.chain_id
        self.network = blockchain_config.network

        # Create Web3 instance
        if self.rpc_url and self.rpc_url.startswith("wss://"):
            self.web3 = Web3(LegacyWebSocketProvider(self.rpc_url))
        elif self.rpc_url:
            self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        else:
            pytest.skip(f"No RPC URL configured for {self.environment.value}")

        if not self.web3.is_connected():
            pytest.skip(f"Cannot connect to {self.network} blockchain at {self.rpc_url}")

        # Load factory contract
        self.factory_address = os.getenv("ESCROW_FACTORY_ADDRESS") or self.config.test_data.get(
            "contracts", {}
        ).get("escrow_factory")
        self.factory_contract = None

        if self.factory_address:
            try:
                factory_abi = load_escrow_factory_abi()
                self.factory_contract = self.web3.eth.contract(
                    address=self.factory_address, abi=factory_abi
                )
            except FileNotFoundError as e:
                print(f"⚠️  Factory ABI not found: {e}")
                print("   Contract interaction tests will be skipped")

    def _setup_services(self):
        """Setup service URLs based on environment."""
        services_config = self.config.services

        self.settlement_url = services_config.settlement
        self.risk_engine_url = os.getenv("RISK_ENGINE_SERVICE_URL")
        self.compliance_url = os.getenv("COMPLIANCE_SERVICE_URL")
        self.relayer_url = services_config.relayer

    def _setup_test_accounts(self):
        """Setup test accounts based on environment."""
        test_data = self.config.test_data

        # Payer account (for transactions)
        if self.environment == Environment.LOCAL:
            # Use Anvil's default account
            self.payer_private_key = test_data.get(
                "deployer_private_key",
                "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
            )
            self.payee_address = test_data.get(
                "test_payee", "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
            )
        else:
            # Use environment-specific accounts
            self.payer_private_key = os.getenv("PAYER_PRIVATE_KEY")
            self.payee_address = os.getenv(
                "PAYEE_ADDRESS", "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
            )

    def _setup_gcp(self):
        """Setup GCP configuration if applicable."""
        if self.environment == Environment.LOCAL:
            self.gcp_project = "fusion-prime-local"
            self.gcp_region = "local"
        else:
            self.gcp_project = os.getenv("GCP_PROJECT", "fusion-prime")
            self.gcp_region = os.getenv("GCP_REGION", "us-central1")

    def _print_configuration(self):
        """Print test configuration for visibility."""
        print(f"  Network: {self.network} (Chain ID: {self.chain_id})")
        print(f"  RPC: {self.rpc_url}")
        print(f"  Settlement Service: {self.settlement_url or 'Not configured'}")
        print(f"  Risk Engine: {self.risk_engine_url or 'Not configured'}")
        print(f"  Compliance: {self.compliance_url or 'Not configured'}")
        print(f"  Relayer: {self.relayer_url or 'Not configured'}")
        print(f"  Factory: {self.factory_address or 'Not configured'}")

        if self.payer_private_key:
            payer_address = self.web3.eth.account.from_key(self.payer_private_key).address
            print(f"  Payer: {payer_address}")

        print("=" * 60)

    def create_test_id(self, workflow_name: str) -> str:
        """Create unique test ID for tracking."""
        return f"{workflow_name}-{self.environment.value}-{int(time.time() * 1000)}"

    def skip_if_no_private_key(self):
        """Skip test if no private key available for transactions."""
        if not self.payer_private_key:
            pytest.skip(
                f"PAYER_PRIVATE_KEY not set - required for real transactions in {self.environment.value}"
            )

    def skip_if_no_factory(self):
        """Skip test if factory contract not available."""
        if not self.factory_contract:
            pytest.skip(
                f"Factory contract not available in {self.environment.value} - cannot create escrows"
            )

    def get_escrow_contract(self, escrow_address: str):
        """Get escrow contract instance."""
        try:
            escrow_abi = load_escrow_abi()
        except (FileNotFoundError, ImportError):
            # Minimal ABI for basic interactions
            escrow_abi = [
                {
                    "inputs": [],
                    "name": "approveRelease",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function",
                },
                {
                    "inputs": [],
                    "name": "releasePayment",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function",
                },
                {
                    "inputs": [],
                    "name": "requestRefund",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function",
                },
                {
                    "anonymous": False,
                    "inputs": [{"indexed": True, "name": "approver", "type": "address"}],
                    "name": "ApprovalGranted",
                    "type": "event",
                },
                {
                    "anonymous": False,
                    "inputs": [
                        {"indexed": True, "name": "payee", "type": "address"},
                        {"indexed": False, "name": "amount", "type": "uint256"},
                    ],
                    "name": "PaymentReleased",
                    "type": "event",
                },
            ]

        return self.web3.eth.contract(address=escrow_address, abi=escrow_abi)

    def wait_for_relayer_processing(self, description: str = "event"):
        """Wait for relayer to process events (environment-aware)."""
        if self.environment == Environment.LOCAL:
            # Local relayer processes faster
            print(f"⏳ Waiting for local relayer to process {description}...")
            time.sleep(5)
        else:
            # Remote relayer may take longer
            print(f"⏳ Waiting for relayer to process {description} (~30-60s cycle)...")
            time.sleep(45)

        print(f"✅ Relayer processing window complete")

    def query_service(
        self,
        service_name: str,
        url: str,
        endpoint: str,
        method: str = "GET",
        json_data: dict = None,
        timeout: int = 10,
    ) -> Optional[dict]:
        """
        Query a service with environment-aware error handling.

        Returns:
            Response JSON if successful, None if service not configured/available
        """
        if not url:
            print(f"⏭️  {service_name} not configured in {self.environment.value}")
            return None

        try:
            full_url = f"{url}{endpoint}"
            print(f"🔍 Querying {service_name}: {full_url}")

            if method.upper() == "GET":
                response = requests.get(full_url, timeout=timeout)
            elif method.upper() == "POST":
                response = requests.post(full_url, json=json_data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                print(f"ℹ️  {service_name}: Resource not found (404)")
                return None
            else:
                print(f"ℹ️  {service_name}: HTTP {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"ℹ️  {service_name} query failed: {e}")
            return None

    def verify_settlement_service(self, escrow_address: str, test_id: str) -> bool:
        """Verify Settlement Service processed the escrow."""
        print(f"\n💾 Verifying Settlement Service")
        print("-" * 60)

        result = self.query_service(
            "Settlement Service", self.settlement_url, f"/escrows/{escrow_address}"
        )

        if result:
            print(f"✅ Settlement Service has escrow data")
            print(f"   Status: {result.get('status', 'unknown')}")
            return True
        else:
            print(f"ℹ️  Settlement Service: Data not yet available")
            return False

    def verify_risk_engine(self, portfolio_data: dict) -> bool:
        """Verify Risk Engine processed portfolio."""
        print(f"\n📊 Verifying Risk Engine")
        print("-" * 60)

        result = self.query_service(
            "Risk Engine",
            self.risk_engine_url,
            "/risk/portfolio",
            method="POST",
            json_data=portfolio_data,
        )

        if result:
            print(f"✅ Risk Engine calculated risk")
            print(f"   Risk Score: {result.get('risk_score', 'N/A')}")
            print(f"   Risk Level: {result.get('risk_level', 'N/A')}")
            return True
        else:
            print(f"ℹ️  Risk Engine: Not available or no response")
            return False

    def verify_compliance_service(self, compliance_data: dict) -> bool:
        """Verify Compliance Service validated transaction."""
        print(f"\n🔍 Verifying Compliance Service")
        print("-" * 60)

        result = self.query_service(
            "Compliance Service",
            self.compliance_url,
            "/compliance/check",
            method="POST",
            json_data=compliance_data,
        )

        if result:
            print(f"✅ Compliance check completed")
            print(f"   Status: {result.get('status', 'unknown')}")
            print(f"   Approved: {result.get('approved', 'N/A')}")
            return True
        else:
            print(f"ℹ️  Compliance Service: Not available or no response")
            return False

    def print_test_summary(self, test_name: str, details: dict):
        """Print standardized test summary."""
        print("\n" + "=" * 60)
        print(f"✅ {test_name.upper()} - {self.environment.value.upper()} ENVIRONMENT")
        print("=" * 60)

        for key, value in details.items():
            print(f"   {key}: {value}")

        print(f"\n✅ Workflow validated on {self.environment.value} environment!")
