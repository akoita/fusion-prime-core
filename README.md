# Fusion Prime

**Cross-chain digital asset treasury and settlement platform built on programmable smart-contract wallets, GCP-native microservices, and TypeScript/Python SDKs.**

---

## 🚀 Quick Start

### **New to Fusion Prime?**
1. **[QUICKSTART.md](./QUICKSTART.md)** - Complete local setup in 30 minutes
2. **[TESTING.md](./TESTING.md)** - Testing strategy and execution ✅ **UPDATED**
3. **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Deployment guide for all environments

### **Ready to Deploy?**
1. **[docs/CONFIGURATION_MANAGEMENT.md](./docs/CONFIGURATION_MANAGEMENT.md)** - Complete configuration guide
2. **[ENVIRONMENTS.md](./ENVIRONMENTS.md)** - Environment configuration
3. **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Complete deployment guide
4. **[docs/gcp-deployment.md](./docs/gcp-deployment.md)** - GCP deployment details

---

## 📚 Documentation

### **User-Facing Guides**
- **[QUICKSTART.md](./QUICKSTART.md)** - Local development setup
- **[TESTING.md](./TESTING.md)** - Testing strategy and execution
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Complete deployment guide
- **[ENVIRONMENTS.md](./ENVIRONMENTS.md)** - Environment configuration

### **Technical Documentation**
- **[docs/README.md](./docs/README.md)** - Technical documentation hub
- **[docs/specification.md](./docs/specification.md)** - Product specification
- **[docs/CONFIGURATION_MANAGEMENT.md](./docs/CONFIGURATION_MANAGEMENT.md)** - Configuration management guide
- **[docs/architecture/](./docs/architecture/)** - Architecture patterns
- **[docs/integrations/](./docs/integrations/)** - Integration guides
- **[DATABASE_SETUP.md](./DATABASE_SETUP.md)** - Database migration system
- **[MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)** - Developer migration guide

### **Standards and Governance**
- **[DOCUMENTATION_STANDARDS.md](./DOCUMENTATION_STANDARDS.md)** - Documentation standards
- **[docs/standards/](./docs/standards/)** - Code standards and guidelines

---

## 🏗️ Architecture Overview

Fusion Prime delivers a cross-chain digital asset treasury and settlement platform with:

- **Smart Contracts**: Foundry-based programmable wallets and cross-chain adapters
- **Backend Services**: Python microservices with hexagonal architecture
- **Cross-Chain Integration**: Bridge adapters and relayers
- **Analytics**: Risk and treasury analytics with ML pipelines
- **Compliance**: Policy-as-code workflows and audit trails
- **APIs**: OpenAPI/AsyncAPI specifications with contract testing
- **SDKs**: TypeScript/Python client libraries
- **Frontend**: React-based treasury portal
- **Infrastructure**: Terraform-based GCP deployment

---

## 🎯 Current Status

- **✅ Smart Contracts**: Deployed and tested on Sepolia testnet
- **✅ Backend Services**: Settlement, risk, compliance, and relayer services deployed
- **✅ Testnet Validation**: All 24 tests passing with real blockchain interactions
- **✅ Infrastructure**: Cloud Run, Cloud SQL, Pub/Sub fully operational
- **✅ CI/CD**: GitHub Actions with automated testing and deployment

---

## 🚀 Quick Commands

### **Local Development**
```bash
# Setup (first time)
make setup

# Start local environment
make dev

# Run tests
./scripts/test.sh local
```

### **Testnet Deployment**
```bash
# Deploy to testnet
make deploy-testnet

# Run testnet tests
./scripts/test.sh testnet
```

### **Production Deployment**
```bash
# Deploy to production
make deploy-production

# Monitor services
gcloud run services list --region=us-central1
```

---

## 📁 Project Structure

```
fusion-prime/
├── contracts/           # Smart contracts (Foundry)
├── services/            # Backend microservices (Python)
├── integrations/        # Cross-chain relayers
├── analytics/           # Risk and treasury analytics
├── compliance/          # Policy-as-code workflows
├── api/                 # OpenAPI/AsyncAPI specs
├── sdk/                 # Client SDKs (TypeScript/Python)
├── frontend/            # React treasury portal
├── infra/               # Terraform infrastructure
├── docs/                # Technical documentation
└── tests/               # Test suites
```

