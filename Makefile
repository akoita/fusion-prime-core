# Fusion Prime - Makefile
# Convenience shortcuts for common development tasks

.PHONY: help build deploy test clean

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m# No Color

# Default target
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "$(BLUE)Fusion Prime - Available Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make build-all        # Build all services"
	@echo "  make deploy-dev       # Deploy to development"
	@echo "  make test             # Run all tests"

## Build Commands

build-all: ## Build all services (settlement + relayer)
	@echo "$(BLUE)Building all services...$(NC)"
	./scripts/build.sh all

build-settlement: ## Build settlement service only
	@echo "$(BLUE)Building settlement service...$(NC)"
	./scripts/build.sh settlement

build-relayer: ## Build escrow event relayer only
	@echo "$(BLUE)Building escrow event relayer...$(NC)"
	./scripts/build.sh relayer

build-tag: ## Build with custom tag (make build-tag TAG=v1.0.0)
	@echo "$(BLUE)Building with tag: $(TAG)$(NC)"
	./scripts/build.sh --tag $(TAG) all

## Deploy Commands

deploy-dev: ## Deploy all services to development (auto on dev branch push)
	@echo "$(BLUE)Deploying to development...$(NC)"
	@echo "$(GREEN)✅ Auto-deployment triggered on dev branch push$(NC)"
	@echo "$(YELLOW)🌍 Environment: DEV (Anvil blockchain)$(NC)"
	@echo "$(YELLOW)💰 Cost: $0 (local blockchain)$(NC)"
	./scripts/deploy.sh dev all

deploy-settlement: ## Deploy settlement service only
	@echo "$(BLUE)Deploying settlement service...$(NC)"
	gcloud run deploy settlement-service \
		--image us-central1-docker.pkg.dev/fusion-prime/services/settlement-service:latest \
		--region us-central1 \
		--platform managed

deploy-staging: ## Deploy to staging (manual trigger)
	@echo "$(BLUE)Deploying to staging...$(NC)"
	@echo "$(GREEN)✅ Manual deployment to staging environment$(NC)"
	@echo "$(YELLOW)🌍 Environment: STAGING (Sepolia testnet)$(NC)"
	@echo "$(YELLOW)💰 Cost: ~$5/month (testnet)$(NC)"
	@echo "$(YELLOW)🚀 Trigger: Push to staging branch or manual workflow$(NC)"
	./scripts/deploy.sh staging all

deploy-prod: ## Deploy to production (requires confirmation)
	@echo "$(YELLOW)⚠️  PRODUCTION DEPLOYMENT$(NC)"
	@echo "$(YELLOW)🌍 Environment: PRODUCTION (Ethereum mainnet)$(NC)"
	@echo "$(YELLOW)💰 Cost: Real ETH costs$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		echo "$(BLUE)Deploying to production...$(NC)"; \
		./scripts/deploy.sh production all; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

## Test Commands

test: ## Run all tests
	@echo "$(BLUE)Running all tests...$(NC)"
	./scripts/test.sh local

test-contracts: ## Run smart contract tests
	@echo "$(BLUE)Running contract tests...$(NC)"
	cd contracts && forge test -vvv

test-settlement: ## Run settlement service tests
	@echo "$(BLUE)Running settlement service tests...$(NC)"
	cd services/settlement && poetry run pytest

test-relayer: ## Run relayer tests
	@echo "$(BLUE)Running relayer tests...$(NC)"
	cd integrations/relayers/escrow && python -m pytest

## Infrastructure Commands

infra-dev: ## Deploy infrastructure to development
	@echo "$(BLUE)Deploying infrastructure to development...$(NC)"
	./scripts/deploy-infrastructure.sh dev apply

infra-staging: ## Deploy infrastructure to staging
	@echo "$(BLUE)Deploying infrastructure to staging...$(NC)"
	./scripts/deploy-infrastructure.sh staging apply

infra-prod: ## Deploy infrastructure to production
	@echo "$(YELLOW)⚠️  DEPLOYING TO PRODUCTION$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		./scripts/deploy-infrastructure.sh production apply; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

infra-plan-dev: ## Plan infrastructure changes for development
	@echo "$(BLUE)Planning infrastructure changes for development...$(NC)"
	./scripts/deploy-infrastructure.sh dev plan

infra-plan-staging: ## Plan infrastructure changes for staging
	@echo "$(BLUE)Planning infrastructure changes for staging...$(NC)"
	./scripts/deploy-infrastructure.sh staging plan

infra-plan-prod: ## Plan infrastructure changes for production
	@echo "$(BLUE)Planning infrastructure changes for production...$(NC)"
	./scripts/deploy-infrastructure.sh production plan

infra-destroy-dev: ## Destroy development infrastructure
	@echo "$(YELLOW)⚠️  DESTROYING DEVELOPMENT INFRASTRUCTURE$(NC)"
	./scripts/deploy-infrastructure.sh dev destroy

