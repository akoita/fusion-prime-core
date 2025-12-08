"""
Escrow Creation Workflow Test (Environment-Agnostic)

This test works identically in local, testnet, and production environments.
Only the configuration differs - test logic is the same.
"""

import json

from tests.workflows.base_workflow_test import BaseWorkflowTest


class EscrowCreationWorkflow(BaseWorkflowTest):
    """
    Environment-agnostic escrow creation workflow test.

    Works with:
    - Local Anvil blockchain
    - Sepolia testnet
    - Ethereum mainnet (if configured)
    """

    def test_escrow_creation_workflow(self):
        """
        Test complete escrow creation workflow.

        Validates:
        1. Smart Contract: Create REAL escrow on blockchain
        2. Blockchain: Verify EscrowDeployed event emission
        3. Relayer: Capture event and publish to Pub/Sub
        4. Settlement: Process event and update database
        5. Risk: Calculate risk for new escrow
        6. Compliance: Perform KYC/AML checks

        Environment-agnostic - runs on local/testnet/production.
        """
        print(f"🔄 Testing escrow creation workflow...")

        self.skip_if_no_private_key()
        self.skip_if_no_factory()

        test_id = self.create_test_id("escrow-creation")

        print(f"\n🔬 Test Run ID: {test_id}")
        print("=" * 60)

        try:
            # ==================================================================
            # STEP 1: Create REAL Escrow on Blockchain
            # ==================================================================
            print("\n1️⃣  BLOCKCHAIN - Create Escrow Transaction")
            print("-" * 60)

            # Test parameters
            payee = self.payee_address
            release_delay = 3600
            approvals_required = 2
            arbiter = "0x0000000000000000000000000000000000000000"
            amount = self.web3.to_wei(0.001, "ether")

            payer_address = self.web3.eth.account.from_key(self.payer_private_key).address
            balance = self.web3.eth.get_balance(payer_address)

            print(f"📊 Payer: {payer_address}")
            print(f"💰 Balance: {self.web3.from_wei(balance, 'ether')} ETH")
            print(f"💸 Amount: {self.web3.from_wei(amount, 'ether')} ETH")
            print(f"🌐 Environment: {self.environment.value}")

            if balance < amount:
                print(f"⚠️  Insufficient balance: {self.web3.from_wei(balance, 'ether')} ETH")
                print(f"   Required: {self.web3.from_wei(amount, 'ether')} ETH")
                pytest.skip(f"Insufficient balance for transaction in {self.environment.value}")

            # Build transaction
            nonce = self.web3.eth.get_transaction_count(payer_address)
            gas_price = self.web3.eth.gas_price

            try:
                gas_estimate = self.factory_contract.functions.createEscrow(
                    payee, release_delay, approvals_required, arbiter
                ).estimate_gas({"from": payer_address, "value": amount})
                gas_limit = int(gas_estimate * 1.2)
                print(f"⛽ Gas estimate: {gas_estimate}, using limit: {gas_limit}")
            except Exception as e:
                print(f"⚠️  Gas estimation: {e}, using default")
                gas_limit = 1500000

            transaction = self.factory_contract.functions.createEscrow(
                payee, release_delay, approvals_required, arbiter
            ).build_transaction(
                {
                    "from": payer_address,
                    "value": amount,
                    "gas": gas_limit,
                    "gasPrice": gas_price,
                    "nonce": nonce,
                }
            )

            # Sign and send transaction
            signed_txn = self.web3.eth.account.sign_transaction(transaction, self.payer_private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_hash_hex = tx_hash.hex()

            print(f"📤 Transaction sent: {tx_hash_hex}")
            if self.config.blockchain.explorer:
                print(f"🔗 Explorer: {self.config.blockchain.explorer}/tx/{tx_hash_hex}")

            # Wait for confirmation
            print(f"⏳ Waiting for confirmation...")
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            assert receipt.status == 1, f"Transaction failed: {receipt}"

            print(f"✅ Transaction confirmed in block: {receipt.blockNumber}")
            print(f"   Gas used: {receipt.gasUsed}")

            # ==================================================================
            # STEP 2: Verify Event Emission
            # ==================================================================
            print("\n2️⃣  BLOCKCHAIN - Verify EscrowDeployed Event")
            print("-" * 60)

            # Extract escrow address from logs
            escrow_address = None
            event_data = None

            for log in receipt.logs:
                if log.address == self.factory_address:
                    try:
                        decoded = self.factory_contract.events.EscrowDeployed().process_log(log)
                        escrow_address = decoded["args"]["escrow"]
                        event_data = decoded["args"]
                        break
                    except:
                        continue

            assert escrow_address, "EscrowDeployed event not found in transaction logs"

            print(f"✅ EscrowDeployed event emitted")
            print(f"   Escrow address: {escrow_address}")
            print(f"   Payer: {event_data.get('payer', 'N/A')}")
            print(f"   Payee: {event_data.get('payee', 'N/A')}")
            print(f"   Amount: {self.web3.from_wei(event_data.get('amount', 0), 'ether')} ETH")

            if self.config.blockchain.explorer:
                print(f"🔗 Explorer: {self.config.blockchain.explorer}/address/{escrow_address}")

            # ==================================================================
            # STEP 3: Wait for Relayer Processing
            # ==================================================================
            print("\n3️⃣  RELAYER - Event Capture & Pub/Sub Publishing")
            print("-" * 60)

            self.wait_for_relayer_processing("EscrowDeployed event")
            print(f"   Event should be published to Pub/Sub topic")

            # ==================================================================
            # STEP 4: Verify Settlement Service
            # ==================================================================
            print("\n4️⃣  SETTLEMENT SERVICE - Event Processing & Database")
            print("-" * 60)

            self.verify_settlement_service(escrow_address, test_id)

            # ==================================================================
            # STEP 5: Verify Risk Engine
            # ==================================================================
            print("\n5️⃣  RISK ENGINE - Portfolio Risk Assessment")
            print("-" * 60)

            portfolio_data = {
                "user_id": payer_address,
                "account_ref": test_id,
                "positions": [
                    {
                        "asset": "ETH",
                        "amount": float(self.web3.from_wei(amount, "ether")),
                        "escrow_address": escrow_address,
                        "status": "locked",
                    }
                ],
                "reference_tx": tx_hash_hex,
            }

            self.verify_risk_engine(portfolio_data)

            # ==================================================================
            # STEP 6: Verify Compliance Service
            # ==================================================================
            print("\n6️⃣  COMPLIANCE SERVICE - KYC/AML Validation")
            print("-" * 60)

            compliance_data = {
                "user_id": payer_address,
                "transaction_type": "escrow_creation",
                "payer_address": payer_address,
                "payee_address": payee,
                "amount": str(self.web3.from_wei(amount, "ether")),
                "asset": "ETH",
                "transaction_hash": tx_hash_hex,
                "escrow_address": escrow_address,
            }

            self.verify_compliance_service(compliance_data)

            # ==================================================================
            # FINAL VALIDATION
            # ==================================================================
            self.print_test_summary(
                "Escrow Creation Workflow",
                {
                    "Environment": self.environment.value,
                    "Network": self.network,
                    "Escrow Address": escrow_address,
                    "Transaction": tx_hash_hex,
                    "Block": receipt.blockNumber,
                    "Amount": f"{self.web3.from_wei(amount, 'ether')} ETH",
                },
            )

        except Exception as e:
            print(f"\n❌ Escrow creation workflow failed: {e}")
            import traceback

            traceback.print_exc()
            raise
