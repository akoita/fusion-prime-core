"""
Margin Health Calculator for Risk Engine.

Calculates margin health scores and detects margin events (warnings, margin calls, liquidations).
"""

import logging
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

from app.integrations.price_oracle_client import PriceOracleClient

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Margin health status levels."""

    HEALTHY = "HEALTHY"  # >= 50%
    WARNING = "WARNING"  # 30% - 50%
    MARGIN_CALL = "MARGIN_CALL"  # 15% - 30%
    LIQUIDATION = "LIQUIDATION"  # < 15%


class MarginHealthCalculator:
    """
    Calculate margin health scores for user positions.

    Margin Health Formula:
        health_score = (total_collateral_usd - total_borrow_usd) / total_borrow_usd * 100

    Status Thresholds:
        - HEALTHY: health_score >= 50%
        - WARNING: 30% <= health_score < 50%
        - MARGIN_CALL: 15% <= health_score < 30%
        - LIQUIDATION: health_score < 15%
    """

    def __init__(self, price_oracle_client: PriceOracleClient):
        """
        Initialize margin health calculator.

        Args:
            price_oracle_client: Client for fetching real-time USD prices
        """
        self.price_oracle = price_oracle_client
        logger.info("Margin health calculator initialized")

    async def calculate_health_score(
        self,
        user_id: str,
        collateral_positions: Dict[str, float],  # {asset_symbol: amount}
        borrow_positions: Dict[str, float],  # {asset_symbol: amount}
    ) -> Dict[str, any]:
        """
        Calculate margin health score for a user's positions.

        Args:
            user_id: User identifier
            collateral_positions: Dictionary mapping asset symbol to collateral amount
            borrow_positions: Dictionary mapping asset symbol to borrow amount

        Returns:
            Dictionary with health metrics:
            {
                "user_id": str,
                "health_score": float,  # percentage
                "status": HealthStatus,
                "total_collateral_usd": float,
                "total_borrow_usd": float,
                "liquidation_price": float,  # Approximate price drop % before liquidation
                "collateral_breakdown": Dict[str, Dict],
                "borrow_breakdown": Dict[str, Dict],
                "calculated_at": str
            }
        """
        try:
            logger.info(f"Calculating margin health for user {user_id}")

            # Step 1: Fetch current prices for all assets
            all_assets = set(collateral_positions.keys()) | set(borrow_positions.keys())
            current_prices = await self.price_oracle.get_multiple_prices(list(all_assets))

            # Step 2: Calculate total collateral value in USD
            collateral_breakdown = {}
            total_collateral_usd = 0.0

            for asset_symbol, amount in collateral_positions.items():
                price_usd = float(current_prices.get(asset_symbol, 0))
                value_usd = amount * price_usd

                collateral_breakdown[asset_symbol] = {
                    "amount": amount,
                    "price_usd": price_usd,
                    "value_usd": value_usd,
                }

                total_collateral_usd += value_usd

            # Step 3: Calculate total borrow value in USD
            borrow_breakdown = {}
            total_borrow_usd = 0.0

            for asset_symbol, amount in borrow_positions.items():
                price_usd = float(current_prices.get(asset_symbol, 0))
                value_usd = amount * price_usd

                borrow_breakdown[asset_symbol] = {
                    "amount": amount,
                    "price_usd": price_usd,
                    "value_usd": value_usd,
                }

                total_borrow_usd += value_usd

            # Step 4: Calculate health score
            if total_borrow_usd == 0:
                # No borrows = infinite health
                health_score = 100.0
                status = HealthStatus.HEALTHY
            else:
                # health_score = (collateral - borrow) / borrow * 100
                health_score = ((total_collateral_usd - total_borrow_usd) / total_borrow_usd) * 100
                status = self._determine_status(health_score)

            # Step 5: Calculate liquidation price (approximate)
            # This is the percentage drop in collateral value before liquidation
            if total_borrow_usd > 0 and total_collateral_usd > 0:
                # Liquidation occurs when health_score < 15%
                # 15% = (collateral - borrow) / borrow * 100
                # 0.15 = (collateral - borrow) / borrow
                # 0.15 * borrow = collateral - borrow
                # 1.15 * borrow = collateral
                # liquidation_collateral = 1.15 * borrow

                liquidation_collateral = 1.15 * total_borrow_usd
                liquidation_price_drop = (
                    (total_collateral_usd - liquidation_collateral) / total_collateral_usd
                ) * 100
            else:
                liquidation_price_drop = 0.0

            return {
                "user_id": user_id,
                "health_score": round(health_score, 2),
                "status": status.value,
                "total_collateral_usd": round(total_collateral_usd, 2),
                "total_borrow_usd": round(total_borrow_usd, 2),
                "liquidation_price_drop_percent": round(liquidation_price_drop, 2),
                "collateral_breakdown": collateral_breakdown,
                "borrow_breakdown": borrow_breakdown,
                "calculated_at": datetime.utcnow().isoformat() + "Z",
            }

        except Exception as e:
            logger.error(f"Error calculating margin health for user {user_id}: {e}")
            return self._empty_health_result(user_id)

    def _determine_status(self, health_score: float) -> HealthStatus:
        """
        Determine health status based on health score.

        Args:
            health_score: Health score percentage

        Returns:
            HealthStatus enum value
        """
        if health_score >= 50:
            return HealthStatus.HEALTHY
        elif health_score >= 30:
            return HealthStatus.WARNING
        elif health_score >= 15:
            return HealthStatus.MARGIN_CALL
        else:
            return HealthStatus.LIQUIDATION

    def _empty_health_result(self, user_id: str) -> Dict[str, any]:
        """Return empty health result when calculation fails."""
        return {
            "user_id": user_id,
            "health_score": 0.0,
            "status": HealthStatus.LIQUIDATION.value,
            "total_collateral_usd": 0.0,
            "total_borrow_usd": 0.0,
            "liquidation_price_drop_percent": 0.0,
            "collateral_breakdown": {},
            "borrow_breakdown": {},
            "calculated_at": datetime.utcnow().isoformat() + "Z",
        }

    async def check_margin_events(
        self,
        user_id: str,
        collateral_positions: Dict[str, float],
        borrow_positions: Dict[str, float],
        previous_health_score: Optional[float] = None,
    ) -> Optional[Dict[str, any]]:
        """
        Check for margin events (status changes requiring alerts).

        Args:
            user_id: User identifier
            collateral_positions: Current collateral positions
            borrow_positions: Current borrow positions
            previous_health_score: Previous health score (if available)

        Returns:
            Margin event dictionary if event detected, None otherwise:
            {
                "event_type": "margin_warning" | "margin_call" | "liquidation_imminent",
                "user_id": str,
                "health_score": float,
                "previous_health_score": float,
                "status": HealthStatus,
                "severity": "low" | "medium" | "high" | "critical",
                "message": str,
                "timestamp": str
            }
        """
        health_result = await self.calculate_health_score(
            user_id, collateral_positions, borrow_positions
        )

        current_health_score = health_result["health_score"]
        current_status = HealthStatus(health_result["status"])

        # Determine if an event should be triggered
        event_type = None
        severity = None
        message = None

        if current_status == HealthStatus.LIQUIDATION:
            event_type = "liquidation_imminent"
            severity = "critical"
            message = f"LIQUIDATION IMMINENT: Health score {current_health_score:.2f}% (< 15%). Immediate action required."

        elif current_status == HealthStatus.MARGIN_CALL:
            event_type = "margin_call"
            severity = "high"
            message = f"MARGIN CALL: Health score {current_health_score:.2f}% (15-30%). Add collateral or reduce borrows."

        elif current_status == HealthStatus.WARNING:
            # Only trigger warning if crossing into warning zone
            if previous_health_score is not None and previous_health_score >= 50:
                event_type = "margin_warning"
                severity = "medium"
                message = f"Margin Warning: Health score {current_health_score:.2f}% (30-50%). Monitor position closely."

        # Return event if detected
        if event_type:
            return {
                "event_type": event_type,
                "user_id": user_id,
                "health_score": current_health_score,
                "previous_health_score": previous_health_score,
                "status": current_status.value,
                "severity": severity,
                "message": message,
                "total_collateral_usd": health_result["total_collateral_usd"],
                "total_borrow_usd": health_result["total_borrow_usd"],
                "liquidation_price_drop_percent": health_result["liquidation_price_drop_percent"],
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        return None

    async def batch_calculate_health_scores(
        self, user_positions: List[Dict[str, any]]
    ) -> List[Dict[str, any]]:
        """
        Calculate health scores for multiple users in batch.

        Args:
            user_positions: List of position dictionaries:
                [
                    {
                        "user_id": str,
                        "collateral": Dict[str, float],
                        "borrows": Dict[str, float]
                    },
                    ...
                ]

        Returns:
            List of health score results
        """
        results = []

        for position in user_positions:
            user_id = position["user_id"]
            collateral = position.get("collateral", {})
            borrows = position.get("borrows", {})

            health_result = await self.calculate_health_score(user_id, collateral, borrows)
            results.append(health_result)

        return results
