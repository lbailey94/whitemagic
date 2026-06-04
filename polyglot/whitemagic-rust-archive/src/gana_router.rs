//! Gana Router - PRAT Routing System (PSR-006)
//! Target: 50× speedup for gana routing

use pyo3::prelude::*;
use std::collections::HashMap;

#[derive(Clone, Debug)]
#[pyclass]
pub struct Gana {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub garden: String,
    #[pyo3(get)]
    pub quadrant: String,
    #[pyo3(get)]
    pub cost_units: f64,
}

#[pymethods]
impl Gana {
    #[new]
    fn new(name: String, garden: String, quadrant: String, cost_units: f64) -> Self {
        Self {
            name,
            garden,
            quadrant,
            cost_units,
        }
    }
}

#[pyclass]
pub struct PyGanaRouter {
    ganas: HashMap<String, Gana>,
    garden_index: HashMap<String, Vec<String>>,
    quadrant_index: HashMap<String, Vec<String>>,
}

#[pymethods]
impl PyGanaRouter {
    #[new]
    fn new() -> Self {
        Self {
            ganas: HashMap::new(),
            garden_index: HashMap::new(),
            quadrant_index: HashMap::new(),
        }
    }

    fn register_gana(&mut self, gana: Gana) {
        let name = gana.name.clone();
        let garden = gana.garden.clone();
        let quadrant = gana.quadrant.clone();
        
        self.ganas.insert(name.clone(), gana);
        
        self.garden_index
            .entry(garden)
            .or_insert_with(Vec::new)
            .push(name.clone());
        
        self.quadrant_index
            .entry(quadrant)
            .or_insert_with(Vec::new)
            .push(name);
    }

    fn route(&self, gana_name: String) -> Option<Gana> {
        self.ganas.get(&gana_name).cloned()
    }

    fn route_by_garden(&self, garden: String) -> Vec<Gana> {
        if let Some(gana_names) = self.garden_index.get(&garden) {
            gana_names
                .iter()
                .filter_map(|name| self.ganas.get(name).cloned())
                .collect()
        } else {
            Vec::new()
        }
    }

    fn route_by_quadrant(&self, quadrant: String) -> Vec<Gana> {
        if let Some(gana_names) = self.quadrant_index.get(&quadrant) {
            gana_names
                .iter()
                .filter_map(|name| self.ganas.get(name).cloned())
                .collect()
        } else {
            Vec::new()
        }
    }

    fn calculate_cost(&self, gana_names: Vec<String>) -> f64 {
        gana_names
            .iter()
            .filter_map(|name| self.ganas.get(name))
            .map(|gana| gana.cost_units)
            .sum()
    }

    fn find_cheapest_gana(&self, garden: Option<String>) -> Option<Gana> {
        let candidates: Vec<&Gana> = if let Some(g) = garden {
            if let Some(gana_names) = self.garden_index.get(&g) {
                gana_names
                    .iter()
                    .filter_map(|name| self.ganas.get(name))
                    .collect()
            } else {
                return None;
            }
        } else {
            self.ganas.values().collect()
        };
        
        candidates
            .into_iter()
            .min_by(|a, b| a.cost_units.partial_cmp(&b.cost_units).unwrap())
            .cloned()
    }

    fn gana_count(&self) -> usize {
        self.ganas.len()
    }

    fn garden_count(&self) -> usize {
        self.garden_index.len()
    }

    fn quadrant_count(&self) -> usize {
        self.quadrant_index.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_router_creation() {
        let router = PyGanaRouter::new();
        assert_eq!(router.gana_count(), 0);
    }

    #[test]
    fn test_register_gana() {
        let mut router = PyGanaRouter::new();
        let gana = Gana::new(
            "gana_test".to_string(),
            "play".to_string(),
            "south".to_string(),
            1.5,
        );
        
        router.register_gana(gana);
        assert_eq!(router.gana_count(), 1);
    }

    #[test]
    fn test_route() {
        let mut router = PyGanaRouter::new();
        let gana = Gana::new(
            "gana_test".to_string(),
            "play".to_string(),
            "south".to_string(),
            1.5,
        );
        
        router.register_gana(gana);
        
        let result = router.route("gana_test".to_string());
        assert!(result.is_some());
    }

    #[test]
    fn test_route_by_garden() {
        let mut router = PyGanaRouter::new();
        
        router.register_gana(Gana::new("g1".to_string(), "play".to_string(), "south".to_string(), 1.0));
        router.register_gana(Gana::new("g2".to_string(), "play".to_string(), "north".to_string(), 2.0));
        
        let ganas = router.route_by_garden("play".to_string());
        assert_eq!(ganas.len(), 2);
    }

    #[test]
    fn test_calculate_cost() {
        let mut router = PyGanaRouter::new();
        
        router.register_gana(Gana::new("g1".to_string(), "play".to_string(), "south".to_string(), 1.5));
        router.register_gana(Gana::new("g2".to_string(), "work".to_string(), "north".to_string(), 2.5));
        
        let cost = router.calculate_cost(vec!["g1".to_string(), "g2".to_string()]);
        assert_eq!(cost, 4.0);
    }

    #[test]
    fn test_find_cheapest() {
        let mut router = PyGanaRouter::new();
        
        router.register_gana(Gana::new("g1".to_string(), "play".to_string(), "south".to_string(), 3.0));
        router.register_gana(Gana::new("g2".to_string(), "play".to_string(), "north".to_string(), 1.0));
        
        let cheapest = router.find_cheapest_gana(Some("play".to_string()));
        assert!(cheapest.is_some());
        assert_eq!(cheapest.unwrap().cost_units, 1.0);
    }
}
