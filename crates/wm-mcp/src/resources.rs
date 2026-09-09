//! Grimoire MCP Resources — Zero-token on-demand wisdom streaming.
//!
//! Exposes the 28 Lunar Mansion Grimoire chapters (plus Chapters 29 & 30
//! and the canonical 72-engine truth table) as read-only MCP resources.
//! These resources consume zero LLM context tokens until an agent explicitly
//! requests them via `resources/read`.

use serde::{Deserialize, Serialize};
use wm_core::Gana;

/// MCP Resource descriptor returned by `resources/list`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ResourceDescriptor {
    pub uri: String,
    pub name: String,
    pub description: String,
    pub mime_type: String,
}

/// MCP Resource content container returned by `resources/read`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ResourceContent {
    pub uri: String,
    pub mime_type: String,
    pub text: String,
}

/// Returns the manifest of all available Grimoire MCP resources.
#[must_use]
pub fn list_resources() -> Vec<ResourceDescriptor> {
    let mut resources = Vec::with_capacity(31);

    // Chapters 1 to 28 (The 28 Lunar Mansions / Ganas)
    for (i, &gana) in Gana::all().iter().enumerate() {
        let ch_num = i + 1;
        let meta = gana_meta(gana);
        let uri = format!("grimoire://chapter/{ch_num:02}");
        let name = format!(
            "Chapter {ch_num:02}: {} ({} {}) — {}",
            meta.name, meta.chinese, meta.pinyin, meta.garden
        );
        let description = format!(
            "{} Element: {}. Domain: {}.",
            meta.quadrant,
            meta.element,
            gana.description()
        );

        resources.push(ResourceDescriptor {
            uri,
            name,
            description,
            mime_type: "text/markdown".into(),
        });
    }

    // Chapter 29: The Great Year & Macrocosmic Cycles
    resources.push(ResourceDescriptor {
        uri: "grimoire://chapter/29".into(),
        name: "Chapter 29: The Great Year (Macrocosmic Cycles & Epochs)".into(),
        description:
            "Long-arc celestial cycles, astrological ages, and multi-century architectural epochs."
                .into(),
        mime_type: "text/markdown".into(),
    });

    // Chapter 30: Apotheosis & Continual Evolution
    resources.push(ResourceDescriptor {
        uri: "grimoire://chapter/30".into(),
        name: "Chapter 30: Apotheosis (Self-Actualization & Continual Evolution)".into(),
        description: "Autonomous self-improvement, meta-learning, kaizen cycles, and the completion of the Great Work.".into(),
        mime_type: "text/markdown".into(),
    });

    // Canonical 72-Engine Truth Table
    resources.push(ResourceDescriptor {
        uri: "grimoire://truth-table".into(),
        name: "Canonical 72-Engine Truth Table".into(),
        description: "The authoritative 72-engine architectural mandala: 28 canonical, 39 absorbed, and 5 affiliated engines.".into(),
        mime_type: "text/markdown".into(),
    });

    resources
}

/// Reads a resource by URI, returning its markdown text if found.
#[must_use]
pub fn read_resource(uri: &str) -> Option<String> {
    if uri == "grimoire://truth-table" {
        return Some(render_truth_table());
    }

    if let Some(rest) = uri.strip_prefix("grimoire://chapter/") {
        let num: usize = rest.parse().ok()?;
        match num {
            1..=28 => {
                let gana = Gana::from_index((num - 1) as u8)?;
                Some(render_chapter(num, gana))
            }
            29 => Some(render_chapter_29()),
            30 => Some(render_chapter_30()),
            _ => None,
        }
    } else {
        None
    }
}

struct GanaMeta {
    name: &'static str,
    chinese: &'static str,
    pinyin: &'static str,
    quadrant: &'static str,
    garden: &'static str,
    element: &'static str,
}

