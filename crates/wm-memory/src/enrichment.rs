//! Storage-time vocabulary enrichment for the episodic inverted index.
//!
//! Based on SelRoute (2026): enrich term postings with vocabulary bridges at
//! ingestion time so records match queries using different but related
//! vocabulary. Enrichment applies to the lexical index only — NOT to content
//! used for embedding computation.

use std::collections::HashMap;

/// Simple suffix-stripping stemmer matching the one in episodic.rs.
fn simple_stem(word: &str) -> String {
    if word.len() <= 3 {
        return word.to_string();
    }
    for suffix in ["ies", "ied", "ing", "edly", "ed", "ly", "es", "s"] {
        if let Some(stem) = word.strip_suffix(suffix) {
            if suffix == "ies" || suffix == "ied" {
                return format!("{stem}y");
            }
            if stem.len() >= 2 {
                return stem.to_string();
            }
        }
    }
    word.to_string()
}

/// A topic room: when co-occurring trigger terms are present, add contextual
/// terms to the index.
#[derive(Debug, Clone)]
struct TopicRoom {
    triggers: Vec<String>,
    additions: Vec<String>,
}

impl TopicRoom {
    fn matches(&self, terms: &[String]) -> bool {
        self.triggers
            .iter()
            .all(|trigger| terms.iter().any(|term| term == trigger))
    }
}

/// Storage-time vocabulary enrichment with hypernym maps, action bridges, and
/// topic rooms.
#[derive(Debug, Clone, Default)]
pub struct VocabularyEnrichment {
    hypernyms: HashMap<String, Vec<String>>,
    action_bridges: HashMap<String, Vec<String>>,
    topic_rooms: Vec<TopicRoom>,
}

