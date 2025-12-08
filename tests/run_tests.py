#!/usr/bin/env python3
"""
Simplified Test Runner for Fusion Prime

This script provides a clean, simple interface for running tests
based on the unified test configuration.
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import httpx
import yaml
from web3_test_utils import BlockchainHealthChecker, EscrowFactoryTester, Web3TestUtils

from tests.common.abi_loader import load_escrow_factory_abi


class TestRunner:
    """Main test runner class."""

    def __init__(
        self,
        config_path: str = "tests/test_config.yaml",
        environment: str = None,
        chain: str = None,
    ):
        self.config_path = config_path
        self.config = self._load_config()
        self.environment = environment or os.getenv(
            "TEST_ENV", self.config["environment"]["default"]
        )
        self.chain = chain or os.getenv("TEST_CHAIN", "ethereum")
        self.env_config = self.config["environment"][self.environment]
        self.results = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}

    def _load_config(self) -> Dict[str, Any]:
        """Load test configuration from YAML file."""
        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"❌ Configuration file not found: {self.config_path}")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"❌ Error parsing configuration: {e}")
            sys.exit(1)

    def _get_chain_config(self) -> Dict[str, Any]:
        """Get configuration for the current chain."""
        if self.environment == "local":
            return self.env_config["blockchain"]
        else:
            if "chains" not in self.env_config:
                raise ValueError(
                    f"Multi-chain configuration not found for environment: {self.environment}"
                )
            if self.chain not in self.env_config["chains"]:
                available_chains = list(self.env_config["chains"].keys())
                raise ValueError(
                    f"Chain '{self.chain}' not found. Available chains: {available_chains}"
                )
            return self.env_config["chains"][self.chain]

    def _print_header(self, title: str):
        """Print a formatted header."""
        print(f"\n{'='*50}")
        print(f"🧪 {title}")
        print(f"{'='*50}")

    def _print_result(self, test_name: str, success: bool, message: str = ""):
        """Print test result with appropriate formatting."""
        if success:
            print(f"✅ {test_name}")
            if message:
                print(f"   {message}")
            self.results["passed"] += 1
        else:
            print(f"❌ {test_name}")
            if message:
                print(f"   {message}")
            self.results["failed"] += 1

    def _print_info(self, message: str):
        """Print informational message."""
        print(f"ℹ️  {message}")

    def _print_warning(self, message: str):
        """Print warning message."""
        print(f"⚠️  {message}")
        self.results["skipped"] += 1

    async def check_services(self) -> bool:
        """Check if all required services are running."""
        self._print_info("Checking service health...")

        services = self.config["services"]
        all_healthy = True

        # Check Anvil
        try:
            response = httpx.post(
                services["anvil"]["url"],
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 1,
                },
                timeout=services["anvil"]["timeout"],
            )
            if response.status_code == 200:
                self._print_result("Anvil", True, "Blockchain accessible")
            else:
                self._print_result("Anvil", False, f"HTTP {response.status_code}")
                all_healthy = False
        except Exception as e:
            self._print_result("Anvil", False, str(e))
            all_healthy = False

        # Check Settlement Service
        try:
            response = httpx.get(
                f"{services['settlement_service']['url']}{services['settlement_service']['health_endpoint']}",
                timeout=services["settlement_service"]["timeout"],
            )
            if response.status_code == 200 and response.json().get("status") == "ok":
                self._print_result("Settlement Service", True, "API healthy")
            else:
                self._print_result("Settlement Service", False, f"HTTP {response.status_code}")
                all_healthy = False
        except Exception as e:
            self._print_result("Settlement Service", False, str(e))
            all_healthy = False

        # Check Pub/Sub Emulator
        try:
            response = httpx.get(
                services["pubsub_emulator"]["url"] + services["pubsub_emulator"]["health_endpoint"],
                timeout=services["pubsub_emulator"]["timeout"],
            )
            if response.status_code in [200, 404]:
                self._print_result("Pub/Sub Emulator", True, "Emulator accessible")
            else:
                self._print_result("Pub/Sub Emulator", False, f"HTTP {response.status_code}")
                all_healthy = False
        except Exception as e:
            self._print_result("Pub/Sub Emulator", False, str(e))
            all_healthy = False

        return all_healthy

    def run_contract_tests(self) -> bool:
        """Run smart contract tests."""
        self._print_info("Running smart contract tests...")

        try:
            # Run Foundry tests
            result = subprocess.run(
                ["forge", "test", "-vv"],
                cwd="contracts",
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                self._print_result("Foundry Contract Tests", True, "All tests passed")
            else:
                self._print_result("Foundry Contract Tests", False, result.stderr)
                return False

            # Run Web3.py integration tests
            return self._run_web3_contract_tests()

        except subprocess.TimeoutExpired:
            self._print_result("Contract Tests", False, "Tests timed out")
            return False
        except Exception as e:
            self._print_result("Contract Tests", False, str(e))
            return False

    def _run_web3_contract_tests(self) -> bool:
        """Run Web3.py-based contract integration tests."""
        try:
            # Get chain configuration
            chain_config = self._get_chain_config()

            # Initialize Web3 utilities with chain configuration
            web3_utils = Web3TestUtils(chain_config["rpc_url"])
            factory_tester = EscrowFactoryTester(
                web3_utils,
                self.config["contracts"]["escrow_factory"],
                load_escrow_factory_abi(),
            )
            health_checker = BlockchainHealthChecker(web3_utils)

            # Test 1: Check contract deployment
            if not health_checker.check_contract_deployment(
                self.config["contracts"]["escrow_factory"]
            ):
                self._print_result("Contract Deployment", False, "Factory contract not deployed")
                return False
            self._print_result("Contract Deployment", True, "Factory contract deployed")

            # Test 2: Check contract functionality
            if not health_checker.check_contract_functionality(factory_tester):
                self._print_result(
                    "Contract Functionality", False, "Contract functions not working"
                )
                return False
            self._print_result("Contract Functionality", True, "Contract functions working")

            # Test 3: Test escrow creation
            accounts = web3_utils.get_accounts()
            if not accounts:
                self._print_result("Escrow Creation", False, "No accounts available")
                return False

            payer = accounts[0]
            payee = accounts[1] if len(accounts) > 1 else accounts[0]
            amount = web3_utils.w3.to_wei(0.01, "ether")

            initial_count = factory_tester.get_escrow_count()

            # Create escrow
            receipt = factory_tester.create_escrow(
                payee=payee,
                release_delay=3600,
                approvals_required=2,
                arbiter="0x0000000000000000000000000000000000000000",
                from_account=payer,
                value=amount,
            )

            if receipt.status != 1:
                self._print_result("Escrow Creation", False, "Transaction failed")
                return False

            # Check escrow count increased
            final_count = factory_tester.get_escrow_count()
            if final_count != initial_count + 1:
                self._print_result(
                    "Escrow Creation",
                    False,
                    f"Count not increased: {initial_count} -> {final_count}",
                )
                return False

            # Check event was emitted
            events = factory_tester.get_escrow_deployed_events(
                from_block=receipt.blockNumber, to_block=receipt.blockNumber
            )

            if not events:
                self._print_result("Escrow Creation", False, "No EscrowDeployed event emitted")
                return False

            self._print_result(
                "Escrow Creation",
                True,
                f"Escrow created successfully, count: {final_count}",
            )

            return True

        except Exception as e:
            self._print_result("Web3 Contract Tests", False, str(e))
            return False

    def run_backend_tests(self) -> bool:
        """Run backend service tests."""
        self._print_info("Running backend service tests...")

        try:
            # Change to settlement service directory
            result = subprocess.run(
                ["poetry", "run", "pytest", "tests/", "-v"],
                cwd="services/settlement",
                capture_output=True,
                text=True,
                timeout=180,
            )

            if result.returncode == 0:
                self._print_result("Backend Tests", True, "All tests passed")
                return True
            else:
                self._print_result("Backend Tests", False, result.stderr)
                return False

        except subprocess.TimeoutExpired:
            self._print_result("Backend Tests", False, "Tests timed out")
            return False
        except Exception as e:
            self._print_result("Backend Tests", False, str(e))
            return False

    def run_integration_tests(self) -> bool:
        """Run integration tests."""
        self._print_info("Running integration tests...")

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "tests/scripts/run_local_tests.py",
                    "--category",
                    "quick",
                ],
                capture_output=True,
                text=True,
                timeout=240,
            )

            if result.returncode == 0:
                self._print_result("Integration Tests", True, "All tests passed")
                return True
            else:
                self._print_result("Integration Tests", False, result.stderr)
                return False

        except subprocess.TimeoutExpired:
            self._print_result("Integration Tests", False, "Tests timed out")
            return False
        except Exception as e:
            self._print_result("Integration Tests", False, str(e))
            return False

    def run_quick_validation(self) -> bool:
        """Run quick validation tests."""
        self._print_info("Running quick validation...")

        # Check services
        if not asyncio.run(self.check_services()):
            return False

        # Test contract interaction using Web3.py
        try:
            # Get chain configuration
            chain_config = self._get_chain_config()

            web3_utils = Web3TestUtils(chain_config["rpc_url"])
            factory_tester = EscrowFactoryTester(
                web3_utils,
                self.config["contracts"]["escrow_factory"],
                load_escrow_factory_abi(),
            )

            # Test contract call
            count = factory_tester.get_escrow_count()
            self._print_result(
                "Contract Interaction",
                True,
                f"Contract call successful, escrow count: {count}",
            )

            # Test blockchain connectivity
            block_number = web3_utils.get_block_number()
            self._print_result(
                "Blockchain Connectivity", True, f"Connected to block {block_number}"
            )

            # Test account availability
            accounts = web3_utils.get_accounts()
            if accounts:
                balance = web3_utils.get_balance(accounts[0])
                self._print_result(
                    "Account Availability",
                    True,
                    f"Account {accounts[0]} has {web3_utils.w3.from_wei(balance, 'ether')} ETH",
                )
            else:
                self._print_result("Account Availability", False, "No accounts available")
                return False

        except Exception as e:
            self._print_result("Contract Interaction", False, str(e))
            return False

        return True

    def run_tests(self, category: str) -> bool:
        """Run tests for specified category."""
        if category not in self.config["test_categories"]:
            print(f"❌ Unknown test category: {category}")
            return False

        category_config = self.config["test_categories"][category]
        self._print_header(f"{category_config['description']} ({category_config['duration']})")

        # Check services first
        if not asyncio.run(self.check_services()):
            self._print_warning("Some services not healthy, but continuing...")

        # Run tests based on category
        success = True

        if category == "quick":
            success = self.run_quick_validation()
        elif category == "local":
            success = (
                self.run_contract_tests()
                and self.run_backend_tests()
                and self.run_integration_tests()
            )
        elif category == "contracts":
            success = self.run_contract_tests()
        elif category == "backend":
            success = self.run_backend_tests()
        elif category == "integration":
            success = self.run_integration_tests()
        elif category == "e2e":
            success = self.run_integration_tests()  # E2E tests are part of integration

        return success

    def print_summary(self):
        """Print test summary."""
        self._print_header("TEST SUMMARY")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"⏭️  Skipped: {self.results['skipped']}")
        print(f"💥 Errors: {self.results['errors']}")

        total = (
            self.results["passed"]
            + self.results["failed"]
            + self.results["skipped"]
            + self.results["errors"]
        )
        if total > 0:
            success_rate = (self.results["passed"] / total) * 100
            print(f"📊 Success Rate: {success_rate:.1f}%")

        if self.results["failed"] == 0 and self.results["errors"] == 0:
            print("🎉 All tests completed successfully!")
        else:
            print("💥 Some tests failed. Check the output above.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Fusion Prime Test Runner")
    parser.add_argument(
        "category",
        choices=["quick", "local", "contracts", "backend", "integration", "e2e"],
        help="Test category to run",
    )
    parser.add_argument(
        "--config",
        default="tests/test_config.yaml",
        help="Path to test configuration file",
    )
    parser.add_argument("--environment", choices=["local", "testnet"], help="Environment to test")
    parser.add_argument(
        "--chain",
        choices=["ethereum", "base", "optimism", "arbitrum", "polygon"],
        help="Chain to test",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    runner = TestRunner(args.config, args.environment, args.chain)

    # Print environment info
    try:
        chain_config = runner._get_chain_config()
        print(f"🌍 Environment: {runner.environment}")
        print(f"⛓️  Chain: {runner.chain} (Chain ID: {chain_config.get('chain_id', 'N/A')})")
        print(f"🔗 Network: {chain_config.get('network', 'N/A')}")
        if "explorer" in chain_config:
            print(f"🔍 Explorer: {chain_config['explorer']}")
    except Exception as e:
        print(f"⚠️  Could not load chain configuration: {e}")

    try:
        success = runner.run_tests(args.category)
        runner.print_summary()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
