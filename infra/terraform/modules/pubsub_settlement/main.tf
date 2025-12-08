resource "google_pubsub_topic" "settlement_events" {
  name = var.topic_name
}

resource "google_pubsub_subscription" "settlement_consumer" {
  name  = var.subscription_name
  topic = google_pubsub_topic.settlement_events.name

  ack_deadline_seconds = 60
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }
}

resource "google_pubsub_subscription_iam_member" "consumer_role" {
  subscription = google_pubsub_subscription.settlement_consumer.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${var.service_account_email}"
}

resource "google_pubsub_topic_iam_member" "publisher_role" {
  topic  = google_pubsub_topic.settlement_events.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${var.service_account_email}"
}
