# Sprint 05 Planning: Authentication, Integration & Production Readiness (UPDATED)

**Planning Date**: November 3, 2025 (Updated based on implementation status analysis)
**Sprint Duration**: 3-4 weeks
**Status**: 🚀 **READY TO START**
**Prerequisites**: ✅ Sprint 04 Complete

---

## 🎯 Sprint 05 Overview (UPDATED)

### Critical Discovery
**Analysis Date**: November 3, 2025

After comprehensive implementation status analysis, we've identified that:
1. ✅ **Backend services are 100% operational** (12 microservices deployed)
2. 🔴 **CRITICAL GAP**: No authentication service exists (frontend uses mock auth)
3. ⚠️ **Sprint 04 features not integrated into frontend** (cross-chain, fiat gateway)
4. ⚠️ **Missing tests for 5/9 services**

**See**: `docs/PROJECT_IMPLEMENTATION_STATUS.md` for full analysis

### Adjusted Goal
**AUTHENTICATION FIRST**, then harden the platform for production deployment with frontend integration, comprehensive testing, monitoring, and security measures.

### Updated Objectives (Priority Order)
1. 🔴 **CRITICAL**: Implement Identity/Authentication Service (PRODUCTION BLOCKER)
2. 🔴 **CRITICAL**: Fix frontend mock authentication
3. 🟡 **HIGH**: Integrate Sprint 04 features into frontend (cross-chain, fiat gateway)
4. 🟡 **HIGH**: Add missing service tests (5 services have no tests)
5. 🟡 **HIGH**: Observability and monitoring dashboards
6. 🟢 **MEDIUM**: Performance optimization
7. 🟢 **MEDIUM**: Security review and hardening
8. 🟢 **MEDIUM**: Production infrastructure preparation

---

## 📋 Workstream Breakdown (UPDATED)

### 1. 🔴 Identity & Authentication Service (Week 1) **NEW - CRITICAL**
**Owner**: Backend Team
**Priority**: CRITICAL (Production Blocker)

**Problem Statement**:
- Risk Dashboard currently uses completely mock authentication
- ANY email/password combination works
- No backend authentication service exists
- No JWT token generation or validation
- Cannot deploy to production

**Tasks:**
- [ ] Create Identity Service microservice
  - [ ] Service scaffold with FastAPI
  - [ ] User registration endpoint (`POST /auth/register`)
  - [ ] User login endpoint (`POST /auth/login`)
  - [ ] Token refresh endpoint (`POST /auth/refresh`)
  - [ ] User profile endpoint (`GET /auth/me`)
  - [ ] Password reset flow
- [ ] Implement JWT token management
  - [ ] Access token generation (15 min expiry)
  - [ ] Refresh token generation (7 day expiry)
  - [ ] Token validation middleware
  - [ ] Token blacklist for logout
- [ ] Database setup
  - [ ] Users table (id, email, password_hash, created_at, etc.)
  - [ ] Refresh tokens table (token_id, user_id, expires_at, revoked)
  - [ ] Alembic migrations
- [ ] Security implementation
  - [ ] Password hashing (bcrypt)
  - [ ] Email validation
  - [ ] Rate limiting on login attempts
  - [ ] CORS configuration
- [ ] Integration tests
  - [ ] Registration flow test
  - [ ] Login flow test
  - [ ] Token refresh test
  - [ ] Invalid credentials test
  - [ ] Expired token test

**Deliverables:**
- `services/identity/` - Complete authentication service
- `services/identity/app/main.py` - FastAPI application
- `services/identity/app/routes/auth.py` - Authentication endpoints
- `services/identity/app/core/security.py` - JWT and password utilities
- `services/identity/infrastructure/db/models.py` - User and token models
- `services/identity/tests/` - Test suite (>80% coverage)
- `services/identity/cloudbuild.yaml` - Deployment configuration
- `services/identity/README.md` - Service documentation

