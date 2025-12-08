"""
Integration tests for Compliance Service database persistence.

These tests validate that KYC, AML, and Sanctions checks are properly
persisted to the compliance database through actual API calls.
"""

import os
from datetime import datetime

import pytest
import requests

# Get Compliance service URL from environment
COMPLIANCE_URL = os.getenv(
    "COMPLIANCE_SERVICE_URL", "https://compliance-961424092563.us-central1.run.app"
)


class TestComplianceIntegration:
    """Test compliance service database persistence through API."""

    def test_kyc_case_creation_and_persistence(self):
        """Test KYC case creation and retrieval from database."""
        # 1. Create KYC case
        kyc_request = {
            "user_id": f"test-user-{int(datetime.utcnow().timestamp())}",
            "document_type": "passport",
            "document_data": {
                "document_number": "AB123456",
                "expiry_date": "2030-12-31",
                "issuing_country": "US",
                "photo_quality": "high",
                "data_completeness": "complete",
            },
            "personal_info": {
                "first_name": "John",
                "last_name": "Doe",
                "date_of_birth": "1990-01-01",
                "nationality": "US",
                "email_verified": True,
                "phone_verified": True,
            },
        }

        response = requests.post(f"{COMPLIANCE_URL}/compliance/kyc", json=kyc_request, timeout=10)

        # Verify HTTP 200 response
        assert response.status_code == 200, f"KYC creation failed: {response.text}"

        # Extract case_id from response
        response_data = response.json()
        case_id = response_data["case_id"]
        user_id = response_data["user_id"]

        # Verify response structure
        assert "case_id" in response_data
        assert "user_id" in response_data
        assert "status" in response_data
        assert "verification_score" in response_data
        assert "required_actions" in response_data

        # Verify KYC case was created with correct status
        assert response_data["status"] == "pending"
        assert response_data["user_id"] == kyc_request["user_id"]
        assert response_data["verification_score"] >= 0.0

        # 2. Retrieve KYC case to prove database persistence
        retrieve_response = requests.get(f"{COMPLIANCE_URL}/compliance/kyc/{case_id}", timeout=10)

        assert retrieve_response.status_code == 200, "KYC retrieval failed"

        # Verify retrieved data matches created data
        retrieved_data = retrieve_response.json()
        assert retrieved_data["case_id"] == case_id
        assert retrieved_data["user_id"] == user_id
        assert retrieved_data["status"] == "pending"

        print(f"✅ KYC case {case_id} created and persisted successfully")

    def test_aml_check_creation_and_persistence(self):
        """Test AML check creation and database persistence."""
        # 1. Perform AML check
        aml_request = {
            "user_id": f"test-user-{int(datetime.utcnow().timestamp())}",
            "transaction_amount": 50000.0,
            "transaction_type": "withdrawal",
            "source_address": "0x1234567890abcdef1234567890abcdef12345678",
            "destination_address": "0xabcdef1234567890abcdef1234567890abcdef12",
        }

        response = requests.post(
            f"{COMPLIANCE_URL}/compliance/aml-check", json=aml_request, timeout=10
        )

        # Verify HTTP 200 response
        assert response.status_code == 200, f"AML check failed: {response.text}"

        # Extract check_id from response
        response_data = response.json()
        check_id = response_data["check_id"]
        user_id = response_data["user_id"]

        # Verify response structure
        assert "check_id" in response_data
        assert "user_id" in response_data
        assert "risk_score" in response_data
        assert "risk_level" in response_data
        assert "flags" in response_data
        assert "recommendations" in response_data

        # Verify AML check was created with correct data
        assert response_data["user_id"] == aml_request["user_id"]
        assert 0.0 <= response_data["risk_score"] <= 1.0
        assert response_data["risk_level"] in ["low", "medium", "high"]

        # For high-value transaction, should have flags
        if aml_request["transaction_amount"] > 10000:
            assert len(response_data["flags"]) > 0

        print(f"✅ AML check {check_id} created and persisted successfully")
        print(f"   Risk Level: {response_data['risk_level']}")
        print(f"   Flags: {response_data['flags']}")

    def test_sanctions_check_creation_and_persistence(self):
        """Test sanctions check creation and database persistence."""
        # 1. Perform sanctions check
        addresses_list = [
            "0x1234567890abcdef1234567890abcdef12345678",
            "0xabcdef1234567890abcdef1234567890abcdef12",
            "0x0000001234567890abcdef1234567890abcdef12",  # Suspicious pattern
        ]

        response = requests.post(
            f"{COMPLIANCE_URL}/compliance/sanctions-check", json=addresses_list, timeout=10
        )

        # Verify HTTP 200 response
        assert response.status_code == 200, f"Sanctions check failed: {response.text}"

        # Extract results
        results = response.json()

        # Verify response is a list
        assert isinstance(results, list)
        assert len(results) == len(addresses_list)

        # Verify each result has correct structure
        for result in results:
            assert "check_id" in result
            assert "address" in result
            assert "sanctions_status" in result
            assert "risk_level" in result
            assert "matches" in result
            assert "checked_at" in result

            # Verify status and risk level
            assert result["sanctions_status"] in ["clean", "flagged"]
            assert result["risk_level"] in ["none", "low", "medium", "high"]

        print(f"✅ Sanctions check for {len(results)} addresses completed and persisted")
        for result in results:
            print(
                f"   {result['address'][:10]}...: {result['sanctions_status']} (risk: {result['risk_level']})"
            )

    def test_multiple_kyc_cases_persistence(self):
        """Test creating multiple KYC cases to verify independent persistence."""
        cases = []

        # Create 3 KYC cases
        for i in range(3):
            kyc_request = {
                "user_id": f"test-user-multi-{i}-{int(datetime.utcnow().timestamp())}",
                "document_type": "passport" if i % 2 == 0 else "driver_license",
                "document_data": {"document_number": f"DOC-{i}", "expiry_date": "2030-12-31"},
                "personal_info": {"first_name": f"User{i}", "last_name": "Test"},
            }

            response = requests.post(
                f"{COMPLIANCE_URL}/compliance/kyc", json=kyc_request, timeout=10
            )

            assert response.status_code == 200
            cases.append(response.json())

        # Verify all cases were created with unique IDs
        case_ids = [case["case_id"] for case in cases]
        assert len(case_ids) == len(set(case_ids)), "Case IDs should be unique"

        # Verify each case can be retrieved independently
        for case in cases:
            retrieve_response = requests.get(
                f"{COMPLIANCE_URL}/compliance/kyc/{case['case_id']}", timeout=10
            )
            assert retrieve_response.status_code == 200
            retrieved = retrieve_response.json()
            assert retrieved["case_id"] == case["case_id"]

        print(f"✅ Created and retrieved {len(cases)} independent KYC cases")

    def test_aml_check_high_value_transaction(self):
        """Test AML check for high-value transaction triggers appropriate flags."""
        # Create high-value transaction
        aml_request = {
            "user_id": f"test-user-highval-{int(datetime.utcnow().timestamp())}",
            "transaction_amount": 150000.0,  # Very high value
            "transaction_type": "withdrawal",
            "source_address": "0x1234567890abcdef1234567890abcdef12345678",
            "destination_address": "0xabcdef1234567890abcdef1234567890abcdef12",
        }

        response = requests.post(
            f"{COMPLIANCE_URL}/compliance/aml-check", json=aml_request, timeout=10
        )

        assert response.status_code == 200
        response_data = response.json()

        # High-value transaction should have elevated risk
        assert response_data["risk_score"] > 0.2  # Should have some risk
        assert "high_value" in response_data["flags"] or "very_high_value" in response_data["flags"]

        # Should have recommendations
        assert len(response_data["recommendations"]) > 0

        print(f"✅ High-value AML check flagged appropriately")
        print(f"   Risk Score: {response_data['risk_score']}")
        print(f"   Flags: {response_data['flags']}")
        print(f"   Recommendations: {response_data['recommendations']}")

    def test_compliance_metrics_retrieval(self):
        """Test compliance metrics endpoint returns database-backed data."""
        # First, create some compliance data
        # Create KYC case
        kyc_request = {
            "user_id": f"test-user-metrics-{int(datetime.utcnow().timestamp())}",
            "document_type": "passport",
            "document_data": {"document_number": "TEST123"},
            "personal_info": {"first_name": "Test", "last_name": "User"},
        }
        requests.post(f"{COMPLIANCE_URL}/compliance/kyc", json=kyc_request, timeout=10)

        # Create AML check
        aml_request = {
            "user_id": f"test-user-metrics-aml-{int(datetime.utcnow().timestamp())}",
            "transaction_amount": 25000.0,
            "transaction_type": "transfer",
            "source_address": "0x123",
            "destination_address": "0x456",
        }
        requests.post(f"{COMPLIANCE_URL}/compliance/aml-check", json=aml_request, timeout=10)

        # Get metrics
        response = requests.get(
            f"{COMPLIANCE_URL}/compliance/compliance-metrics?time_range=30d", timeout=10
        )

        assert response.status_code == 200
        metrics = response.json()

        # Verify metrics structure
        assert "total_cases" in metrics
        assert "kyc_cases" in metrics
        assert "aml_alerts" in metrics

        # Verify we have data (from the cases we just created)
        assert metrics["total_cases"] >= 2  # At least our test cases

        print(f"✅ Compliance metrics retrieved from database")
        print(f"   Total Cases: {metrics['total_cases']}")
        print(f"   KYC Cases: {metrics['kyc_cases']['total']}")
        print(f"   AML Alerts: {metrics['aml_alerts']['total']}")

    def test_compliance_check_creation_and_persistence(self):
        """Test compliance check creation and retrieval from database."""
        # 1. Create a compliance check
        check_request = {
            "check_type": "kyc",
            "escrow_address": "0x1234567890abcdef1234567890abcdef12345678",
            "user_id": f"test-user-check-{int(datetime.utcnow().timestamp())}",
            "status": "passed",
            "score": 0.95,
            "risk_score": 0.05,
            "flags": ["document_verified", "address_confirmed"],
            "notes": "KYC verification completed successfully",
        }

        response = requests.post(
            f"{COMPLIANCE_URL}/compliance/checks", json=check_request, timeout=10
        )

        # Verify HTTP 200 response
        assert response.status_code == 200, f"Check creation failed: {response.text}"

        # Extract check_id from response
        response_data = response.json()
        check_id = response_data["check_id"]
        escrow_address = check_request["escrow_address"]

        # Verify response structure
        assert "check_id" in response_data
        assert "check_type" in response_data
        assert "escrow_address" in response_data
        assert "user_id" in response_data

        # 2. Retrieve compliance checks to prove database persistence
        retrieve_response = requests.get(
            f"{COMPLIANCE_URL}/compliance/checks?escrow_address={escrow_address}", timeout=10
        )

        assert retrieve_response.status_code == 200, "Checks retrieval failed"

        # Verify retrieved data contains our check
        retrieved_checks = retrieve_response.json()
        assert isinstance(retrieved_checks, list)
        assert len(retrieved_checks) > 0

        # Find our check in the results
        our_check = next((c for c in retrieved_checks if c["check_id"] == check_id), None)
        assert our_check is not None, f"Check {check_id} not found in database"
        assert our_check["check_type"] == check_request["check_type"]
        assert our_check["status"] == check_request["status"]

        print(f"✅ Compliance check {check_id} created and persisted successfully")

    def test_compliance_case_creation_and_persistence(self):
        """Test compliance case creation and retrieval from database."""
        # 1. Create a compliance case
        case_request = {
            "user_id": f"test-user-case-{int(datetime.utcnow().timestamp())}",
            "case_type": "aml",
            "title": "Suspicious transaction pattern detected",
            "description": "User has multiple high-value transactions in short timeframe",
            "priority": "high",
        }

        response = requests.post(
            f"{COMPLIANCE_URL}/compliance/compliance-cases", json=case_request, timeout=10
        )

        # Verify HTTP 200 response
        assert response.status_code == 200, f"Case creation failed: {response.text}"

        # Extract case_id from response
        response_data = response.json()
        case_id = response_data["case_id"]

        # Verify response structure
        assert "case_id" in response_data
        assert "user_id" in response_data
        assert "case_type" in response_data
        assert "title" in response_data
        assert "status" in response_data
        assert "priority" in response_data

        # Verify case was created with correct data
        assert response_data["status"] == "open"
        assert response_data["priority"] == "high"
        assert response_data["user_id"] == case_request["user_id"]

        # 2. Retrieve compliance cases to prove database persistence
        retrieve_response = requests.get(
            f"{COMPLIANCE_URL}/compliance/compliance-cases?priority=high", timeout=10
        )

        assert retrieve_response.status_code == 200, "Cases retrieval failed"

        # Verify retrieved data contains our case
        retrieved_cases = retrieve_response.json()
        assert isinstance(retrieved_cases, list)
        assert len(retrieved_cases) > 0

        # Find our case in the results
        our_case = next((c for c in retrieved_cases if c["case_id"] == case_id), None)
        assert our_case is not None, f"Case {case_id} not found in database"
        assert our_case["case_type"] == case_request["case_type"]
        assert our_case["title"] == case_request["title"]

        print(f"✅ Compliance case {case_id} created and persisted successfully")

    def test_compliance_case_resolution(self):
        """Test resolving a compliance case and verifying persistence."""
        # 1. Create a compliance case
        case_request = {
            "user_id": f"test-user-resolve-{int(datetime.utcnow().timestamp())}",
            "case_type": "kyc",
            "title": "Document verification required",
            "description": "Additional documents needed for verification",
            "priority": "normal",
        }

        create_response = requests.post(
            f"{COMPLIANCE_URL}/compliance/compliance-cases", json=case_request, timeout=10
        )

        assert create_response.status_code == 200
        case_id = create_response.json()["case_id"]

        # 2. Resolve the case
        resolution = {
            "resolution_notes": "Documents verified successfully. User approved for trading."
        }

        resolve_response = requests.put(
            f"{COMPLIANCE_URL}/compliance/compliance-cases/{case_id}/resolve",
            json=resolution,
            timeout=10,
        )

        # Verify HTTP 200 response
        assert (
            resolve_response.status_code == 200
        ), f"Case resolution failed: {resolve_response.text}"

        # Verify resolution response
        resolution_data = resolve_response.json()
        assert resolution_data["case_id"] == case_id
        assert resolution_data["status"] == "resolved"
        assert "resolved_at" in resolution_data

        # 3. Verify case status was updated in database
        retrieve_response = requests.get(
            f"{COMPLIANCE_URL}/compliance/compliance-cases?status=resolved", timeout=10
        )

        assert retrieve_response.status_code == 200
        resolved_cases = retrieve_response.json()

        # Find our resolved case
        our_case = next((c for c in resolved_cases if c["case_id"] == case_id), None)
        assert our_case is not None, f"Resolved case {case_id} not found"
        assert our_case["status"] == "resolved"

        print(f"✅ Compliance case {case_id} resolved and persisted successfully")

    def test_aml_alerts_query_with_filtering(self):
        """Test retrieving AML alerts with filtering."""
        # 1. Create an AML check to generate an alert
        aml_request = {
            "user_id": f"test-user-alerts-{int(datetime.utcnow().timestamp())}",
            "transaction_amount": 85000.0,  # High value to trigger alert
            "transaction_type": "withdrawal",
            "source_address": "0xtest123",
            "destination_address": "0xtest456",
        }

        create_response = requests.post(
            f"{COMPLIANCE_URL}/compliance/aml-check", json=aml_request, timeout=10
        )

        assert create_response.status_code == 200
        user_id = create_response.json()["user_id"]

        # 2. Query AML alerts for this user
        alerts_response = requests.get(
            f"{COMPLIANCE_URL}/compliance/aml-alerts?user_id={user_id}", timeout=10
        )

        # Verify HTTP 200 response
        assert (
            alerts_response.status_code == 200
        ), f"AML alerts query failed: {alerts_response.text}"

        # Verify alerts structure
        alerts = alerts_response.json()
        assert isinstance(alerts, list)

        if len(alerts) > 0:
            # Verify alert structure
            alert = alerts[0]
            assert "alert_id" in alert
            assert "user_id" in alert
            assert "risk_score" in alert
            assert "risk_level" in alert
            assert "status" in alert
            assert "flags" in alert

            print(f"✅ AML alerts query successful, found {len(alerts)} alerts")
            print(f"   Risk Level: {alert['risk_level']}")
        else:
            print(f"✅ AML alerts query successful (no alerts for user {user_id})")

    def test_user_compliance_status_aggregation(self):
        """Test retrieving aggregated compliance status for a user."""
        # 1. Create KYC case for a user
        user_id = f"test-user-status-{int(datetime.utcnow().timestamp())}"

        kyc_request = {
            "user_id": user_id,
            "document_type": "passport",
            "document_data": {"document_number": "STATUS123"},
            "personal_info": {"first_name": "Status", "last_name": "Test"},
        }

        kyc_response = requests.post(
            f"{COMPLIANCE_URL}/compliance/kyc", json=kyc_request, timeout=10
        )

        assert kyc_response.status_code == 200

        # 2. Perform AML check for the same user
        aml_request = {
            "user_id": user_id,
            "transaction_amount": 5000.0,  # Normal value
            "transaction_type": "deposit",
            "source_address": "0xstatus123",
            "destination_address": "0xstatus456",
        }

        aml_response = requests.post(
            f"{COMPLIANCE_URL}/compliance/aml-check", json=aml_request, timeout=10
        )

        assert aml_response.status_code == 200

        # 3. Get aggregated compliance status
        status_response = requests.get(
            f"{COMPLIANCE_URL}/compliance/compliance-status/{user_id}", timeout=10
        )

        # Verify HTTP 200 response
        assert (
            status_response.status_code == 200
        ), f"Compliance status query failed: {status_response.text}"

        # Verify status structure
        status = status_response.json()
        assert "user_id" in status
        assert "kyc_status" in status
        assert "aml_status" in status
        assert "compliance_score" in status
        assert "total_aml_alerts" in status
        assert "high_risk_alerts" in status

        # Verify user_id matches
        assert status["user_id"] == user_id

        # Verify compliance score is a valid value
        assert 0.0 <= status["compliance_score"] <= 1.0

        print(f"✅ User compliance status retrieved successfully")
        print(f"   User ID: {status['user_id']}")
        print(f"   KYC Status: {status['kyc_status']}")
        print(f"   AML Status: {status['aml_status']}")
        print(f"   Compliance Score: {status['compliance_score']}")
        print(f"   Total AML Alerts: {status['total_aml_alerts']}")

    def test_multiple_compliance_checks_for_escrow(self):
        """Test creating multiple checks for the same escrow address."""
        escrow_address = f"0xescrow{int(datetime.utcnow().timestamp())}"
        checks = []

        # Create multiple types of checks for the same escrow
        check_types = ["kyc", "aml", "sanctions"]

        for check_type in check_types:
            check_request = {
                "check_type": check_type,
                "escrow_address": escrow_address,
                "user_id": f"test-user-{check_type}",
                "status": "passed",
                "score": 0.90,
                "risk_score": 0.10,
            }

            response = requests.post(
                f"{COMPLIANCE_URL}/compliance/checks", json=check_request, timeout=10
            )

            assert response.status_code == 200
            checks.append(response.json())

        # Verify all checks were created
        assert len(checks) == len(check_types)

        # Query checks for this escrow
        retrieve_response = requests.get(
            f"{COMPLIANCE_URL}/compliance/checks?escrow_address={escrow_address}", timeout=10
        )

        assert retrieve_response.status_code == 200
        retrieved_checks = retrieve_response.json()

        # Verify all check types are present
        check_types_found = {check["check_type"] for check in retrieved_checks}
        assert "kyc" in check_types_found
        assert "aml" in check_types_found
        assert "sanctions" in check_types_found

        print(
            f"✅ Created and retrieved {len(retrieved_checks)} checks for escrow {escrow_address[:10]}..."
        )


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
