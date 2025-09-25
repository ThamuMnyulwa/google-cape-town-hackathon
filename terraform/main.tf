# Terraform configuration for MedAssist AI Pro deployment on GCP
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  
  backend "gcs" {
    # Backend configuration will be provided via backend config file
    # bucket = "your-terraform-state-bucket"
    # prefix = "medassist-ai-pro"
  }
}

# Configure the Google Cloud Provider
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "cloudbuild.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "bigquery.googleapis.com",
    "storage.googleapis.com"
  ])
  
  service = each.value
  project = var.project_id
  
  disable_on_destroy = false
}

# Create Artifact Registry repository for Docker images
resource "google_artifact_registry_repository" "medassist_repo" {
  location      = var.region
  repository_id = "medassist-ai-pro"
  description   = "Docker repository for MedAssist AI Pro application"
  format        = "DOCKER"
  
  depends_on = [google_project_service.required_apis]
}

# Create BigQuery dataset for storing patient data
resource "google_bigquery_dataset" "medassist_dataset" {
  dataset_id    = "medassist_data"
  friendly_name = "MedAssist AI Pro Dataset"
  description   = "Dataset for storing MedAssist AI Pro patient and clinical data"
  location      = var.region
  
  # Set default table expiration (optional)
  default_table_expiration_ms = 365 * 24 * 60 * 60 * 1000  # 1 year
  
  # Access controls
  access {
    role   = "OWNER"
    user_by_email = "${var.project_id}@appspot.gserviceaccount.com"
  }
  
  depends_on = [google_project_service.required_apis]
}

# Create BigQuery tables for different data types
resource "google_bigquery_table" "patient_data" {
  dataset_id = google_bigquery_dataset.medassist_dataset.dataset_id
  table_id   = "patient_data"
  
  schema = jsonencode([
    {
      name = "patient_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "timestamp"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    },
    {
      name = "patient_name"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "patient_age"
      type = "INTEGER"
      mode = "NULLABLE"
    },
    {
      name = "patient_gender"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "chief_complaint"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "symptoms"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "diagnosis"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "treatment_plan"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "clinical_notes"
      type = "TEXT"
      mode = "NULLABLE"
    },
    {
      name = "user_role"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "session_data"
      type = "JSON"
      mode = "NULLABLE"
    }
  ])
  
  time_partitioning {
    type = "DAY"
    field = "timestamp"
  }
  
  depends_on = [google_bigquery_dataset.medassist_dataset]
}

resource "google_bigquery_table" "clinical_reports" {
  dataset_id = google_bigquery_dataset.medassist_dataset.dataset_id
  table_id   = "clinical_reports"
  
  schema = jsonencode([
    {
      name = "report_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "patient_id"
      type = "STRING"
      mode = "REQUIRED"
    },
    {
      name = "timestamp"
      type = "TIMESTAMP"
      mode = "REQUIRED"
    },
    {
      name = "report_type"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "report_content"
      type = "TEXT"
      mode = "NULLABLE"
    },
    {
      name = "ai_generated"
      type = "BOOLEAN"
      mode = "NULLABLE"
    },
    {
      name = "doctor_id"
      type = "STRING"
      mode = "NULLABLE"
    },
    {
      name = "status"
      type = "STRING"
      mode = "NULLABLE"
    }
  ])
  
  time_partitioning {
    type = "DAY"
    field = "timestamp"
  }
  
  depends_on = [google_bigquery_dataset.medassist_dataset]
}

# Create secrets for sensitive data
resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "gemini-api-key"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.required_apis]
}

resource "google_secret_manager_secret_version" "gemini_api_key" {
  secret      = google_secret_manager_secret.gemini_api_key.id
  secret_data = var.gemini_api_key
}

# Create Cloud Run service
resource "google_cloud_run_v2_service" "medassist_app" {
  name     = "medassist-ai-pro"
  location = var.region
  
  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.medassist_repo.repository_id}/medassist-ai-pro:latest"
      
      ports {
        container_port = 8502
      }
      
      env {
        name  = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }
      
      env {
        name  = "BIGQUERY_PROJECT_ID"
        value = var.project_id
      }
      
      env {
        name  = "BIGQUERY_DATASET_ID"
        value = google_bigquery_dataset.medassist_dataset.dataset_id
      }
      
      env {
        name  = "BIGQUERY_PATIENT_TABLE"
        value = google_bigquery_table.patient_data.table_id
      }
      
      env {
        name  = "BIGQUERY_REPORTS_TABLE"
        value = google_bigquery_table.clinical_reports.table_id
      }
      
      env {
        name  = "STORAGE_BUCKET"
        value = google_storage_bucket.medassist_uploads.name
      }
      
      env {
        name  = "STREAMLIT_SERVER_PORT"
        value = "8502"
      }
      
      env {
        name  = "STREAMLIT_SERVER_ADDRESS"
        value = "0.0.0.0"
      }
      
      env {
        name  = "STREAMLIT_SERVER_HEADLESS"
        value = "true"
      }
      
      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
      }
    }
    
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }
    
    timeout = "300s"
  }
  
  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }
  
  depends_on = [
    google_project_service.required_apis,
    google_artifact_registry_repository.medassist_repo
  ]
}

# Allow unauthenticated access to Cloud Run service
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.medassist_app.location
  name     = google_cloud_run_v2_service.medassist_app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Create Cloud Build trigger for CI/CD
resource "google_cloudbuild_trigger" "medassist_trigger" {
  name        = "medassist-build-trigger"
  description = "Build and deploy MedAssist AI Pro application"
  
  github {
    owner = var.github_owner
    name  = var.github_repo
    push {
      branch = "^main$"
    }
  }
  
  filename = "cloudbuild.yaml"
  
  depends_on = [google_project_service.required_apis]
}

# Create Cloud Storage bucket for file uploads
resource "google_storage_bucket" "medassist_uploads" {
  name          = "${var.project_id}-medassist-uploads"
  location      = var.region
  force_destroy = true
  
  uniform_bucket_level_access = true
  
  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
  
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

# Create IAM binding for Cloud Run to access secrets
resource "google_secret_manager_secret_iam_member" "gemini_api_key_access" {
  secret_id = google_secret_manager_secret.gemini_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_cloud_run_v2_service.medassist_app.template[0].service_account}"
}

# Create IAM binding for Cloud Run to access BigQuery
resource "google_project_iam_member" "bigquery_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_cloud_run_v2_service.medassist_app.template[0].service_account}"
}

resource "google_project_iam_member" "bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_cloud_run_v2_service.medassist_app.template[0].service_account}"
}

# Create IAM binding for Cloud Run to access Cloud Storage
resource "google_project_iam_member" "storage_object_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_cloud_run_v2_service.medassist_app.template[0].service_account}"
}