**API Spec (OpenAPI)**:
```yaml
/auth/register:
  post:
    summary: Register new user
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              email: string
              password: string
              name: string
    responses:
      201: User created
      400: Validation error
      409: User already exists

/auth/login:
  post:
    summary: Login user
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              email: string
              password: string
    responses:
      200:
        description: Login successful
        content:
          application/json:
            schema:
              type: object
              properties:
                access_token: string
                refresh_token: string
                token_type: string (Bearer)
                expires_in: integer
      401: Invalid credentials
      429: Too many login attempts

/auth/refresh:
  post:
    summary: Refresh access token
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              refresh_token: string
    responses:
      200: New tokens issued
      401: Invalid or expired refresh token

/auth/me:
  get:
    summary: Get current user profile
    security:
      - BearerAuth: []
    responses:
      200: User profile
      401: Unauthorized
```

**Dependencies**:
- PostgreSQL database (create `fp-identity-db`)
- Secret Manager for JWT secret key
- VPC connector for database access

---

### 2. 🔴 Frontend Authentication Fix (Week 1) **NEW - CRITICAL**
**Owner**: Frontend Team
**Priority**: CRITICAL (Production Blocker)

**Problem Statement**:
- `frontend/risk-dashboard/src/lib/auth.ts` has mock authentication
- No integration with real authentication backend
- Token management not implemented
- Session handling not implemented

**Tasks:**
- [ ] Update authentication library (`auth.ts`)
  - [ ] Remove mock authentication code
  - [ ] Add Identity Service API client
  - [ ] Implement real login function
  - [ ] Implement real registration function
  - [ ] Implement token refresh logic
  - [ ] Implement logout function
- [ ] Token management
  - [ ] Store access token in memory or sessionStorage
  - [ ] Store refresh token in httpOnly cookie (preferred) or localStorage
  - [ ] Implement automatic token refresh before expiry
  - [ ] Clear tokens on logout
- [ ] API client updates
  - [ ] Add Authorization header with Bearer token
  - [ ] Implement token refresh on 401 responses
  - [ ] Retry failed requests after token refresh
- [ ] Login/Logout UI
  - [ ] Update login form to call real API
  - [ ] Add loading states
  - [ ] Add error handling
  - [ ] Add "Remember me" option (optional)
- [ ] Protected routes
  - [ ] Verify routes check authentication
  - [ ] Redirect to login if unauthenticated
  - [ ] Handle token expiry gracefully
- [ ] Testing
  - [ ] Test login flow
  - [ ] Test logout flow
  - [ ] Test token refresh
  - [ ] Test error handling

**Deliverables:**
- Updated `frontend/risk-dashboard/src/lib/auth.ts` with real authentication
- Token management implementation
- Updated API client with authentication
- Tests for authentication flows

**Example Implementation**:
```typescript
// auth.ts (updated)
import { apiClient } from './api-client';

export interface User {
  id: string;
  email: string;
  name: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

class AuthService {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  async login(email: string, password: string): Promise<User> {
    const response = await apiClient.post<AuthTokens>('/auth/login', {
      email,
      password,
    });

    this.accessToken = response.access_token;
    this.refreshToken = response.refresh_token;

    // Store refresh token securely
    localStorage.setItem('refresh_token', response.refresh_token);

    // Get user profile
    const user = await this.getCurrentUser();
    return user;
  }

  async refreshAccessToken(): Promise<string> {
    const refreshToken = this.refreshToken || localStorage.getItem('refresh_token');
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await apiClient.post<AuthTokens>('/auth/refresh', {
      refresh_token: refreshToken,
    });

    this.accessToken = response.access_token;
    return response.access_token;
  }

  getAccessToken(): string | null {
    return this.accessToken;
  }

  async logout(): Promise<void> {
    this.accessToken = null;
    this.refreshToken = null;
    localStorage.removeItem('refresh_token');
  }

  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>('/auth/me');
    return response;
  }
}

export const authService = new AuthService();
```

**Dependencies**:
- Identity Service deployed and operational
- Environment variable for Identity Service URL

---

### 3. 🟡 Frontend Integration of Sprint 04 Features (Week 2) **NEW - HIGH**
**Owner**: Frontend Team
**Priority**: HIGH

**Problem Statement**:
- Cross-Chain Integration Service is operational but no UI
- Fiat Gateway Service is operational but no UI
- Developer Portal not deployed
- Users cannot access Sprint 04 features

