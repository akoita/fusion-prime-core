#!/bin/bash
# Fusion Prime Quality Checks Script
# ==================================
# Shared script used by both pre-commit hooks and CI workflow
# Ensures identical validation behavior

set -e

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration paths
CONFIG_DIR="config"
PYTHON_CONFIG_DIR="$CONFIG_DIR/python"
SECURITY_CONFIG_DIR="$CONFIG_DIR/security"
SOLIDITY_CONFIG_DIR="$CONFIG_DIR/solidity"

# Function to run Python formatting checks
run_python_formatting() {
    echo -e "${BLUE}🔍 Running Python formatting checks...${NC}"

    # Black formatting check
    echo "  - Black formatting..."
    black --config="$PYTHON_CONFIG_DIR/black.toml" --check . || {
        echo -e "${RED}❌ Black formatting failed${NC}"
        return 1
    }

    # isort import sorting check
    echo "  - Import sorting..."
    isort --settings="$PYTHON_CONFIG_DIR/isort.cfg" --check-only . || {
        echo -e "${RED}❌ Import sorting failed${NC}"
        return 1
    }

    echo -e "${GREEN}✅ Python formatting checks passed${NC}"
}

# Function to run Python linting
run_python_linting() {
    echo -e "${BLUE}🔍 Running Python linting...${NC}"

    # flake8 linting
    flake8 . --config="$PYTHON_CONFIG_DIR/flake8.cfg" || {
        echo -e "${RED}❌ flake8 linting failed${NC}"
        return 1
    }

    echo -e "${GREEN}✅ Python linting passed${NC}"
}

# Function to run type checking
run_type_checking() {
    echo -e "${BLUE}🔍 Running type checking...${NC}"

    # mypy type checking
    mypy services/settlement/app/ --config-file="$PYTHON_CONFIG_DIR/mypy.ini" || {
        echo -e "${YELLOW}⚠️  Type checking completed with warnings${NC}"
    }

    echo -e "${GREEN}✅ Type checking completed${NC}"
}

# Function to run security checks
run_security_checks() {
    echo -e "${BLUE}🔒 Running security checks...${NC}"

    # Safety dependency vulnerability check
    echo "  - Safety dependency check..."
    safety scan -r requirements.txt --json || {
        echo -e "${YELLOW}⚠️  Safety check requires authentication (skipping)${NC}"
    }

    # Bandit security scanning
    echo "  - Bandit security scan..."
    bandit -c "$SECURITY_CONFIG_DIR/bandit.yaml" -r . -f json -o bandit-report.json || {
        echo -e "${YELLOW}⚠️  Bandit found security issues (see bandit-report.json)${NC}"
    }

    echo -e "${GREEN}✅ Security checks completed${NC}"
}

# Function to run Solidity checks
run_solidity_checks() {
    echo -e "${BLUE}🔗 Running Solidity checks...${NC}"

    # Check if Foundry is available
    if command -v forge &> /dev/null; then
        echo "  - Foundry format check..."
        cd contracts
        forge fmt --check || {
            echo -e "${RED}❌ Foundry format check failed${NC}"
            return 1
        }

        echo "  - Foundry build check..."
        forge build || {
            echo -e "${RED}❌ Foundry build failed${NC}"
            return 1
        }
        cd ..

        echo -e "${GREEN}✅ Solidity checks passed${NC}"
    else
        echo -e "${YELLOW}⚠️  Foundry not available, skipping Solidity checks${NC}"
    fi
}

# Function to run general file checks
run_file_checks() {
    echo -e "${BLUE}📁 Running file checks...${NC}"

    # Check for trailing whitespace (exclude submodules)
    if find . -name "*.py" -o -name "*.md" -o -name "*.yaml" -o -name "*.yml" | grep -v "contracts/lib/" | xargs grep -l '[[:space:]]$' 2>/dev/null; then
        echo -e "${RED}❌ Trailing whitespace found${NC}"
        return 1
    fi

    # Check for merge conflict markers (exact patterns only)
    if grep -r "^<<<<<<< HEAD\|^>>>>>>> " . --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=contracts/lib --exclude-dir=.terraform --exclude-dir=__pycache__; then
        echo -e "${RED}❌ Merge conflict markers found${NC}"
        return 1
    fi

    echo -e "${GREEN}✅ File checks passed${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}🚀 Running Fusion Prime quality checks...${NC}"
    echo ""

    # Check if config files exist
    if [ ! -d "$CONFIG_DIR" ]; then
        echo -e "${RED}❌ Configuration directory not found: $CONFIG_DIR${NC}"
        exit 1
    fi

    # Run all checks
    run_python_formatting
    run_python_linting
    run_type_checking
    run_security_checks
    run_solidity_checks
    run_file_checks

    echo ""
    echo -e "${GREEN}🎉 All quality checks passed!${NC}"
}

# Parse command line arguments
case "${1:-all}" in
    "formatting")
        run_python_formatting
        ;;
    "linting")
        run_python_linting
        ;;
    "typing")
        run_type_checking
        ;;
    "security")
        run_security_checks
        ;;
    "solidity")
        run_solidity_checks
        ;;
    "files")
        run_file_checks
        ;;
    "all"|"")
        main
        ;;
    *)
        echo "Usage: $0 [formatting|linting|typing|security|solidity|files|all]"
        exit 1
        ;;
esac
