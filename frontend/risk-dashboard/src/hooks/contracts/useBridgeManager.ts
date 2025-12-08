import { useReadContract, useWriteContract, useWaitForTransactionReceipt } from 'wagmi';
import { type Address, type Hex, parseEther, keccak256, encodeAbiParameters } from 'viem';
import { sepolia } from 'wagmi/chains';
import { CONTRACTS } from '@/config/chains';
import { polygonAmoy } from '@/config/chains';
import BridgeManagerABI from '@/abis/BridgeManager.json';

/**
 * Hook to check if a chain is supported for cross-chain messaging
 *
 * @param chainName - Name of the chain to check (e.g., "polygon-amoy", "ethereum-sepolia")
 * @param chainId - The chain ID to query from
 * @returns Object containing boolean indicating if chain is supported
 *
 * @example
 * const { data: isSupported } = useIsChainSupportedForBridge('polygon-amoy');
 */
export function useIsChainSupportedForBridge(chainName?: string, chainId: number = sepolia.id) {
  const contractAddress = CONTRACTS[chainId]?.BridgeManager as Address;

  return useReadContract({
    address: contractAddress,
    abi: BridgeManagerABI,
    functionName: 'isChainSupported',
    args: chainName ? [chainName] : undefined,
    chainId,
    query: {
      enabled: !!chainName && !!contractAddress,
    },
  });
}

/**
 * Hook to get all registered bridge protocols
 *
 * @param chainId - The chain ID to query from
 * @returns Object containing array of registered protocols (e.g., ["axelar", "ccip"])
 *
 * @example
 * const { data: protocols } = useRegisteredProtocols();
 * // Returns: ["axelar", "ccip"]
 */
export function useRegisteredProtocols(chainId: number = sepolia.id) {
  const contractAddress = CONTRACTS[chainId]?.BridgeManager as Address;

  return useReadContract({
    address: contractAddress,
    abi: BridgeManagerABI,
    functionName: 'getRegisteredProtocols',
    chainId,
    query: {
      enabled: !!contractAddress,
    },
  });
}

/**
 * Hook to get the preferred bridge protocol for a destination chain
 *
 * @param chainName - Name of the destination chain
 * @param chainId - The chain ID to query from
 * @returns Object containing preferred protocol name
 *
 * @example
 * const { data: protocol } = usePreferredProtocol('polygon-amoy');
 * // Returns: "axelar" or "ccip"
 */
export function usePreferredProtocol(chainName?: string, chainId: number = sepolia.id) {
  const contractAddress = CONTRACTS[chainId]?.BridgeManager as Address;

  return useReadContract({
    address: contractAddress,
    abi: BridgeManagerABI,
    functionName: 'preferredProtocol',
    args: chainName ? [chainName] : undefined,
    chainId,
    query: {
      enabled: !!chainName && !!contractAddress,
    },
  });
}

/**
 * Hook to get the adapter address for a specific protocol
 *
 * @param protocolName - Name of the protocol (e.g., "axelar", "ccip")
 * @param chainId - The chain ID to query from
 * @returns Object containing adapter contract address
 *
 * @example
 * const { data: adapterAddress } = useAdapterAddress('axelar');
 */
export function useAdapterAddress(protocolName?: string, chainId: number = sepolia.id) {
  const contractAddress = CONTRACTS[chainId]?.BridgeManager as Address;

  return useReadContract({
    address: contractAddress,
    abi: BridgeManagerABI,
    functionName: 'adapters',
    args: protocolName ? [protocolName] : undefined,
    chainId,
    query: {
      enabled: !!protocolName && !!contractAddress,
    },
  });
}

/**
 * Hook to estimate gas cost for a cross-chain message
 *
 * @param destinationChain - Name of the destination chain
 * @param payload - Message payload as hex string
 * @param chainId - The chain ID to query from
 * @returns Object containing estimated gas and protocol that will be used
 *
 * @example
 * const { data: estimate } = useEstimateCrossChainGas(
 *   'polygon-amoy',
 *   '0x1234...'
 * );
 * // Returns: { estimatedGas: 200000n, protocol: "axelar" }
 */