**Tasks:**

#### A. Cross-Chain Integration UI
- [ ] Create cross-chain settlement page
  - [ ] Settlement initiation form
    - Source chain selector (Sepolia/Amoy)
    - Destination chain selector
    - Asset selector (USDC, WETH, etc.)
    - Amount input
    - Bridge protocol selector (Axelar/CCIP)
  - [ ] Message status tracking page
    - List of cross-chain messages
    - Status indicator (pending, confirmed, failed)
    - Transaction hash links
    - Retry button for failed messages
  - [ ] Collateral snapshot page
    - Multi-chain collateral visualization
    - Per-chain breakdown
    - Total collateral in USD
    - Credit line calculation display

#### B. Fiat Gateway UI
- [ ] Create fiat on-ramp page
  - [ ] Circle USDC on-ramp form
    - Amount input (USD)
    - Payment method (bank transfer, card)
    - Destination address
    - Transaction confirmation
  - [ ] Stripe payment integration
    - Payment intent creation
    - Payment form (Stripe Elements)
    - Payment confirmation
- [ ] Create fiat off-ramp page
  - [ ] USDC → Fiat form
    - Amount input (USDC)
    - Bank account details
    - Transaction confirmation
  - [ ] Transaction status tracking
- [ ] Transaction history page
  - [ ] List of fiat transactions
  - [ ] Status (pending, completed, failed)
  - [ ] Transaction details

#### C. Developer Portal Deployment
- [ ] Deploy to Cloud Run
  - [ ] Create cloudbuild.yaml
  - [ ] Configure environment variables
  - [ ] Set up custom domain
- [ ] Update API documentation
  - [ ] Add cross-chain endpoints
  - [ ] Add fiat gateway endpoints
  - [ ] Update examples

#### D. API Integration
- [ ] Create Cross-Chain Integration Service client
- [ ] Create Fiat Gateway Service client
- [ ] Add error handling
- [ ] Add loading states
- [ ] Add success/error notifications

**Deliverables:**
- Cross-chain settlement UI in Risk Dashboard
- Fiat gateway UI in Risk Dashboard
- Developer Portal deployed
- API documentation updated
- Integration tests for new features

**Dependencies**:
- Authentication service operational
- Cross-Chain Integration Service operational (✅ already deployed)
- Fiat Gateway Service operational (✅ already deployed)

---

### 4. 🟡 Missing Service Tests (Week 2) **NEW - HIGH**
**Owner**: Backend Team
**Priority**: HIGH

**Problem Statement**:
- 5/9 services have NO tests
- Test coverage insufficient for production

**Services Without Tests**:
1. Fiat Gateway Service (0 tests)
2. API Key Service (0 tests)
3. Alert Notification Service (0 tests)
4. Event Relayer (0 tests)
5. Price Oracle (0 tests)

**Tasks for Each Service:**
- [ ] Unit tests
  - [ ] Route tests (all endpoints)
  - [ ] Service logic tests
  - [ ] Database model tests
  - [ ] Integration client tests (Circle, Stripe, etc.)
- [ ] Integration tests
  - [ ] End-to-end workflow tests
  - [ ] Database integration tests
  - [ ] External API integration tests (with mocks)
- [ ] Test infrastructure
  - [ ] Pytest fixtures
  - [ ] Test database setup
  - [ ] Mock factories

**Fiat Gateway Service Tests (Example)**:
```python
# tests/test_fiat_gateway.py
def test_create_circle_on_ramp(client, db_session):
    """Test Circle USDC on-ramp transaction creation."""
    response = client.post("/fiat/on-ramp", json={
        "amount": 1000,
        "provider": "circle",
        "destination_address": "0x123...",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == 1000
    assert data["provider"] == "circle"
    assert data["status"] == "pending"

def test_stripe_payment_intent(client, mock_stripe):
    """Test Stripe payment intent creation."""
    # Test implementation
    pass

# tests/test_transaction_service.py
def test_transaction_persistence(db_session):
    """Test transaction service database operations."""
    # Test implementation
    pass
```

