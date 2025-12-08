/**
 * Escrow Indexer API Client
 *
 * Provides fast queries to indexed escrow data instead of scanning the blockchain.
 * The indexer service maintains a PostgreSQL database of all escrows and their states,
 * updated in real-time via Pub/Sub events from the relayer.
 */

import axios, { AxiosInstance } from 'axios';
import type { Address } from 'viem';

// Get indexer service URL from environment
const ESCROW_INDEXER_URL =
  import.meta.env.VITE_ESCROW_INDEXER_URL ||
  'https://escrow-indexer-961424092563.us-central1.run.app';

// Create dedicated axios instance for escrow indexer
const escrowIndexerClient: AxiosInstance = axios.create({
  baseURL: ESCROW_INDEXER_URL,
  timeout: 10000, // 10s timeout (much faster than blockchain scanning)
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
escrowIndexerClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('Escrow Indexer API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Types matching the indexer API responses
export interface IndexedEscrow {
  escrow_address: string;
  payer_address: string;
  payee_address: string;
  arbiter_address: string;
  amount: string;
  release_delay: number;
  approvals_required: number;
  status: 'created' | 'approved' | 'released' | 'refunded';
  chain_id: number;
  created_block: number;
  created_tx: string;
  created_at: string;
  updated_at: string;
  approval_count?: number;
}

export interface EscrowApproval {
  id: number;
  escrow_address: string;
  approver_address: string;
  block_number: number;
  tx_hash: string;
  timestamp: string;
}

export interface EscrowEvent {
  id: number;
  escrow_address: string;
  event_type: string;
  event_data: string;
  block_number: number;
  tx_hash: string;
  timestamp: string;
}

export interface EscrowsByRoleResponse {
  success: boolean;
  escrows: {
    asPayer: IndexedEscrow[];
    asPayee: IndexedEscrow[];
    asArbiter: IndexedEscrow[];
  };
}

export interface EscrowStatsResponse {
  success: boolean;
  stats: {
    total_escrows: number;
    by_status: {
      created: number;
      approved: number;
      released: number;
      refunded: number;
    };
  };
}

/**
 * Get all escrows where the address is involved in any role (payer, payee, or arbiter)
 * This is the main function to replace blockchain scanning in useEscrowsByRole
 */
export async function getEscrowsByRole(address: Address): Promise<EscrowsByRoleResponse> {
  const response = await escrowIndexerClient.get<EscrowsByRoleResponse>(
    `/api/v1/escrows/by-role/${address.toLowerCase()}`
  );
  return response.data;
}

/**
 * Get all escrows where the address is the payer
 */
export async function getEscrowsByPayer(address: Address): Promise<IndexedEscrow[]> {
  const response = await escrowIndexerClient.get<{ success: boolean; escrows: IndexedEscrow[] }>(
    `/api/v1/escrows/by-payer/${address.toLowerCase()}`
  );
  return response.data.escrows;
}

/**
 * Get all escrows where the address is the payee
 */
export async function getEscrowsByPayee(address: Address): Promise<IndexedEscrow[]> {
  const response = await escrowIndexerClient.get<{ success: boolean; escrows: IndexedEscrow[] }>(
    `/api/v1/escrows/by-payee/${address.toLowerCase()}`
  );
  return response.data.escrows;
}

/**
 * Get all escrows where the address is the arbiter
 */
export async function getEscrowsByArbiter(address: Address): Promise<IndexedEscrow[]> {
  const response = await escrowIndexerClient.get<{ success: boolean; escrows: IndexedEscrow[] }>(
    `/api/v1/escrows/by-arbiter/${address.toLowerCase()}`
  );
  return response.data.escrows;
}

/**
 * Get a specific escrow by address
 */
export async function getEscrow(escrowAddress: Address): Promise<IndexedEscrow> {
  const response = await escrowIndexerClient.get<{ success: boolean; escrow: IndexedEscrow }>(
    `/api/v1/escrows/${escrowAddress.toLowerCase()}`
  );
  return response.data.escrow;
}

/**
 * Get all approvals for a specific escrow
 */
export async function getEscrowApprovals(escrowAddress: Address): Promise<EscrowApproval[]> {
  const response = await escrowIndexerClient.get<{ success: boolean; approvals: EscrowApproval[] }>(
    `/api/v1/escrows/${escrowAddress.toLowerCase()}/approvals`
  );
  return response.data.approvals;
}

/**
 * Get complete event history (audit trail) for a specific escrow
 */
export async function getEscrowEvents(escrowAddress: Address): Promise<EscrowEvent[]> {
  const response = await escrowIndexerClient.get<{ success: boolean; events: EscrowEvent[] }>(
    `/api/v1/escrows/${escrowAddress.toLowerCase()}/events`
  );
  return response.data.events;
}

/**
 * Get global escrow statistics
 */
export async function getEscrowStats(): Promise<EscrowStatsResponse> {
  const response = await escrowIndexerClient.get<EscrowStatsResponse>('/api/v1/escrows/stats');
  return response.data;
}

/**
 * Health check for the indexer service
 */
export async function checkIndexerHealth(): Promise<{ status: string; service: string }> {
  const response = await escrowIndexerClient.get<{ status: string; service: string }>('/health');
  return response.data;
}
