//! WhiteMagic Rust JSON stdio bridge
//!
//! Reads JSON requests from stdin, writes JSON responses to stdout.
//! Usage: cargo run --example bridge --release
//!
//! Supported methods:
//!   - ping: {}
//!   - encode: {"text": "hello world"}
//!   - nearest_neighbors: {"query": "hello", "texts": ["a", "b"], "k": 2}
//!   - distance: {"a": {"x":0,...}, "b": {"x":1,...}}
//!   - zone: {"coord": {"x":0, "y":0, "z":0, "w":0, "v":0.1}}

use std::io::{self, BufRead, Write};
use wm_core::{Coordinate5D, HRR, Zone, detect_constellations, hrr_to_coordinate, joint_query, nearest_neighbors};

fn main() {
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut stdout_lock = stdout.lock();

    for line in stdin.lock().lines() {
        let line = match line {
            Ok(l) if l.trim().is_empty() => continue,
            Ok(l) => l,
            Err(_) => break,
        };

        let response = match serde_json::from_str::<serde_json::Value>(&line) {
            Ok(req) => handle_request(req),
            Err(e) => json_error(&format!("Invalid JSON: {}", e)),
        };

        if let Err(_) = writeln!(stdout_lock, "{}", response) {
            break;
        }
        let _ = stdout_lock.flush();
    }
}

