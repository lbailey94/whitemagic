//! Sangha Webhook Dispatcher
//!
//! Handles high-speed notification of agents based on spatial triggers
//! in the 5D Sangha Galaxy.

use crate::conductor::spatial_index::Point5D;
use reqwest::Client;
use serde_json::json;

pub struct WebhookSubscription {
    pub agent_id: String,
    pub url: String,
    pub center: Point5D,
    pub radius: f32,
}

pub struct WebhookDispatcher {
    client: Client,
    subscriptions: Vec<WebhookSubscription>,
}

impl WebhookDispatcher {
    pub fn new() -> Self {
        Self {
            client: Client::new(),
            subscriptions: Vec::new(),
        }
    }

    pub fn subscribe(&mut self, sub: WebhookSubscription) {
        self.subscriptions.push(sub);
    }

    pub async fn dispatch_signal(&self, signal_id: &str, origin: Point5D, content: &str) {
        for sub in &self.subscriptions {
            if origin.distance_to(&sub.center) <= sub.radius {
                let payload = json!({
                    "id": signal_id,
                    "origin": origin,
                    "content": content,
                    "event": "sangha_galaxy_signal"
                });
                
                let _ = self.client.post(&sub.url)
                    .json(&payload)
                    .send()
                    .await;
            }
        }
    }
}