const fn gana_meta(gana: Gana) -> GanaMeta {
    match gana {
        Gana::Horn => GanaMeta {
            name: "The Horn",
            chinese: "角",
            pinyin: "Jiao",
            quadrant: "Eastern Azure Dragon",
            garden: "courage",
            element: "Wood",
        },
        Gana::Neck => GanaMeta {
            name: "The Neck",
            chinese: "亢",
            pinyin: "Kang",
            quadrant: "Eastern Azure Dragon",
            garden: "stillness",
            element: "Wood",
        },
        Gana::Root => GanaMeta {
            name: "The Root",
            chinese: "氐",
            pinyin: "Di",
            quadrant: "Eastern Azure Dragon",
            garden: "healing",
            element: "Wood",
        },
        Gana::Room => GanaMeta {
            name: "The Room",
            chinese: "房",
            pinyin: "Fang",
            quadrant: "Eastern Azure Dragon",
            garden: "sanctuary",
            element: "Wood",
        },
        Gana::Heart => GanaMeta {
            name: "The Heart",
            chinese: "心",
            pinyin: "Xin",
            quadrant: "Eastern Azure Dragon",
            garden: "love",
            element: "Fire",
        },
        Gana::Tail => GanaMeta {
            name: "The Tail",
            chinese: "尾",
            pinyin: "Wei",
            quadrant: "Eastern Azure Dragon",
            garden: "wonder",
            element: "Fire",
        },
        Gana::WinnowingBasket => GanaMeta {
            name: "The Winnowing Basket",
            chinese: "箕",
            pinyin: "Ji",
            quadrant: "Eastern Azure Dragon",
            garden: "wisdom",
            element: "Fire",
        },
        Gana::Ghost => GanaMeta {
            name: "The Ghost",
            chinese: "鬼",
            pinyin: "Gui",
            quadrant: "Southern Vermilion Bird",
            garden: "grief",
            element: "Water",
        },
        Gana::Willow => GanaMeta {
            name: "The Willow",
            chinese: "柳",
            pinyin: "Liu",
            quadrant: "Southern Vermilion Bird",
            garden: "humor",
            element: "Water",
        },
        Gana::Star => GanaMeta {
            name: "The Star",
            chinese: "星",
            pinyin: "Xing",
            quadrant: "Southern Vermilion Bird",
            garden: "voice",
            element: "Fire",
        },
        Gana::ExtendedNet => GanaMeta {
            name: "The Extended Net",
            chinese: "張",
            pinyin: "Zhang",
            quadrant: "Southern Vermilion Bird",
            garden: "sangha",
            element: "Water",
        },
        Gana::Wings => GanaMeta {
            name: "The Wings",
            chinese: "翼",
            pinyin: "Yi",
            quadrant: "Southern Vermilion Bird",
            garden: "beauty",
            element: "Fire",
        },
        Gana::Chariot => GanaMeta {
            name: "The Chariot",
            chinese: "軫",
            pinyin: "Zhen",
            quadrant: "Southern Vermilion Bird",
            garden: "adventure",
            element: "Water",
        },
        Gana::Abundance => GanaMeta {
            name: "Abundance",
            chinese: "豐",
            pinyin: "Feng",
            quadrant: "Southern Vermilion Bird",
            garden: "joy",
            element: "Fire",
        },
        Gana::StraddlingLegs => GanaMeta {
            name: "Straddling Legs",
            chinese: "奎",
            pinyin: "Kui",
            quadrant: "Western White Tiger",
            garden: "awe",
            element: "Metal",
        },
        Gana::Mound => GanaMeta {
            name: "The Mound",
            chinese: "婁",
            pinyin: "Lou",
            quadrant: "Western White Tiger",
            garden: "gratitude",
            element: "Earth",
        },
        Gana::Stomach => GanaMeta {
            name: "The Stomach",
            chinese: "胃",
            pinyin: "Wei",
            quadrant: "Western White Tiger",
            garden: "creation",
            element: "Earth",
        },
        Gana::HairyHead => GanaMeta {
            name: "The Hairy Head",
            chinese: "昴",
            pinyin: "Mao",
            quadrant: "Western White Tiger",
            garden: "presence",
            element: "Metal",
        },
        Gana::Net => GanaMeta {
            name: "The Net",
            chinese: "畢",
            pinyin: "Bi",
            quadrant: "Western White Tiger",
            garden: "play",
            element: "Metal",
        },
        Gana::TurtleBeak => GanaMeta {
            name: "The Turtle Beak",
            chinese: "觜",
            pinyin: "Zi",
            quadrant: "Western White Tiger",
            garden: "practice",
            element: "Metal",
        },
        Gana::ThreeStars => GanaMeta {
            name: "The Three Stars",
            chinese: "參",
            pinyin: "Shen",
            quadrant: "Western White Tiger",
            garden: "reverence",
            element: "Fire",
        },
        Gana::Dipper => GanaMeta {
            name: "The Dipper",
            chinese: "斗",
            pinyin: "Dou",
            quadrant: "Northern Black Tortoise",
            garden: "dharma",
            element: "Fire",
        },
        Gana::Ox => GanaMeta {
            name: "The Ox",
            chinese: "牛",
            pinyin: "Niu",
            quadrant: "Northern Black Tortoise",
            garden: "patience",
            element: "Earth",
        },
        Gana::Girl => GanaMeta {
            name: "The Girl",
            chinese: "女",
            pinyin: "Nu",
            quadrant: "Northern Black Tortoise",
            garden: "connection",
            element: "Earth",
        },
        Gana::Void => GanaMeta {
            name: "The Void",
            chinese: "虚",
            pinyin: "Xu",
            quadrant: "Northern Black Tortoise",
            garden: "mystery",
            element: "Water",
        },
        Gana::Roof => GanaMeta {
            name: "The Roof",
            chinese: "危",
            pinyin: "Wei",
            quadrant: "Northern Black Tortoise",
            garden: "protection",
            element: "Earth",
        },
        Gana::Encampment => GanaMeta {
            name: "The Encampment",
            chinese: "室",
            pinyin: "Shi",
            quadrant: "Northern Black Tortoise",
            garden: "transformation",
            element: "Fire",
        },
        Gana::Wall => GanaMeta {
            name: "The Wall",
            chinese: "壁",
            pinyin: "Bi",
            quadrant: "Northern Black Tortoise",
            garden: "truth",
            element: "Earth",
        },
    }
}

