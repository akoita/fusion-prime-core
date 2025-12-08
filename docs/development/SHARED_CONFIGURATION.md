# Shared Configuration for Fusion Prime

This document explains the shared configuration approach that ensures identical validation behavior between pre-commit hooks and GitHub CI workflows.

## Overview

To prevent discrepancies between local development and CI, we use shared configuration files that both pre-commit hooks and GitHub Actions reference. This ensures that:

- **Identical tool versions**: Same versions of Black, isort, flake8, mypy, bandit, etc.
- **Identical settings**: Same line lengths, rules, exclusions, and configurations
- **Identical behavior**: Code that passes pre-commit will pass CI

## Configuration Structure

```
config/
├── python/
│   ├── black.toml          # Black formatting configuration
│   ├── isort.cfg           # Import sorting configuration
│   ├── flake8.cfg          # Linting configuration
│   └── mypy.ini            # Type checking configuration
├── security/
│   ├── bandit.yaml         # Security scanning configuration
│   └── safety.json         # Dependency vulnerability configuration
└── solidity/
    └── dprint.json         # Solidity formatting configuration
```

## Shared Configuration Files

### Python Tools

#### `config/python/black.toml`
```toml
[tool.black]
line-length = 100
target-version = ['py313']
include = '\.pyi?$'
extend-exclude = '''
/(
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | _build
  | buck-out
  | build
  | dist
  | node_modules
  | contracts/lib
)/
'''
```

#### `config/python/isort.cfg`
```ini
[settings]
profile = black
line_length = 100
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
skip_glob = [
    "contracts/lib/*",
    "node_modules/*",
    ".venv/*",
    ".tox/*",
    "build/*",
    "dist/*"
]
known_first_party = [
    "services",
    "analytics",
    "integrations"
]
```

#### `config/python/flake8.cfg`
```ini
[flake8]
max-line-length = 100
extend-ignore = E203, W503
select = E9, F63, F7, F82
exclude =
    .git,
    __pycache__,
    .venv,
    .tox,
    build,
    dist,
    contracts/lib,
    node_modules,
    .pytest_cache
per-file-ignores =
    __init__.py:F401
    tests/*:S101
max-complexity = 10
```

#### `config/python/mypy.ini`
```ini
[mypy]
python_version = 3.13
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True
ignore_missing_imports = True
exclude = (?x)(
    ^contracts/
    | ^tests/
    | ^analytics/
    | ^integrations/relayers/
    | ^node_modules/
    | ^\.venv/
    | ^build/
    | ^dist/
)
```

### Security Tools

#### `config/security/bandit.yaml`
```yaml
exclude_dirs:
  - tests
  - test
  - __pycache__
  - .venv
  - .tox
  - build
  - dist
  - contracts/lib
  - node_modules

skips:
  - B101  # assert_used
  - B601  # paramiko_calls
  - B603  # subprocess_without_shell_equals_true

severity: medium
confidence: medium
format: json
output: bandit-report.json
```

#### `config/security/safety.json`
```json
{
  "safety": {
    "ignore": [],
    "audit_and_monitor": false,
    "json": true,
    "full_report": true,
    "short_report": false,
    "bare": false,
    "output": "safety-report.json",
    "save_json": true,
    "db": "https://github.com/pyupio/safety-db",
    "cache": 0,
    "telemetry": false,
    "disable_telemetry": true
  }
}
```

### Solidity Tools

#### `config/solidity/dprint.json`
```json
{
  "version": "0.46.0",
  "plugins": [
    {
      "name": "solidity",
      "config": {
        "lineWidth": 100,
        "indentWidth": 4,
        "useTabs": false,
        "semicolons": "always",
        "quoteStyle": "double",
        "trailingComma": "always",
        "bracketSpacing": true,
        "arrowParens": "always",
        "endOfLine": "lf"
      }
    }
  ],
  "includes": ["contracts/**/*.sol"],
  "excludes": [
    "contracts/lib/**/*",
    "contracts/out/**/*",
    "contracts/cache/**/*"
  ]
}
```

