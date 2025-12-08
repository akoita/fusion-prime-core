import { useState } from 'react';
import { useAccount } from 'wagmi';
import { AlertCircle, ExternalLink, Search, Clock, CheckCircle2, XCircle } from 'lucide-react';

export default function MessageTracker() {
  const { isConnected } = useAccount();
  const [messageId, setMessageId] = useState('');
  const [txHash, setTxHash] = useState('');

  if (!isConnected) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-yellow-600 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Wallet Not Connected</h2>
          <p className="text-gray-600">
            Please connect your wallet to track cross-chain messages.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Cross-Chain Message Tracker</h1>
        <p className="text-gray-600">
          Track the status of your cross-chain settlements using the bridge explorer tools.
        </p>
      </div>

      {/* Quick Search */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Track Your Message</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Message ID or Transaction Hash
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={messageId || txHash}
                onChange={(e) => {
                  const value = e.target.value;
                  if (value.length === 66) {
                    setTxHash(value);
                    setMessageId('');
                  } else {
                    setMessageId(value);
                    setTxHash('');
                  }
                }}
                placeholder="0x... (message ID or transaction hash)"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={() => {
                  if (messageId || txHash) {
                    // In a real implementation, this would query the contract or indexer
                    alert('Message tracking will be implemented with backend indexer');
                  }
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
              >
                <Search className="h-4 w-4" />
                Search
              </button>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Enter the message ID from your settlement confirmation or the transaction hash
            </p>
          </div>
        </div>
      </div>

      {/* Bridge Explorers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Axelar Explorer */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <ExternalLink className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Axelar Network</h3>
              <p className="text-sm text-gray-600">Track Axelar bridge messages</p>
            </div>
          </div>

          <div className="space-y-3 mb-4">
            <div className="bg-gray-50 rounded p-3">
              <p className="text-xs text-gray-600 mb-1">Testnet Explorer:</p>
              <a
                href="https://testnet.axelarscan.io"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
              >
                testnet.axelarscan.io
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
            <div className="bg-gray-50 rounded p-3">
              <p className="text-xs text-gray-600 mb-1">Search by:</p>
              <ul className="text-sm text-gray-700 space-y-1">
                <li>• Transaction hash</li>
                <li>• Message ID</li>
                <li>• Wallet address</li>
              </ul>
            </div>
          </div>

          <a
            href="https://testnet.axelarscan.io"
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-center font-medium"
          >
            Open Axelarscan
          </a>
        </div>

        {/* Chainlink CCIP Explorer */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
              <ExternalLink className="h-6 w-6 text-purple-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Chainlink CCIP</h3>
              <p className="text-sm text-gray-600">Track CCIP bridge messages</p>
            </div>
          </div>

          <div className="space-y-3 mb-4">
            <div className="bg-gray-50 rounded p-3">
              <p className="text-xs text-gray-600 mb-1">CCIP Explorer:</p>
              <a
                href="https://ccip.chain.link"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
              >
                ccip.chain.link
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
            <div className="bg-gray-50 rounded p-3">
              <p className="text-xs text-gray-600 mb-1">Search by:</p>
              <ul className="text-sm text-gray-700 space-y-1">
                <li>• Transaction hash</li>
                <li>• Message ID</li>
                <li>• Source/destination address</li>
              </ul>
            </div>
          </div>

          <a
            href="https://ccip.chain.link"
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 text-center font-medium"
          >
            Open CCIP Explorer
          </a>
        </div>
      </div>

      {/* Message Status Guide */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Understanding Message Status</h2>

        <div className="space-y-4">
          <div className="flex items-start gap-3 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <Clock className="h-6 w-6 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">Pending</h3>
              <p className="text-sm text-gray-700">
                The message has been submitted to the source chain but has not yet been picked up by
                the bridge relayers. This typically takes 1-5 minutes depending on network
                congestion.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <Clock className="h-6 w-6 text-blue-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">Processing</h3>
              <p className="text-sm text-gray-700">
                The bridge has picked up your message and is currently processing it. The message is
                being verified and will be relayed to the destination chain. This can take 5-15
                minutes.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-4 bg-green-50 border border-green-200 rounded-lg">
            <CheckCircle2 className="h-6 w-6 text-green-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">Completed</h3>
              <p className="text-sm text-gray-700">
                Your message has been successfully delivered to the destination chain and the
                settlement has been executed. You can view the destination transaction hash in the
                explorer.
              </p>
            </div>
          </div>

          <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
            <XCircle className="h-6 w-6 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-gray-900 mb-1">Failed</h3>
              <p className="text-sm text-gray-700">
                The message failed to execute on the destination chain. This could be due to
                insufficient gas, invalid destination address, or contract execution errors. Your
                funds remain secure on the source chain.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Helpful Tips */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">💡 Helpful Tips</h3>
        <ul className="space-y-2 text-sm text-gray-700">
          <li className="flex items-start gap-2">
            <span className="text-blue-600 font-bold">•</span>
            <span>
              <strong>Save your message ID:</strong> Always save the message ID or transaction
              hash from your settlement confirmation for tracking purposes.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-blue-600 font-bold">•</span>
            <span>
              <strong>Be patient:</strong> Cross-chain messages can take 5-20 minutes to complete
              depending on the bridge protocol and network congestion.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-blue-600 font-bold">•</span>
            <span>
              <strong>Gas fees:</strong> Make sure you provided enough gas when initiating the
              settlement. Insufficient gas is the most common cause of failures.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-blue-600 font-bold">•</span>
            <span>
              <strong>Support:</strong> If your message is stuck for more than 30 minutes, check
              the bridge's official status page or contact support.
            </span>
          </li>
        </ul>
      </div>
    </div>
  );
}
