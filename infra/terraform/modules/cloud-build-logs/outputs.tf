output "bucket_name" {
  description = "Name of the created Cloud Build logs bucket"
  value       = google_storage_bucket.cloud_build_logs.name
}

output "bucket_url" {
  description = "URL of the created Cloud Build logs bucket"
  value       = google_storage_bucket.cloud_build_logs.url
}

output "bucket_self_link" {
  description = "Self-link of the created Cloud Build logs bucket"
  value       = google_storage_bucket.cloud_build_logs.self_link
}