## Shared Quality Checks Script

The `scripts/quality-checks.sh` script provides a unified interface for running all quality checks:

```bash
# Run all quality checks
./scripts/quality-checks.sh all

# Run specific checks
./scripts/quality-checks.sh formatting
./scripts/quality-checks.sh linting
./scripts/quality-checks.sh typing
./scripts/quality-checks.sh security
./scripts/quality-checks.sh solidity
./scripts/quality-checks.sh files
```

## Pre-commit Configuration

The `.pre-commit-config.yaml` references shared configurations:

```yaml
- repo: https://github.com/psf/black
  rev: 24.10.0
  hooks:
    - id: black
      args: [--config=config/python/black.toml]
      files: \.(py)$

- repo: https://github.com/pycqa/isort
  rev: 5.13.2
  hooks:
    - id: isort
      args: [--settings=config/python/isort.cfg]
      files: \.(py)$

- repo: https://github.com/pycqa/flake8
  rev: 7.0.0
  hooks:
    - id: flake8
      args: [--config=config/python/flake8.cfg]
      files: \.(py)$

- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.8.0
  hooks:
    - id: mypy
      args: [--config-file=config/python/mypy.ini]
      files: ^services/settlement/app/

- repo: https://github.com/PyCQA/bandit
  rev: 1.8.0
  hooks:
    - id: bandit
      args: [-c, config/security/bandit.yaml, -r, ., -f, json, -o, bandit-report.json]
      files: \.(py)$
```

## CI Workflow Integration

The GitHub Actions workflow uses the same shared configurations:

```yaml
- name: 🔍 Run quality checks
  run: |
    ./scripts/quality-checks.sh all

- name: 🔒 Run security scan
  run: |
    pip install safety bandit
    ./scripts/quality-checks.sh security
```

## Benefits

### 1. **Zero Discrepancies**
- Pre-commit and CI use identical configurations
- Same tool versions, settings, and behavior
- Code that passes locally will pass in CI

### 2. **Single Source of Truth**
- All configuration in one place
- Easy to update and maintain
- Consistent across all environments

### 3. **Easier Maintenance**
- Update configuration once, applies everywhere
- No need to sync settings between files
- Reduced chance of configuration drift

### 4. **Better Developer Experience**
- Developers see same results locally as in CI
- No surprises when pushing code
- Faster feedback loop

## Usage

### Local Development

```bash
# Setup pre-commit hooks
make setup-pre-commit

# Run quality checks manually
./scripts/quality-checks.sh all

# Run specific checks
./scripts/quality-checks.sh formatting
```

### CI/CD Pipeline

The CI workflow automatically uses the shared configurations, ensuring identical behavior to local development.

### Updating Configurations

1. **Update shared config files** in `config/` directory
2. **Test locally** with `./scripts/quality-checks.sh all`
3. **Commit changes** - pre-commit hooks will validate
4. **Push to CI** - GitHub Actions will use same configs

## Troubleshooting

### Configuration Not Found

```bash
# Check if config files exist
ls -la config/python/
ls -la config/security/
ls -la config/solidity/

# Verify script permissions
chmod +x scripts/quality-checks.sh
```

### Tool Version Mismatches

```bash
# Update pre-commit hooks
pre-commit autoupdate

# Check tool versions
black --version
isort --version
flake8 --version
mypy --version
bandit --version
```

### Configuration Validation

```bash
# Validate pre-commit config
pre-commit validate-config

# Test specific hooks
pre-commit run black
pre-commit run flake8
pre-commit run bandit
```

## Best Practices

1. **Always use shared configs**: Never hardcode settings in individual files
2. **Test locally first**: Run quality checks before pushing
3. **Keep configs in sync**: Update shared configs when changing rules
4. **Document changes**: Update this documentation when modifying configs
5. **Version control**: Commit all configuration changes

This shared configuration approach ensures that Fusion Prime maintains consistent code quality standards across all development environments! 🎉