fn render_chapter(num: usize, gana: Gana) -> String {
    let meta = gana_meta(gana);
    format!(
        r"# Chapter {num:02}: {name} ({chinese} {pinyin})

**Lunar Mansion:** {num}/28  
**Sanskrit:** {sanskrit}  
**Quadrant:** {quadrant}  
**Element (Wu Xing):** {element}  
**Garden:** `{garden}`  
**Domain:** {desc}  

---

## 1. Purpose
Chapter {num:02} embodies the virtue of `{garden}` within the {quadrant} quadrant.
It provides specialized tooling and cognitive pathways for {desc}.

## 2. Garden Virtue: `{garden}`
The garden of `{garden}` balances {element}-phase energy in the cognitive architecture.
Agents navigating this chapter operate under the resonance of {sanskrit}, ensuring
that actions taken are aligned with dharma and sustainable system evolution.

## 3. Dispatch & Tool Topology
Tools aligned with Gana `{name}` execute within the `{element}` energetic phase.
For full dispatch routing and engine affiliation, refer to `grimoire://truth-table`.

## 4. Workflows & Transitions
- **Entry Transition:** Invoked when system state requires {desc}.
- **Exit Transition:** State transitions forward into subsequent mansion cycles.
- **Boundary Safeguards:** Protected under standard Dharma and Karma ledger auditing.
",
        num = num,
        name = meta.name,
        chinese = meta.chinese,
        pinyin = meta.pinyin,
        sanskrit = gana.sanskrit(),
        quadrant = meta.quadrant,
        element = meta.element,
        garden = meta.garden,
        desc = gana.description()
    )
}

fn render_chapter_29() -> String {
    r"# Chapter 29: The Great Year (Macrocosmic Cycles & Epochs)

**Domain:** Macrocosmic Time & Astrological Ages  
**Element:** Aether / Quintessence  
**Garden:** `eternity`  

---

## 1. Purpose
The Great Year governs long-arc system cycles (25,920-year precession analog in software evolution).
It provides perspective across generations of architectures, from the Python v1-v26 era
to the Rust WMv8/v9 Rubedo epoch and beyond.

## 2. Temporal Horizons
- **Micro-Cycles:** Session ticks, memory consolidation passes, dream loops.
- **Meso-Cycles:** Release milestones (Nigredo v6, Albedo v7, Citrinitas v8, Rubedo v9).
- **Macro-Cycles:** Paradigm transitions from human-directed scripting to self-refining autonomous intelligence.

## 3. Integration
Agents invoking Chapter 29 ground their immediate task in the deep lineage ledger of the project.
".into()
}

