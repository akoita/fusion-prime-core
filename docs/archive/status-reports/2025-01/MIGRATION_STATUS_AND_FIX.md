# Database Migration Status and Fix

## Problem Summary

The Cloud Run job `database-migrations` was failing with:
```
connection to server on socket "/cloudsql/fusion-prime:us-central1:fp-settlement-db-590d836a/.s.PGSQL.5432" failed: server closed the connection unexpectedly
```

The underlying error was:
```
failed to connect to instance: dial tcp 10.30.0.18:3307: i/o timeout
```

## Root Causes Identified

1. **Missing Service Account**: The Cloud Run job didn't have a service account configured
2. **Missing IAM Permissions**: Service account lacked `SecretManager.secretAccessor` role
3. **Network Configuration**: Cloud SQL instances didn't have `enablePrivatePathForGoogleCloudServices` enabled
4. **env.py Logic**: The migration script wasn't properly detecting Cloud Run environment

## Fixes Applied

### 1. Updated `env.py` for Cloud Run Detection ✅
File: `services/settlement/alembic/env.py`

**Changes**:
- Added logic to always use Unix socket when running in Cloud Run
- Improved URL parsing to handle special characters in passwords
- Added proper port detection and fallback logic

### 2. Configured Service Account ✅
```bash
# Granted Secret Manager access
gcloud projects add-iam-policy-binding fusion-prime \
  --member="serviceAccount:fp-settlement-db-proxy-sa@fusion-prime.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Updated Cloud Run job to use the service account
gcloud run jobs update database-migrations \
  --region=us-central1 \
  --service-account=fp-settlement-db-proxy-sa@fusion-prime.iam.gserviceaccount.com
```

### 3. Enabled Private Path for Cloud SQL ✅
```bash
# Enabled private path for all three databases
gcloud sql instances patch fp-settlement-db-590d836a --enable-google-private-path
gcloud sql instances patch fp-risk-db-1d929830 --enable-google-private-path
gcloud sql instances patch fp-compliance-db-0b9f2040 --enable-google-private-path
```

## Remaining Issue ⚠️

The migration is **still failing** with the same port 3307 timeout error even after all fixes. This suggests a deeper networking issue:

**Root Problem**: Cloud Run cannot establish a connection to Cloud SQL on the private network (VPC).

**Possible causes**:
1. **Missing VPC Connector**: Cloud Run might need a Serverless VPC Connector to access Cloud SQL private IPs
2. **Firewall Rules**: Network firewall might be blocking port 3307 (Cloud SQL Admin API control port)
3. **Private Service Networking**: The private service networking peering might not be configured correctly
4. **Instance Authorization**: Cloud SQL might not be authorized to accept connections from Cloud Run service account

## Next Steps to Try

### Option 1: Wait and Retry (Recommended)
```bash
# Wait 15 minutes for configuration to propagate, then retry
gcloud run jobs execute database-migrations --region=us-central1
```

### Option 2: Use Public IP (Temporary)
If private network connectivity is problematic, temporarily enable public IP on the databases:
```bash
gcloud sql instances patch fp-settlement-db-590d836a --assign-ip
```

### Option 3: Create VPC Connector
If private path doesn't work, create a VPC connector for Cloud Run:
```bash
gcloud compute networks vpc-access connectors create fusion-prime-connector \
  --region=us-central1 \
  --subnet-project=fusion-prime \
  --subnet=fusion-prime-subnet

# Then update the Cloud Run job to use the connector
gcloud run jobs update database-migrations \
  --vpc-connector=fusion-prime-connector \
  --region=us-central1
```

### Option 4: Run Migrations Manually
As an alternative, you could run migrations from Cloud Shell where network access is already configured:
```bash
# In Cloud Shell
export DATABASE_URL="$(gcloud secrets versions access latest --secret=fp-settlement-db-connection-string)"
cd services/settlement
alembic upgrade head
```

## Verification

To verify the fixes:
```bash
# Check service account is set
gcloud run jobs describe database-migrations --region=us-central1 \
  --format="value(spec.template.spec.serviceAccountName)"

# Check private path is enabled
gcloud sql instances describe fp-settlement-db-590d836a \
  --format="value(settings.ipConfiguration.enablePrivatePathForGoogleCloudServices)"

# Check IAM permissions
gcloud projects get-iam-policy fusion-prime \
  --flatten="bindings[].members" \
  --filter="bindings.members:fp-settlement-db-proxy-sa@fusion-prime.iam.gserviceaccount.com"
```

## References

- [Connecting from Cloud Run](https://cloud.google.com/sql/docs/postgres/connect-run)
- [Cloud SQL IAM Database Authentication](https://cloud.google.com/sql/docs/postgres/authentication)
- [Cloud SQL Private IP](https://cloud.google.com/sql/docs/postgres/private-ip)
