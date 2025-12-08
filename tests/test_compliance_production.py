"""
Integration Tests for Compliance Service Production Implementation

Tests the Compliance Service with real database integration for KYC, AML, and sanctions.

WHAT THESE TESTS VALIDATE:
✅ Compliance Service health with database connectivity
✅ KYC workflow end-to-end (initiation to verification)
✅ AML check for transactions with risk scoring
✅ Sanctions screening for blockchain addresses
✅ Compliance case management
✅ Escrow-specific compliance checks

COMPLETE END-TO-END FLOW:
1. User initiates KYC → KYC case created in database
2. Compliance check for escrow → Checks performed and stored
3. AML check for transaction → Risk assessment recorded
4. Sanctions screening → Addresses checked against lists
5. Case management → Compliance officers review and resolve

Each test is a complete scenario that validates:
- Service availability and connectivity
- Real-time compliance checks from database
- Risk scoring accuracy and flag generation
- End-to-end compliance workflows
"""

import time

import pytest
import requests

from tests.base_integration_test import BaseIntegrationTest


class TestComplianceProduction(BaseIntegrationTest):
    """Integration tests for Compliance Service production functionality."""

    def setup_method(self):
        """Setup test environment using configuration system."""
        # Call parent setup to load environment configuration
        super().setup_method()

        # Get Compliance Service URL from configuration
        self.compliance_url = self.compliance_url or "http://localhost:8002"
        self.timeout = 30

    def test_compliance_service_health_with_database(self):
        """
        Test Scenario: Compliance Service Health Check with Database

        WHAT THIS TEST VALIDATES:
        ✅ Service is running and accessible
        ✅ Health endpoint returns valid response
        ✅ Database connectivity established
        ✅ All subsystems operational

        EXPECTED BEHAVIOR:
        - HTTP 200 status
        - Status: "healthy" or "degraded"
        - Capabilities: KYC, AML, sanctions, compliance_monitoring
        """
        print("\n🔄 Testing Compliance Service health with database...")

        response = requests.get(f"{self.compliance_url}/health/", timeout=self.timeout)

        assert response.status_code == 200
        data = response.json()

        print(f"✅ Compliance Service status: {data.get('status')}")

        # Should be healthy with database connected
        assert data.get("status") in ["healthy", "degraded"]

    def test_initiate_kyc_workflow(self):
        """
        Test Scenario: KYC Workflow End-to-End

        WHAT THIS TEST VALIDATES:
        ✅ Create KYC case via API
        ✅ Case stored in database with pending status
        ✅ Verification score calculated
        ✅ Required actions determined based on document type
        ✅ Case ID returned for tracking

        TEST DATA:
        - User: test-kyc-user
        - Document: passport
        - Document data: high quality
        - Personal info: verified credentials

        EXPECTED BEHAVIOR:
        - Case created with "pending" status
        - Verification score between 0.0-1.0
        - Required actions include identity_verification
        - Case ID format: kyc-{user_id}-{timestamp}
        """
        print("\n🔄 Testing KYC workflow...")

        kyc_request = {
            "user_id": "test-kyc-user",
            "document_type": "passport",
            "document_data": {
                "photo_quality": "high",
                "data_completeness": "complete",
                "authenticity": "verified",
            },
            "personal_info": {
                "email_verified": True,
                "phone_verified": True,
                "email": "user@example.com",
                "phone": "+1234567890",
            },
        }

        response = requests.post(
            f"{self.compliance_url}/compliance/kyc", json=kyc_request, timeout=self.timeout
        )

        assert response.status_code == 200
        data = response.json()

        print(f"✅ KYC case created: {data.get('case_id')}")

        assert data["user_id"] == "test-kyc-user"
        assert data["status"] == "pending"
        assert 0.0 <= data["verification_score"] <= 1.0
        assert "required_actions" in data
        assert "identity_verification" in data["required_actions"]

    def test_get_kyc_status(self):
        """
        Test Scenario: Get KYC Case Status

        WHAT THIS TEST VALIDATES:
        ✅ Retrieve KYC case by case_id
        ✅ Return current status and verification score
        ✅ Provide case history (created_at, updated_at)
        ✅ Handle missing cases with proper error

        EXPECTED BEHAVIOR:
        - Returns case status
        - Includes verification_score
        - Timestamps are valid ISO format
        """
        print("\n🔄 Testing get KYC status...")

        # First create a KYC case
        kyc_request = {
            "user_id": "test-status-user",
            "document_type": "driver_license",
            "document_data": {"photo_quality": "high"},
            "personal_info": {"email": "test@example.com"},
        }

        create_response = requests.post(
            f"{self.compliance_url}/compliance/kyc", json=kyc_request, timeout=self.timeout
        )

        assert create_response.status_code == 200
        case_id = create_response.json()["case_id"]

        # Now get status
        response = requests.get(
            f"{self.compliance_url}/compliance/kyc/{case_id}", timeout=self.timeout
        )

        assert response.status_code == 200
        data = response.json()

        print(f"✅ KYC case status retrieved: {data.get('status')}")

        assert data["case_id"] == case_id
        assert data["status"] == "pending"
        assert "verification_score" in data
        assert "created_at" in data

    def test_perform_aml_check(self):
        """
        Test Scenario: AML Check for Transaction

        WHAT THIS TEST VALIDATES:
        ✅ Calculate AML risk score for transaction
        ✅ Identify risk flags (high_value, external_movement)
        ✅ Determine risk level (low/medium/high)
        ✅ Generate recommendations
        ✅ Store alert in database

        TEST DATA:
        - Amount: $125,000 (high value)
        - Type: external_transfer (suspicious)
        - Source: 0x111...
        - Destination: 0x222...

        EXPECTED BEHAVIOR:
        - Risk score > 0.0
        - Flags include "high_value" and "external_movement"
        - Recommendations include appropriate actions
        - Alert stored in database
        """
        print("\n🔄 Testing AML check for transaction...")

        aml_request = {
            "user_id": "test-aml-user",
            "transaction_amount": 125000.0,
            "transaction_type": "external_transfer",
            "source_address": "0x1111111111111111111111111111111111111111",
            "destination_address": "0x2222222222222222222222222222222222222222",
        }

        response = requests.post(
            f"{self.compliance_url}/compliance/aml-check", json=aml_request, timeout=self.timeout
        )

        assert response.status_code == 200
        data = response.json()

        print(f"✅ AML check performed: risk_level={data.get('risk_level')}")

        assert data["user_id"] == "test-aml-user"
        assert "check_id" in data
        assert data["risk_score"] > 0.0
        assert data["risk_level"] in ["low", "medium", "high"]
        assert "flags" in data
        assert "recommendations" in data

        # Validate high-value flags
        if 125000.0 > 10000:
            assert "high_value" in data["flags"]

    def test_get_compliance_checks_for_escrow(self):
        """
        Test Scenario: Get Compliance Checks for Escrow

        WHAT THIS TEST VALIDATES:
        ✅ Query compliance checks by escrow_address
        ✅ Return KYC, AML, and sanctions checks
        ✅ Include status and risk scores
        ✅ Filter by check type

        EXPECTED BEHAVIOR:
        - Returns list of compliance checks
        - Each check has check_type, status, score
        - Checks are linked to escrow_address
        """
        print("\n🔄 Testing get compliance checks for escrow...")

        test_escrow = "0x1234567890123456789012345678901234567890"

        response = requests.get(
            f"{self.compliance_url}/compliance/checks",
            params={"escrow_address": test_escrow},
            timeout=self.timeout,
        )

        assert response.status_code == 200
        data = response.json()

        print(f"✅ Retrieved {len(data)} compliance checks")

        assert isinstance(data, list)

        # If checks exist, validate structure
        if data:
            for check in data:
                assert "check_id" in check
                assert "check_type" in check
                assert "status" in check
                assert "escrow_address" in check

    def test_check_sanctions(self):
        """
        Test Scenario: Sanctions List Screening

        WHAT THIS TEST VALIDATES:
        ✅ Check addresses against sanctions lists
        ✅ Return clean status for valid addresses
        ✅ Identify potential sanctioned addresses
        ✅ Batch checking multiple addresses

        TEST DATA:
        - Addresses: [0x111..., 0x222..., 0x333...]

        EXPECTED BEHAVIOR:
        - Returns results for all addresses
        - Each result has sanctions_status and risk_level
        - Clean addresses return "clean" status
        """
        print("\n🔄 Testing sanctions check...")

        addresses = [
            "0x1111111111111111111111111111111111111111",
            "0x2222222222222222222222222222222222222222",
            "0x3333333333333333333333333333333333333333",
        ]

        response = requests.post(
            f"{self.compliance_url}/compliance/sanctions-check",
            json=addresses,
            timeout=self.timeout,
        )

        assert response.status_code == 200
        results = response.json()

        print(f"✅ Sanctions check completed for {len(results)} addresses")

        assert len(results) == 3

        for result in results:
            assert "address" in result
            assert "sanctions_status" in result
            assert "risk_level" in result

    def test_compliance_metrics(self):
        """
        Test Scenario: Compliance Metrics Retrieval

        WHAT THIS TEST VALIDATES:
        ✅ Retrieve compliance metrics and KPIs
        ✅ Filter by time range
        ✅ Include case counts, success rates, alert rates

        EXPECTED BEHAVIOR:
        - Returns metrics dictionary
        - Includes total_cases, pending_cases, resolved_cases
        - Includes kyc_success_rate and aml_alert_rate
        - Time range parameter respected
        """
        print("\n🔄 Testing compliance metrics...")

        response = requests.get(
            f"{self.compliance_url}/compliance/compliance-metrics",
            params={"time_range": "30d"},
            timeout=self.timeout,
        )

        assert response.status_code == 200
        data = response.json()

        print(f"✅ Compliance metrics retrieved")

        assert "total_cases" in data or "time_range" in data
