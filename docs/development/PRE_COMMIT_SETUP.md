# Pre-commit Hooks Setup

This document explains how to set up and use pre-commit hooks for Fusion Prime development. The pre-commit configuration mirrors the CI workflow verification steps to ensure consistency between local development and the CI/CD pipeline.

## Overview

The pre-commit hooks are configured to match the CI workflow in `.github/workflows/ci.yml` and include:

- **Python**: Black formatting, isort import sorting, flake8 linting, mypy type checking
- **Security**: Bandit security scanning, Safety dependency vulnerability checks
- **Smart Contracts**: Foundry formatting and build checks, dprint Solidity formatting
- **General**: YAML/JSON validation, file checks, Docker linting, shell script linting
- **Frontend**: ESLint and Prettier for JavaScript/TypeScript

## Quick Setup

### 1. Install Pre-commit

```bash
# Install pre-commit
pip install pre-commit>=3.6.0

# Or use the setup script
make setup-pre-commit
```

### 2. Install Hooks

```bash
# Install the pre-commit hooks
pre-commit install

# Run on all files (first time)
pre-commit run --all-files
```

### 3. Verify Setup

```bash
# Check that hooks are working
pre-commit run --all-files

# Run specific hooks
pre-commit run black
pre-commit run flake8
pre-commit run bandit
```

## Available Hooks

### Python Development

| Hook | Purpose | CI Equivalent |
|------|---------|---------------|
| `black` | Python code formatting | `black --check .` |
| `isort` | Import statement sorting | `isort --check-only .` |
| `flake8` | Python linting | `flake8 . --count --select=E9,F63,F7,F82` |
| `mypy` | Type checking | `mypy services/settlement/app/` |
| `bandit` | Security vulnerability scanning | `bandit -r . -f json` |
| `python-safety-dependencies-check` | Dependency vulnerability scanning | `safety check -r requirements.txt` |

### Smart Contracts

| Hook | Purpose | CI Equivalent |
|------|---------|---------------|
| `dprint` | Solidity code formatting | `forge fmt --check` |
| `foundry-fmt-check` | Foundry format validation | `forge fmt --check` |
| `foundry-build-check` | Foundry build validation | `forge build` |

### General File Checks

| Hook | Purpose | CI Equivalent |
|------|---------|---------------|
| `trailing-whitespace` | Remove trailing whitespace | Built into CI |
| `end-of-file-fixer` | Ensure files end with newline | Built into CI |
| `check-yaml` | YAML syntax validation | Built into CI |
| `check-json` | JSON syntax validation | Built into CI |
| `check-toml` | TOML syntax validation | Built into CI |
| `check-merge-conflict` | Detect merge conflict markers | Built into CI |
| `check-added-large-files` | Prevent large file commits | Built into CI |
| `check-case-conflict` | Detect case conflicts | Built into CI |
| `check-ast` | Python AST validation | Built into CI |
| `debug-statements` | Remove debug statements | Built into CI |
| `check-docstring-first` | Ensure docstrings come first | Built into CI |

### Infrastructure

| Hook | Purpose | CI Equivalent |
|------|---------|---------------|
| `hadolint` | Dockerfile linting | Built into CI |
| `shellcheck` | Shell script linting | Built into CI |
| `markdownlint` | Markdown linting | Built into CI |

### Frontend

| Hook | Purpose | CI Equivalent |
|------|---------|---------------|
| `eslint` | JavaScript/TypeScript linting | Built into CI |
| `prettier` | Code formatting | Built into CI |

## Usage

### Running Hooks

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black
pre-commit run flake8
pre-commit run bandit

# Run hooks on staged files only (default behavior)
pre-commit run

# Run specific hook on specific files
pre-commit run black --files services/settlement/app/main.py
```

### Updating Hooks

```bash
# Update all hooks to latest versions
pre-commit autoupdate

# Update specific hook
pre-commit autoupdate --repo https://github.com/psf/black
```

### Skipping Hooks

```bash
# Skip all hooks for a commit
git commit --no-verify -m "Emergency fix"

# Skip specific hook
SKIP=flake8 git commit -m "Commit message"
```

## Configuration

### Pre-commit Configuration

The main configuration is in `.pre-commit-config.yaml`. Key features:

- **Language versions**: Python 3.13, Node 20
- **File patterns**: Specific file extensions for each hook
- **Exclusions**: Test files, library files, node_modules
- **Arguments**: Custom arguments matching CI behavior

### Hook-specific Configuration

Some hooks use additional configuration files:

- **Black**: `pyproject.toml` or `black` section in `pyproject.toml`
- **isort**: `pyproject.toml` or `.isort.cfg`
- **flake8**: `.flake8` or `setup.cfg`
- **mypy**: `mypy.ini` or `pyproject.toml`
- **dprint**: `dprint.json`
- **ESLint**: `.eslintrc.js` or `.eslintrc.json`
- **Prettier**: `.prettierrc` or `prettier.config.js`

## Troubleshooting

### Common Issues

1. **Hook fails on first run**
   ```bash
   # This is normal - fix issues and run again
   pre-commit run --all-files
   ```

2. **Foundry not found**
   ```bash
   # Install Foundry first
   curl -L https://foundry.paradigm.xyz | bash
   source ~/.bashrc
   foundryup
   ```

3. **Python dependencies missing**
   ```bash
   # Install required packages
   pip install safety bandit types-requests types-PyYAML
   ```

4. **Node.js dependencies missing**
   ```bash
   # Install Node.js dependencies
   cd frontend && npm install
   ```

### Debugging

```bash
# Run with verbose output
pre-commit run --all-files --verbose

# Run specific hook with debug info
pre-commit run black --verbose

# Check hook configuration
pre-commit config

# Clean hook cache
pre-commit clean
```

## Integration with CI

The pre-commit hooks are designed to match the CI workflow exactly:

1. **Same tools**: Uses identical versions and configurations
2. **Same arguments**: Command-line arguments match CI exactly
3. **Same file patterns**: File inclusion/exclusion rules match CI
4. **Same dependencies**: Required packages match CI requirements

This ensures that code that passes pre-commit hooks will also pass CI checks.

## Best Practices

1. **Run hooks before pushing**: Always run `pre-commit run --all-files` before pushing
2. **Fix issues immediately**: Don't skip hooks - fix the underlying issues
3. **Keep hooks updated**: Regularly run `pre-commit autoupdate`
4. **Use consistent formatting**: Let Black and isort handle formatting automatically
5. **Review security findings**: Pay attention to Bandit and Safety warnings

## Makefile Integration

The Makefile includes convenient targets for pre-commit operations:

```bash
# Setup pre-commit hooks
make setup-pre-commit

# Run all pre-commit hooks
make pre-commit

# Update pre-commit hooks
make pre-commit-update
```

## CI Discrepancy Prevention

The pre-commit configuration is designed to prevent discrepancies with CI by:

1. **Matching CI commands exactly**: Same tools, versions, and arguments
2. **Including all CI checks**: Every CI verification step has a corresponding hook
3. **Using same file patterns**: Same inclusion/exclusion rules as CI
4. **Testing locally first**: Run pre-commit before pushing to catch issues early

This ensures that local development matches CI behavior and reduces failed CI runs.
