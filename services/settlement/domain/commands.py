"""Domain commands for settlement workflows."""

from datetime import datetime
from typing import Literal

CommandType = Literal["DVP", "COLLATERAL_TRANSFER"]


class SettlementCommand:
    def __init__(
        self,
        command_id: str,
        workflow_id: str,
        account_ref: str,
        asset_symbol: str,
        amount: str,
        deadline: datetime,
        command_type: CommandType,
    ) -> None:
        self.command_id = command_id
        self.workflow_id = workflow_id
        self.account_ref = account_ref
        self.asset_symbol = asset_symbol
        self.amount = amount
        self.deadline = deadline
        self.command_type = command_type


__all__ = ["SettlementCommand", "CommandType"]