export function useEstimateCrossChainGas(
  destinationChain?: string,
  payload?: Hex,
  chainId: number = sepolia.id
) {
  const contractAddress = CONTRACTS[chainId]?.BridgeManager as Address;

  return useReadContract({
    address: contractAddress,
    abi: BridgeManagerABI,
    functionName: 'estimateGas',
    args: destinationChain && payload ? [destinationChain, payload] : undefined,
    chainId,
    query: {
      enabled: !!destinationChain && !!payload && !!contractAddress,
    },
  });
}

/**
 * Hook to send a cross-chain message
 *
 * @param chainId - The chain ID to send from
 * @returns Object with sendMessage function and transaction state
 *
 * @example
 * const { sendMessage, isLoading, isSuccess, messageId } = useSendCrossChainMessage();
 *
 * sendMessage({
 *   destinationChain: 'polygon-amoy',
 *   destinationAddress: '0x...',
 *   payload: '0x1234...',
 *   gasToken: '0x0000000000000000000000000000000000000000', // Native token
 *   gasAmount: '0.1', // ETH for gas fees
 * });
 */
export function useSendCrossChainMessage(chainId: number = sepolia.id) {
  const contractAddress = CONTRACTS[chainId]?.BridgeManager as Address;

  const { data: hash, writeContract, isPending, isError, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess: txMined, data: receipt } = useWaitForTransactionReceipt({
    hash,
  });

  // Check if transaction actually succeeded on-chain (not just mined)
  // receipt.status can be 'success' or 'reverted'
  const isSuccess = txMined && receipt?.status === 'success';
  const isReverted = txMined && receipt?.status === 'reverted';

  /**
   * Send a cross-chain message
   *
   * @param destinationChain - Name of destination chain (e.g., "polygon-amoy")
   * @param destinationAddress - Address on destination chain (as string, e.g., "0x...")
   * @param payload - Message payload (as hex string)
   * @param gasToken - Token address to pay for gas (use 0x0 for native token)
   * @param gasAmount - Amount of native token to send for gas fees (as string, e.g., "0.1")
   */
  const sendMessage = ({
    destinationChain,
    destinationAddress,
    payload,
    gasToken,
    gasAmount,
  }: {
    destinationChain: string;
    destinationAddress: string;
    payload: Hex;
    gasToken: Address;
    gasAmount: string;
  }) => {
    writeContract({
      address: contractAddress,
      abi: BridgeManagerABI,
      functionName: 'sendMessage',
      args: [destinationChain, destinationAddress, payload, gasToken],
      value: parseEther(gasAmount),
      chainId,
    });
  };

  // Extract messageId from receipt logs if available
  const messageId = receipt?.logs?.[0]?.data as Hex | undefined;

  return {
    sendMessage,
    isLoading: isPending || isConfirming,
    isSuccess,
    isError: isError || isReverted, // Error if user rejected OR transaction reverted
    error,
    txHash: hash,
    messageId, // The cross-chain message ID
  };
}

/**
 * Hook to set preferred protocol for a destination chain (admin only)
 *
 * @param chainId - The chain ID to execute on
 * @returns Object with setPreferredProtocol function and transaction state
 *
 * @example
 * const { setPreferredProtocol, isLoading } = useSetPreferredProtocol();
 * setPreferredProtocol({
 *   chainName: 'polygon-amoy',
 *   protocolName: 'axelar',
 * });
 */
export function useSetPreferredProtocol(chainId: number = sepolia.id) {
  const contractAddress = CONTRACTS[chainId]?.BridgeManager as Address;

  const { data: hash, writeContract, isPending, isError, error } = useWriteContract();

  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({
    hash,
  });

  const setPreferredProtocol = ({
    chainName,
    protocolName,
  }: {
    chainName: string;
    protocolName: string;
  }) => {
    writeContract({
      address: contractAddress,
      abi: BridgeManagerABI,
      functionName: 'setPreferredProtocol',
      args: [chainName, protocolName],
      chainId,
    });
  };

  return {
    setPreferredProtocol,
    isLoading: isPending || isConfirming,
    isSuccess,
    isError,
    error,
    txHash: hash,
  };
}

