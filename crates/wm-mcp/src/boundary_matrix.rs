//! Q08 dispatch-boundary matrix — registry-derived route classification and
//! per-boundary expectations, rendered so the artifact cannot drift from the
//! registry dispatch actually builds.
//!
//! The authoritative artifact is `docs/Q08_DISPATCH_BOUNDARY_MATRIX.md`; its
//! `q08-route-matrix` block is produced by [`render_block`] and drift-checked
//! by `tests/dispatch_boundary_matrix.rs` (fixture coverage lives there too).

use crate::gateway::FEDERATED_READS;
use std::fmt::Write as _;
use wm_core::{Sandbox, Tool};
use wm_dispatch::ToolRegistry;

/// Exclusive route class for matrix purposes. First match wins in this
/// order: meta (by name) > destructive > spawn > coordination > write > read.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RouteClass {
    Meta,
    Destructive,
    Spawn,
    Coordination,
    Write,
    Read,
}

impl RouteClass {
    /// Stable lowercase label used in the rendered block.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Meta => "meta",
            Self::Destructive => "destructive",
            Self::Spawn => "spawn",
            Self::Coordination => "coordination",
            Self::Write => "write",
            Self::Read => "read",
        }
    }
}

/// Routes that are dispatch layers rather than dispatched work: they route
/// to other routes (or describe the surface) and are boundary subjects only
/// as entrypoints, not as work.
pub const META_ROUTES: &[&str] = &[
    "wm",
    "tools.list",
    "tools.usage_report",
    "gnosis",
    "nlu.shadow_report",
];

/// Classify one registered tool from its declared `EffectRow`.
#[must_use]
pub fn classify(tool: &dyn Tool) -> RouteClass {
    if META_ROUTES.contains(&tool.name()) {
        return RouteClass::Meta;
    }
    let effects = tool.effects();
    if effects.destructive {
        return RouteClass::Destructive;
    }
    if effects.spawns {
        return RouteClass::Spawn;
    }
    if effects.acquires_coordination_lease() || effects.is_coordination_cleanup() {
        return RouteClass::Coordination;
    }
    if !effects.writes.is_empty() {
        return RouteClass::Write;
    }
    RouteClass::Read
}

/// Expected verdict per boundary, fixed order B1–B6.
///
/// Symbols: `A` admitted (standard pipeline gates apply) · `C` admitted only
/// with `confirm: true` plus an explicit `SCOPE_REGISTRY` scope · `R` refused
/// (NLU structural unreachability) · `P` pinned to an explicit gateway scope
/// (write-without-scope refused) · `F` federated read fan-out · `N` no
/// registry dispatch path at this boundary · `—` boundary does not carry
/// registry routes.
#[must_use]
pub fn boundary_cells(name: &str, class: RouteClass) -> [&'static str; 6] {
    let direct = if class == RouteClass::Destructive {
        "C"
    } else {
        "A"
    };
    let nlu = match class {
        RouteClass::Meta => "—",
        RouteClass::Destructive => "R",
        _ => "A",
    };
    let gateway = if FEDERATED_READS.contains(&name) {
        "F"
    } else if class == RouteClass::Destructive {
        "PC"
    } else {
        "P"
    };
    [direct, direct, nlu, "N", gateway, "—"]
}

fn effect_flags(tool: &dyn Tool) -> String {
    let effects = tool.effects();
    let mut flags = String::new();
    if !effects.reads.is_empty() {
        flags.push('r');
    }
    if !effects.writes.is_empty() {
        flags.push('w');
    }
    if !effects.invokes.is_empty() {
        flags.push('i');
    }
    if effects.spawns {
        flags.push('s');
    }
    if effects.destructive {
        flags.push('d');
    }
    if effects.sandbox != Sandbox::Inherit {
        flags.push('x');
    }
    if flags.is_empty() {
        flags.push('-');
    }
    flags
}

/// Render the generated `q08-route-matrix` block: counts plus one row per
/// registered route (sorted by name) with its class, effect flags, and the
/// per-boundary verdict.
#[must_use]
pub fn render_block(registry: &ToolRegistry) -> String {
    let mut tools: Vec<&dyn Tool> = registry.all_ref().iter().map(AsRef::as_ref).collect();
    tools.sort_by_key(|tool| tool.name());

    let mut counts = [0usize; 6];
    for tool in &tools {
        let class = classify(*tool);
        let index = match class {
            RouteClass::Read => 0,
            RouteClass::Write => 1,
            RouteClass::Destructive => 2,
            RouteClass::Spawn => 3,
            RouteClass::Coordination => 4,
            RouteClass::Meta => 5,
        };
        counts[index] += 1;
    }

    let mut block = format!(
        "Routes: {} — read {}, write {}, destructive {}, spawn {}, coordination {}, meta {} \
         (exclusive class; first match wins in that order, meta by route name).\n\n",
        tools.len(),
        counts[0],
        counts[1],
        counts[2],
        counts[3],
        counts[4],
        counts[5],
    );
    block.push_str(
        "| Route | Gana | Class | Effects | B1 direct | B2 wrapper | B3 NLU | B4 daemon | B5 gateway | B6 mesh |\n",
    );
    block.push_str("|---|---|---|---|---|---|---|---|---|---|\n");
    for tool in &tools {
        let class = classify(*tool);
        let cells = boundary_cells(tool.name(), class);
        writeln!(
            block,
            "| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |",
            tool.name(),
            tool.gana(),
            class.as_str(),
            effect_flags(*tool),
            cells[0],
            cells[1],
            cells[2],
            cells[3],
            cells[4],
            cells[5],
        )
        .expect("writing to a String cannot fail");
    }
    block
}