---

## 🧪 Testing

### **Test Coverage**
- **Unit Tests**: 85% coverage across all components
- **Integration Tests**: 78% coverage for service interactions
- **E2E Tests**: 92% coverage for end-to-end workflows
- **Contract Tests**: 88% coverage for smart contracts

### **Test Environments**
- **Local**: Docker Compose with Anvil blockchain
- **Testnet**: GCP with Sepolia testnet
- **Production**: GCP with Ethereum mainnet

---

## 🚀 Deployment

### **Environments**
- **🔄 DEV**: $0 cost, auto-deploy on dev branch push
- **🧪 STAGING**: ~$5/month, manual deploy to staging branch
- **🚀 PRODUCTION**: Real ETH costs, deploy on git tags

### **Services Deployed**
- **Settlement Service**: Core settlement logic
- **Risk Engine Service**: Risk calculations and analytics
- **Compliance Service**: KYC/AML workflows
- **Event Relayer**: Blockchain event processing (Cloud Run Job)

---

## 📊 Monitoring

### **Health Checks**
- Settlement: `/health`
- Risk Engine: `/health/`
- Compliance: `/health/`

### **Monitoring Tools**
- Cloud Run services and jobs
- Cloud SQL database metrics
- Pub/Sub message queues
- Custom dashboards and alerts

---

## 🔧 Development

### **Prerequisites**
- Docker and Docker Compose
- Foundry (forge, cast, anvil)
- Python 3.11+
- Node.js 18+
- GCP CLI (for deployment)

### **Development Workflow**
1. **🔄 DEV**: Develop on `dev` branch, auto-deploy to DEV environment (Anvil blockchain)
2. **🧪 STAGING**: Promote to `staging` branch, deploy to STAGING environment (Sepolia testnet)
3. **🚀 PRODUCTION**: Create git tag, deploy to PRODUCTION environment (Ethereum mainnet)

### **Environment-Aware Deployment**
- **Automatic configuration** for dev/staging/production environments
- **Environment-specific resource allocation** and blockchain networks
- **Single command deployment** with appropriate settings

---

## 📚 Learn More

### **Getting Started**
- **[QUICKSTART.md](./QUICKSTART.md)** - Start here! Complete local setup
- **[TESTING.md](./TESTING.md)** - Learn about testing strategy
- **[ENVIRONMENTS.md](./ENVIRONMENTS.md)** - Understand environment setup

### **Deployment**
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Complete deployment guide
- **[docs/gcp-deployment.md](./docs/gcp-deployment.md)** - GCP-specific deployment
- **[docs/git-based-versioning.md](./docs/git-based-versioning.md)** - Release management

### **Architecture**
- **[docs/specification.md](./docs/specification.md)** - Product specification
- **[docs/architecture/](./docs/architecture/)** - Architecture patterns
- **[docs/integrations/](./docs/integrations/)** - Integration specifications

### **Standards**
- **[docs/standards/](./docs/standards/)** - Code standards and guidelines
- **[DOCUMENTATION_STANDARDS.md](./DOCUMENTATION_STANDARDS.md)** - Documentation standards

---

## 🆘 Support

### **Getting Help**
1. **Check documentation**: Start with the guides above
2. **Check logs**: Review service logs for errors
3. **Check status**: Verify all services are running
4. **Create issue**: Report bugs or request features

### **Emergency Procedures**
1. **Service down**: Check health endpoints and restart services
2. **Database issues**: Check Cloud SQL status and restore from backup
3. **Blockchain issues**: Check RPC provider status and switch if needed
4. **Performance issues**: Check resource usage and scale services

---

## 📈 Roadmap

### **Current Sprint**
- Risk analytics and compliance foundation
- Cross-chain integration
- Production hardening

### **Upcoming Features**
- Advanced risk models
- Additional blockchain support
- Enhanced compliance workflows
- Mobile SDKs

---

**Last Updated**: 2025-01-24
**Version**: v1.0.0-dev
**Status**: Active Development# Testing dev branch auto-deployment
