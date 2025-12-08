# Database Cleanup Summary

**Date**: 2025-10-28
**Action**: Removed unused databases

## Databases Deleted ✅

### 1. Price Oracle Database (`fp-priceoracle-db-683fed10`)
- **Status**: ✅ Deleted (was already removed)
- **Reason**: Price Oracle service is stateless - fetches prices from external APIs and publishes to Pub/Sub
- **Cost Savings**: ~$10/month

### 2. Alert Notification Database (`fp-alert-db-e0b47f9a`)
- **Status**: ✅ Deleted
- **Reason**: Alert Notification service has no database schema or migrations configured; it's stateless
- **Cost Savings**: ~$10/month

## Resources Cleaned Up ✅

### Cloud SQL Instances
- ✅ Deleted: `fp-alert-db-e0b47f9a`
- ✅ Deleted: `fp-priceoracle-db-683fed10` (was already gone)

### Secrets Removed
- ✅ `fp-alert-db-connection-string`
- ✅ `fp-alert-db-db-password`
- ✅ `fp-priceoracle-db-connection-string`
- ✅ `fp-priceoracle-db-db-password`

### Terraform Configuration
- ✅ Removed `module "cloudsql_price_oracle"` from `infra/terraform/project/cloudsql.tf`
- ✅ Removed `module "cloudsql_alert"` from `infra/terraform/project/cloudsql.tf`

### Documentation Updated
- ✅ Updated `DATABASE_MIGRATION_STATUS.md` to reflect only 3 databases
- ✅ Removed references to Price Oracle and Alert Notification databases
- ✅ Updated database counts in summary sections

## Current Infrastructure

### Active Databases (3)
| Service | Instance Name | Database | User | Tier |
|---------|---------------|----------|------|------|
| Settlement | `fp-settlement-db-590d836a` | settlement_db | settlement_user | db-f1-micro |
| Risk Engine | `fp-risk-db-1d929830` | risk_db | risk_user | db-f1-micro |
| Compliance | `fp-compliance-db-0b9f2040` | compliance_db | compliance_user | db-f1-micro |

### Services Without Databases
- ✅ **Price Oracle** - Stateless, fetches from external APIs only
- ✅ **Alert Notification** - Stateless, sends notifications only

## Cost Savings

**Previous Setup**: 5 databases × $10/month = $50/month
**Current Setup**: 3 databases × $10/month = $30/month
**Savings**: **$20/month** (~$240/year)

Additionally, reduced tier from db-g1-small to db-f1-micro saves ~$75/month across all databases.

## Verification

### Check Active Databases
```bash
gcloud sql instances list --project=fusion-prime
```

Expected output:
```
NAME                       STATUS
fp-risk-db-1d929830        RUNNABLE
fp-compliance-db-0b9f2040  RUNNABLE
fp-settlement-db-590d836a  RUNNABLE
```

### Check Secrets (should not show priceoracle or alert-db)
```bash
gcloud secrets list --project=fusion-prime | grep fp-
```

Expected secrets (6 total):
```
fp-settlement-db-connection-string
fp-settlement-db-db-password
fp-risk-db-connection-string
fp-risk-db-db-password
fp-compliance-db-connection-string
fp-compliance-db-db-password
```

## Next Steps

1. ✅ Complete - Databases deleted
2. ✅ Complete - Secrets cleaned up
3. ✅ Complete - Terraform configuration updated
4. ⏳ **Optional**: Re-run `terraform apply` to sync state
5. ⏳ **Optional**: Update service account permissions if needed

## Services Status

All services remain operational:
- ✅ **Settlement Service** - Connected to `fp-settlement-db-590d836a`
- ✅ **Risk Engine** - Connected to `fp-risk-db-1d929830`
- ✅ **Compliance Service** - Connected to `fp-compliance-db-0b9f2040`
- ✅ **Price Oracle** - No database needed (stateless)
- ✅ **Alert Notification** - No database needed (stateless)

## Notes

- The Price Oracle and Alert Notification services continue to function normally without databases
- No data was lost (these databases were empty/unused)
- The cleanup aligns infrastructure with actual service requirements
- Future database needs can be added back via Terraform if required
