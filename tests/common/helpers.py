"""
Shared helper classes and utilities for integration tests.

This module provides common functionality used across all integration test modules,
including Docker Compose management, test helpers, and verification utilities.
"""

import asyncio
import json
import re
import subprocess
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import httpx
import psycopg2
from google.cloud import pubsub_v1
from psycopg2.extras import RealDictCursor
from web3 import Web3

# ============================================================================
# DOCKER COMPOSE MANAGEMENT UTILITIES
# ============================================================================


class DockerComposeManager:
    """Manages Docker Compose services for isolated testing."""

    @staticmethod
    def clean_environment():
        """Clean all Docker Compose services."""
        try:
            subprocess.run(
                ["docker", "compose", "down", "-v", "--remove-orphans"],
                cwd=".",
                check=True,
                capture_output=True,
                timeout=30,
            )
            print("✅ Cleaned Docker Compose environment")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Failed to clean environment: {e}")
        except subprocess.TimeoutExpired:
            print("⚠️ Clean environment timed out")

    @staticmethod
    def start_services(services: List[str]):
        """Start specific Docker Compose services."""
        try:
            cmd = ["docker", "compose", "up", "-d"] + services
            result = subprocess.run(
                cmd, cwd=".", check=True, capture_output=True, text=True, timeout=60
            )
            print(f"✅ Started services: {', '.join(services)}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to start services {services}: {e}")
            print(f"Error output: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            print(f"❌ Starting services {services} timed out")
            return False

    @staticmethod
    def check_services_running(services: List[str]) -> Dict[str, bool]:
        """Check which services are currently running."""
        running_services = {}
        try:
            result = subprocess.run(
                ["docker", "compose", "ps", "--format", "json"],
                cwd=".",
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and result.stdout.strip():
                containers = [
                    json.loads(line) for line in result.stdout.strip().split("\n") if line
                ]
                running_names = {
                    container["Name"] for container in containers if container["State"] == "running"
                }

                for service in services:
                    # Check if service is running (handle both service names and container names)
                    service_running = any(
                        service in name
                        or name.endswith(f"-{service}")
                        or name.startswith(f"fusion-prime-{service}")
                        for name in running_names
                    )
                    running_services[service] = service_running
            else:
                # If no containers found, assume none are running
                for service in services:
                    running_services[service] = False

        except Exception as e:
            print(f"ℹ️ Could not check running services: {e}")
            for service in services:
                running_services[service] = False

        return running_services

    @staticmethod
    def ensure_services_running(required_services: List[str]) -> bool:
        """Ensure required services are running, start them if needed."""
        running_services = DockerComposeManager.check_services_running(required_services)

        # Check if all required services are running
        all_running = all(running_services.get(service, False) for service in required_services)

        if all_running:
            print(f"✅ All required services already running: {required_services}")
            return True

        # Start missing services
        missing_services = [
            service for service in required_services if not running_services.get(service, False)
        ]
        print(f"ℹ️ Starting missing services: {missing_services}")

        return DockerComposeManager.start_services(missing_services)

    @staticmethod
    def wait_for_service(
        service_name: str,
        health_check_url: str,
        max_retries: int = 30,
        retry_delay: int = 2,
    ):
        """Wait for a service to be healthy."""
        import httpx
        import psycopg2
        from web3 import Web3

        for attempt in range(max_retries):
            try:
                if service_name == "anvil":
                    # Special handling for Anvil RPC service
                    w3 = Web3(Web3.HTTPProvider(health_check_url))
                    if w3.is_connected():
                        print(f"✅ Service {service_name} is healthy")
                        return True
                elif service_name == "postgres":
                    # Special handling for PostgreSQL database connection
                    conn = psycopg2.connect(
                        host="localhost",
                        port=5432,
                        database="fusion_prime",
                        user="fusion_prime",
                        password="fusion_prime_dev_pass",
                    )
                    conn.close()
                    print(f"✅ Service {service_name} is healthy")
                    return True
                else:
                    # Standard HTTP health check
                    with httpx.Client(timeout=5.0) as client:
                        response = client.get(health_check_url)
                        if response.status_code == 200:
                            print(f"✅ Service {service_name} is healthy")
                            return True
            except Exception as e:
                print(f"ℹ️ Attempt {attempt + 1}/{max_retries}: {service_name} not ready yet ({e})")

            time.sleep(retry_delay)

        print(f"❌ Service {service_name} failed to become healthy")
        return False

    @staticmethod
    def stop_services(services: List[str]):
        """Stop specific Docker Compose services."""
        try:
            cmd = ["docker", "compose", "stop"] + services
            subprocess.run(cmd, cwd=".", check=True, capture_output=True, timeout=30)
            print(f"✅ Stopped services: {', '.join(services)}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Failed to stop services {services}: {e}")


# ============================================================================
# TEST HELPER CLASSES
# ============================================================================


class RelayerVerificationHelper:
    """Helper class for verifying relayer event processing."""

    @staticmethod
    async def get_relayer_metrics() -> Dict[str, int]:
        """Get relayer metrics from logs."""
        try:
            logs_result = subprocess.run(
                ["docker", "logs", "--tail", "10", "fusion-prime-relayer"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if logs_result.returncode == 0:
                logs = logs_result.stdout
                metrics_match = re.search(
                    r"processed=(\d+), published=(\d+), last_block=(\d+)", logs
                )

                if metrics_match:
                    return {
                        "processed": int(metrics_match.group(1)),
                        "published": int(metrics_match.group(2)),
                        "last_block": int(metrics_match.group(3)),
                    }
        except Exception as e:
            print(f"ℹ️ Could not get relayer metrics: {e}")
        return {}

    @staticmethod
    async def wait_for_relayer_processing(
        initial_metrics: Dict[str, int],
        target_block: int,
        max_retries: int = 10,
        retry_delay: int = 2,
    ) -> Tuple[bool, Dict[str, int]]:
        """Wait for relayer to process events up to target block."""
        for attempt in range(max_retries):
            await asyncio.sleep(retry_delay)

            current_metrics = await RelayerVerificationHelper.get_relayer_metrics()
            current_processed = current_metrics.get("processed", 0)
            current_last_block = current_metrics.get("last_block", 0)

            print(
                f"ℹ️ Attempt {attempt + 1}: processed={current_processed}, last_block={current_last_block}"
            )

            if current_processed > initial_metrics.get("processed", 0):
                print(
                    f"✅ Relayer processed new events! Count increased from {initial_metrics.get('processed', 0)} to {current_processed}"
                )

                if current_last_block >= target_block:
                    print(
                        f"✅ Relayer processed up to block {current_last_block} (target was block {target_block})"
                    )
                    return True, current_metrics
                else:
                    print(f"ℹ️ Relayer processed events but not yet up to block {target_block}")
            else:
                print(f"ℹ️ No new events processed yet (still at {current_processed})")

        return False, current_metrics

    @staticmethod
    def check_relayer_logs_for_event(block_number: int) -> bool:
        """Check relayer logs for specific event processing."""
        try:
            logs_result = subprocess.run(
                ["docker", "logs", "--tail", "50", "fusion-prime-relayer"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if logs_result.returncode == 0:
                logs = logs_result.stdout
                event_patterns = [
                    r"Processed event.*EscrowDeployed",
                    r"Published event.*EscrowDeployed",
                    r"Processing block.*{}".format(block_number),
                    r"Event.*EscrowDeployed.*block.*{}".format(block_number),
                ]

                for pattern in event_patterns:
                    if re.search(pattern, logs, re.IGNORECASE):
                        print(f"✅ Found event processing in relayer logs: {pattern}")
                        return True

                print(f"ℹ️ No clear event processing found in logs for block {block_number}")
                print(f"ℹ️ Recent logs:\n{logs[-500:]}")
                return False
            else:
                print(f"ℹ️ Could not retrieve relayer logs: {logs_result.stderr}")
                return False

        except Exception as e:
            print(f"ℹ️ Could not check relayer logs: {e}")
            return False


class ContractTestHelper:
    """Helper class for contract testing operations."""

    @staticmethod
    def create_escrow_transaction(
        web3_client: Web3,
        escrow_factory_contract,
        payee: str = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        release_delay: int = 3600,
        approvals_required: int = 2,
        arbiter: str = "0x0000000000000000000000000000000000000000",
        amount_eth: float = 0.01,
    ) -> Tuple[str, Any]:
        """Create an escrow transaction with enhanced validation and gas optimization."""
        amount = web3_client.to_wei(amount_eth, "ether")
        sender = web3_client.eth.accounts[0]

        # Enhanced gas estimation (like remote tests)
        try:
            gas_estimate = escrow_factory_contract.functions.createEscrow(
                web3_client.to_checksum_address(payee),
                release_delay,
                approvals_required,
                web3_client.to_checksum_address(arbiter),
            ).estimate_gas({"from": sender, "value": amount})
            gas_limit = int(gas_estimate * 1.2)  # Add 20% buffer
            print(f"📋 Gas estimate: {gas_estimate}, using limit: {gas_limit}")
        except Exception as e:
            print(f"⚠️ Gas estimation failed: {e}, using default")
            gas_limit = 200000  # Fallback

        # Enhanced transaction with proper gas management
        tx_hash = escrow_factory_contract.functions.createEscrow(
            web3_client.to_checksum_address(payee),
            release_delay,
            approvals_required,
            web3_client.to_checksum_address(arbiter),
        ).transact({"from": sender, "value": amount, "gas": gas_limit})

        # Enhanced receipt validation with timeout
        receipt = web3_client.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        # Enhanced transaction validation
        assert receipt.status == 1, f"Transaction failed: {receipt}"
        assert receipt.transactionHash == tx_hash, "Transaction hash mismatch"

        # Verify gas efficiency
        gas_efficiency = receipt.gasUsed / gas_limit
        assert (
            gas_efficiency < 0.9
        ), f"Gas usage too high: {receipt.gasUsed}/{gas_limit} ({gas_efficiency:.2%})"

        print(
            f"✅ Transaction successful - Gas: {receipt.gasUsed}/{gas_limit} ({gas_efficiency:.1%})"
        )
        return tx_hash, receipt

    @staticmethod
    def verify_escrow_event(escrow_factory_contract, receipt) -> Dict[str, Any]:
        """Verify that EscrowDeployed event was emitted with enhanced validation."""
        events = escrow_factory_contract.events.EscrowDeployed.get_logs(
            from_block=receipt.blockNumber, to_block=receipt.blockNumber
        )
        assert len(events) == 1, f"Expected 1 EscrowDeployed event, got {len(events)}"

        event = events[0]

        # Enhanced event validation
        assert (
            event["args"]["escrow"] != "0x0000000000000000000000000000000000000000"
        ), "Escrow address should be valid"
        assert event["args"]["amount"] > 0, "Amount should be positive"
        assert event["args"]["releaseDelay"] > 0, "Release delay should be positive"
        assert event["args"]["approvalsRequired"] >= 1, "Approvals required should be at least 1"
        assert event["args"]["approvalsRequired"] <= 3, "Approvals required should be at most 3"

        print(
            f"✅ Event validated - Escrow: {event['args']['escrow']}, Amount: {event['args']['amount']}"
        )
        return event

    @staticmethod
    def advance_blockchain_time(web3_client: Web3, seconds: int) -> None:
        """Advance blockchain time by the specified number of seconds using Anvil RPC."""
        try:
            # Use Anvil's evm_increaseTime RPC method
            web3_client.manager.request_blocking("evm_increaseTime", [hex(seconds)])
            # Mine a new block to apply the time change
            web3_client.manager.request_blocking("evm_mine", [])
        except Exception as e:
            raise Exception(f"Failed to advance blockchain time: {e}")

    @staticmethod
    def get_current_block_timestamp(web3_client: Web3) -> int:
        """Get the current blockchain timestamp."""
        latest_block = web3_client.eth.get_block("latest")
        return latest_block.timestamp


class PubSubTestHelper:
    """Helper class for Pub/Sub testing operations."""

    @staticmethod
    def setup_pubsub_environment():
        """Set up Pub/Sub emulator environment."""
        import os

        os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"
        return pubsub_v1.PublisherClient(), pubsub_v1.SubscriberClient()

    @staticmethod
    def create_topic_and_subscription(
        publisher,
        subscriber,
        project_id: str = "fusion-prime-local",
        topic_name: str = "settlement.events.v1",
        subscription_name: str = "test-subscription",
    ) -> Tuple[str, str]:
        """Create topic and subscription for testing."""
        topic_path = publisher.topic_path(project_id, topic_name)
        subscription_path = subscriber.subscription_path(project_id, subscription_name)

        # Create topic if it doesn't exist
        try:
            publisher.create_topic(request={"name": topic_path})
        except Exception:
            pass

        # Create subscription if it doesn't exist
        try:
            subscriber.create_subscription(request={"name": subscription_path, "topic": topic_path})
        except Exception:
            pass

        return topic_path, subscription_path

    @staticmethod
    def publish_test_message(publisher, topic_path: str, message_data: Dict[str, Any]) -> str:
        """Publish a test message to Pub/Sub."""
        future = publisher.publish(
            topic_path,
            json.dumps(message_data).encode("utf-8"),
            event_type=message_data.get("event_type", "EscrowDeployed"),
            chain_id=message_data.get("chain_id", "31337"),
        )
        return future.result(timeout=10)

    @staticmethod
    def consume_test_message(
        subscriber, subscription_path: str, max_messages: int = 1
    ) -> List[Dict[str, Any]]:
        """Consume messages from Pub/Sub subscription."""
        response = subscriber.pull(
            request={
                "subscription": subscription_path,
                "max_messages": max_messages,
            },
            timeout=5.0,
        )

        messages = []
        for received_message in response.received_messages:
            message_data = json.loads(received_message.message.data.decode("utf-8"))
            messages.append({"data": message_data, "ack_id": received_message.ack_id})

        return messages


class DatabaseTestHelper:
    """Helper class for database testing operations."""

    @staticmethod
    def get_db_connection():
        """Get database connection for testing."""
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            database="fusion_prime",
            user="fusion_prime",
            password="fusion_prime_dev_pass",
        )
        conn.autocommit = True
        return conn

    @staticmethod
    def insert_test_command(
        cursor,
        command_id: str,
        workflow_id: str = "test-workflow",
        account_ref: str = "test-account",
        payer: str = "0xf39Fd6e51aad88F6f4ce6aB8827279cffFb92266",
        payee: str = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
        amount_numeric: int = 1000000000000000000,
        status: str = "RECEIVED",
    ):
        """Insert a test settlement command."""
        cursor.execute(
            """
            INSERT INTO settlement_commands
            (command_id, workflow_id, account_ref, payer, payee, amount_numeric, status, last_updated)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """,
            (
                command_id,
                workflow_id,
                account_ref,
                payer,
                payee,
                amount_numeric,
                status,
            ),
        )

    @staticmethod
    def query_test_command(cursor, command_id: str) -> Optional[Dict[str, Any]]:
        """Query a test settlement command."""
        cursor.execute(
            """
            SELECT command_id, workflow_id, account_ref, payer, payee, amount_numeric, status
            FROM settlement_commands
            WHERE command_id = %s
        """,
            (command_id,),
        )
        result = cursor.fetchone()
        if result:
            # Convert tuple to dictionary
            columns = [
                "command_id",
                "workflow_id",
                "account_ref",
                "payer",
                "payee",
                "amount_numeric",
                "status",
            ]
            return dict(zip(columns, result))
        return None

    @staticmethod
    def cleanup_test_command(cursor, command_id: str):
        """Clean up test settlement command."""
        cursor.execute("DELETE FROM settlement_commands WHERE command_id = %s", (command_id,))


class ContainerHealthHelper:
    """Helper class for container health checks."""

    @staticmethod
    def check_container_running(container_name: str) -> Optional[Dict[str, str]]:
        """Check if a Docker container is running."""
        try:
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    f"name={container_name}",
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and result.stdout.strip():
                containers = [
                    json.loads(line) for line in result.stdout.strip().split("\n") if line
                ]
                if containers:
                    container = containers[0]
                    return {
                        "id": container["ID"][:12],
                        "state": container["State"],
                        "name": container["Names"],
                    }
        except Exception as e:
            print(f"ℹ️ Could not check container {container_name}: {e}")
        return None

    @staticmethod
    def get_container_logs(container_name: str, tail: int = 10) -> str:
        """Get recent container logs."""
        try:
            logs_result = subprocess.run(
                ["docker", "logs", "--tail", str(tail), container_name],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if logs_result.returncode == 0:
                return logs_result.stdout
        except Exception as e:
            print(f"ℹ️ Could not get logs for {container_name}: {e}")
        return ""


# ============================================================================
# COMMON FIXTURES AND UTILITIES
# ============================================================================


def deploy_contracts():
    """Deploy smart contracts to Anvil."""
    try:
        import os
        import subprocess

        # Get the project root directory (two levels up from tests/common)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        contracts_dir = os.path.join(project_root, "contracts")

        # First, fund the deployer account
        print("ℹ️ Funding deployer account...")
        fund_result = subprocess.run(
            [
                "cast",
                "send",
                "--private-key",
                "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
                "0xe1fc045daBb45b78fC2D48D32086E4a0b11ca6eA",
                "--value",
                "1ether",
                "--rpc-url",
                "http://localhost:8545",
            ],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        print("✅ Deployer account funded")

        # Deploy EscrowFactory contract
        print("ℹ️ Deploying contracts...")
        # Use Anvil's default private key (first account)
        anvil_private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
        result = subprocess.run(
            [
                "forge",
                "script",
                "script/DeployMultichain.s.sol:DeployMultichain",
                "--rpc-url",
                "http://localhost:8545",
                "--broadcast",
                "--private-key",
                anvil_private_key,
            ],
            cwd=contracts_dir,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        print("✅ Smart contracts deployed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to deploy contracts: {e}")
        print(f"Error output: {e.stderr}")
        raise
    except subprocess.TimeoutExpired:
        print("❌ Contract deployment timed out")
        raise


def get_escrow_factory_contract(web3_client: Web3):
    """Get deployed EscrowFactory contract."""
    try:
        with open("contracts/deployments/31337-unknown.json", "r") as f:
            deployment_data = json.load(f)
            factory_address = deployment_data["escrowFactory"]
    except FileNotFoundError:
        factory_address = "0x3481dbE036C0F4076B397e27FFb8dC32B88d8882"

    abi = [
        {
            "inputs": [
                {"internalType": "address", "name": "payee", "type": "address"},
                {"internalType": "uint256", "name": "releaseDelay", "type": "uint256"},
                {"internalType": "uint8", "name": "approvalsRequired", "type": "uint8"},
                {"internalType": "address", "name": "arbiter", "type": "address"},
            ],
            "name": "createEscrow",
            "outputs": [{"internalType": "address", "name": "escrow", "type": "address"}],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "payee", "type": "address"},
                {"internalType": "uint256", "name": "releaseDelay", "type": "uint256"},
                {"internalType": "uint8", "name": "approvalsRequired", "type": "uint8"},
                {"internalType": "address", "name": "arbiter", "type": "address"},
                {"internalType": "bytes32", "name": "salt", "type": "bytes32"},
            ],
            "name": "createEscrowDeterministic",
            "outputs": [{"internalType": "address", "name": "escrow", "type": "address"}],
            "stateMutability": "payable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "payer", "type": "address"},
                {"internalType": "address", "name": "payee", "type": "address"},
                {"internalType": "uint256", "name": "releaseDelay", "type": "uint256"},
                {"internalType": "uint8", "name": "approvalsRequired", "type": "uint8"},
                {"internalType": "address", "name": "arbiter", "type": "address"},
                {"internalType": "bytes32", "name": "salt", "type": "bytes32"},
            ],
            "name": "computeEscrowAddress",
            "outputs": [{"internalType": "address", "name": "predicted", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "anonymous": False,
            "inputs": [
                {"indexed": True, "name": "escrow", "type": "address"},
                {"indexed": True, "name": "payer", "type": "address"},
                {"indexed": True, "name": "payee", "type": "address"},
                {"indexed": False, "name": "amount", "type": "uint256"},
                {"indexed": False, "name": "releaseDelay", "type": "uint256"},
                {"indexed": False, "name": "approvalsRequired", "type": "uint8"},
            ],
            "name": "EscrowDeployed",
            "type": "event",
        },
    ]
    return web3_client.eth.contract(address=factory_address, abi=abi)
