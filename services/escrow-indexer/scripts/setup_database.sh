#!/bin/bash
#
# Database Setup Script for Escrow Indexer
# Initializes the PostgreSQL database and creates the schema
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration from environment or defaults
PROJECT_ID="${GCP_PROJECT:-fusion-prime}"
DB_INSTANCE="${DB_INSTANCE:-escrow-indexer-db}"
DB_NAME="${DB_NAME:-escrow_indexer}"
DB_USER="${DB_USER:-escrow_indexer}"

echo -e "${BLUE}🗄️  Escrow Indexer Database Setup${NC}"
echo ""

# Function to print colored status
print_status() {
    echo -e "${GREEN}✅${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ️${NC} $1"
}

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

# Check if psql is installed (for local connections)
if ! command -v psql &> /dev/null; then
    print_warning "psql not found. Will use gcloud sql connect instead."
    USE_GCLOUD=true
else
    USE_GCLOUD=false
fi

# Set project
print_info "Setting GCP project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Check if Cloud SQL instance exists
print_info "Checking if Cloud SQL instance exists..."
if gcloud sql instances describe $DB_INSTANCE --project=$PROJECT_ID &> /dev/null; then
    print_status "Cloud SQL instance '$DB_INSTANCE' found"
else
    print_error "Cloud SQL instance '$DB_INSTANCE' not found"
    echo ""
    echo "Please create the instance first using Terraform:"
    echo "  cd infra/terraform/project/escrow-indexer"
    echo "  terraform apply"
    echo ""
    exit 1
fi

# Get database connection info
print_info "Getting database connection info..."
DB_CONNECTION_NAME=$(gcloud sql instances describe $DB_INSTANCE \
    --format='value(connectionName)' \
    --project=$PROJECT_ID)
DB_REGION=$(gcloud sql instances describe $DB_INSTANCE \
    --format='value(region)' \
    --project=$PROJECT_ID)

print_status "Connection name: $DB_CONNECTION_NAME"
print_status "Region: $DB_REGION"

# Check if database exists
print_info "Checking if database '$DB_NAME' exists..."
if gcloud sql databases describe $DB_NAME \
    --instance=$DB_INSTANCE \
    --project=$PROJECT_ID &> /dev/null; then
    print_status "Database '$DB_NAME' already exists"
else
    print_info "Creating database '$DB_NAME'..."
    gcloud sql databases create $DB_NAME \
        --instance=$DB_INSTANCE \
        --project=$PROJECT_ID
    print_status "Database created"
fi

# Initialize schema using Python application
print_info "Initializing database schema..."
echo ""
echo "The schema will be initialized automatically when the application starts."
echo "Alternatively, you can run the initialization script:"
echo ""
echo "  python -c \\"
echo "    from infrastructure.db import init_db; \\"
echo "    init_db()\\"
echo ""

# Option to run schema initialization now
read -p "Do you want to initialize the schema now? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Initializing schema..."

    # Get database password from Secret Manager
    if gcloud secrets describe escrow-indexer-db-password --project=$PROJECT_ID &> /dev/null; then
        print_info "Fetching database password from Secret Manager..."
        DB_PASSWORD=$(gcloud secrets versions access latest \
            --secret=escrow-indexer-db-password \
            --project=$PROJECT_ID)
    else
        print_warning "Password secret not found. Please enter password manually."
        read -s -p "Enter database password: " DB_PASSWORD
        echo ""
    fi

    # Get database IP
    DB_IP=$(gcloud sql instances describe $DB_INSTANCE \
        --format='value(ipAddresses[0].ipAddress)' \
        --project=$PROJECT_ID)

    # Set DATABASE_URL environment variable
    export DATABASE_URL="postgresql://$DB_USER:$DB_PASSWORD@$DB_IP:5432/$DB_NAME"

    # Run Python initialization
    cd "$(dirname "$0")/.."
    python3 << EOF
import sys
sys.path.insert(0, '.')
from infrastructure.db import init_db
try:
    init_db()
    print('✅ Schema initialized successfully')
except Exception as e:
    print(f'❌ Error initializing schema: {e}')
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        print_status "Schema initialization complete"
    else
        print_error "Schema initialization failed"
        exit 1
    fi
fi

# Summary
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
print_status "Database setup complete"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Database Details:"
echo "  Instance: $DB_INSTANCE"
echo "  Connection: $DB_CONNECTION_NAME"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""
echo "Next Steps:"
echo "  1. Deploy the service:"
echo "     cd infra/terraform/project/escrow-indexer"
echo "     terraform apply"
echo ""
echo "  2. Or run locally:"
echo "     export DATABASE_URL=<connection-string>"
echo "     python app/main.py"
echo ""
echo "  3. Run backfill script to index existing escrows:"
echo "     ./scripts/backfill.sh"
echo ""
