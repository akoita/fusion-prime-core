"""Escrow Registry - maintains discovered escrow contract addresses"""

import json
import logging
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)


class EscrowRegistry:
    """
    Manages discovered escrow addresses with persistence.

    The registry maintains an in-memory set of escrow addresses that have been
    discovered from Factory EscrowDeployed events. It persists this set to a
    checkpoint file for recovery after restarts.

    Usage:
        registry = EscrowRegistry("/tmp/escrow_registry.json")

        # Add new escrow
        if registry.add_escrow("0xABC..."):
            print("New escrow discovered!")

        # Get all escrows to monitor
        escrows = registry.get_all_escrows()

        # Save checkpoint
        registry.save()
    """

    def __init__(self, checkpoint_file: str = "/tmp/escrow_registry.json"):
        """
        Initialize the registry.

        Args:
            checkpoint_file: Path to JSON file for persistence
        """
        self.checkpoint_file = Path(checkpoint_file)
        self.escrows: Set[str] = set()
        self._load()

    def add_escrow(self, address: str) -> bool:
        """
        Add new escrow address to registry.

        Args:
            address: Escrow contract address (will be lowercased)

        Returns:
            True if newly added, False if already existed
        """
        address_lower = address.lower()
        if address_lower not in self.escrows:
            self.escrows.add(address_lower)
            logger.info(f"📝 New escrow discovered: {address_lower}")
            return True
        return False

    def get_all_escrows(self) -> Set[str]:
        """
        Get all registered escrow addresses.

        Returns:
            Set of escrow addresses (all lowercase)
        """
        return self.escrows.copy()

    def count(self) -> int:
        """Get count of registered escrows."""
        return len(self.escrows)

    def contains(self, address: str) -> bool:
        """Check if address is in registry."""
        return address.lower() in self.escrows

    def save(self) -> None:
        """
        Persist registry to checkpoint file.

        Saves the current set of escrows to a JSON file for recovery.
        """
        try:
            data = {
                "escrows": sorted(list(self.escrows)),  # Sort for consistent output
                "count": len(self.escrows),
                "version": "1.0",
            }

            # Ensure directory exists
            self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

            # Write to temp file first, then rename (atomic)
            temp_file = self.checkpoint_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)
            temp_file.replace(self.checkpoint_file)

            logger.debug(f"Saved {len(self.escrows)} escrows to {self.checkpoint_file}")
        except Exception as e:
            logger.error(f"Failed to save registry to {self.checkpoint_file}: {e}")

    def _load(self) -> None:
        """
        Load registry from checkpoint file.

        If the file doesn't exist or is invalid, starts with an empty registry.
        """
        if not self.checkpoint_file.exists():
            logger.info("No existing registry checkpoint found, starting fresh")
            return

        try:
            with open(self.checkpoint_file, "r") as f:
                data = json.load(f)

            escrows_list = data.get("escrows", [])
            self.escrows = set(addr.lower() for addr in escrows_list)

            logger.info(f"📚 Loaded {len(self.escrows)} escrows from {self.checkpoint_file}")

            # Log some examples if we have escrows
            if self.escrows:
                examples = list(self.escrows)[:3]
                logger.info(f"   Examples: {', '.join(examples)}")

        except Exception as e:
            logger.error(
                f"Failed to load registry from {self.checkpoint_file}: {e}, " "starting fresh"
            )
            self.escrows = set()

    def clear(self) -> None:
        """Clear all escrows from registry (useful for testing)."""
        self.escrows.clear()
        logger.info("Registry cleared")

    def __len__(self) -> int:
        """Return count of escrows."""
        return len(self.escrows)

    def __contains__(self, address: str) -> bool:
        """Support 'address in registry' syntax."""
        return self.contains(address)

    def __repr__(self) -> str:
        """String representation."""
        return f"EscrowRegistry(count={len(self.escrows)}, checkpoint={self.checkpoint_file})"
