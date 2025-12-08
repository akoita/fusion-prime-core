# Cloud Build Configuration

This directory contains Cloud Build configurations and trigger definitions for Fusion Prime.

## Overview

Fusion Prime uses Cloud Build for automated container building with these benefits:

- ✅ **Declarative Configuration** - Version-controlled build definitions
- ✅ **Docker Layer Caching** - Faster builds (up to 5x)
- ✅ **Parallel Builds** - Multiple services build simultaneously
- ✅ **Automated Triggers** - CI/CD integration with Git
- ✅ **Build History** - Audit trail and rollback capability
- ✅ **Cost Efficient** - Only pay for build time

## Quick Start

### Build Individual Services

```bash
# Settlement service
./scripts/build.sh settlement

# Escrow relayer
./scripts/build.sh relayer

# All services (parallel)
./scripts/build.sh all
```

### Build with Custom Tags

```bash
# Production release
./scripts/build.sh --tag v1.0.0 all

# Development build
./scripts/build.sh --tag dev-$(git rev-parse --short HEAD) settlement

# Pull request build
./scripts/build.sh --tag pr-123 settlement
```

## Cloud Build Configurations

### Root Configuration (`/cloudbuild.yaml`)

Builds all services in parallel:
- Settlement service
- Escrow event relayer

**Usage:**
```bash
gcloud builds submit --config cloudbuild.yaml
```

**Features:**
- Parallel builds for faster completion
- Multi-stage tagging (latest, SHORT_SHA, custom tag)
- Docker layer caching
- Build summary output

### Service-Specific Configurations

#### Settlement Service (`services/settlement/cloudbuild.yaml`)

**Usage:**
```bash
cd services/settlement
gcloud builds submit --config cloudbuild.yaml
```

**Features:**
- Multi-stage Docker build optimization
- Poetry dependency caching
- Optional test execution (commented out)
- Optional Cloud Run deployment (commented out)

#### Escrow Relayer (`integrations/relayers/escrow/cloudbuild.yaml`)

**Usage:**
```bash
cd integrations/relayers/escrow
gcloud builds submit --config cloudbuild.yaml
```

**Features:**
- Auto-generates Dockerfile if missing
- Auto-generates requirements.txt if missing
- Lightweight Python base image
- Fast builds (<5 minutes)

## Build Triggers

Automated builds can be triggered by Git events. See `triggers.yaml` for configuration.

### Available Triggers

1. **Main Branch Push** - Build all services on merge to main
2. **Pull Request** - Build affected services on PR
3. **Tagged Release** - Build with version tag (e.g., v1.0.0)
4. **Manual Dev** - Build development versions

### Setup Triggers

#### Option 1: Import from File

```bash
# Edit triggers.yaml with your GitHub org/repo
cd infra/cloudbuild

# Import triggers
gcloud builds triggers import --source=triggers.yaml
```

#### Option 2: Create in Console

