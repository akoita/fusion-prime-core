# Dependency Version Strategy

## Current Status: Version Conflicts Detected ⚠️

Multiple services are using different versions of core dependencies, which can cause:
- Runtime incompatibilities
- Security vulnerabilities
- Maintenance overhead
- Deployment complexity

## Version Conflicts Summary

### Critical Conflicts (Breaking Changes Possible)

1. **FastAPI**: `0.104.x`, `0.109.x`, `0.115.0`
   - Services using `0.115.0`: fiat-gateway, cross-chain-integration (newest)
   - Services using `0.109.0`: alert-notification, price-oracle
   - Services using `0.104.x`: compliance, risk-engine

2. **Pydantic**: `2.5.x`, `2.9.2`
   - Services using `2.9.2`: fiat-gateway, cross-chain-integration (newest)
   - Services using `2.5.x`: compliance, risk-engine, alert-notification, price-oracle

3. **Uvicorn**: `0.27.0`, `0.32.0`, `>=0.38.0`
   - Services using `0.32.0`: fiat-gateway, cross-chain-integration
   - Services using `0.38.0+`: compliance, risk-engine
   - Services using `0.27.0`: alert-notification, price-oracle

4. **SQLAlchemy**: `2.0.0`, `2.0.23`, `2.0.25`, `2.0.36`
   - Services using `2.0.36`: fiat-gateway, cross-chain-integration (newest)
   - Services using older: compliance, risk-engine, alert-notification

5. **HTTPX**: `0.25.x`, `0.26.0`, `0.27.2`
   - Services using `0.27.2`: fiat-gateway, cross-chain-integration (newest)

### Medium Priority Conflicts

- **google-cloud-pubsub**: `2.18.x`, `2.19.0`, `2.25.0`
- **alembic**: `1.13.0`, `1.13.1`, `1.13.2`
- **pydantic-settings**: `2.1.0`, `2.6.1`

## Recommended Strategy

### Option A: Standardize on Latest Stable (Recommended for New Services)

**Target Versions** (as of 2025-11-02):
- `fastapi==0.115.0` (latest stable)
- `uvicorn[standard]==0.32.0` or `>=0.38.0` (check compatibility)
- `pydantic==2.9.2` (latest stable)
- `pydantic-settings==2.6.1` (latest stable)
- `sqlalchemy[asyncio]==2.0.36` (latest stable)
- `httpx==0.27.2` (latest stable)
- `google-cloud-pubsub>=2.25.0` (latest stable)
- `alembic==1.13.2` (latest stable)

**Pros**: Latest features, security patches, performance improvements
**Cons**: Requires testing and potentially updating older services

### Option B: Standardize on Current Majority (Safer for Existing Services)

**Target Versions**:
- `fastapi>=0.104.0,<0.116.0`
- `uvicorn[standard]>=0.38.0`
- `pydantic>=2.5.0,<3.0.0`
- `sqlalchemy>=2.0.0,<3.0.0`
- Use range constraints to allow patch updates

**Pros**: Less disruptive to existing services
**Cons**: Misses latest improvements

## Migration Plan

### Phase 1: New Services (fiat-gateway, cross-chain-integration)
✅ **Status**: Already using latest versions
- Keep current versions
- These are the reference implementations

### Phase 2: Update Core Services (Compliance, Risk Engine)
- Update `requirements.txt` and `pyproject.toml` to latest versions
- Test thoroughly (especially Pydantic v2 breaking changes)
- Update any code that relies on deprecated APIs

### Phase 3: Update Supporting Services (Alert Notification, Price Oracle)
- Update to match core services
- Less critical, can be done incrementally

## Immediate Actions

1. **Document current state** (this file) ✅
2. **Create shared requirements** (optional, for common dependencies)
3. **Update services incrementally** (prioritize critical services first)
4. **Test inter-service compatibility**

## Compatibility Notes

### Pydantic v2 Breaking Changes
- Pydantic v2.9.2 requires code updates for:
  - Field validation changes
  - JSON serialization differences
  - Model configuration changes

### FastAPI Compatibility
- FastAPI 0.115.0 is compatible with Pydantic 2.9.2
- Older FastAPI versions may work with newer Pydantic, but not recommended

### SQLAlchemy 2.0.x
- All versions 2.0.x are compatible
- Recommend using `2.0.36` for latest bug fixes

## Recommended Action: Incremental Alignment

1. **Keep new services as-is** (they're using latest)
2. **Update older services gradually**:
   - Start with non-critical services (price-oracle, alert-notification)
   - Then update compliance and risk-engine
3. **Use version ranges** for less critical dependencies (google-cloud-*)
4. **Test thoroughly** before deployment

## Monitoring

Regularly check for:
- Security vulnerabilities: `safety check`
- Outdated packages: `pip list --outdated`
- Breaking changes in release notes
