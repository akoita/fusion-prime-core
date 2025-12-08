# Cross-Chain Contract Testing Guide

## Current Status

✅ **Test Infrastructure Complete**:
- BridgeManager.t.sol - Adapter registration and routing tests
- AxelarAdapter.t.sol - Axelar protocol adapter tests
- CCIPAdapter.t.sol - Chainlink CCIP adapter tests
- Mock contracts (MockAxelarGateway, MockAxelarGasService, MockCCIPRouter)

⚠️ **Foundry Configuration**:
- Foundry doesn't easily support multi-module structure (escrow/, cross-chain/)
- Tests need to be run in isolation or with manual configuration

## Testing Approach

### Option 1: Test Cross-Chain Contracts in Isolation

```bash
# Create a temporary test directory structure
cd contracts
mkdir -p test-isolated/cross-chain
cp -r cross-chain/test/* test-isolated/cross-chain/
cp -r cross-chain/src test-isolated/cross-chain/

# Update imports in test files to use relative paths
# Run tests
forge test --match-path "test-isolated/cross-chain/*"
```

### Option 2: Manual Foundry Configuration

Update `foundry.toml` to point to cross-chain module only:

```toml
[profile.cross-chain]
src = "cross-chain/src"
test = "cross-chain/test"
script = "cross-chain/script"
```

Then test with:
```bash
forge test --profile cross-chain
```

### Option 3: Use Foundry Workspaces (Future)

Restructure to use Foundry workspaces:
- `contracts/escrow/` - separate workspace
- `contracts/cross-chain/` - separate workspace
- Each has its own `foundry.toml`

## Test Coverage

**BridgeManager Tests**:
- ✅ Adapter registration
- ✅ Protocol preference selection
- ✅ Automatic adapter fallback
- ✅ Chain support validation
- ✅ Message routing

**AxelarAdapter Tests**:
- ✅ Protocol name
- ✅ Chain support checks
- ✅ Message sending
- ✅ Gas estimation
- ✅ Unsupported chain rejection

**CCIPAdapter Tests**:
- ✅ Protocol name
- ✅ Chain selector mapping
- ✅ Message sending via router
- ✅ Fee estimation
- ✅ Address conversion

## Manual Verification

Until Foundry config is resolved, contracts can be verified manually:

1. **Compile contracts**:
   ```bash
   forge build --contracts cross-chain/src
   ```

2. **Deploy to testnet** and test integration manually

3. **Use Hardhat/Remix** for testing if needed

## Next Steps

- [ ] Resolve Foundry multi-module configuration
- [ ] Write CrossChainVault integration tests
- [ ] Add fork tests for real bridge protocols
- [ ] Set up CI/CD for contract testing
