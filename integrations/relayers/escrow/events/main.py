"""Escrow event relayer prototype."""

import json
import os
from dataclasses import dataclass

from google.cloud import pubsub_v1
from web3 import Web3

from analytics.schemas.pubsub.fusionprime.settlement.v1 import (  # type: ignore
    settlement_pb2,
)


@dataclass
class Config:
    rpc_url: str
    contract_address: str
    topic: str
    project_id: str


class EscrowRelayer:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._web3 = Web3(Web3.HTTPProvider(config.rpc_url))
        self._publisher = pubsub_v1.PublisherClient()
        self._topic_path = self._publisher.topic_path(config.project_id, config.topic)

    def run_once(self) -> None:
        # Placeholder: fetch events via RPC (not implemented)
        events = [
            {
                "event_id": "evt-placeholder",
                "command_id": "cmd-1",
                "workflow_id": "wf-1",
                "payer": "0xPAYER",
                "payee": "0xPAYEE",
                "amount": "1000",
                "chain_id": "1",
                "status": settlement_pb2.EVENT_STATUS_CONFIRMED,
            }
        ]

        for evt in events:
            message = settlement_pb2.SettlementEvent(
                event_id=evt["event_id"],
                command_id=evt["command_id"],
                workflow_id=evt["workflow_id"],
                status=evt["status"],
                payer=evt["payer"],
                payee=evt["payee"],
                chain_id=evt["chain_id"],
            )
            self._publisher.publish(self._topic_path, message.SerializeToString()).result()


def load_config() -> Config:
    return Config(
        rpc_url=os.environ.get("RPC_URL", "http://localhost:8545"),
        contract_address=os.environ.get("CONTRACT_ADDRESS", "0x0"),
        topic=os.environ.get("PUBSUB_TOPIC", "settlement.events.v1"),
        project_id=os.environ["GCP_PROJECT"],
    )


if __name__ == "__main__":
    config = load_config()
    relayer = EscrowRelayer(config)
    relayer.run_once()
