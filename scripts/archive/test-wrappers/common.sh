#!/bin/bash
# Common utilities for test scripts

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo ""
    echo -e "${PURPLE}========================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}========================================${NC}"
    echo ""
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_step() {
    echo -e "${CYAN}🔄 $1${NC}"
}

# Service checking functions
check_services() {
    print_step "Checking required services..."

    local all_services_ready=true
    local services=("anvil" "postgres" "pubsub-emulator" "settlement-service" "event-relayer")
    local services_to_start=()

    # Check each service individually
    for service in "${services[@]}"; do
        if ! docker compose ps "$service" | grep -q "Up"; then
            print_warning "Service $service is not running"
            services_to_start+=("$service")
            all_services_ready=false
        fi
    done

    # Start missing services if any
    if [ ${#services_to_start[@]} -gt 0 ]; then
        print_warning "Starting missing services: ${services_to_start[*]}"
        if ! docker compose up -d; then
            print_error "Failed to start Docker Compose services"
            return 1
        fi

        # Wait for services to become healthy
        print_step "Waiting for services to become healthy..."
        local max_attempts=30
        local attempt=0

        while [ $attempt -lt $max_attempts ]; do
            all_services_ready=true
            for service in "${services[@]}"; do
                if ! docker compose ps "$service" | grep -q "Up"; then
                    all_services_ready=false
                    break
                fi
            done

            if [ "$all_services_ready" = true ]; then
                break
            fi

            sleep 2
            attempt=$((attempt + 1))
        done

        if [ "$all_services_ready" = false ]; then
            print_error "Services failed to start within expected time"
            return 1
        fi
    fi

    print_success "All services are running"
    return 0
}

# Contract deployment
deploy_contracts() {
    print_step "Deploying smart contracts..."

    if python tests/scripts/deploy_contracts.py; then
        print_success "Smart contracts deployed successfully"
        return 0
    else
        print_error "Failed to deploy smart contracts"
        return 1
    fi
}

# Status functions
show_status() {
    print_info "System Status:"
    echo ""

    # Docker services
    echo "Docker Services:"
    docker compose ps
    echo ""

    # Test results
    if [ -d "test-reports" ]; then
        echo "Latest Test Results:"
        ls -la test-reports/ | head -5
    fi
}

show_services() {
    print_info "Service Status and Instructions:"
    echo ""

    echo "1. Start all services:"
    echo "   docker compose up -d"
    echo ""

    echo "2. Check service status:"
    echo "   docker compose ps"
    echo ""

    echo "3. View service logs:"
    echo "   docker compose logs [service-name]"
    echo ""

    echo "4. Stop services:"
    echo "   docker compose down"
    echo ""

    echo "5. Restart services:"
    echo "   docker compose restart"
    echo ""

    # Show current status
    show_status
}

# Environment checking
check_environment() {
    local env_type="$1"

    if [ -z "$env_type" ]; then
        print_error "Environment type not specified"
        return 1
    fi

    local env_file=".env.$env_type"
    if [ ! -f "$env_file" ]; then
        print_error "Environment file $env_file not found"
        print_info "Run setup-env.sh to configure environments"
        return 1
    fi

    print_success "Environment $env_type is configured"
    return 0
}

# Report generation
generate_reports() {
    if [ "$NO_REPORTS" = true ]; then
        return 0
    fi

    print_step "Generating test reports..."

    if [ -d "test-reports" ]; then
        print_success "Test reports generated in test-reports/"
    else
        print_warning "No test reports found"
    fi
}
