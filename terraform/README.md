# MedAssist AI Pro - GCP Terraform Deployment

This directory contains Terraform configuration files to deploy the MedAssist AI Pro Streamlit application on Google Cloud Platform.

## Architecture Overview

The deployment creates the following GCP resources:

- **Cloud Run**: Serverless container platform for the Streamlit application
- **BigQuery**: Data warehouse for storing patient data and clinical reports
- **Artifact Registry**: Docker image repository
- **Secret Manager**: Secure storage for API keys
- **Cloud Storage**: Bucket for file uploads
- **Cloud Build**: CI/CD pipeline for automated deployments

## Prerequisites

1. **GCP Project**: You need a GCP project with billing enabled
2. **Service Account**: A service account with appropriate permissions
3. **Terraform State Bucket**: A Cloud Storage bucket for Terraform state
4. **Google Gemini API Key**: For AI functionality
5. **Terraform**: Version >= 1.0 installed locally
6. **gcloud CLI**: Authenticated with your GCP project

## Setup Instructions

### 1. Configure Backend State

Create a backend configuration file:

```bash
cp terraform/backend.tf.example terraform/backend.tf
```

Edit `terraform/backend.tf` and update the bucket name:

```hcl
terraform {
  backend "gcs" {
    bucket = "your-terraform-state-bucket"
    prefix = "medassist-ai-pro/terraform/state"
  }
}
```

### 2. Configure Variables

Copy the example variables file and update with your values:

```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
```

Edit `terraform/terraform.tfvars`:

```hcl
project_id     = "your-gcp-project-id"
region         = "us-central1"
zone           = "us-central1-a"
gemini_api_key = "your-gemini-api-key-here"
github_owner   = "your-github-username"
github_repo    = "google-cape-town-hackathon"
```

### 3. Initialize Terraform

```bash
cd terraform
terraform init
```

### 4. Plan the Deployment

```bash
terraform plan
```

### 5. Apply the Configuration

```bash
terraform apply
```

## Deployment Process

### Manual Deployment

1. **Build and Push Docker Image**:
   ```bash
   gcloud builds submit --tag us-central1-docker.pkg.dev/YOUR_PROJECT_ID/medassist-ai-pro/medassist-ai-pro:latest
   ```

2. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy medassist-ai-pro \
     --image us-central1-docker.pkg.dev/YOUR_PROJECT_ID/medassist-ai-pro/medassist-ai-pro:latest \
     --region us-central1 \
     --platform managed \
     --allow-unauthenticated \
     --port 8502 \
     --memory 4Gi \
     --cpu 2 \
     --min-instances 0 \
     --max-instances 10
   ```

### Automated CI/CD Deployment

The Cloud Build trigger will automatically:
1. Build the Docker image when code is pushed to the main branch
2. Push the image to Artifact Registry
3. Deploy the new version to Cloud Run

## Environment Variables

The application uses the following environment variables:

- `GEMINI_API_KEY`: Google Gemini API key (stored in Secret Manager)
- `BIGQUERY_PROJECT_ID`: GCP project ID
- `BIGQUERY_DATASET_ID`: BigQuery dataset ID
- `BIGQUERY_PATIENT_TABLE`: BigQuery patient data table name
- `BIGQUERY_REPORTS_TABLE`: BigQuery clinical reports table name
- `STORAGE_BUCKET`: Cloud Storage bucket name for uploads

## Security Features

- **Secret Manager**: Encrypted storage for sensitive data
- **IAM Roles**: Least privilege access control
- **SSL/TLS**: Encrypted communication
- **BigQuery Security**: Row-level security and data encryption
- **Cloud Run Security**: Automatic HTTPS and secure runtime

## Monitoring and Logging

- **Cloud Logging**: Application logs are automatically collected
- **Cloud Monitoring**: Performance metrics and health checks
- **Cloud Trace**: Distributed tracing for debugging

## Scaling Configuration

- **Min Instances**: 0 (cost-effective for low traffic)
- **Max Instances**: 10 (adjustable based on needs)
- **CPU**: 2 vCPU
- **Memory**: 4GB
- **Timeout**: 300 seconds

## Cost Optimization

- **Serverless**: Pay only for actual usage
- **Min Instances**: 0 to avoid idle costs
- **BigQuery**: Pay per query and storage used
- **Auto-scaling**: Scales down during low usage
- **No Infrastructure**: No VPC or database management costs

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure service account has required roles
2. **API Not Enabled**: Run `terraform apply` to enable required APIs
3. **Quota Exceeded**: Check GCP quotas for your project
4. **Build Failures**: Verify Dockerfile and dependencies

### Useful Commands

```bash
# Check Cloud Run service status
gcloud run services describe medassist-ai-pro --region us-central1

# View application logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=medassist-ai-pro" --limit 50

# Query BigQuery data
bq query --use_legacy_sql=false 'SELECT * FROM `your-project-id.medassist_data.patient_data` LIMIT 10'

# Check Secret Manager secrets
gcloud secrets list
```

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning**: This will permanently delete all resources including the database and stored data.

## Support

For issues and questions:
1. Check the application logs in Cloud Logging
2. Review Terraform state for resource status
3. Verify IAM permissions and API enablement
4. Check GCP quotas and billing

## Next Steps

After successful deployment:
1. Configure custom domain (optional)
2. Set up monitoring alerts
3. Configure backup schedules
4. Implement additional security measures
5. Set up staging environment
