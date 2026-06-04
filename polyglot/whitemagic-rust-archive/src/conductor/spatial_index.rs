//! Sangha Galaxy Spatial Indexing (5D)
//!
//! Implements a 5D spatial index (penta-tree) for efficient 
//! spherical subscription queries across the Sangha Galaxy.

use serde::{Deserialize, Serialize};

/// 5D Sangha coordinate:
/// x = logic/emotion, y = micro/macro, z = time/chronos,
/// w = importance/gravity, v = vitality/distance.
#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct Point5D {
    pub x: f32,
    pub y: f32,
    pub z: f32,
    pub w: f32,
    pub v: f32,
}

impl Point5D {
    pub fn distance_to(&self, other: &Point5D) -> f32 {
        ((self.x - other.x).powi(2) +
         (self.y - other.y).powi(2) +
         (self.z - other.z).powi(2) +
         (self.w - other.w).powi(2) +
         (self.v - other.v).powi(2)).sqrt()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpatialSignal {
    pub id: String,
    pub origin: Point5D,
    pub timestamp: u64,
}

pub struct PentaNode {
    pub bounds_min: Point5D,
    pub bounds_max: Point5D,
    pub signals: Vec<SpatialSignal>,
    pub children: Option<Box<[PentaNode; 32]>>, // 2^5 = 32 quadrants
}

impl PentaNode {
    pub fn new(min: Point5D, max: Point5D) -> Self {
        Self {
            bounds_min: min,
            bounds_max: max,
            signals: Vec::new(),
            children: None,
        }
    }

    fn bounds_intersects_sphere(&self, center: &Point5D, radius: f32) -> bool {
        let closest = Point5D {
            x: center.x.clamp(self.bounds_min.x, self.bounds_max.x),
            y: center.y.clamp(self.bounds_min.y, self.bounds_max.y),
            z: center.z.clamp(self.bounds_min.z, self.bounds_max.z),
            w: center.w.clamp(self.bounds_min.w, self.bounds_max.w),
            v: center.v.clamp(self.bounds_min.v, self.bounds_max.v),
        };

        center.distance_to(&closest) <= radius
    }

    pub fn insert(&mut self, signal: SpatialSignal) -> bool {
        // Check bounds
        if signal.origin.x < self.bounds_min.x || signal.origin.x > self.bounds_max.x ||
           signal.origin.y < self.bounds_min.y || signal.origin.y > self.bounds_max.y ||
           signal.origin.z < self.bounds_min.z || signal.origin.z > self.bounds_max.z ||
           signal.origin.w < self.bounds_min.w || signal.origin.w > self.bounds_max.w ||
           signal.origin.v < self.bounds_min.v || signal.origin.v > self.bounds_max.v {
            return false;
        }

        if self.children.is_none() && self.signals.len() < 16 {
            self.signals.push(signal);
            return true;
        }

        if self.children.is_none() {
            self.subdivide();
        }

        if let Some(ref mut children) = self.children {
            for child in children.iter_mut() {
                if child.insert(signal.clone()) {
                    return true;
                }
            }
        }

        false
    }

    fn subdivide(&mut self) {
        let mid_x = (self.bounds_min.x + self.bounds_max.x) / 2.0;
        let mid_y = (self.bounds_min.y + self.bounds_max.y) / 2.0;
        let mid_z = (self.bounds_min.z + self.bounds_max.z) / 2.0;
        let mid_w = (self.bounds_min.w + self.bounds_max.w) / 2.0;
        let mid_v = (self.bounds_min.v + self.bounds_max.v) / 2.0;

        let mut child_array: [PentaNode; 32] = std::array::from_fn(|i| {
            let mut min = self.bounds_min;
            let mut max = Point5D { x: mid_x, y: mid_y, z: mid_z, w: mid_w, v: mid_v };

            if (i & 1) != 0 { min.x = mid_x; max.x = self.bounds_max.x; }
            if (i & 2) != 0 { min.y = mid_y; max.y = self.bounds_max.y; }
            if (i & 4) != 0 { min.z = mid_z; max.z = self.bounds_max.z; }
            if (i & 8) != 0 { min.w = mid_w; max.w = self.bounds_max.w; }
            if (i & 16) != 0 { min.v = mid_v; max.v = self.bounds_max.v; }

            PentaNode::new(min, max)
        });

        // Re-insert existing signals into children
        let signals = std::mem::take(&mut self.signals);
        for signal in signals {
            for child in child_array.iter_mut() {
                if child.insert(signal.clone()) {
                    break;
                }
            }
        }

        self.children = Some(Box::new(child_array));
    }

    pub fn query_sphere(&self, center: Point5D, radius: f32, results: &mut Vec<String>) {
        if !self.bounds_intersects_sphere(&center, radius) {
            return;
        }

        for signal in &self.signals {
            if signal.origin.distance_to(&center) <= radius {
                results.push(signal.id.clone());
            }
        }

        if let Some(ref children) = self.children {
            for child in children.iter() {
                if child.bounds_intersects_sphere(&center, radius) {
                    child.query_sphere(center, radius, results);
                }
            }
        }
    }
}

pub struct GalaxyCore {
    pub root: PentaNode,
}

impl GalaxyCore {
    pub fn new() -> Self {
        Self {
            root: PentaNode::new(
                Point5D { x: -2.0, y: -2.0, z: -2.0, w: 0.0, v: 0.0 },
                Point5D { x: 2.0, y: 2.0, z: 2.0, w: 5.0, v: 1.0 },
            ),
        }
    }
}
