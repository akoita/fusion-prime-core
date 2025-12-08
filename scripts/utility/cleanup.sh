#!/bin/bash
# Cleanup Local Development Environment
# Wipes out all local dev resources (Docker containers, volumes, cached data)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Fusion Prime - Local Development Environment Cleanup      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Parse arguments
LEVEL="${1:-standard}"

case "$LEVEL" in
  minimal)
    echo -e "${GREEN}Cleanup Level: MINIMAL${NC}"
    echo "  - Stop running containers"
    echo "  - Keep volumes (data preserved)"
    echo ""
    ;;
  standard)
    echo -e "${YELLOW}Cleanup Level: STANDARD (default)${NC}"
    echo "  - Stop running containers"
    echo "  - Remove volumes (⚠️  deletes all data)"
    echo "  - Keep images (faster restart)"
    echo ""
    ;;
  deep)
    echo -e "${RED}Cleanup Level: DEEP${NC}"
    echo "  - Stop running containers"
    echo "  - Remove volumes (⚠️  deletes all data)"
    echo "  - Remove images (⚠️  requires re-download)"
    echo ""
    ;;
  nuclear)
    echo -e "${RED}Cleanup Level: NUCLEAR ☢️${NC}"
    echo "  - Everything in DEEP"
    echo "  - Clean Docker system"
    echo "  - Remove build caches"
    echo "  - Remove broadcast artifacts"
    echo ""
    ;;
  *)
    echo -e "${RED}Invalid cleanup level: $LEVEL${NC}"
    echo ""
    echo "Usage: $0 [LEVEL]"
    echo ""
    echo "Available levels:"
    echo "  minimal   - Stop containers only"
    echo "  standard  - Stop containers + remove volumes (default)"
    echo "  deep      - Standard + remove images"
    echo "  nuclear   - Deep + system cleanup + artifacts"
    echo ""
    exit 1
    ;;
esac

# Confirmation
read -p "Continue with cleanup? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo -e "${YELLOW}Cleanup cancelled.${NC}"
  exit 0
fi

cd "$PROJECT_ROOT"

# MINIMAL: Stop containers
echo ""
echo -e "${BLUE}Step 1: Stopping containers...${NC}"
docker compose down
echo -e "${GREEN}✓ Containers stopped${NC}"

if [[ "$LEVEL" == "minimal" ]]; then
  echo ""
  echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║  Cleanup Complete (MINIMAL)                                ║${NC}"
  echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo "To restart: docker compose up -d"
  exit 0
fi

# STANDARD: Remove volumes
echo ""
echo -e "${BLUE}Step 2: Removing volumes...${NC}"
docker compose down -v
echo -e "${GREEN}✓ Volumes removed${NC}"

if [[ "$LEVEL" == "standard" ]]; then
  echo ""
  echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║  Cleanup Complete (STANDARD)                               ║${NC}"
  echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo "Data wiped. Database and Redis data deleted."
  echo "To restart: docker compose up -d"
  exit 0
fi

# DEEP: Remove images
echo ""
echo -e "${BLUE}Step 3: Removing images...${NC}"
docker compose down -v --rmi all
echo -e "${GREEN}✓ Images removed${NC}"

if [[ "$LEVEL" == "deep" ]]; then
  echo ""
  echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║  Cleanup Complete (DEEP)                                   ║${NC}"
  echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo "Images removed. Next startup will re-download images."
  echo "To restart: docker compose up -d"
  exit 0
fi

# NUCLEAR: System cleanup + artifacts
echo ""
echo -e "${BLUE}Step 4: Docker system cleanup...${NC}"
docker system prune -a --volumes -f
echo -e "${GREEN}✓ Docker system cleaned${NC}"

echo ""
echo -e "${BLUE}Step 5: Removing build artifacts...${NC}"

# Remove contract artifacts
if [ -d "$PROJECT_ROOT/contracts/broadcast" ]; then
  rm -rf "$PROJECT_ROOT/contracts/broadcast"
  echo -e "${GREEN}✓ Contract broadcast artifacts removed${NC}"
fi

if [ -d "$PROJECT_ROOT/contracts/cache" ]; then
  rm -rf "$PROJECT_ROOT/contracts/cache"
  echo -e "${GREEN}✓ Contract cache removed${NC}"
fi

if [ -d "$PROJECT_ROOT/contracts/out" ]; then
  rm -rf "$PROJECT_ROOT/contracts/out"
  echo -e "${GREEN}✓ Contract build output removed${NC}"
fi

# Remove Python caches
find "$PROJECT_ROOT" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_ROOT" -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find "$PROJECT_ROOT" -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
echo -e "${GREEN}✓ Python caches removed${NC}"

# Remove Node modules caches (but keep node_modules)
find "$PROJECT_ROOT" -type d -name ".turbo" -exec rm -rf {} + 2>/dev/null || true
echo -e "${GREEN}✓ Node build caches removed${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Cleanup Complete (NUCLEAR) ☢️                              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Everything has been wiped clean.${NC}"
echo ""
echo "To restart development:"
echo "  1. docker compose up -d"
echo "  2. export PUBSUB_EMULATOR_HOST=localhost:8085"
echo "  3. ./scripts/init-pubsub-emulator.sh"
echo "  4. cd contracts && forge build"
echo ""
echo "See QUICKSTART.md for complete setup instructions."

