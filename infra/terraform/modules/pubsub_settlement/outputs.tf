output "topic_name" {
  description = "The name of the Pub/Sub topic"
  value       = google_pubsub_topic.settlement_events.name
}

output "topic_id" {
  description = "The ID of the Pub/Sub topic"
  value       = google_pubsub_topic.settlement_events.id
}

output "subscription_name" {
  description = "The name of the Pub/Sub subscription"
  value       = google_pubsub_subscription.settlement_consumer.name
}

output "subscription_id" {
  description = "The ID of the Pub/Sub subscription"
  value       = google_pubsub_subscription.settlement_consumer.id
}
