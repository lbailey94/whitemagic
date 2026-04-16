//! Performance Monitor - Performance Monitoring (PSR-005)
//! Target: Real-time performance tracking

use pyo3::prelude::*;
use std::time::{SystemTime, UNIX_EPOCH};
use std::collections::VecDeque;

#[derive(Clone, Debug)]
#[pyclass]
pub struct PerformanceMetric {
    #[pyo3(get)]
    pub timestamp: u64,
    #[pyo3(get)]
    pub throughput: f64,
    #[pyo3(get)]
    pub latency_ms: f64,
    #[pyo3(get)]
    pub success_rate: f64,
}

#[pymethods]
impl PerformanceMetric {
    #[new]
    fn new(timestamp: u64, throughput: f64, latency_ms: f64, success_rate: f64) -> Self {
        Self {
            timestamp,
            throughput,
            latency_ms,
            success_rate,
        }
    }
}

#[pyclass]
pub struct PyPerformanceMonitor {
    metrics: VecDeque<PerformanceMetric>,
    max_history: usize,
    window_size: usize,
}

#[pymethods]
impl PyPerformanceMonitor {
    #[new]
    fn new(max_history: Option<usize>, window_size: Option<usize>) -> Self {
        Self {
            metrics: VecDeque::new(),
            max_history: max_history.unwrap_or(1000),
            window_size: window_size.unwrap_or(10),
        }
    }

    fn record(&mut self, throughput: f64, latency_ms: f64, success_rate: f64) {
        let timestamp = current_timestamp();
        
        let metric = PerformanceMetric {
            timestamp,
            throughput,
            latency_ms,
            success_rate,
        };
        
        self.metrics.push_back(metric);
        
        if self.metrics.len() > self.max_history {
            self.metrics.pop_front();
        }
    }

    fn get_average_throughput(&self) -> f64 {
        if self.metrics.is_empty() {
            return 0.0;
        }
        
        let sum: f64 = self.metrics.iter().map(|m| m.throughput).sum();
        sum / self.metrics.len() as f64
    }

    fn get_average_latency(&self) -> f64 {
        if self.metrics.is_empty() {
            return 0.0;
        }
        
        let sum: f64 = self.metrics.iter().map(|m| m.latency_ms).sum();
        sum / self.metrics.len() as f64
    }

    fn get_average_success_rate(&self) -> f64 {
        if self.metrics.is_empty() {
            return 0.0;
        }
        
        let sum: f64 = self.metrics.iter().map(|m| m.success_rate).sum();
        sum / self.metrics.len() as f64
    }

    fn get_windowed_average_throughput(&self) -> f64 {
        if self.metrics.is_empty() {
            return 0.0;
        }
        
        let window = self.metrics.iter().rev().take(self.window_size);
        let sum: f64 = window.map(|m| m.throughput).sum();
        let count = self.metrics.len().min(self.window_size);
        
        sum / count as f64
    }

    fn get_peak_throughput(&self) -> f64 {
        self.metrics
            .iter()
            .map(|m| m.throughput)
            .fold(0.0f64, |a, b| a.max(b))
    }

    fn get_min_latency(&self) -> f64 {
        self.metrics
            .iter()
            .map(|m| m.latency_ms)
            .fold(f64::INFINITY, |a, b| a.min(b))
    }

    fn get_recent_metrics(&self, count: usize) -> Vec<PerformanceMetric> {
        self.metrics
            .iter()
            .rev()
            .take(count)
            .cloned()
            .collect()
    }

    fn clear(&mut self) {
        self.metrics.clear();
    }

    fn metric_count(&self) -> usize {
        self.metrics.len()
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
    fn test_monitor_creation() {
        let monitor = PyPerformanceMonitor::new(Some(100), Some(10));
        assert_eq!(monitor.metric_count(), 0);
    }

    #[test]
    fn test_record_metric() {
        let mut monitor = PyPerformanceMonitor::new(None, None);
        
        monitor.record(1000.0, 10.0, 0.95);
        
        assert_eq!(monitor.metric_count(), 1);
    }

    #[test]
    fn test_average_throughput() {
        let mut monitor = PyPerformanceMonitor::new(None, None);
        
        monitor.record(1000.0, 10.0, 0.95);
        monitor.record(2000.0, 15.0, 0.90);
        
        let avg = monitor.get_average_throughput();
        assert!((avg - 1500.0).abs() < 0.1);
    }

    #[test]
    fn test_max_history() {
        let mut monitor = PyPerformanceMonitor::new(Some(5), None);
        
        for i in 0..10 {
            monitor.record(i as f64, 10.0, 0.95);
        }
        
        assert_eq!(monitor.metric_count(), 5);
    }

    #[test]
    fn test_peak_throughput() {
        let mut monitor = PyPerformanceMonitor::new(None, None);
        
        monitor.record(1000.0, 10.0, 0.95);
        monitor.record(5000.0, 15.0, 0.90);
        monitor.record(2000.0, 12.0, 0.92);
        
        assert_eq!(monitor.get_peak_throughput(), 5000.0);
    }
}
