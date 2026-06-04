//! Campaign Executor - Campaign Execution Engine (PSR-005)
//! Target: 100× throughput for campaign execution

use pyo3::prelude::*;
use std::collections::HashMap;
use std::sync::Arc;
use parking_lot::RwLock;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Clone, Debug, PartialEq)]
pub enum CampaignStatus {
    Pending,
    Running,
    Completed,
    Failed,
}

#[derive(Clone, Debug)]
#[pyclass]
pub struct Campaign {
    #[pyo3(get)]
    pub id: String,
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub objectives: Vec<String>,
    #[pyo3(get)]
    pub clone_count: usize,
    #[pyo3(get)]
    pub started_at: Option<u64>,
    #[pyo3(get)]
    pub completed_at: Option<u64>,
    status: CampaignStatus,
}

#[pymethods]
impl Campaign {
    #[new]
    fn new(id: String, name: String, objectives: Vec<String>, clone_count: usize) -> Self {
        Self {
            id,
            name,
            objectives,
            clone_count,
            started_at: None,
            completed_at: None,
            status: CampaignStatus::Pending,
        }
    }

    fn get_status(&self) -> String {
        match self.status {
            CampaignStatus::Pending => "pending".to_string(),
            CampaignStatus::Running => "running".to_string(),
            CampaignStatus::Completed => "completed".to_string(),
            CampaignStatus::Failed => "failed".to_string(),
        }
    }
}

#[pyclass]
pub struct PyCampaignExecutor {
    campaigns: Arc<RwLock<HashMap<String, Campaign>>>,
    results: Arc<RwLock<HashMap<String, Vec<String>>>>,
}

#[pymethods]
impl PyCampaignExecutor {
    #[new]
    fn new() -> Self {
        Self {
            campaigns: Arc::new(RwLock::new(HashMap::new())),
            results: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    fn register_campaign(&self, campaign: Campaign) {
        self.campaigns.write().insert(campaign.id.clone(), campaign);
        self.results.write().insert(campaign.id.clone(), Vec::new());
    }

    fn start_campaign(&self, campaign_id: String) -> bool {
        if let Some(campaign) = self.campaigns.write().get_mut(&campaign_id) {
            if campaign.status == CampaignStatus::Pending {
                campaign.status = CampaignStatus::Running;
                campaign.started_at = Some(current_timestamp());
                return true;
            }
        }
        false
    }

    fn complete_campaign(&self, campaign_id: String) -> bool {
        if let Some(campaign) = self.campaigns.write().get_mut(&campaign_id) {
            if campaign.status == CampaignStatus::Running {
                campaign.status = CampaignStatus::Completed;
                campaign.completed_at = Some(current_timestamp());
                return true;
            }
        }
        false
    }

    fn fail_campaign(&self, campaign_id: String) -> bool {
        if let Some(campaign) = self.campaigns.write().get_mut(&campaign_id) {
            campaign.status = CampaignStatus::Failed;
            campaign.completed_at = Some(current_timestamp());
            return true;
        }
        false
    }

    fn add_result(&self, campaign_id: String, result: String) -> bool {
        if let Some(results) = self.results.write().get_mut(&campaign_id) {
            results.push(result);
            return true;
        }
        false
    }

    fn get_campaign(&self, campaign_id: String) -> Option<Campaign> {
        self.campaigns.read().get(&campaign_id).cloned()
    }

    fn get_results(&self, campaign_id: String) -> Vec<String> {
        self.results.read().get(&campaign_id).cloned().unwrap_or_default()
    }

    fn get_running_campaigns(&self) -> Vec<Campaign> {
        self.campaigns
            .read()
            .values()
            .filter(|c| c.status == CampaignStatus::Running)
            .cloned()
            .collect()
    }

    fn get_completed_campaigns(&self) -> Vec<Campaign> {
        self.campaigns
            .read()
            .values()
            .filter(|c| c.status == CampaignStatus::Completed)
            .cloned()
            .collect()
    }

    fn campaign_count(&self) -> usize {
        self.campaigns.read().len()
    }

    fn total_clone_count(&self) -> usize {
        self.campaigns.read().values().map(|c| c.clone_count).sum()
    }
}

fn current_timestamp() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_executor_creation() {
        let executor = PyCampaignExecutor::new();
        assert_eq!(executor.campaign_count(), 0);
    }

    #[test]
    fn test_register_campaign() {
        let executor = PyCampaignExecutor::new();
        let campaign = Campaign::new(
            "c1".to_string(),
            "Test Campaign".to_string(),
            vec!["obj1".to_string()],
            1000,
        );
        
        executor.register_campaign(campaign);
        assert_eq!(executor.campaign_count(), 1);
    }

    #[test]
    fn test_campaign_lifecycle() {
        let executor = PyCampaignExecutor::new();
        let campaign = Campaign::new(
            "c1".to_string(),
            "Test".to_string(),
            vec![],
            100,
        );
        
        executor.register_campaign(campaign);
        
        assert!(executor.start_campaign("c1".to_string()));
        assert_eq!(executor.get_running_campaigns().len(), 1);
        
        assert!(executor.complete_campaign("c1".to_string()));
        assert_eq!(executor.get_completed_campaigns().len(), 1);
    }

    #[test]
    fn test_add_result() {
        let executor = PyCampaignExecutor::new();
        let campaign = Campaign::new("c1".to_string(), "Test".to_string(), vec![], 100);
        
        executor.register_campaign(campaign);
        executor.add_result("c1".to_string(), "finding1".to_string());
        
        let results = executor.get_results("c1".to_string());
        assert_eq!(results.len(), 1);
    }
}
