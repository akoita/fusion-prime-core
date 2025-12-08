## Smart Contracts

This module houses Foundry-based smart contract projects organized by domain.

### Structure

- **`escrow/`**: Core escrow contracts (Escrow, EscrowFactory)
  - `src/`: Contract source files
  - `test/`: Foundry tests
  - `script/`: Deployment scripts

- **`cross-chain/`**: Cross-chain messaging and vault contracts
  - `src/`: CrossChainVault, bridge adapters
  - `test/`: Foundry tests
  - `script/`: Deployment scripts

- **`shared/`**: Common libraries reused across contracts

### Module Pattern

Each module follows the Foundry layout (`src/`, `script/`, `test/`):

```
module-name/
├── src/          # Contract source files
├── test/         # Foundry tests
└── script/       # Deployment scripts
```

### Building

To build a specific module:

```bash
# Build escrow contracts
forge build --contracts escrow/src/

# Build cross-chain contracts
forge build --contracts cross-chain/src/

# Build all
forge build
```

### Testing

```bash
# Test escrow module
forge test --match-path escrow/test/*

# Test cross-chain module
forge test --match-path cross-chain/test/*

# Test all
forge test
```

### Import Paths

Use remappings for cross-module imports:

```solidity
// From escrow module
import {Escrow} from "escrow/Escrow.sol";

// From cross-chain module
import {CrossChainVault} from "cross-chain/CrossChainVault.sol";
```