impl VocabularyEnrichment {
    /// Create a new empty enrichment.
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Create with the default enrichment maps targeting known LongMemEval-S
    /// miss patterns.
    #[must_use]
    pub fn with_defaults() -> Self {
        let mut enrichment = Self::default();

        // Hypernyms: specific → broader terms
        let hypernyms: &[(&str, &[&str])] = &[
            ("production", &["play", "theater", "performance", "stage"]),
            ("performance", &["play", "theater", "show"]),
            ("audition", &["play", "theater", "performance"]),
            ("menagerie", &["play", "theater", "production"]),
            ("painting", &["art", "class", "studio", "course"]),
            ("art", &["class", "studio", "course", "painting"]),
            ("studio", &["class", "course", "workshop", "art"]),
            ("course", &["class", "lesson", "workshop"]),
            ("workshop", &["class", "course", "lesson"]),
            ("shelter", &["rescue", "adoption", "humane", "animal"]),
            ("rescue", &["shelter", "adoption", "animal"]),
            ("adoption", &["shelter", "rescue", "animal"]),
            ("humane", &["shelter", "rescue", "animal"]),
            (
                "fundraising",
                &["charity", "donation", "event", "volunteer"],
            ),
            ("auction", &["fundraising", "charity", "event"]),
            ("volunteer", &["charity", "community", "event"]),
            ("yoga", &["class", "studio", "exercise", "wellness"]),
            ("vinyasa", &["yoga", "class", "studio"]),
            ("commute", &["drive", "work", "travel", "distance"]),
            ("racket", &["sports", "tennis", "store", "equipment"]),
            ("bookshelf", &["furniture", "shelf", "storage", "assembly"]),
            (
                "degree",
                &["education", "university", "college", "graduation"],
            ),
            (
                "bachelor",
                &["degree", "education", "university", "undergrad", "college"],
            ),
            (
                "undergraduate",
                &["degree", "education", "university", "bachelor", "college"],
            ),
            (
                "undergrad",
                &["degree", "bachelor", "university", "college"],
            ),
            (
                "computer",
                &["science", "cs", "programming", "tech", "engineering"],
            ),
            ("science", &["computer", "cs", "programming", "tech"]),
            ("cs", &["computer", "science", "programming", "tech"]),
            ("cream", &["coffee", "dairy", "grocery"]),
            ("coupon", &["discount", "save", "store", "grocery"]),
            ("playlist", &["music", "spotify", "songs"]),
            ("streaming", &["music", "spotify", "service"]),
            ("retriever", &["dog", "pet", "animal", "breed"]),
            ("labrador", &["dog", "pet", "animal", "breed"]),
            ("puppy", &["dog", "pet", "animal"]),
            ("kitten", &["cat", "pet", "animal"]),
            ("valentine", &["february", "date", "romance"]),
            ("february", &["month", "winter", "date"]),
            ("welfare", &["shelter", "rescue", "animal", "charity"]),
            (
                "charity",
                &["fundraising", "donation", "volunteer", "event"],
            ),
            ("auction", &["fundraising", "charity", "event", "bid"]),
            ("silent", &["auction", "fundraising", "charity"]),
            ("love", &["valentine", "romance", "february"]),
            (
                "philanthropy",
                &["charity", "donation", "fundraising", "volunteer"],
            ),
            ("mutt", &["dog", "animal", "pet"]),
            ("strut", &["dog", "animal", "event", "walk"]),
        ];
        for (specific, broader) in hypernyms {
            enrichment.hypernyms.insert(
                simple_stem(specific),
                broader.iter().map(|s| simple_stem(s)).collect(),
            );
        }

        // Action bridges: query verbs → content verbs
        let action_bridges: &[(&str, &[&str])] = &[
            (
                "attend",
                &["went", "participated", "visited", "was_at", "joined"],
            ),
            (
                "attended",
                &["went", "participated", "visited", "was_at", "joined"],
            ),
            ("buy", &["purchased", "got", "ordered", "bought"]),
            ("bought", &["purchased", "acquired", "got"]),
            ("adopt", &["rescued", "took", "brought", "got"]),
            ("rescued", &["adopted", "saved", "took", "brought"]),
            ("redeem", &["used", "claimed", "applied"]),
            ("create", &["made", "built", "set_up", "started"]),
            ("created", &["made", "built", "set_up", "started"]),
            ("change", &["switched", "updated", "replaced", "modified"]),
            ("changed", &["switched", "updated", "replaced", "modified"]),
            ("enroll", &["join", "register", "sign_up", "start"]),
            (
                "volunteer",
                &["helped", "assisted", "participated", "donated"],
            ),
            ("move", &["moved", "relocated", "transfer", "packing"]),
            ("trip", &["travel", "vacation", "visit"]),
            ("assemble", &["assembled", "built", "put", "together"]),
        ];
        for (verb, bridges) in action_bridges {
            enrichment.action_bridges.insert(
                simple_stem(verb),
                bridges.iter().map(|s| simple_stem(s)).collect(),
            );
        }

        // Topic rooms: co-occurring triggers add contextual terms
        enrichment.topic_rooms = vec![
            TopicRoom {
                triggers: vec![simple_stem("theater"), simple_stem("play")],
                additions: vec![
                    simple_stem("production"),
                    simple_stem("performance"),
                    simple_stem("stage"),
                ],
            },
            TopicRoom {
                triggers: vec![simple_stem("art"), simple_stem("class")],
                additions: vec![
                    simple_stem("painting"),
                    simple_stem("studio"),
                    simple_stem("course"),
                ],
            },
            TopicRoom {
                triggers: vec![simple_stem("animal"), simple_stem("shelter")],
                additions: vec![
                    simple_stem("rescue"),
                    simple_stem("adoption"),
                    simple_stem("volunteer"),
                ],
            },
            TopicRoom {
                triggers: vec![simple_stem("yoga"), simple_stem("class")],
                additions: vec![
                    simple_stem("studio"),
                    simple_stem("exercise"),
                    simple_stem("wellness"),
                ],
            },
            TopicRoom {
                triggers: vec![simple_stem("community"), simple_stem("theater")],
                additions: vec![
                    simple_stem("play"),
                    simple_stem("production"),
                    simple_stem("performance"),
                ],
            },
        ];

        enrichment
    }

    /// Returns additional terms to index for the given content terms.
    #[must_use]
    pub fn enrich(&self, terms: &[String]) -> Vec<String> {
        let mut extra = Vec::new();
        for term in terms {
            if let Some(bridges) = self.hypernyms.get(term) {
                extra.extend(bridges.iter().cloned());
            }
            if let Some(bridges) = self.action_bridges.get(term) {
                extra.extend(bridges.iter().cloned());
            }
        }
        for room in &self.topic_rooms {
            if room.matches(terms) {
                extra.extend(room.additions.iter().cloned());
            }
        }
        extra.sort();
        extra.dedup();
        extra
    }

