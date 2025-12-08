"""Contract ABIs for escrow relayer"""

from typing import Any, Dict, List

# Escrow Factory contract ABI - for discovering new escrows
FACTORY_ABI: List[Dict[str, Any]] = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "escrow", "type": "address"},
            {"indexed": True, "name": "payer", "type": "address"},
            {"indexed": True, "name": "payee", "type": "address"},
            {"indexed": False, "name": "amount", "type": "uint256"},
            {"indexed": False, "name": "releaseDelay", "type": "uint256"},
            {"indexed": False, "name": "approvalsRequired", "type": "uint8"},
        ],
        "name": "EscrowDeployed",
        "type": "event",
    },
]

# Individual Escrow contract ABI - for lifecycle events
ESCROW_CONTRACT_ABI: List[Dict[str, Any]] = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "approver", "type": "address"},
        ],
        "name": "Approved",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "payee", "type": "address"},
            {"indexed": False, "name": "amount", "type": "uint256"},
        ],
        "name": "EscrowReleased",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "payer", "type": "address"},
            {"indexed": False, "name": "amount", "type": "uint256"},
        ],
        "name": "EscrowRefunded",
        "type": "event",
    },
]
