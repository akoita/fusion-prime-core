"""
Compliance endpoints for Compliance Service.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.dependencies import get_compliance_engine
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

router = APIRouter()


def get_compliance_engine_from_state(request: Request):
    """Get initialized compliance engine from app state."""
    engine = getattr(request.app.state, "compliance_engine", None)
    if engine is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail="Compliance engine not initialized. Check service logs for initialization errors.",
        )
    return engine


class KYCRequest(BaseModel):
    """KYC verification request."""

    user_id: str = Field(..., description="User identifier")
    document_type: str = Field(..., description="Document type (passport, driver_license, etc.)")
    document_data: Dict[str, Any] = Field(..., description="Document data")
    personal_info: Dict[str, Any] = Field(..., description="Personal information")


class KYCResponse(BaseModel):
    """KYC verification response."""

    case_id: str
    user_id: str
    status: str
    verification_score: float
    required_actions: List[str]
    created_at: datetime


class AMLCheckRequest(BaseModel):
    """AML check request."""

    user_id: str = Field(..., description="User identifier")
    transaction_amount: float = Field(..., description="Transaction amount")
    transaction_type: str = Field(..., description="Transaction type")
    source_address: str = Field(..., description="Source blockchain address")
    destination_address: str = Field(..., description="Destination blockchain address")


class AMLCheckResponse(BaseModel):
    """AML check response."""

    check_id: str
    user_id: str
    risk_score: float
    risk_level: str
    flags: List[str]
    recommendations: List[str]
    created_at: datetime


@router.post("/kyc", response_model=KYCResponse)
async def initiate_kyc(
    request: KYCRequest, compliance_engine=Depends(get_compliance_engine_from_state)
):
    """Initiate KYC verification process."""
    try:
        if compliance_engine is None:
            raise HTTPException(status_code=503, detail="Compliance engine not initialized")
        result = await compliance_engine.initiate_kyc(
            user_id=request.user_id,
            document_type=request.document_type,
            document_data=request.document_data,
            personal_info=request.personal_info,
        )
        return result
    except HTTPException:
        raise
    except AttributeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Compliance engine method error: {str(e)}. Check service initialization.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"KYC initiation failed: {str(e)}")


@router.get("/kyc/{case_id}")
async def get_kyc_status(case_id: str, compliance_engine=Depends(get_compliance_engine_from_state)):
    """Get KYC case status."""
    try:
        if compliance_engine is None:
            raise HTTPException(status_code=503, detail="Compliance engine not initialized")
        status = await compliance_engine.get_kyc_status(case_id)
        return status
    except HTTPException:
        raise
    except AttributeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Compliance engine method error: {str(e)}. Check service initialization.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"KYC status retrieval failed: {str(e)}")


@router.post("/aml-check", response_model=AMLCheckResponse)
async def perform_aml_check(
    request: AMLCheckRequest, compliance_engine=Depends(get_compliance_engine_from_state)
):
    """Perform AML check for transaction."""
    try:
        if compliance_engine is None:
            raise HTTPException(status_code=503, detail="Compliance engine not initialized")
        result = await compliance_engine.perform_aml_check(
            user_id=request.user_id,
            transaction_amount=request.transaction_amount,
            transaction_type=request.transaction_type,
            source_address=request.source_address,
            destination_address=request.destination_address,
        )
        return result
    except HTTPException:
        raise
    except AttributeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Compliance engine method error: {str(e)}. Check service initialization.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AML check failed: {str(e)}")


@router.get("/aml-alerts")
async def get_aml_alerts(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by alert status"),
    compliance_engine=Depends(get_compliance_engine_from_state),
):
    """Get AML alerts."""
    try:
        alerts = await compliance_engine.get_aml_alerts(user_id=user_id, status=status)
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AML alerts retrieval failed: {str(e)}")


@router.get("/compliance-status/{user_id}")
async def get_user_compliance_status(
    user_id: str, compliance_engine=Depends(get_compliance_engine_from_state)
):
    """Get user compliance status."""
    try:
        status = await compliance_engine.get_user_compliance_status(user_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compliance status retrieval failed: {str(e)}")


@router.post("/sanctions-check")
async def check_sanctions(
    addresses: List[str], compliance_engine=Depends(get_compliance_engine_from_state)
):
    """Check addresses against sanctions lists."""
    try:
        results = await compliance_engine.check_sanctions(addresses)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sanctions check failed: {str(e)}")


@router.get("/compliance-cases")
async def get_compliance_cases(
    status: Optional[str] = Query(None, description="Filter by case status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    compliance_engine=Depends(get_compliance_engine_from_state),
):
    """Get compliance cases for review."""
    try:
        cases = await compliance_engine.get_compliance_cases(status=status, priority=priority)
        return cases
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compliance cases retrieval failed: {str(e)}")


@router.put("/compliance-cases/{case_id}/resolve")
async def resolve_compliance_case(
    case_id: str,
    resolution: Dict[str, Any],
    compliance_engine=Depends(get_compliance_engine_from_state),
):
    """Resolve a compliance case."""
    try:
        result = await compliance_engine.resolve_compliance_case(
            case_id=case_id, resolution=resolution
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Case resolution failed: {str(e)}")


@router.get("/checks")
async def get_compliance_checks(
    escrow_address: Optional[str] = Query(None, description="Filter by escrow address"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    compliance_engine=Depends(get_compliance_engine_from_state),
):
    """
    Get compliance checks with optional filtering.

    This endpoint retrieves compliance check records from the database.
    Checks are linked to escrows/transactions and track KYC, AML, and sanctions verification.

    Args:
        escrow_address: Filter checks for a specific escrow contract
        user_id: Filter checks for a specific user

    Returns:
        List of compliance checks with their status and results
    """
    try:
        checks = await compliance_engine.get_compliance_checks(
            escrow_address=escrow_address, user_id=user_id
        )
        return checks
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compliance checks retrieval failed: {str(e)}")


@router.get("/compliance-metrics")
async def get_compliance_metrics(
    time_range: str = Query("30d", description="Time range for metrics"),
    compliance_engine=Depends(get_compliance_engine_from_state),
):
    """Get compliance metrics and KPIs."""
    try:
        if compliance_engine is None:
            raise HTTPException(status_code=503, detail="Compliance engine not initialized")
        metrics = await compliance_engine.get_compliance_metrics(time_range)
        return metrics
    except HTTPException:
        raise
    except AttributeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Compliance engine method error: {str(e)}. Check service initialization.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Compliance metrics retrieval failed: {str(e)}"
        )


class ComplianceCheckRequest(BaseModel):
    """Request to create a compliance check."""

    check_type: str = Field(..., description="Check type (kyc, aml, sanctions, kyb)")
    escrow_address: Optional[str] = Field(None, description="Escrow contract address")
    user_id: Optional[str] = Field(None, description="User ID")
    status: str = Field(default="pending", description="Check status")
    score: Optional[float] = Field(None, description="Verification score")
    risk_score: Optional[float] = Field(None, description="Risk score")
    flags: Optional[List[str]] = Field(None, description="Check flags")
    notes: Optional[str] = Field(None, description="Additional notes")


@router.post("/checks")
async def create_compliance_check(
    request: ComplianceCheckRequest, compliance_engine=Depends(get_compliance_engine_from_state)
):
    """Create a compliance check record."""
    try:
        result = await compliance_engine.create_compliance_check(
            check_type=request.check_type,
            escrow_address=request.escrow_address,
            user_id=request.user_id,
            status=request.status,
            score=request.score,
            risk_score=request.risk_score,
            flags=request.flags,
            notes=request.notes,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compliance check creation failed: {str(e)}")


class ComplianceCaseRequest(BaseModel):
    """Request to create a compliance case."""

    user_id: str = Field(..., description="User ID")
    case_type: str = Field(..., description="Case type (kyc, aml, sanctions, general)")
    title: str = Field(..., description="Case title")
    description: Optional[str] = Field(None, description="Case description")
    priority: str = Field(default="normal", description="Case priority (low, normal, high, urgent)")


@router.post("/compliance-cases")
async def create_compliance_case(
    request: ComplianceCaseRequest, compliance_engine=Depends(get_compliance_engine_from_state)
):
    """Create a compliance case for manual review."""
    try:
        result = await compliance_engine.create_compliance_case(
            user_id=request.user_id,
            case_type=request.case_type,
            title=request.title,
            description=request.description,
            priority=request.priority,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Compliance case creation failed: {str(e)}")


class UpdateKYCClaimRequest(BaseModel):
    """Request to update KYC case with identity claim information."""

    case_id: str = Field(..., description="KYC case ID")
    claim_id: str = Field(..., description="On-chain claim ID")
    claim_tx_hash: str = Field(..., description="Blockchain transaction hash")


@router.put("/kyc/{case_id}/claim")
async def update_kyc_claim(
    case_id: str,
    request: UpdateKYCClaimRequest,
    compliance_engine=Depends(get_compliance_engine_from_state),
):
    """
    Update KYC case with identity claim information.

    This endpoint is called by the Identity Service after issuing an on-chain claim
    for a verified KYC case.
    """
    try:
        if compliance_engine is None:
            raise HTTPException(status_code=503, detail="Compliance engine not initialized")

        result = await compliance_engine.update_kyc_claim(
            case_id=request.case_id,
            claim_id=request.claim_id,
            claim_tx_hash=request.claim_tx_hash,
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update KYC claim: {str(e)}")