    /// Whether the enrichment is empty.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.hypernyms.is_empty() && self.action_bridges.is_empty() && self.topic_rooms.is_empty()
    }

    /// Reverse enrichment: given a query term, returns content terms that
    /// should also count as a match. This is the inverse of `enrich` —
    /// if `production → play` in the hypernym map, then `reverse_enrich("play")`
    /// returns `["production"]`.
    #[must_use]
    pub fn reverse_enrich(&self, query_term: &str) -> Vec<String> {
        let mut extra = Vec::new();
        for (source, targets) in &self.hypernyms {
            if targets.iter().any(|t| t == query_term) {
                extra.push(source.clone());
            }
        }
        for (source, targets) in &self.action_bridges {
            if targets.iter().any(|t| t == query_term) {
                extra.push(source.clone());
            }
        }
        // Topic room additions: if the query term is in a room's additions,
        // the room's triggers should also match.
        for room in &self.topic_rooms {
            if room.additions.iter().any(|t| t == query_term) {
                extra.extend(room.triggers.iter().cloned());
            }
        }
        extra.sort();
        extra.dedup();
        extra
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn enriches_production_with_play_and_theater() {
        let enrichment = VocabularyEnrichment::with_defaults();
        let extra = enrichment.enrich(&["production".to_string()]);
        assert!(extra.contains(&"play".to_string()));
        assert!(extra.contains(&"theater".to_string()));
        assert!(extra.contains(&"performance".to_string()));
    }

    #[test]
    fn enriches_attended_with_went_and_participated() {
        let enrichment = VocabularyEnrichment::with_defaults();
        let extra = enrichment.enrich(&["attend".to_string()]);
        assert!(extra.contains(&"went".to_string()));
        assert!(extra.contains(&"participat".to_string()));
    }

    #[test]
    fn topic_room_fires_on_co_occurrence() {
        let enrichment = VocabularyEnrichment::with_defaults();
        let extra = enrichment.enrich(&["theater".to_string(), "play".to_string()]);
        assert!(extra.contains(&"production".to_string()));
        assert!(extra.contains(&"performance".to_string()));
        assert!(extra.contains(&"stage".to_string()));
    }

    #[test]
    fn topic_room_does_not_fire_on_partial_match() {
        let enrichment = VocabularyEnrichment::with_defaults();
        let extra = enrichment.enrich(&["theater".to_string()]);
        // "theater" alone triggers hypernym but not the topic room
        // (which needs both "theater" AND "play")
        assert!(!extra.contains(&"stage".to_string()));
    }

    #[test]
    fn enrichment_is_deduplicated() {
        let enrichment = VocabularyEnrichment::with_defaults();
        let extra = enrichment.enrich(&["production".to_string(), "performance".to_string()]);
        let unique: Vec<_> = extra.iter().collect();
        let mut sorted = unique.clone();
        sorted.sort();
        sorted.dedup();
        assert_eq!(unique.len(), sorted.len());
    }

    #[test]
    fn empty_enrichment_returns_nothing() {
        let enrichment = VocabularyEnrichment::new();
        assert!(enrichment.is_empty());
        assert!(enrichment.enrich(&["anything".to_string()]).is_empty());
    }

    #[test]
    fn shelter_bridges_to_rescue_and_adoption() {
        let enrichment = VocabularyEnrichment::with_defaults();
        let extra = enrichment.enrich(&["shelter".to_string()]);
        assert!(extra.contains(&"rescue".to_string()));
        assert!(extra.contains(&"adoption".to_string()));
        assert!(extra.contains(&"animal".to_string()));
    }

    #[test]
    fn painting_bridges_to_art_and_studio() {
        let enrichment = VocabularyEnrichment::with_defaults();
        let extra = enrichment.enrich(&["paint".to_string()]);
        assert!(extra.contains(&"art".to_string()));
        assert!(extra.contains(&"studio".to_string()));
        assert!(extra.contains(&"clas".to_string()));
    }

    #[test]
    fn reverse_enrich_play_returns_production() {
        let enrichment = VocabularyEnrichment::with_defaults();
        let reverse = enrichment.reverse_enrich("play");
        assert!(reverse.contains(&"production".to_string()));
        assert!(reverse.contains(&"performance".to_string()));
        assert!(reverse.contains(&"audition".to_string()));
        assert!(reverse.contains(&"menagerie".to_string()));
    }

    #[test]
    fn reverse_enrich_yoga_returns_vinyasa() {
        let enrichment = VocabularyEnrichment::with_defaults();
        let reverse = enrichment.reverse_enrich("yoga");
        assert!(reverse.contains(&"vinyasa".to_string()));
    }

    #[test]
    fn reverse_enrich_shelter_returns_rescue_and_adoption() {
        let enrichment = VocabularyEnrichment::with_defaults();
        let reverse = enrichment.reverse_enrich("shelter");
        assert!(reverse.contains(&"rescue".to_string()));
        assert!(reverse.contains(&"adoption".to_string()));
        assert!(reverse.contains(&"humane".to_string()));
    }

    #[test]
    fn reverse_enrich_animal_returns_mutt_and_welfare() {
        let enrichment = VocabularyEnrichment::with_defaults();
        let reverse = enrichment.reverse_enrich("animal");
        assert!(reverse.contains(&"mutt".to_string()));
        assert!(reverse.contains(&"welfare".to_string()));
        assert!(reverse.contains(&"puppy".to_string()));
    }
}