infra-destroy-staging: ## Destroy staging infrastructure
	@echo "$(YELLOW)⚠️  DESTROYING STAGING INFRASTRUCTURE$(NC)"
	./scripts/deploy-infrastructure.sh staging destroy

infra-destroy-prod: ## Destroy production infrastructure (requires confirmation)
	@echo "$(RED)⚠️  DESTROYING PRODUCTION INFRASTRUCTURE$(NC)"
	./scripts/deploy-infrastructure.sh production destroy

## Cloud Build Commands

triggers-create: ## Create Cloud Build triggers
	@echo "$(BLUE)Creating Cloud Build triggers...$(NC)"
	gcloud builds triggers import --source=infra/cloudbuild/triggers.yaml

triggers-list: ## List Cloud Build triggers
	@echo "$(BLUE)Listing Cloud Build triggers...$(NC)"
	gcloud builds triggers list

builds-list: ## List recent builds
	@echo "$(BLUE)Recent builds:$(NC)"
	gcloud builds list --limit=10

## Development Commands

setup: ## Setup development environment
	@echo "$(BLUE)Setting up development environment...$(NC)"
	@echo "Installing Forge..."
	@curl -L https://foundry.paradigm.xyz | bash
	@echo "Installing Poetry..."
	@curl -sSL https://install.python-poetry.org | python3 -
	@echo "$(GREEN)✓ Setup complete$(NC)"

setup-pre-commit: ## Setup pre-commit hooks
	@echo "$(BLUE)Setting up pre-commit hooks...$(NC)"
	./scripts/setup-pre-commit.sh
	@echo "$(GREEN)✓ Pre-commit setup complete$(NC)"

pre-commit: ## Run all pre-commit hooks
	@echo "$(BLUE)Running pre-commit hooks...$(NC)"
	pre-commit run --all-files
	@echo "$(GREEN)✓ Pre-commit checks complete$(NC)"

pre-commit-update: ## Update pre-commit hooks
	@echo "$(BLUE)Updating pre-commit hooks...$(NC)"
	pre-commit autoupdate
	@echo "$(GREEN)✓ Pre-commit hooks updated$(NC)"

clean: ## Clean build artifacts
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	cd contracts && forge clean || true
	@echo "$(GREEN)✓ Clean complete$(NC)"

fmt: ## Format code
	@echo "$(BLUE)Formatting code...$(NC)"
	cd contracts && forge fmt
	cd services/settlement && poetry run black . && poetry run isort .
	@echo "$(GREEN)✓ Format complete$(NC)"

lint: ## Lint code
	@echo "$(BLUE)Linting code...$(NC)"
	cd contracts && forge fmt --check
	cd services/settlement && poetry run black --check . && poetry run isort --check .
	@echo "$(GREEN)✓ Lint complete$(NC)"

## Documentation Commands

docs: ## Generate documentation
	@echo "$(BLUE)Generating documentation...$(NC)"
	cd contracts && forge doc
	@echo "$(GREEN)✓ Documentation generated$(NC)"

docs-serve: ## Serve documentation locally
	@echo "$(BLUE)Serving documentation at http://localhost:8080$(NC)"
	cd contracts/docs && python3 -m http.server 8080

## Utility Commands

logs-settlement: ## Tail settlement service logs
	@echo "$(BLUE)Tailing settlement service logs...$(NC)"
	gcloud run services logs tail settlement-service --region us-central1

logs-relayer: ## Tail relayer job logs
	@echo "$(BLUE)Tailing relayer job logs...$(NC)"
	gcloud run jobs logs tail escrow-event-relayer --region us-central1

status: ## Show deployment status
	@echo "$(BLUE)Deployment Status:$(NC)"
	@echo ""
	@echo "$(GREEN)Services:$(NC)"
	@gcloud run services list --region us-central1 2>/dev/null || echo "  No services deployed"
	@echo ""
	@echo "$(GREEN)Cloud SQL:$(NC)"
	@gcloud sql instances list 2>/dev/null || echo "  No databases"
	@echo ""
	@echo "$(GREEN)Recent Builds:$(NC)"
	@gcloud builds list --limit=3 2>/dev/null || echo "  No builds"

version: ## Show versions of tools
	@echo "$(BLUE)Tool Versions:$(NC)"
	@echo "  Forge:      $$(forge --version 2>/dev/null | head -n1 || echo 'Not installed')"
	@echo "  Poetry:     $$(poetry --version 2>/dev/null || echo 'Not installed')"
	@echo "  Terraform:  $$(terraform version -json 2>/dev/null | jq -r .terraform_version || echo 'Not installed')"
	@echo "  gcloud:     $$(gcloud version --format='value(\"Google Cloud SDK\")' 2>/dev/null || echo 'Not installed')"
	@echo "  Docker:     $$(docker --version 2>/dev/null || echo 'Not installed')"