fn handle_request(req: serde_json::Value) -> String {
    let method = req.get("method").and_then(|m| m.as_str()).unwrap_or("");
    let params = req.get("params").cloned().unwrap_or(serde_json::json!({}));

    match method {
        "ping" => json_ok(serde_json::json!({"backend": "rust"})),
        "encode" => {
            let text = params.get("text").and_then(|t| t.as_str()).unwrap_or("");
            let coord = Coordinate5D::encode(text);
            json_ok(coord_to_json(&coord))
        }
        "nearest_neighbors" => {
            let query_text = params.get("query").and_then(|t| t.as_str()).unwrap_or("");
            let empty_vec = vec![];
            let texts = params.get("texts").and_then(|t| t.as_array()).unwrap_or(&empty_vec);
            let k = params.get("k").and_then(|k| k.as_u64()).unwrap_or(3) as usize;

            let query = Coordinate5D::encode(query_text);
            let coords: Vec<Coordinate5D> = texts
                .iter()
                .filter_map(|t| t.as_str().map(Coordinate5D::encode))
                .collect();

            let results = nearest_neighbors(&query, &coords, k);
            let json_results: Vec<serde_json::Value> = results
                .into_iter()
                .map(|(idx, dist)| {
                    serde_json::json!({"index": idx, "distance": dist})
                })
                .collect();

            json_ok(serde_json::json!({"results": json_results}))
        }
        "distance" => {
            let a = params.get("a").and_then(parse_coord);
            let b = params.get("b").and_then(parse_coord);
            match (a, b) {
                (Some(a), Some(b)) => {
                    json_ok(serde_json::json!({"distance": a.distance(&b)}))
                }
                _ => json_error("Expected params.a and params.b as 5D coords"),
            }
        }
        "zone" => {
            let coord = params.get("coord").and_then(parse_coord);
            match coord {
                Some(c) => {
                    let zone = Zone::from_valence(c.v);
                    json_ok(serde_json::json!({"zone": zone.as_str()}))
                }
                _ => json_error("Expected params.coord as 5D coord"),
            }
        }
        "encode_hrr" => {
            let text = params.get("text").and_then(|t| t.as_str()).unwrap_or("");
            let dim = params.get("dim").and_then(|d| d.as_u64()).unwrap_or(64) as usize;
            let hrr = HRR::encode(text, dim);
            json_ok(serde_json::json!({
                "dim": hrr.dim(),
                "vec": hrr.vec,
            }))
        }
        "bind" => {
            let a = params.get("a").and_then(parse_hrr);
            let b = params.get("b").and_then(parse_hrr);
            match (a, b) {
                (Some(a), Some(b)) => {
                    let c = a.bind(&b);
                    json_ok(serde_json::json!({"dim": c.dim(), "vec": c.vec}))
                }
                _ => json_error("Expected params.a and params.b as HRR vectors"),
            }
        }
        "unbind" => {
            let a = params.get("a").and_then(parse_hrr);
            let b = params.get("b").and_then(parse_hrr);
            match (a, b) {
                (Some(a), Some(b)) => {
                    let c = a.unbind(&b);
                    json_ok(serde_json::json!({"dim": c.dim(), "vec": c.vec}))
                }
                _ => json_error("Expected params.a and params.b as HRR vectors"),
            }
        }
        "dual_encode" => {
            let text = params.get("text").and_then(|t| t.as_str()).unwrap_or("");
            let dim = params.get("dim").and_then(|d| d.as_u64()).unwrap_or(64) as usize;
            let hrr = HRR::encode(text, dim);
            let coord = hrr_to_coordinate(&hrr);
            json_ok(serde_json::json!({
                "hrr": {"dim": hrr.dim(), "vec": hrr.vec},
                "coord": coord_to_json(&coord),
            }))
        }
        "joint_query" => {
            let query_text = params.get("query").and_then(|t| t.as_str()).unwrap_or("");
            let empty_vec2 = vec![];
            let texts = params.get("texts").and_then(|t| t.as_array()).unwrap_or(&empty_vec2);
            let k = params.get("k").and_then(|k| k.as_u64()).unwrap_or(3) as usize;
            let hrr_weight = params.get("hrr_weight").and_then(|w| w.as_f64()).unwrap_or(0.5);
            let spatial_weight = params.get("spatial_weight").and_then(|w| w.as_f64()).unwrap_or(0.5);
            let dim = params.get("dim").and_then(|d| d.as_u64()).unwrap_or(64) as usize;

            let query_hrr = HRR::encode(query_text, dim);
            let query_coord = hrr_to_coordinate(&query_hrr);

            let hrrs: Vec<HRR> = texts
                .iter()
                .filter_map(|t| t.as_str().map(|s| HRR::encode(s, dim)))
                .collect();
            let coords: Vec<Coordinate5D> = texts
                .iter()
                .filter_map(|t| t.as_str().map(Coordinate5D::encode))
                .collect();

            let results = joint_query(&hrrs, &coords, &query_hrr, &query_coord, k, hrr_weight, spatial_weight);
            let json_results: Vec<serde_json::Value> = results
                .into_iter()
                .map(|(idx, score)| {
                    serde_json::json!({"index": idx, "score": score})
                })
                .collect();

            json_ok(serde_json::json!({"results": json_results}))
        }
        "constellation_detect" => {
            let coords_json = params.get("coords").and_then(|c| c.as_array());
            match coords_json {
                Some(arr) => {
                    let coords: Vec<Coordinate5D> = arr.iter().filter_map(parse_coord).collect();
                    let clusters = detect_constellations(&coords, 0.5, 2);
                    let json_clusters: Vec<serde_json::Value> = clusters
                        .into_iter()
                        .map(|c| serde_json::json!({"members": c}))
                        .collect();
                    json_ok(serde_json::json!({"clusters": json_clusters}))
                }
                _ => json_error("Expected params.coords as array of 5D coords"),
            }
        }
        _ => json_error(&format!("Unknown method: {}", method)),
    }
}

fn parse_hrr(v: &serde_json::Value) -> Option<HRR> {
    let vec = v.get("vec")?.as_array()?;
    let values: Vec<f64> = vec.iter().filter_map(|x| x.as_f64()).collect();
    Some(HRR { vec: values })
}

fn parse_coord(v: &serde_json::Value) -> Option<Coordinate5D> {
    Some(Coordinate5D {
        x: v.get("x")?.as_f64()?,
        y: v.get("y")?.as_f64()?,
        z: v.get("z")?.as_f64()?,
        w: v.get("w")?.as_f64()?,
        v: v.get("v")?.as_f64()?,
    })
}

fn coord_to_json(c: &Coordinate5D) -> serde_json::Value {
    serde_json::json!({
        "x": c.x,
        "y": c.y,
        "z": c.z,
        "w": c.w,
        "v": c.v,
        "zone": Zone::from_valence(c.v).as_str()
    })
}

fn json_ok(data: serde_json::Value) -> String {
    serde_json::json!({"status": "ok", "result": data}).to_string()
}

fn json_error(msg: &str) -> String {
    serde_json::json!({"status": "error", "error": msg}).to_string()
}
