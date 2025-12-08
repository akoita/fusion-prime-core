/**
 * Helper to add or switch to Polygon Amoy network with Infura RPC
 * This avoids rate limiting issues with public RPCs
 */

export async function addPolygonAmoyNetwork() {
  if (!window.ethereum) {
    throw new Error('MetaMask is not installed');
  }

  const chainId = '0x13882'; // 80002 in hex

  try {
    // Try to switch to the network
    await window.ethereum.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId }],
    });
  } catch (switchError: any) {
    // Network doesn't exist, add it
    if (switchError.code === 4902) {
      try {
        await window.ethereum.request({
          method: 'wallet_addEthereumChain',
          params: [
            {
              chainId,
              chainName: 'Polygon Amoy Testnet',
              nativeCurrency: {
                name: 'MATIC',
                symbol: 'MATIC',
                decimals: 18,
              },
              rpcUrls: [
                'https://polygon-amoy.infura.io/v3/6c474ab8fd5f48b294e1a082adc2c826',
              ],
              blockExplorerUrls: ['https://amoy.polygonscan.com'],
            },
          ],
        });
      } catch (addError) {
        throw new Error('Failed to add Polygon Amoy network to MetaMask');
      }
    } else {
      throw switchError;
    }
  }
}

export async function addSepoliaNetwork() {
  if (!window.ethereum) {
    throw new Error('MetaMask is not installed');
  }

  const chainId = '0xaa36a7'; // 11155111 in hex

  try {
    await window.ethereum.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId }],
    });
  } catch (switchError: any) {
    if (switchError.code === 4902) {
      try {
        await window.ethereum.request({
          method: 'wallet_addEthereumChain',
          params: [
            {
              chainId,
              chainName: 'Sepolia Testnet',
              nativeCurrency: {
                name: 'SepoliaETH',
                symbol: 'ETH',
                decimals: 18,
              },
              rpcUrls: [
                'https://sepolia.infura.io/v3/6c474ab8fd5f48b294e1a082adc2c826',
              ],
              blockExplorerUrls: ['https://sepolia.etherscan.io'],
            },
          ],
        });
      } catch (addError) {
        throw new Error('Failed to add Sepolia network to MetaMask');
      }
    } else {
      throw switchError;
    }
  }
}