**Test Coverage Goal**: >80% for all services

**Deliverables:**
- Test suite for each service
- Test coverage reports
- CI/CD integration for tests

---

### 5. 🟡 Observability & Monitoring (Week 2-3) **HIGH**
**Owner**: DevOps Team
**Priority**: HIGH

**Problem Statement**:
- Only basic Cloud Logging and Monitoring
- No custom dashboards
- No alerting policies
- Cannot proactively detect issues

**Tasks:**
- [ ] Create Custom Cloud Monitoring Dashboards
  - [ ] Service Health Dashboard
    - Service uptime status
    - Request rate per service
    - Error rate per service
    - Latency (p50, p95, p99)
  - [ ] Cross-Chain Dashboard
    - Message success rate
    - Message latency by bridge
    - Failed message count
    - Retry attempts
  - [ ] Business Metrics Dashboard
    - Fiat transactions (volume, count)
    - Cross-chain settlements (volume, count)
    - Active users
    - API usage by tier
  - [ ] Cost Tracking Dashboard
    - Compute costs
    - Data storage costs
    - Network egress costs
- [ ] Configure Alerting Policies
  - [ ] Critical Alerts (PagerDuty integration)
    - Service down (any service)
    - Database connection failures
    - High error rate (>5%)
    - API Gateway down
  - [ ] Warning Alerts (Email/Slack)
    - High latency (p95 >500ms)
    - Database high CPU (>80%)
    - Disk space low (<20%)
    - Failed cross-chain messages
- [ ] Distributed Tracing
  - [ ] Enable Cloud Trace for all services
  - [ ] Add trace context propagation
  - [ ] Create trace analysis views
- [ ] Log Aggregation
  - [ ] Structured logging for all services
  - [ ] Log-based metrics
  - [ ] Error log aggregation
  - [ ] Audit log collection

**Deliverables:**
- 4+ Custom Cloud Monitoring dashboards
- 10+ Alerting policies configured
- Distributed tracing operational
- Log aggregation setup

**Dependencies**:
- Cloud Monitoring API enabled
- PagerDuty integration (optional)
- Slack webhook for alerts (optional)

---

### 6. 🟢 Performance Optimization (Week 3) **MEDIUM**
**Owner**: Backend Team
**Priority**: MEDIUM

**Tasks:**
- [ ] Database query optimization
  - [ ] Add indexes for frequently queried fields
  - [ ] Optimize cross-chain message queries
  - [ ] Implement query result caching where appropriate
  - [ ] Add connection pooling configuration
- [ ] Service performance tuning
  - [ ] Review and optimize async operations
  - [ ] Implement request batching for bridge operations
  - [ ] Add response caching for static endpoints
- [ ] API Gateway optimization
  - [ ] Review and optimize rate limits
  - [ ] Implement CDN for static assets
  - [ ] Add response compression
- [ ] Performance benchmarking
  - [ ] Baseline performance metrics
  - [ ] Load testing (Apache JMeter or k6)
  - [ ] Identify bottlenecks

**Deliverables:**
- Performance benchmarks
- Optimization report
- Updated monitoring dashboards

---

### 7. 🟢 Security Review & Hardening (Week 3) **MEDIUM**
**Owner**: Security Team / DevOps
**Priority**: MEDIUM

**Tasks:**
- [ ] Internal security review
  - [ ] Review and update access controls (IAM, service accounts)
  - [ ] Implement secrets rotation strategy
  - [ ] Add security headers and HTTPS enforcement
  - [ ] Review and harden API Gateway security
- [ ] Authentication security
  - [ ] Verify JWT token security
  - [ ] Implement rate limiting on login attempts
  - [ ] Add brute force protection
  - [ ] Implement session management security
- [ ] API Gateway security
  - [ ] Verify API key authentication
  - [ ] Test rate limiting
  - [ ] Add request signing for sensitive operations
  - [ ] Implement CORS properly
- [ ] Security monitoring
  - [ ] Set up security event logging
  - [ ] Configure Cloud Security Command Center
  - [ ] Add anomaly detection

**Deliverables:**
- Security audit report
- Vulnerability remediation plan
- Updated security documentation
- Security monitoring dashboards

