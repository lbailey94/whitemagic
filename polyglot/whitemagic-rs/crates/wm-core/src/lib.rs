//! WhiteMagic Unified Memory Core (Rust)
//!
//! Combines:
//! - 5D Holographic Spatial Coordinates (X, Y, Z, W, V)
//! - Holographic Reduced Representations (HRR / Plate vectors)
//! - Joint Symbolic-Spatial Query Model (Option 2)
//!
//! The unified model maps HRR vectors into 5D holographic space,
//! enabling memory retrieval by both semantic similarity and spatial proximity.

pub mod holographic;
pub mod hrr;
pub mod novelty;
pub mod unified;
pub mod vector_index;

pub use holographic::*;
pub use hrr::HRR;
pub use unified::{dual_encode, hrr_to_coordinate, joint_query};
