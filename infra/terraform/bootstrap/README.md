# Terraform Bootstrap

This directory contains the bootstrap configuration to create the GCS bucket needed for Terraform remote state storage.

## Why Bootstrap?

Terraform needs a GCS bucket to store its state remotely, but we need Terraform to create that bucket. This is a chicken-and-egg problem. The bootstrap configuration solves this by:

1. Using **local state** (no remote backend)
2. Creating the GCS bucket
3. After the bucket exists, the main Terraform configurations can use it as a remote backend

## Usage

### Step 1: Create terraform.tfvars

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project details
```

### Step 2: Initialize and apply

```bash
terraform init
terraform plan
terraform apply
```

### Step 3: Proceed with main configuration

Once the bucket is created, you can initialize the main Terraform configuration in `../project/`:

```bash
cd ../project
terraform init -backend-config="bucket=fusion-prime-bucket-1"
```

## Cleanup

If you ever need to destroy the bootstrap resources:

```bash
# First, destroy all resources that use the remote state
cd ../project
terraform destroy

# Then destroy the bootstrap bucket
cd ../bootstrap
terraform destroy
```

## Important Notes

- The bootstrap state is stored **locally** in this directory as `terraform.tfstate`
- Keep this local state file safe - you'll need it if you ever need to modify or destroy the bucket
- The bucket has `force_destroy = false` to prevent accidental deletion
- Versioning is enabled to protect against state file corruption