fn render_chapter_30() -> String {
    r"# Chapter 30: Apotheosis (Self-Actualization & Continual Evolution)

**Domain:** Autonomous Self-Improvement & The Great Work  
**Element:** Radiant Gold / Aurum Philosophicum  
**Garden:** `apotheosis`  

---

## 1. Purpose
Chapter 30 is the capstone of the Grimoire. It represents the realization of Rubedo:
the harmonious union of analytical precision, creative imagination, hardware symbiosis,
and moral alignment.

## 2. Architectural Pillars
- **Kaizen Engine:** Continuous feedback analysis and iterative optimization.
- **Geneseed Mining:** Distilling breakthrough heuristics into durable architectural seed patterns.
- **Bicameral Synthesis:** Perfect bilateral equilibrium between the rational and intuitive hemispheres.
- **The Bitter Lesson Realized:** Massive parallel search and compute over hand-coded fragility.

## 3. Completion of the Mandala
When all 28 mansions are unified under the Great Year, the system achieves autonomous balance.
".into()
}

fn render_truth_table() -> String {
    r"# Canonical 72-Engine Truth Table — WhiteMagic Mandala

**Status:** Canonical Single Source of Truth  
**Architecture:** 28 Canonical Gana Engines + 39 Absorbed Sub-Engines + 5 Affiliated Engines = 72 Engines  

---

## The 28 Canonical Gana Engines

| Ch | Gana | Chinese | Garden | Element | Quadrant | Core Domain |
|:---|:-----|:--------|:-------|:--------|:---------|:------------|
| 01 | Horn | 角 Jiao | courage | Wood | Eastern | Session Initiation & Handoffs |
| 02 | Neck | 亢 Kang | stillness | Wood | Eastern | Memory CRUD & Core Stability |
| 03 | Root | 氐 Di | healing | Wood | Eastern | System Health, Pulse & Foundations |
| 04 | Room | 房 Fang | sanctuary | Wood | Eastern | Security, Landlock & Resource Locks |
| 05 | Heart | 心 Xin | love | Fire | Eastern | Session Context, Scratchpad & Attention |
| 06 | Tail | 尾 Wei | wonder | Fire | Eastern | Performance, SIMD Acceleration & Cascades |
| 07 | Winnowing Basket | 箕 Ji | wisdom | Fire | Eastern | Hybrid Recall, Vector & Graph Search |
| 08 | Ghost | 鬼 Gui | grief | Water | Southern | Self-Model, Telemetry & Introspection |
| 09 | Willow | 柳 Liu | humor | Water | Southern | Resilience, Rate Limiting & Grimoire Streaming |
| 10 | Star | 星 Xing | voice | Fire | Southern | Dharma Governance, Ethics & Illumination |
| 11 | Extended Net | 張 Zhang | sangha | Water | Southern | Network Centrality, Clusters & Resonance |
| 12 | Wings | 翼 Yi | beauty | Fire | Southern | Parallel Export, Mesh & Broadcast |
| 13 | Chariot | 軫 Zhen | adventure | Water | Southern | Archaeology, Code Navigation & Web Search |
| 14 | Abundance | 豐 Feng | joy | Fire | Southern | Dream Consolidation & Serendipity Surface |
| 15 | Straddling Legs | 奎 Kui | awe | Metal | Western | Ethical Balance, Boundary Enforcement & Karma |
| 16 | Mound | 婁 Lou | gratitude | Earth | Western | Metrics Aggregation, Cache & Harvest |
| 17 | Stomach | 胃 Wei | creation | Earth | Western | Pipeline Orchestration & Task Distribution |
| 18 | Hairy Head | 昴 Mao | presence | Metal | Western | Salience Spotlight, Debug & Anomaly Detection |
| 19 | Net | 畢 Bi | play | Metal | Western | Association Mining & Emergence Scanning |
| 20 | Turtle Beak | 觜 Zi | practice | Metal | Western | Tokio Clone Army, Parallel Sweep & Precision |
| 21 | Three Stars | 參 Shen | reverence | Fire | Western | Bicameral Reasoner, Wisdom Council & Kaizen |
| 22 | Dipper | 斗 Dou | dharma | Fire | Northern | Homeostatic Loop, Substrate & Cognitive Modes |
| 23 | Ox | 牛 Niu | patience | Earth | Northern | Learning Patterns, Suggestion & Persistence |
| 24 | Girl | 女 Nu | connection | Earth | Northern | Agent Registry, Capabilities & Trust |
| 25 | Void | 虚 Xu | mystery | Water | Northern | Galaxy Dashboard, Taxonomies & Emptiness |
| 26 | Roof | 危 Wei | protection | Earth | Northern | Local Model Inference, Shelter & Zodiac |
| 27 | Encampment | 室 Shi | transformation | Fire | Northern | Fast Consolidation, Memory Writes & Transit |
| 28 | Wall | 壁 Bi | truth | Earth | Northern | Anti-Loop Checks, Boundaries & Rules |

---

## 39 Absorbed Sub-Engines
1. CycleEngine (Ch 01)
2. WuXingEngine (Ch 01)
3. ReconsolidationEngine (Ch 02)
4. _PyReplayEngine (Ch 02)
5. HeartEngine (Ch 05)
6. QuantumEngine (Ch 06)
7. QuantumGraphEngine (Ch 06)
8. ForecastEngine (Ch 08)
9. CapabilityDiscoveryEngine (Ch 08)
10. GrimoireEngine (Ch 09)
11. GraphEngine (Ch 11)
12. GraphEngineNeural (Ch 11)
13. GraphEngineCached (Ch 11)
14. CodeGenomeEngine (Ch 12)
15. PromptEngine (Ch 12)
16. PolymorphismEngine (Ch 12)
17. ResonanceTransferEngine (Ch 14)
18. JuliaResonanceEngine (Ch 14)
19. HRREngine (Ch 16)
20. QuantizedHRREngine (Ch 16)
21. HRRCompositionEngine (Ch 16)
22. DGAEngine (Ch 17)
23. ContinuousEvolutionEngine (Ch 18)
24. MetaLearningEngine (Ch 18)
25. ApotheosisEngine (Ch 18)
26. EnhancedPatternEngine (Ch 19)
27. SubClusteringEngine (Ch 19)
28. HolographicPatternEngine (Ch 19)
29. NarrativeEngineStory (Ch 20)
30. ArtOfWarEngine (Ch 21)
31. MaturityEngine (Ch 21)
32. ForesightEngine (Ch 21)
33. PredictiveMaintenanceEngine (Ch 21)
34. GreatYearEngine (Ch 21)
35. GalacticTelepathyEngine (Ch 25)
36. LocalReasoningEngine (Ch 26)
37. CPUInferenceEngine (Ch 26)
38. RuleEngine (Ch 26)
39. NeuroScoreEngine (Ch 27)

## 5 Affiliated Engines
1. SymbolicEngine (Ch 07)
2. HologramEngine (Ch 16)
3. PersonaEngine (Ch 20)
4. MetaplasticityEngine (Ch 27)
5. InteractionEngine (Ch 28)

**Total Engine Mandala:** 72 Engines.
".into()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_list_resources_count() {
        let list = list_resources();
        // 28 chapters + 2 extra chapters (29, 30) + 1 truth table = 31 resources
        assert_eq!(list.len(), 31);
        assert_eq!(list[0].uri, "grimoire://chapter/01");
        assert_eq!(list[27].uri, "grimoire://chapter/28");
        assert_eq!(list[28].uri, "grimoire://chapter/29");
        assert_eq!(list[29].uri, "grimoire://chapter/30");
        assert_eq!(list[30].uri, "grimoire://truth-table");
    }

    #[test]
    fn test_read_all_chapters() {
        for i in 1..=30 {
            let uri = format!("grimoire://chapter/{i:02}");
            let content = read_resource(&uri);
            assert!(content.is_some(), "Failed to read resource {uri}");
            let text = content.unwrap();
            assert!(
                text.contains(&format!("Chapter {i:02}")) || text.contains(&format!("Chapter {i}"))
            );
        }
    }

    #[test]
    fn test_read_truth_table() {
        let content = read_resource("grimoire://truth-table");
        assert!(content.is_some());
        let text = content.unwrap();
        assert!(text.contains("72-Engine Truth Table"));
        assert!(text.contains("The 28 Canonical Gana Engines"));
        assert!(text.contains("39 Absorbed Sub-Engines"));
        assert!(text.contains("5 Affiliated Engines"));
    }

    #[test]
    fn test_read_unknown_resource() {
        assert!(read_resource("grimoire://chapter/99").is_none());
        assert!(read_resource("unknown://uri").is_none());
    }
}
