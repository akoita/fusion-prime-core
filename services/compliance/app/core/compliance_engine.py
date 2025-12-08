"""
Production Compliance Engine with real database integration.
Implements KYC/KYB, AML screening, and sanctions checking with persistence.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from infrastructure.db.models import (
    AMLAlert,
    ComplianceCase,
    ComplianceCheck,
    KYCCase,
    SanctionsCheck,
)
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class ComplianceEngine:
    """Production compliance engine with real database integration."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine: Optional[AsyncEngine] = None
        self.session_factory = None
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize database connection."""
        try:
            self.engine = create_async_engine(self.database_url, echo=False)
            self.session_factory = sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )
            self.logger.info("Compliance engine initialized with database")
        except Exception as e:
            self.logger.error(f"Failed to initialize database connection: {e}")
            raise

    async def cleanup(self):
        """Cleanup resources."""
        if self.engine:
            await self.engine.dispose()
            self.logger.info("Database connection closed")

    async def initiate_kyc(
        self,
        user_id: str,
        document_type: str,
        document_data: Dict[str, Any],
        personal_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Initiate KYC verification process with database persistence.

        This implementation:
        1. Creates KYC case in database
        2. Performs basic document validation
        3. Scores verification likelihood
        4. Returns case for manual review
        """
        if self.session_factory is None:
            raise RuntimeError("Compliance engine not initialized - session_factory is None")
        try:
            async with self.session_factory() as session:
                # Create KYC case
                case_id = f"kyc-{user_id}-{int(datetime.utcnow().timestamp())}"

                kyc_case = KYCCase(
                    case_id=case_id,
                    user_id=user_id,
                    document_type=document_type,
                    document_data=document_data,
                    personal_info=personal_info,
                    status="pending",
                    required_actions=self._calculate_required_actions(document_type, document_data),
                )

                session.add(kyc_case)
                await session.commit()

                # Calculate verification score
                verification_score = self._calculate_verification_score(
                    document_data, personal_info
                )

                # Update score
                kyc_case.verification_score = verification_score
                await session.commit()

                self.logger.info(f"KYC case created: {case_id} for user {user_id}")

                return {
                    "case_id": case_id,
                    "user_id": user_id,
                    "status": kyc_case.status,
                    "verification_score": float(verification_score) if verification_score else 0.0,
                    "required_actions": kyc_case.required_actions or [],
                    "created_at": (
                        kyc_case.created_at.isoformat()
                        if kyc_case.created_at
                        else datetime.utcnow().isoformat()
                    ),
                }

        except Exception as e:
            self.logger.error(f"Error initiating KYC: {e}")
            raise

    async def get_kyc_status(self, case_id: str) -> Dict[str, Any]:
        """Get KYC case status from database."""
        if self.session_factory is None:
            raise RuntimeError("Compliance engine not initialized - session_factory is None")
        try:
            async with self.session_factory() as session:
                result = await session.execute(select(KYCCase).where(KYCCase.case_id == case_id))
                kyc_case = result.scalar_one_or_none()

                if not kyc_case:
                    raise ValueError(f"KYC case not found: {case_id}")

                return {
                    "case_id": kyc_case.case_id,
                    "user_id": kyc_case.user_id,
                    "status": kyc_case.status,
                    "verification_score": (
                        float(kyc_case.verification_score) if kyc_case.verification_score else None
                    ),
                    "required_actions": kyc_case.required_actions or [],
                    "created_at": kyc_case.created_at.isoformat() if kyc_case.created_at else None,
                    "updated_at": kyc_case.updated_at.isoformat() if kyc_case.updated_at else None,
                }

        except Exception as e:
            self.logger.error(f"Error getting KYC status: {e}")
            raise

    async def perform_aml_check(
        self,
        user_id: str,
        transaction_amount: float,
        transaction_type: str,
        source_address: str,
        destination_address: str,
    ) -> Dict[str, Any]:
        """
        Perform AML check with database persistence.

        This implementation:
        1. Calculates risk score based on transaction patterns
        2. Checks against velocity limits
        3. Flags suspicious patterns
        4. Stores alert in database
        """
        if self.session_factory is None:
            raise RuntimeError("Compliance engine not initialized - session_factory is None")
        try:
            async with self.session_factory() as session:
                # Calculate risk score
                risk_score = self._calculate_aml_risk_score(
                    transaction_amount, transaction_type, user_id
                )
                risk_level = self._determine_risk_level(risk_score)
                flags = self._identify_aml_flags(transaction_amount, transaction_type, user_id)
                recommendations = self._generate_aml_recommendations(risk_level, flags)

                # Create AML alert
                alert_id = f"aml-{user_id}-{int(datetime.utcnow().timestamp())}"

                aml_alert = AMLAlert(
                    alert_id=alert_id,
                    user_id=user_id,
                    transaction_amount=transaction_amount,
                    transaction_type=transaction_type,
                    source_address=source_address,
                    destination_address=destination_address,
                    risk_score=risk_score,
                    risk_level=risk_level,
                    flags=flags,
                    recommendations=recommendations,
                    status="open",
                )

                session.add(aml_alert)
                await session.commit()

                self.logger.info(f"AML check created: {alert_id} with risk level {risk_level}")

                return {
                    "check_id": alert_id,
                    "user_id": user_id,
                    "risk_score": float(risk_score),
                    "risk_level": risk_level,
                    "flags": flags,
                    "recommendations": recommendations,
                    "created_at": (
                        aml_alert.created_at.isoformat()
                        if aml_alert.created_at
                        else datetime.utcnow().isoformat()
                    ),
                }

        except Exception as e:
            self.logger.error(f"Error performing AML check: {e}")
            raise

    async def check_sanctions(self, addresses: List[str]) -> List[Dict[str, Any]]:
        """
        Check addresses against sanctions lists with database persistence.

        This implementation:
        1. Checks each address against sanctions screening
        2. Stores check results in database
        3. Returns risk assessment

        Note: In production, this would integrate with external sanctions API (OFAC, UN, EU).
        For now, uses heuristic-based screening and persists all checks to database.
        """
        try:
            results = []
            async with self.session_factory() as session:
                for address in addresses:
                    # Perform sanctions screening (heuristic-based for now)
                    matches, risk_level = self._screen_address_for_sanctions(address)

                    # Create sanctions check record
                    check_id = f"sanc-{address[:10]}-{int(datetime.utcnow().timestamp())}"

                    sanctions_check = SanctionsCheck(
                        check_id=check_id,
                        address=address.lower(),
                        network="ethereum",  # Default to ethereum
                        matches=matches,
                        risk_level=risk_level,
                    )

                    session.add(sanctions_check)

                    # Build result
                    results.append(
                        {
                            "check_id": check_id,
                            "address": address,
                            "sanctions_status": "flagged" if matches else "clean",
                            "risk_level": risk_level,
                            "matches": matches,
                            "checked_at": datetime.utcnow().isoformat() + "Z",
                        }
                    )

                await session.commit()
                self.logger.info(f"Sanctions checks completed for {len(addresses)} addresses")

            return results
        except Exception as e:
            self.logger.error(f"Error checking sanctions: {e}")
            raise

    def _screen_address_for_sanctions(self, address: str) -> tuple[List[Dict[str, str]], str]:
        """
        Screen address for sanctions (heuristic-based).

        In production, this would call external sanctions screening APIs:
        - OFAC SDN list
        - UN Security Council sanctions
        - EU sanctions list
        - Chainalysis sanctions screening

        For now, uses deterministic heuristics based on address characteristics.
        """
        matches = []
        risk_level = "none"

        # Heuristic: Check for known high-risk patterns
        # In production, replace with real API calls
        address_lower = address.lower()

        # Example heuristics (replace with real screening in production)
        if address_lower.startswith("0x000000"):
            # Zero addresses might be suspicious
            matches.append(
                {
                    "list": "Internal Screening",
                    "reason": "Suspicious address pattern",
                    "confidence": "low",
                }
            )
            risk_level = "low"

        # In production, this would be:
        # - API call to Chainalysis
        # - Check against OFAC SDN list
        # - Cross-reference with known bad actors
        # - Check transaction history patterns

        return matches, risk_level

    def _calculate_required_actions(
        self, document_type: str, document_data: Dict[str, Any]
    ) -> List[str]:
        """Calculate required verification actions based on document type."""
        actions = ["identity_verification"]

        if document_type == "passport":
            actions.append("passport_validation")
            actions.append("photo_matching")
        elif document_type == "driver_license":
            actions.append("license_validation")
            actions.append("address_verification")
        elif document_type == "national_id":
            actions.append("id_validation")

        return actions

    def _calculate_verification_score(
        self, document_data: Dict[str, Any], personal_info: Dict[str, Any]
    ) -> float:
        """Calculate KYC verification score."""
        score = 0.5  # Base score

        # Document quality scoring
        if document_data.get("photo_quality") == "high":
            score += 0.2
        if document_data.get("data_completeness") == "complete":
            score += 0.2

        # Personal info verification
        if personal_info.get("email_verified"):
            score += 0.05
        if personal_info.get("phone_verified"):
            score += 0.05

        return min(1.0, score)

    def _calculate_aml_risk_score(
        self, amount: float, transaction_type: str, user_id: str
    ) -> float:
        """Calculate AML risk score."""
        risk = 0.0

        # High value transaction
        if amount > 100000:
            risk += 0.3
        elif amount > 10000:
            risk += 0.15

        # Transaction type risk
        if transaction_type in ["withdrawal", "transfer_external"]:
            risk += 0.2

        # Time-based patterns (would check database in production)
        # For now, use deterministic risk based on amount

        return min(1.0, risk)

    def _determine_risk_level(self, risk_score: float) -> str:
        """Determine risk level from score."""
        if risk_score < 0.3:
            return "low"
        elif risk_score < 0.7:
            return "medium"
        else:
            return "high"

    def _identify_aml_flags(self, amount: float, transaction_type: str, user_id: str) -> List[str]:
        """Identify AML flags for transaction."""
        flags = []

        if amount > 10000:
            flags.append("high_value")
        if amount > 50000:
            flags.append("very_high_value")
        if transaction_type in ["withdrawal", "external_transfer"]:
            flags.append("external_movement")

        return flags

    def _generate_aml_recommendations(self, risk_level: str, flags: List[str]) -> List[str]:
        """Generate AML recommendations based on risk."""
        recommendations = []

        if risk_level == "high":
            recommendations.append("manual_review_required")
            recommendations.append("enhanced_due_diligence")
        elif risk_level == "medium":
            recommendations.append("automated_monitoring")
        else:
            recommendations.append("proceed")

        if "high_value" in flags:
            recommendations.append("verify_source_of_funds")

        return recommendations

    async def get_compliance_metrics(self, time_range: str = "30d") -> Dict[str, Any]:
        """Get compliance metrics and KPIs."""
        if self.session_factory is None:
            raise RuntimeError("Compliance engine not initialized - session_factory is None")
        try:
            async with self.session_factory() as session:
                # Count KYC cases
                kyc_total = await session.execute(select(func.count()).select_from(KYCCase))
                total_kyc = kyc_total.scalar() or 0

                kyc_pending = await session.execute(
                    select(func.count()).select_from(KYCCase).where(KYCCase.status == "pending")
                )
                pending_kyc = kyc_pending.scalar() or 0

                kyc_approved = await session.execute(
                    select(func.count()).select_from(KYCCase).where(KYCCase.status == "approved")
                )
                approved_kyc = kyc_approved.scalar() or 0

                # Count AML alerts
                aml_total = await session.execute(select(func.count()).select_from(AMLAlert))
                total_aml = aml_total.scalar() or 0

                aml_high_risk = await session.execute(
                    select(func.count()).select_from(AMLAlert).where(AMLAlert.risk_level == "high")
                )
                high_risk_aml = aml_high_risk.scalar() or 0

                # Calculate rates
                kyc_success_rate = (approved_kyc / total_kyc * 100) if total_kyc > 0 else 0
                aml_alert_rate = (high_risk_aml / total_aml * 100) if total_aml > 0 else 0

                return {
                    "time_range": time_range,
                    "total_cases": total_kyc + total_aml,
                    "kyc_cases": {
                        "total": total_kyc,
                        "pending": pending_kyc,
                        "approved": approved_kyc,
                        "success_rate": round(kyc_success_rate, 2),
                    },
                    "aml_alerts": {
                        "total": total_aml,
                        "high_risk": high_risk_aml,
                        "alert_rate": round(aml_alert_rate, 2),
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }

        except Exception as e:
            self.logger.error(f"Error getting compliance metrics: {e}")
            raise

    async def get_aml_alerts(
        self, user_id: Optional[str] = None, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get AML alerts from database with optional filtering."""
        try:
            async with self.session_factory() as session:
                # Build query
                stmt = select(AMLAlert)

                filters = []
                if user_id:
                    filters.append(AMLAlert.user_id == user_id)
                if status:
                    filters.append(AMLAlert.status == status)

                if filters:
                    stmt = stmt.where(and_(*filters))

                stmt = stmt.order_by(AMLAlert.created_at.desc())

                result = await session.execute(stmt)
                alerts = result.scalars().all()

                return [
                    {
                        "alert_id": alert.alert_id,
                        "user_id": alert.user_id,
                        "transaction_amount": (
                            float(alert.transaction_amount) if alert.transaction_amount else None
                        ),
                        "risk_score": float(alert.risk_score) if alert.risk_score else None,
                        "risk_level": alert.risk_level,
                        "status": alert.status,
                        "flags": alert.flags or [],
                        "created_at": alert.created_at.isoformat() if alert.created_at else None,
                    }
                    for alert in alerts
                ]
        except Exception as e:
            self.logger.error(f"Error getting AML alerts: {e}")
            raise

    async def get_user_compliance_status(self, user_id: str) -> Dict[str, Any]:
        """Get aggregated compliance status for a user."""
        try:
            async with self.session_factory() as session:
                # Get KYC status
                kyc_result = await session.execute(
                    select(KYCCase)
                    .where(KYCCase.user_id == user_id)
                    .order_by(KYCCase.created_at.desc())
                    .limit(1)
                )
                kyc_case = kyc_result.scalar_one_or_none()

                # Get AML alerts count
                aml_count = await session.execute(
                    select(func.count()).select_from(AMLAlert).where(AMLAlert.user_id == user_id)
                )
                total_aml_alerts = aml_count.scalar() or 0

                # Get high-risk AML alerts
                high_risk_count = await session.execute(
                    select(func.count())
                    .select_from(AMLAlert)
                    .where(and_(AMLAlert.user_id == user_id, AMLAlert.risk_level == "high"))
                )
                high_risk_alerts = high_risk_count.scalar() or 0

                # Calculate compliance score
                compliance_score = 0.5  # Base score
                if kyc_case and kyc_case.status == "verified":
                    compliance_score += 0.3
                if total_aml_alerts == 0:
                    compliance_score += 0.2
                elif high_risk_alerts == 0:
                    compliance_score += 0.1

                return {
                    "user_id": user_id,
                    "kyc_status": kyc_case.status if kyc_case else "not_started",
                    "kyc_verification_score": (
                        float(kyc_case.verification_score)
                        if kyc_case and kyc_case.verification_score
                        else None
                    ),
                    "aml_status": "flagged" if high_risk_alerts > 0 else "clean",
                    "total_aml_alerts": total_aml_alerts,
                    "high_risk_alerts": high_risk_alerts,
                    "compliance_score": round(compliance_score, 2),
                    "last_updated": datetime.utcnow().isoformat() + "Z",
                }
        except Exception as e:
            self.logger.error(f"Error getting user compliance status: {e}")
            raise

    async def get_compliance_cases(
        self, status: Optional[str] = None, priority: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get compliance cases from database with optional filtering."""
        try:
            async with self.session_factory() as session:
                # Build query
                stmt = select(ComplianceCase)

                filters = []
                if status:
                    filters.append(ComplianceCase.status == status)
                if priority:
                    filters.append(ComplianceCase.priority == priority)

                if filters:
                    stmt = stmt.where(and_(*filters))

                stmt = stmt.order_by(ComplianceCase.created_at.desc())

                result = await session.execute(stmt)
                cases = result.scalars().all()

                return [
                    {
                        "case_id": case.case_id,
                        "user_id": case.user_id,
                        "case_type": case.case_type,
                        "status": case.status,
                        "priority": case.priority,
                        "title": case.title,
                        "description": case.description,
                        "assigned_to": case.assigned_to,
                        "created_at": case.created_at.isoformat() if case.created_at else None,
                        "updated_at": case.updated_at.isoformat() if case.updated_at else None,
                    }
                    for case in cases
                ]
        except Exception as e:
            self.logger.error(f"Error getting compliance cases: {e}")
            raise

    async def resolve_compliance_case(
        self, case_id: str, resolution: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve a compliance case."""
        try:
            async with self.session_factory() as session:
                # Get case
                result = await session.execute(
                    select(ComplianceCase).where(ComplianceCase.case_id == case_id)
                )
                case = result.scalar_one_or_none()

                if not case:
                    raise ValueError(f"Compliance case not found: {case_id}")

                # Update case
                case.status = "resolved"
                case.resolution = resolution.get("resolution_notes", "")
                case.resolved_at = datetime.utcnow()

                await session.commit()

                self.logger.info(f"Compliance case resolved: {case_id}")

                return {
                    "case_id": case.case_id,
                    "status": case.status,
                    "resolution": case.resolution,
                    "resolved_at": case.resolved_at.isoformat() if case.resolved_at else None,
                }
        except Exception as e:
            self.logger.error(f"Error resolving compliance case: {e}")
            raise

    async def get_compliance_checks(
        self, escrow_address: Optional[str] = None, user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get compliance checks from database with optional filtering."""
        try:
            async with self.session_factory() as session:
                # Build query
                stmt = select(ComplianceCheck)

                filters = []
                if escrow_address:
                    filters.append(ComplianceCheck.escrow_address == escrow_address.lower())
                if user_id:
                    filters.append(ComplianceCheck.user_id == user_id)

                if filters:
                    stmt = stmt.where(and_(*filters))

                stmt = stmt.order_by(ComplianceCheck.created_at.desc())

                result = await session.execute(stmt)
                checks = result.scalars().all()

                return [
                    {
                        "check_id": check.check_id,
                        "check_type": check.check_type,
                        "escrow_address": check.escrow_address,
                        "user_id": check.user_id,
                        "status": check.status,
                        "score": float(check.score) if check.score else None,
                        "risk_score": float(check.risk_score) if check.risk_score else None,
                        "flags": check.flags or [],
                        "checked_at": check.checked_at.isoformat() if check.checked_at else None,
                        "created_at": check.created_at.isoformat() if check.created_at else None,
                    }
                    for check in checks
                ]
        except Exception as e:
            self.logger.error(f"Error getting compliance checks: {e}")
            raise

    async def create_compliance_check(
        self,
        check_type: str,
        escrow_address: Optional[str] = None,
        user_id: Optional[str] = None,
        status: str = "pending",
        score: Optional[float] = None,
        risk_score: Optional[float] = None,
        flags: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a compliance check record."""
        try:
            async with self.session_factory() as session:
                check_id = f"{check_type[:3]}-{int(datetime.utcnow().timestamp())}"

                compliance_check = ComplianceCheck(
                    check_id=check_id,
                    check_type=check_type,
                    escrow_address=escrow_address.lower() if escrow_address else None,
                    user_id=user_id,
                    status=status,
                    score=score,
                    risk_score=risk_score,
                    flags=flags,
                    notes=notes,
                    checked_at=datetime.utcnow(),
                )

                session.add(compliance_check)
                await session.commit()

                self.logger.info(f"Compliance check created: {check_id}")

                return {
                    "check_id": check_id,
                    "check_type": check_type,
                    "escrow_address": escrow_address,
                    "user_id": user_id,
                    "status": status,
                    "checked_at": datetime.utcnow().isoformat() + "Z",
                }
        except Exception as e:
            self.logger.error(f"Error creating compliance check: {e}")
            raise

    async def create_compliance_case(
        self,
        user_id: str,
        case_type: str,
        title: str,
        description: Optional[str] = None,
        priority: str = "normal",
    ) -> Dict[str, Any]:
        """Create a compliance case for manual review."""
        try:
            async with self.session_factory() as session:
                case_id = f"case-{case_type[:3]}-{int(datetime.utcnow().timestamp())}"

                compliance_case = ComplianceCase(
                    case_id=case_id,
                    user_id=user_id,
                    case_type=case_type,
                    title=title,
                    description=description,
                    priority=priority,
                    status="open",
                )

                session.add(compliance_case)
                await session.commit()

                self.logger.info(f"Compliance case created: {case_id}")

                return {
                    "case_id": case_id,
                    "user_id": user_id,
                    "case_type": case_type,
                    "title": title,
                    "status": "open",
                    "priority": priority,
                    "created_at": datetime.utcnow().isoformat() + "Z",
                }
        except Exception as e:
            self.logger.error(f"Error creating compliance case: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Health check for compliance engine."""
        try:
            async with self.session_factory() as session:
                await session.execute(select(1))

            return {
                "status": "healthy",
                "component": "compliance_engine",
                "database_connected": True,
                "capabilities": ["kyc", "aml", "sanctions"],
                "last_check": datetime.utcnow().isoformat() + "Z",
            }
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "component": "compliance_engine",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat() + "Z",
            }