/**
 * Helper to create a vault deposit payload for cross-chain balance sync
 * This encodes the data format expected by CrossChainVault
 *
 * @param user - User address depositing
 * @param amount - Amount to deposit (in wei as bigint)
 * @param sourceChain - Source chain name (e.g., "ethereum-sepolia")
 * @returns Encoded payload as hex string
 *
 * Payload format matches CrossChainVault._processMessage:
 * (bytes32 messageId, address user, uint8 action, uint256 amount, string chainName)
 */
export function encodeSettlementPayload(user: Address, amount: bigint, sourceChain: string = 'ethereum-sepolia'): Hex {
  // Generate a unique message ID based on timestamp and user
  const messageId = keccak256(
    encodeAbiParameters(
      [{ type: 'uint256' }, { type: 'address' }, { type: 'uint256' }],
      [BigInt(Date.now()), user, amount]
    )
  );

  // Action codes:
  // 1 = Deposit (collateral update)
  // 2 = Withdrawal (collateral update)
  // 3 = Borrow
  // 4 = Repay
  const action = 1; // Deposit

  // ABI encode the full payload
  return encodeAbiParameters(
    [
      { type: 'bytes32', name: 'messageId' },
      { type: 'address', name: 'user' },
      { type: 'uint8', name: 'action' },
      { type: 'uint256', name: 'amount' },
      { type: 'string', name: 'chainName' },
    ],
    [messageId, user, action, amount, sourceChain]
  );
}

/**
 * Hook to get bridge data for all supported chains
 * This is a convenience hook that aggregates bridge info
 *
 * @param chainId - The chain ID to query from
 * @returns Object containing bridge data
 *
 * @example
 * const { protocols, sepoliaSupported, amoySupported, isLoading } = useBridgeInfo();
 */
export function useBridgeInfo(chainId: number = sepolia.id) {
  const protocols = useRegisteredProtocols(chainId);
  const sepoliaSupported = useIsChainSupportedForBridge('ethereum-sepolia', chainId);
  const amoySupported = useIsChainSupportedForBridge('polygon-sepolia', chainId);
  const sepoliaProtocol = usePreferredProtocol('ethereum-sepolia', chainId);
  const amoyProtocol = usePreferredProtocol('polygon-sepolia', chainId);

  return {
    protocols: protocols.data,
    supportedChains: {
      sepolia: sepoliaSupported.data,
      amoy: amoySupported.data,
    },
    preferredProtocols: {
      sepolia: sepoliaProtocol.data,
      amoy: amoyProtocol.data,
    },
    isLoading:
      protocols.isLoading ||
      sepoliaSupported.isLoading ||
      amoySupported.isLoading ||
      sepoliaProtocol.isLoading ||
      amoyProtocol.isLoading,
    isError:
      protocols.isError ||
      sepoliaSupported.isError ||
      amoySupported.isError ||
      sepoliaProtocol.isError ||
      amoyProtocol.isError,
  };
}

/**
 * Chain name mapping for consistency
 * IMPORTANT: These names must match exactly what's configured in the BridgeManager contract
 * Updated for V2 deployment with testnet-specific chain names
 * See: contracts/cross-chain/script/DeployBridgeV2.s.sol
 */
export const BRIDGE_CHAIN_NAMES = {
  [sepolia.id]: 'ethereum-sepolia',
  [polygonAmoy.id]: 'polygon-sepolia',
} as const;

/**
 * Get bridge chain name from chain ID
 */
export function getBridgeChainName(chainId: number): string {
  return BRIDGE_CHAIN_NAMES[chainId as keyof typeof BRIDGE_CHAIN_NAMES] || '';
}
