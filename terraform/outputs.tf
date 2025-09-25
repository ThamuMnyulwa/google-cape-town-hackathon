# Outputs for MedAssist AI Pro Terraform deployment

output "cloud_run_service_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.medassist_app.uri
}

output "cloud_run_service_name" {
  description = "Name of the Cloud Run service"
  value       = google_cloud_run_v2_service.medassist_app.name
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository for Docker images"
  value       = google_artifact_registry_repository.medassist_repo.name
}

output "artifact_registry_location" {
  description = "Location of the Artifact Registry repository"
  value       = google_artifact_registry_repository.medassist_repo.location
}

output "bigquery_dataset_id" {
  description = "ID of the BigQuery dataset"
  value       = google_bigquery_dataset.medassist_dataset.dataset_id
}

output "bigquery_dataset_location" {
  description = "Location of the BigQuery dataset"
  value       = google_bigquery_dataset.medassist_dataset.location
}

output "bigquery_patient_table_id" {
  description = "ID of the patient data table"
  value       = google_bigquery_table.patient_data.table_id
}

output "bigquery_reports_table_id" {
  description = "ID of the clinical reports table"
  value       = google_bigquery_table.clinical_reports.table_id
}

output "storage_bucket_name" {
  description = "Name of the Cloud Storage bucket for uploads"
  value       = google_storage_bucket.medassist_uploads.name
}

output "storage_bucket_url" {
  description = "URL of the Cloud Storage bucket"
  value       = google_storage_bucket.medassist_uploads.url
}

output "cloud_build_trigger_name" {
  description = "Name of the Cloud Build trigger"
  value       = google_cloudbuild_trigger.medassist_trigger.name
}

output "secret_manager_secrets" {
  description = "Names of created Secret Manager secrets"
  value = {
    gemini_api_key = google_secret_manager_secret.gemini_api_key.secret_id
  }
}

output "deployment_instructions" {
  description = "Instructions for deploying the application"
  value = <<-EOT
    To deploy your MedAssist AI Pro application:
    
    1. Build and push your Docker image:
       gcloud builds submit --tag ${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.medassist_repo.repository_id}/medassist-ai-pro:latest
    
    2. Your application will be available at:
       ${google_cloud_run_v2_service.medassist_app.uri}
    
    3. BigQuery dataset details:
       Dataset: ${google_bigquery_dataset.medassist_dataset.dataset_id}
       Patient Table: ${google_bigquery_table.patient_data.table_id}
       Reports Table: ${google_bigquery_table.clinical_reports.table_id}
    
    4. File uploads will be stored in:
       ${google_storage_bucket.medassist_uploads.url}
    
    5. Monitor your application in the Cloud Console:
       https://console.cloud.google.com/run/detail/${var.region}/${google_cloud_run_v2_service.medassist_app.name}
    
    6. View BigQuery data:
       https://console.cloud.google.com/bigquery?project=${var.project_id}
  EOT
}

output "environment_variables" {
  description = "Environment variables needed for the application"
  value = {
    GEMINI_API_KEY         = "Set via Secret Manager"
    BIGQUERY_PROJECT_ID    = var.project_id
    BIGQUERY_DATASET_ID    = google_bigquery_dataset.medassist_dataset.dataset_id
    BIGQUERY_PATIENT_TABLE = google_bigquery_table.patient_data.table_id
    BIGQUERY_REPORTS_TABLE = google_bigquery_table.clinical_reports.table_id
    STORAGE_BUCKET         = google_storage_bucket.medassist_uploads.name
  }
  sensitive = true
}