**Note**: Full external security audit deferred to Sprint 06

---

### 8. 🟢 Production Infrastructure Preparation (Week 3-4) **MEDIUM**
**Owner**: DevOps Team
**Priority**: MEDIUM (Can start in Week 3)

**Tasks:**
- [ ] Set up production GCP project
  - [ ] Create production project
  - [ ] Configure IAM and service accounts
  - [ ] Set up billing alerts
- [ ] Production database setup
  - [ ] Create production Cloud SQL instances
  - [ ] Set up automated backups
  - [ ] Configure high availability
- [ ] Production deployment pipelines
  - [ ] Create production Cloud Build configurations
  - [ ] Set up deployment approvals
  - [ ] Configure blue-green deployments
- [ ] Disaster recovery
  - [ ] Document backup and restore procedures
  - [ ] Test disaster recovery scenarios

**Deliverables:**
- Production environment ready
- Deployment runbooks
- Disaster recovery plan

**Note**: Mainnet contract deployment deferred to Sprint 06 (after security audit)

---

## 📊 Sprint 05 Success Criteria (UPDATED)

**Critical Success Criteria** (Must Have):
- [x] Identity/Authentication Service deployed and operational
- [x] Frontend authentication working with real backend
- [x] Users can login, register, and manage sessions
- [x] Sprint 04 features accessible in UI (cross-chain, fiat gateway)
- [x] Test coverage >80% for all services
- [x] Custom monitoring dashboards operational
- [x] Alerting configured for critical issues

**High Priority Criteria** (Should Have):
- [ ] Performance benchmarks established
- [ ] Security review completed
- [ ] Production environment ready
- [ ] End-to-end tests for key workflows
- [ ] Developer Portal deployed

**Medium Priority Criteria** (Nice to Have):
- [ ] Distributed tracing operational
- [ ] Advanced monitoring dashboards
- [ ] Load testing completed
- [ ] Documentation complete

---

## 📅 Week-by-Week Breakdown (UPDATED)

### Week 1: Authentication & Critical Fixes 🔴

**Day 1-2: Identity Service Implementation**
- Create service scaffold
- Implement registration and login endpoints
- Set up database and migrations
- Implement JWT token generation

**Day 3: Identity Service Completion**
- Implement token refresh
- Add password reset
- Write tests (>80% coverage)
- Deploy to Cloud Run

**Day 4: Frontend Authentication**
- Update auth.ts with real API calls
- Implement token management
- Update API client
- Test login/logout flows

**Day 5: Integration & Testing**
- Integration testing (frontend + backend)
- Fix issues
- Deploy Developer Portal
- Fix API Gateway configuration

**Week 1 Deliverables**:
- ✅ Identity Service deployed
- ✅ Frontend authentication working
- ✅ Developer Portal deployed
- ✅ API Gateway configuration fixed

---

### Week 2: Frontend Integration & Testing 🟡

**Day 1-2: Cross-Chain Integration UI**
- Settlement initiation form
- Message status tracking page
- Collateral snapshot visualization
- Integration with Cross-Chain Integration Service

**Day 3: Fiat Gateway UI**
- Fiat on-ramp form (Circle)
- Fiat off-ramp form (Stripe)
- Transaction history page
- Integration with Fiat Gateway Service

**Day 4: Service Tests (Part 1)**
- Fiat Gateway Service tests
- API Key Service tests
- Alert Notification Service tests

**Day 5: Service Tests (Part 2)**
- Event Relayer tests
- Price Oracle tests
- Integration test fixes

**Week 2 Deliverables**:
- ✅ Cross-chain and fiat features in UI
- ✅ Test coverage >80% for all services
- ✅ Integration tests passing

---

### Week 3: Monitoring, Performance & Security 🟢

**Day 1-2: Observability**
- Create custom monitoring dashboards
- Configure alerting policies
- Set up distributed tracing
- Log aggregation

**Day 3: Performance Optimization**
- Database query optimization
- Service performance tuning
- Performance benchmarking
- Load testing

**Day 4: Security Review**
- Internal security assessment
- Access control review
- API Gateway security verification
- Security monitoring setup