1. Go to [Cloud Build Triggers](https://console.cloud.google.com/cloud-build/triggers)
2. Click **Create Trigger**
3. Configure:
   - **Name**: `fusion-prime-main-build`
   - **Event**: Push to branch
   - **Branch**: `^main$`
   - **Build Configuration**: Cloud Build configuration file
   - **File location**: `cloudbuild.yaml`
4. Add substitution variables:
   - `_TAG`: `latest`
   - `_REGION`: `us-central1`
   - `_REPOSITORY`: `services`

## Substitution Variables

All configurations support these substitution variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `_TAG` | Image tag | `latest` |
| `_REGION` | Artifact Registry region | `us-central1` |
| `_REPOSITORY` | Artifact Registry repository | `services` |
| `_SERVICES` | Services to build (root config only) | `all` |

### Usage Examples

```bash
# Custom tag
gcloud builds submit --substitutions _TAG=v1.0.0

# Different region
gcloud builds submit --substitutions _REGION=us-east1

# Multiple substitutions
gcloud builds submit \
  --substitutions _TAG=prod,_REGION=us-central1,_REPOSITORY=production
```

## Build Options

### Machine Types

Configurations use these machine types:
- **Single service**: `N1_HIGHCPU_8` (8 vCPU, 7.2 GB)
- **All services**: `N1_HIGHCPU_32` (32 vCPU, 28.8 GB)

Change in `options.machineType` to:
- `E2_HIGHCPU_8` - Budget option
- `N1_HIGHCPU_32` - Faster parallel builds
- `E2_HIGHCPU_32` - Budget parallel builds

### Timeouts

- Single service: 20 minutes
- All services: 30 minutes

### Disk Size

- Single service: 100 GB
- All services: 200 GB

## Docker Layer Caching

All configurations use Docker layer caching for faster builds:

```yaml
args:
  - '--cache-from'
  - '${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/settlement-service:latest'
```

**First build**: ~15 minutes
**Cached build**: ~3-5 minutes (70% faster!)

## Build Script (`scripts/build.sh`)

Simplified wrapper around Cloud Build:

```bash
# Show help
./scripts/build.sh --help

# Build with defaults
./scripts/build.sh settlement

# Custom tag and project
./scripts/build.sh \
  --project my-project \
  --tag v2.0.0 \
  --region us-east1 \
  settlement

# Dry run (show commands without executing)
./scripts/build.sh --dry-run all
```

## Cost Optimization

### Build Minutes Included

Cloud Build includes:
- **120 build-minutes/day** free tier
- After free tier: $0.003/build-minute

### Cost Estimates

| Build Type | Machine | Time | Cost |
|------------|---------|------|------|
| Settlement (first) | 8 vCPU | 15 min | $0.045 |
| Settlement (cached) | 8 vCPU | 3 min | $0.009 |
| Relayer (first) | 8 vCPU | 8 min | $0.024 |
| Relayer (cached) | 8 vCPU | 2 min | $0.006 |
| All services | 32 vCPU | 10 min | $0.120 |

**Monthly costs** (assuming 20 builds/month):
- Settlement only: ~$1.80
- Both services (parallel): ~$2.40

### Tips to Reduce Costs

1. **Use Docker layer caching** ✅ Already configured
2. **Build only changed services** - Use service-specific configs
3. **Use smaller machine types** - E2_HIGHCPU_8 for development
4. **Limit builds** - Only trigger on main branch and releases
5. **Use local builds** - For rapid iteration

## Monitoring & Debugging

### View Build History

```bash
# List recent builds
gcloud builds list --limit=10

# View specific build
gcloud builds describe BUILD_ID

# Stream build logs
gcloud builds log BUILD_ID --stream
```

### Console Access

- **Build History**: https://console.cloud.google.com/cloud-build/builds
- **Triggers**: https://console.cloud.google.com/cloud-build/triggers
- **Artifact Registry**: https://console.cloud.google.com/artifacts

### Common Issues

#### Build Timeout

**Solution**: Increase timeout in config:
```yaml
timeout: '2400s'  # 40 minutes
```

#### Out of Disk Space

**Solution**: Increase disk size:
```yaml
options:
  diskSizeGb: 200
```

#### Cache Miss

**Solution**: Ensure latest image is pulled:
```bash
docker pull us-central1-docker.pkg.dev/fusion-prime/services/settlement-service:latest
```

## Integration with Deployment

After building, deploy to Cloud Run:

```bash
# Build
./scripts/build.sh --tag v1.0.0 settlement

# Deploy
gcloud run deploy settlement-service \
  --image us-central1-docker.pkg.dev/fusion-prime/services/settlement-service:v1.0.0 \
  --region us-central1
```

Or enable automatic deployment in `cloudbuild.yaml` (uncomment the deploy step).

## Best Practices

1. **Tag releases** - Use semantic versioning (v1.0.0)
2. **Test before deploy** - Enable test step in config
3. **Use triggers** - Automate builds on Git events
4. **Monitor costs** - Set up budget alerts
5. **Review logs** - Check build logs for optimization opportunities
6. **Keep caches warm** - Build regularly to maintain cache

## See Also

- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Artifact Registry Documentation](https://cloud.google.com/artifact-registry/docs)
- [Cloud Run Deployment](../../docs/PHASE2_DEPLOYMENT.md)

