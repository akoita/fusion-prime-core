"""Escrow relayer implementation using web3.py."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from google.cloud import pubsub_v1
from web3 import Web3
from web3.types import EventData

from analytics.schemas.pubsub.fusionprime.settlement.v1 import (  # type: ignore
    settlement_pb2,
)


@dataclass
class EscrowEvent:
    command_id: str
    workflow_id: str
    payer: str
    payee: str
    chain_id: str
    status: settlement_pb2.EventStatus


class EscrowRelayer:
    def __init__(
        self,
        web3: Web3,
        contract_address: str,
        topic_path: str,
        publisher: pubsub_v1.PublisherClient,
    ) -> None:
        self._web3 = web3
        self._contract_address = Web3.to_checksum_address(contract_address)
        self._publisher = publisher
        self._topic_path = topic_path

    def fetch_events(self, from_block: int, to_block: int) -> Iterable[EventData]:
        contract = self._web3.eth.contract(
            address=self._contract_address,
            abi=[
                {
                    "anonymous": False,
                    "inputs": [
                        {
                            "indexed": True,
                            "internalType": "address",
                            "name": "payee",
                            "type": "address",
                        },
                        {
                            "indexed": False,
                            "internalType": "uint256",
                            "name": "amount",
                            "type": "uint256",
                        },
                    ],
                    "name": "EscrowReleased",
                    "type": "event",
                }
            ],
        )
        event_filter = contract.events.EscrowReleased.create_filter(
            fromBlock=from_block, toBlock=to_block
        )
        return event_filter.get_all_entries()

    def publish(self, escrow_event: EscrowEvent) -> None:
        message = settlement_pb2.SettlementEvent(
            event_id=f"escrow-{escrow_event.command_id}",
            command_id=escrow_event.command_id,
            workflow_id=escrow_event.workflow_id,
            payer=escrow_event.payer,
            payee=escrow_event.payee,
            chain_id=escrow_event.chain_id,
            status=escrow_event.status,
        )
        self._publisher.publish(self._topic_path, message.SerializeToString())
