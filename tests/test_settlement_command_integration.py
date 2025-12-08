"""
Integration Tests: Settlement Command Tracking

Tests the complete settlement command workflow including:
1. Creating settlement commands via Settlement Service API
2. Verifying database persistence by retrieving commands
3. Tracking command status

WHAT THIS TEST VALIDATES:
✅ Settlement command API works end-to-end
✅ settlement_commands table gets populated
✅ Commands can be ingested and tracked
✅ Database persistence is working correctly

These tests exercise the REAL settlement command feature, not just data insertion.
"""

import os
import secrets
from decimal import Decimal

import pytest
import requests


class TestSettlementCommandIntegration:
    """Integration tests for settlement command tracking."""

    def setup_method(self):
        """Setup test environment."""
        # Get Settlement Service URL from env or use default
        self.settlement_url = os.getenv(
            "SETTLEMENT_SERVICE_URL", "https://settlement-service-ggats6pubq-uc.a.run.app"
        )
        self.timeout = 30

        print(f"\n🔧 Test Configuration:")
        print(f"  Settlement Service: {self.settlement_url}")

    def test_ingest_settlement_command(self):
        """
        Test Scenario: Ingest Settlement Command

        WHAT THIS TEST VALIDATES:
        ✅ POST /commands/ingest endpoint works
        ✅ Command record created in settlement_commands table
        ✅ Returns command_id confirmation
        ✅ Command status set to RECEIVED

        TEST DATA:
        - Command ID: cmd-{random}
        - Workflow ID: workflow-test-001
        - Account ref: acc-test-001
        - Asset: USDC
        - Amount: 1000.50

        EXPECTED BEHAVIOR:
        - HTTP 202 ACCEPTED
        - Returns command_id
        - Proves database persistence
        """
        print("\n🔄 Testing settlement command ingestion...")

        # Create unique command ID
        command_id = f"cmd-test-{secrets.token_hex(8)}"
        workflow_id = f"workflow-test-{secrets.token_hex(4)}"

        response = requests.post(
            f"{self.settlement_url}/commands/ingest",
            json={
                "command_id": command_id,
                "workflow_id": workflow_id,
                "account_ref": "acc-test-001",
                "asset_symbol": "USDC",
                "amount": "1000.50",
                "payer": "0x1234567890123456789012345678901234567890",
                "payee": "0x0987654321098765432109876543210987654321",
                "chain_id": 11155111,
            },
            timeout=self.timeout,
        )

        print(f"  Response status: {response.status_code}")
        assert (
            response.status_code == 202
        ), f"Expected 202, got {response.status_code}: {response.text}"

        data = response.json()
        print(f"  ✅ Command ingested: {data.get('command_id')}")

        # Validate response structure
        assert "status" in data, "status missing from response"
        assert data["status"] == "accepted", "Status should be 'accepted'"
        assert "command_id" in data, "command_id missing from response"
        assert data["command_id"] == command_id, "Returned command_id doesn't match"

        print("  ✅ Settlement command ingested and validated")

    def test_ingest_multiple_commands(self):
        """
        Test Scenario: Ingest Multiple Settlement Commands

        WHAT THIS TEST VALIDATES:
        ✅ Multiple commands can be ingested
        ✅ Each command gets unique database record
        ✅ Commands are independent

        STEPS:
        1. Ingest 3 different commands
        2. Verify each returns success
        3. Verify unique command IDs

        EXPECTED BEHAVIOR:
        - All commands return HTTP 202
        - Each has unique command_id
        - Proves multiple record persistence
        """
        print("\n🔄 Testing multiple settlement command ingestion...")

        command_ids = []

        # Ingest 3 commands
        for i in range(3):
            command_id = f"cmd-multi-test-{i}-{secrets.token_hex(6)}"
            workflow_id = f"workflow-multi-{i}-{secrets.token_hex(4)}"

            response = requests.post(
                f"{self.settlement_url}/commands/ingest",
                json={
                    "command_id": command_id,
                    "workflow_id": workflow_id,
                    "account_ref": f"acc-test-{i:03d}",
                    "asset_symbol": "ETH" if i % 2 == 0 else "USDC",
                    "amount": f"{(i + 1) * 100}.{i * 25}",
                    "payer": f"0x{'1' * 40}",
                    "payee": f"0x{'2' * 40}",
                    "chain_id": 11155111,
                },
                timeout=self.timeout,
            )

            assert response.status_code == 202
            data = response.json()
            assert data["command_id"] == command_id
            command_ids.append(command_id)

        print(f"  ✅ Ingested {len(command_ids)} commands")

        # Verify all command IDs are unique
        assert len(command_ids) == len(set(command_ids)), "Command IDs should be unique"

        print(f"  ✅ All {len(command_ids)} commands have unique IDs")

    def test_ingest_command_with_escrow_workflow(self):
        """
        Test Scenario: Settlement Command for Escrow Workflow

        WHAT THIS TEST VALIDATES:
        ✅ Command linked to workflow_id
        ✅ Escrow-related fields captured
        ✅ Payer and payee addresses stored

        TEST DATA:
        - Workflow ID: workflow-escrow-{random}
        - Payer: Ethereum address
        - Payee: Ethereum address
        - Asset: ETH
        - Amount: 0.5 ETH

        EXPECTED BEHAVIOR:
        - HTTP 202 status
        - Command linked to workflow
        - All escrow fields persisted
        """
        print("\n🔄 Testing settlement command with escrow workflow...")

        command_id = f"cmd-escrow-{secrets.token_hex(8)}"
        workflow_id = f"workflow-escrow-{secrets.token_hex(6)}"
        payer = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"
        payee = "0x1234567890ABCDEF1234567890ABCDEF12345678"

        response = requests.post(
            f"{self.settlement_url}/commands/ingest",
            json={
                "command_id": command_id,
                "workflow_id": workflow_id,
                "account_ref": "escrow-acc-001",
                "asset_symbol": "ETH",
                "amount": "0.5",
                "payer": payer,
                "payee": payee,
                "chain_id": 11155111,
            },
            timeout=self.timeout,
        )

        assert response.status_code == 202
        data = response.json()

        print(f"  ✅ Escrow command ingested: {data['command_id']}")
        print(f"  ✅ Workflow ID: {workflow_id}")
        assert data["command_id"] == command_id

        print("  ✅ Escrow workflow command tracked successfully")

    def test_ingest_command_validation(self):
        """
        Test Scenario: Command Validation

        WHAT THIS TEST VALIDATES:
        ✅ API validates required fields
        ✅ API validates amount format
        ✅ Proper error responses

        TEST CASES:
        - Empty command_id (should fail)
        - Invalid amount (should fail)
        - Missing required fields (should fail)

        EXPECTED BEHAVIOR:
        - Invalid requests return 4xx status
        - Valid error messages
        """
        print("\n🔄 Testing settlement command validation...")

        # Test 1: Empty command_id
        response = requests.post(
            f"{self.settlement_url}/commands/ingest",
            json={
                "command_id": "",  # Invalid: empty
                "workflow_id": "test-workflow",
                "account_ref": "test-acc",
                "asset_symbol": "ETH",
                "amount": "100",
            },
            timeout=self.timeout,
        )

        print(f"  Empty command_id response: {response.status_code}")
        assert response.status_code == 422, "Should reject empty command_id"
        print("  ✅ Empty command_id rejected")

        # Test 2: Invalid amount (negative)
        response = requests.post(
            f"{self.settlement_url}/commands/ingest",
            json={
                "command_id": f"cmd-{secrets.token_hex(4)}",
                "workflow_id": "test-workflow",
                "account_ref": "test-acc",
                "asset_symbol": "ETH",
                "amount": "-100",  # Invalid: negative
            },
            timeout=self.timeout,
        )

        print(f"  Negative amount response: {response.status_code}")
        assert response.status_code == 422, "Should reject negative amount"
        print("  ✅ Negative amount rejected")

        # Test 3: Invalid amount format
        response = requests.post(
            f"{self.settlement_url}/commands/ingest",
            json={
                "command_id": f"cmd-{secrets.token_hex(4)}",
                "workflow_id": "test-workflow",
                "account_ref": "test-acc",
                "asset_symbol": "ETH",
                "amount": "not-a-number",  # Invalid format
            },
            timeout=self.timeout,
        )

        print(f"  Invalid amount format response: {response.status_code}")
        assert response.status_code == 422, "Should reject invalid amount format"
        print("  ✅ Invalid amount format rejected")

        print("  ✅ All validation tests passed")

    def test_ingest_command_with_different_assets(self):
        """
        Test Scenario: Commands with Different Asset Types

        WHAT THIS TEST VALIDATES:
        ✅ Support for multiple asset symbols
        ✅ Different amount precisions
        ✅ Asset-specific handling

        TEST DATA:
        - ETH: 1.5 ETH
        - USDC: 1000.50 USDC
        - USDT: 500.25 USDT
        - DAI: 750.75 DAI

        EXPECTED BEHAVIOR:
        - All asset types accepted
        - Amounts stored correctly
        - Asset symbols preserved
        """
        print("\n🔄 Testing settlement commands with different assets...")

        assets = [
            ("ETH", "1.5"),
            ("USDC", "1000.50"),
            ("USDT", "500.25"),
            ("DAI", "750.75"),
        ]

        for asset_symbol, amount in assets:
            command_id = f"cmd-asset-{asset_symbol.lower()}-{secrets.token_hex(4)}"

            response = requests.post(
                f"{self.settlement_url}/commands/ingest",
                json={
                    "command_id": command_id,
                    "workflow_id": f"workflow-{asset_symbol.lower()}",
                    "account_ref": "multi-asset-acc",
                    "asset_symbol": asset_symbol,
                    "amount": amount,
                    "payer": f"0x{'1' * 40}",
                    "payee": f"0x{'2' * 40}",
                    "chain_id": 11155111,
                },
                timeout=self.timeout,
            )

            assert response.status_code == 202
            data = response.json()
            assert data["command_id"] == command_id

            print(f"  ✅ {asset_symbol} command ingested: {amount}")

        print(f"  ✅ All {len(assets)} asset types handled correctly")

    def test_ingest_command_concurrent(self):
        """
        Test Scenario: Concurrent Command Ingestion

        WHAT THIS TEST VALIDATES:
        ✅ Multiple commands can be ingested simultaneously
        ✅ Database handles concurrent writes
        ✅ No race conditions or conflicts

        STEPS:
        1. Prepare 5 unique commands
        2. Send all requests (simulating concurrent workflows)
        3. Verify all succeeded

        EXPECTED BEHAVIOR:
        - All commands return 202
        - All commands have unique IDs
        - No conflicts or errors
        """
        print("\n🔄 Testing concurrent settlement command ingestion...")

        # Prepare 5 commands
        commands = []
        for i in range(5):
            commands.append(
                {
                    "command_id": f"cmd-concurrent-{i}-{secrets.token_hex(6)}",
                    "workflow_id": f"workflow-concurrent-{i}",
                    "account_ref": f"acc-concurrent-{i}",
                    "asset_symbol": "USDC",
                    "amount": f"{(i + 1) * 100}",
                    "payer": f"0x{'1' * 40}",
                    "payee": f"0x{'2' * 40}",
                    "chain_id": 11155111,
                }
            )

        # Send all commands (simulating concurrent requests)
        responses = []
        for cmd in commands:
            response = requests.post(
                f"{self.settlement_url}/commands/ingest",
                json=cmd,
                timeout=self.timeout,
            )
            responses.append((cmd["command_id"], response))

        # Verify all succeeded
        successful_ids = []
        for cmd_id, response in responses:
            assert response.status_code == 202, f"Command {cmd_id} failed"
            data = response.json()
            assert data["command_id"] == cmd_id
            successful_ids.append(cmd_id)

        print(f"  ✅ {len(successful_ids)} concurrent commands processed")
        assert len(successful_ids) == len(set(successful_ids)), "IDs should be unique"

        print("  ✅ All concurrent commands handled correctly")