**Day 5: Production Preparation**
- Start production GCP project setup
- Production database planning
- Deployment runbook creation

**Week 3 Deliverables**:
- ✅ Monitoring dashboards operational
- ✅ Performance benchmarks established
- ✅ Security review completed
- ✅ Production preparation started

---

### Week 4 (Optional): Production Finalization 🟢

**Day 1-3: Production Environment**
- Complete production GCP project setup
- Configure production databases
- Set up production deployment pipelines
- Disaster recovery testing

**Day 4-5: Documentation & Review**
- Complete operational runbooks
- Finish API documentation
- Sprint review and retrospective
- Planning for Sprint 06

**Week 4 Deliverables** (Optional):
- ✅ Production environment ready
- ✅ Documentation complete
- ✅ Ready for Sprint 06

---

## 🚀 Sprint 05 Dependencies (UPDATED)

**Completed**:
- ✅ Sprint 04 backend complete (all services operational)
- ✅ Testnet deployments successful
- ✅ Cross-Chain Integration Service operational
- ✅ Fiat Gateway Service operational

**Required**:
- PostgreSQL database for Identity Service (create `fp-identity-db`)
- JWT secret key (generate and store in Secret Manager)
- Developer Portal domain (optional)

**External**:
- Security audit firm engagement (deferred to Sprint 06)
- Mainnet RPC provider setup (deferred to Sprint 06)

---

## 📈 Expected Outcomes (UPDATED)

By the end of Sprint 05:
- ✅ **Authentication functional** (frontend + backend)
- ✅ **Sprint 04 features accessible** (cross-chain, fiat gateway in UI)
- ✅ **Test coverage >80%** for all services
- ✅ **Monitoring operational** with custom dashboards and alerting
- ✅ **Performance benchmarks** established
- ✅ **Security review** completed
- ⚠️ **Production environment** prepared (deployment in Sprint 06)

---

## 🔍 Risk Mitigation (UPDATED)

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Authentication complexity** | High | Start with minimal viable auth, iterate. Use proven libraries (PyJWT, bcrypt) |
| **Frontend integration delays** | High | Parallelize work. Use mock data initially. Incremental integration |
| **Test coverage time** | Medium | Prioritize critical services (Fiat Gateway). Template-based tests |
| **Monitoring setup complexity** | Medium | Start with essential dashboards. Iterate based on needs |
| **Performance optimization** | Low | Focus on quick wins (indexes, caching). Deep optimization in Sprint 06 |

---

## 📝 Notes (UPDATED)

- **Critical Discovery**: After analysis, authentication identified as production blocker
- **Sprint Reprioritization**: Authentication moved to highest priority
- **Sprint 04 Completion**: Backend 100% complete, frontend integration 0%
- **Testing Gap**: 5/9 services have no tests
- **Production Timeline**: Production deployment moved to Sprint 06 (after authentication)
- **Security Audit**: Full external audit deferred to Sprint 06

---

## 🎯 Key Metrics to Track

**Week 1**:
- [ ] Identity Service deployed and healthy
- [ ] Frontend authentication working (0 mock auth code remaining)
- [ ] Developer Portal deployed

**Week 2**:
- [ ] Sprint 04 features integrated into UI (cross-chain, fiat)
- [ ] Test coverage: 5/5 services with tests >80%
- [ ] End-to-end tests: ≥3 critical workflows

**Week 3**:
- [ ] Monitoring: ≥4 custom dashboards operational
- [ ] Alerting: ≥10 policies configured
- [ ] Performance: p95 latency <200ms for all APIs
- [ ] Security: 0 critical vulnerabilities

---

**Status**: 🚀 Ready to Start
**Next Action**: Begin Identity Service implementation (Week 1, Day 1)
**Sprint Review**: After Week 3

---

## See Also
- `docs/PROJECT_IMPLEMENTATION_STATUS.md` - Full implementation analysis
- `docs/SPRINT_04_COMPLETE.md` - Sprint 04 completion summary
- `frontend/risk-dashboard/src/lib/auth.ts` - Current mock authentication (TO BE REPLACED)
