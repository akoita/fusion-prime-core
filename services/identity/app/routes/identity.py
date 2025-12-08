"""
Identity endpoints for Identity Service.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from app.services.identity_service import IdentityService
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()


def get_identity_service(request: Request) -> IdentityService:
    """Get identity service from app state."""
    service = getattr(request.app.state, "identity_service", None)
    if service is None:
        raise HTTPException(
            status_code=503,
            detail="Identity service not initialized",
        )
    return service


class CreateIdentityRequest(BaseModel):
    """Request to create an identity."""

    user_id: str = Field(..., description="Internal user ID")
    wallet_address: str = Field(..., description="User's wallet address")


class CreateIdentityResponse(BaseModel):
    """Response for identity creation."""

    user_id: str
    wallet_address: str
    identity_address: str
    tx_hash: Optional[str]
    already_exists: bool
    block_number: Optional[int]
    created_at: str


class IssueClaimRequest(BaseModel):
    """Request to issue a claim."""

    user_id: str = Field(..., description="Internal user ID")
    wallet_address: str = Field(..., description="User's wallet address")
    claim_type: str = Field(..., description="Claim type (KYC_VERIFIED, AML_CLEARED, etc.)")
    case_id: str = Field(..., description="Compliance case ID")
    inquiry_id: Optional[str] = Field(None, description="External inquiry ID (e.g., Persona)")


class IssueClaimResponse(BaseModel):
    """Response for claim issuance."""

    user_id: str
    wallet_address: str
    identity_address: str
    claim_topic: int
    claim_topic_name: str
    claim_id: Optional[str]
    tx_hash: str
    block_number: int
    issued_at: str


@router.post("/create", response_model=CreateIdentityResponse)
async def create_identity(
    request: CreateIdentityRequest, identity_service: IdentityService = Depends(get_identity_service)
):
    """
    Create a new identity for a user.

    This endpoint is called when a user completes onboarding.
    It deploys a new Identity contract for the user on the blockchain.
    """
    try:
        result = await identity_service.create_identity_for_user(
            user_id=request.user_id, wallet_address=request.wallet_address
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Identity creation failed: {str(e)}")


@router.post("/issue-claim", response_model=IssueClaimResponse)
async def issue_claim(
    request: IssueClaimRequest, identity_service: IdentityService = Depends(get_identity_service)
):
    """
    Issue a claim to a user's identity.

    This endpoint is called by the Compliance Service after verifying a user.
    It adds a claim (KYC, AML, etc.) to the user's Identity contract on the blockchain.
    """
    try:
        # Route to appropriate claim issuance method
        if request.claim_type == "KYC_VERIFIED":
            result = await identity_service.issue_kyc_claim(
                user_id=request.user_id,
                wallet_address=request.wallet_address,
                kyc_case_id=request.case_id,
                kyc_inquiry_id=request.inquiry_id or request.case_id,
            )
        elif request.claim_type == "AML_CLEARED":
            result = await identity_service.issue_aml_claim(
                user_id=request.user_id,
                wallet_address=request.wallet_address,
                aml_check_id=request.case_id,
            )
        else:
            raise ValueError(f"Unsupported claim type: {request.claim_type}")

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Claim issuance failed: {str(e)}")


@router.get("/{wallet_address}")
async def get_identity(
    wallet_address: str, identity_service: IdentityService = Depends(get_identity_service)
):
    """
    Get identity information for a wallet address.

    Returns the identity contract address if it exists.
    """
    try:
        result = await identity_service.get_user_identity(wallet_address)

        if result is None:
            raise HTTPException(status_code=404, detail="Identity not found")

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Identity lookup failed: {str(e)}")


@router.get("/{wallet_address}/claims")
async def get_user_claims(
    wallet_address: str, identity_service: IdentityService = Depends(get_identity_service)
):
    """
    Get all claims for a user's identity.

    (Implementation would query blockchain for claims)
    """
    # TODO: Implement claim querying from blockchain
    raise HTTPException(status_code=501, detail="Not implemented yet")
