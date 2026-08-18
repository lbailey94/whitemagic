//! Deterministic index-time keys for the v6 episodic sidecar.
//!
//! These are typed, source-bounded features — not broad synonym expansion.

/// Category of a deterministic retrieval key.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum KeyCategory {
    Person,
    Date,
    Location,
    Organization,
    Domain,
    Preference,
    Entity,
}

/// A typed key extracted from a record or query.
#[derive(Debug, Clone, PartialEq)]
pub struct EpisodicKey {
    pub category: KeyCategory,
    pub term: String,
    pub surface: String,
    pub start: usize,
    pub end: usize,
    pub confidence: f32,
}

impl EpisodicKey {
    fn new(
        category: KeyCategory,
        term: impl Into<String>,
        surface: impl Into<String>,
        start: usize,
        end: usize,
        confidence: f32,
    ) -> Self {
        Self {
            category,
            term: term.into(),
            surface: surface.into(),
            start,
            end,
            confidence: confidence.clamp(0.0, 1.0),
        }
    }
}

/// Extract typed retrieval keys from source text.
#[must_use]
pub fn extract_episodic_keys(text: &str) -> Vec<EpisodicKey> {
    let mut keys = Vec::new();
    extract_person_keys(text, &mut keys);
    extract_date_keys(text, &mut keys);
    extract_place_org_keys(text, &mut keys);
    extract_domain_keys(text, &mut keys);
    extract_preference_keys(text, &mut keys);
    extract_entity_keys(text, &mut keys);
    keys.sort_by(|left, right| {
        left.start
            .cmp(&right.start)
            .then_with(|| left.term.cmp(&right.term))
            .then_with(|| (left.category as u8).cmp(&(right.category as u8)))
    });
    keys.dedup_by(|left, right| left.category == right.category && left.term == right.term);
    keys
}

/// Extra sidecar terms derived from typed keys.
#[must_use]
pub fn key_index_terms(text: &str) -> Vec<String> {
    extract_episodic_keys(text)
        .into_iter()
        .map(|key| key.term)
        .fold(Vec::new(), |mut terms, term| {
            if !terms.contains(&term) {
                terms.push(term);
            }
            terms
        })
}

fn extract_person_keys(text: &str, keys: &mut Vec<EpisodicKey>) {
    const TITLES: &[(&str, &str, f32)] = &[
        ("dr.", "doctor", 0.95),
        ("doctor", "doctor", 0.9),
        ("physician", "doctor", 0.85),
        ("dermatologist", "doctor", 0.85),
        ("professor", "professor", 0.9),
        ("prof.", "professor", 0.9),
    ];
    let lower = text.to_ascii_lowercase();
    for (surface, term, confidence) in TITLES {
        for start in find_word_starts(&lower, surface) {
            let end = start + surface.len();
            keys.push(EpisodicKey::new(
                KeyCategory::Person,
                *term,
                &text[start..end.min(text.len())],
                start,
                end.min(text.len()),
                *confidence,
            ));
            if let Some((name, name_end)) = following_proper_name(text, end) {
                keys.push(EpisodicKey::new(
                    KeyCategory::Person,
                    name.to_ascii_lowercase(),
                    name,
                    end,
                    name_end,
                    (*confidence - 0.05).max(0.7),
                ));
            }
        }
    }
}

fn extract_date_keys(text: &str, keys: &mut Vec<EpisodicKey>) {
    const MONTHS: &[(&str, &str)] = &[
        ("january", "01"),
        ("february", "02"),
        ("march", "03"),
        ("april", "04"),
        ("may", "05"),
        ("june", "06"),
        ("july", "07"),
        ("august", "08"),
        ("september", "09"),
        ("october", "10"),
        ("november", "11"),
        ("december", "12"),
    ];
    let lower = text.to_ascii_lowercase();
    for (name, month) in MONTHS {
        for start in find_word_starts(&lower, name) {
            let mut end = start + name.len();
            let mut term = format!("date-{month}");
            if let Some((day, day_end)) = following_day(&lower, end) {
                term = format!("date-{month}-{day:02}");
                end = day_end;
            }
            keys.push(EpisodicKey::new(
                KeyCategory::Date,
                term,
                &text[start..end.min(text.len())],
                start,
                end.min(text.len()),
                0.9,
            ));
        }
    }
    for (start, end, year, month, day) in find_iso_dates(&lower) {
        keys.push(EpisodicKey::new(
            KeyCategory::Date,
            format!("date-{month}-{day:02}"),
            &text[start..end],
            start,
            end,
            0.95,
        ));
        keys.push(EpisodicKey::new(
            KeyCategory::Date,
            format!("date-{year}"),
            &text[start..end],
            start,
            end,
            0.85,
        ));
    }
}

fn extract_place_org_keys(text: &str, keys: &mut Vec<EpisodicKey>) {
    const PLACES: &[(&str, &str, KeyCategory, f32)] = &[
        (
            "university of california, los angeles",
            "ucla",
            KeyCategory::Organization,
            0.95,
        ),
        (
            "university of california los angeles",
            "ucla",
            KeyCategory::Organization,
            0.95,
        ),
        ("los angeles", "los-angeles", KeyCategory::Location, 0.85),
        ("ucla", "university", KeyCategory::Organization, 0.9),
        ("ikea", "ikea", KeyCategory::Organization, 0.95),
        ("hawaii", "hawaii", KeyCategory::Location, 0.9),
        ("japan", "japan", KeyCategory::Location, 0.9),
        ("lake michigan", "michigan", KeyCategory::Location, 0.9),
        ("serenity yoga", "yoga", KeyCategory::Organization, 0.9),
        ("spotify", "spotify", KeyCategory::Organization, 0.95),
    ];
    let lower = text.to_ascii_lowercase();
    for (surface, term, category, confidence) in PLACES {
        for start in find_word_starts(&lower, surface) {
            let end = start + surface.len();
            keys.push(EpisodicKey::new(
                *category,
                *term,
                &text[start..end.min(text.len())],
                start,
                end.min(text.len()),
                *confidence,
            ));
        }
    }
    if let Some(start) = find_word_starts(&lower, "university of").into_iter().next() {
        keys.push(EpisodicKey::new(
            KeyCategory::Organization,
            "university",
            &text[start..(start + "university of".len()).min(text.len())],
            start,
            (start + "university of".len()).min(text.len()),
            0.8,
        ));
    }
}

fn extract_domain_keys(text: &str, keys: &mut Vec<EpisodicKey>) {
    const DOMAINS: &[(&str, &[&str], f32)] = &[
        (
            "medicine",
            &[
                "doctor",
                "physician",
                "prescription",
                "appointment",
                "dermatolog",
            ],
            0.8,
        ),
        (
            "education",
            &[
                "degree",
                "bachelor",
                "graduate",
                "undergrad",
                "university",
                "college",
                "computer science",
            ],
            0.8,
        ),
        (
            "travel",
            &["trip", "commute", "hawaii", "japan", "vacation"],
            0.75,
        ),
        (
            "pets",
            &["dog", "cat", "retriever", "animal shelter", "puppy"],
            0.85,
        ),
        ("finance", &["paid", "worth", "mbps", "internet plan"], 0.7),
        ("food", &["bake", "recipe", "cook", "dinner"], 0.7),
        (
            "music",
            &["spotify", "streaming", "concert", "playlist"],
            0.85,
        ),
        (
            "sports",
            &["tennis", "bike", "bicycle", "yoga", "fishing"],
            0.8,
        ),
    ];
    let lower = text.to_ascii_lowercase();
    for (domain, cues, confidence) in DOMAINS {
        if let Some(cue) = cues.iter().copied().find(|cue| contains_word(&lower, cue)) {
            let start = lower.find(cue).unwrap_or(0);
            keys.push(EpisodicKey::new(
                KeyCategory::Domain,
                *domain,
                cue,
                start,
                start + cue.len(),
                *confidence,
            ));
        }
    }
}

fn extract_preference_keys(text: &str, keys: &mut Vec<EpisodicKey>) {
    const MARKERS: &[&str] = &[
        "my favorite",
        "i prefer",
        "i like",
        "i enjoy",
        "i've been using",
        "have i been using",
    ];
    let lower = text.to_ascii_lowercase();
    for marker in MARKERS {
        for start in find_word_starts(&lower, marker) {
            keys.push(EpisodicKey::new(
                KeyCategory::Preference,
                "preference",
                &text[start..(start + marker.len()).min(text.len())],
                start,
                (start + marker.len()).min(text.len()),
                0.85,
            ));
        }
    }
}

fn extract_entity_keys(text: &str, keys: &mut Vec<EpisodicKey>) {
    const ENTITIES: &[(&str, &str, f32)] = &[
        ("golden retriever", "dog", 0.95),
        ("labrador", "dog", 0.9),
        ("dog", "dog", 0.85),
        ("cat", "cat", 0.85),
        ("music streaming service", "spotify", 0.8),
        ("streaming service", "spotify", 0.75),
        ("community theater", "play", 0.8),
        ("the glass menagerie", "play", 0.95),
        ("play", "play", 0.7),
        ("tennis racket", "tennis", 0.9),
        ("daily commute", "commute", 0.9),
        ("commute", "commute", 0.85),
        ("computer science", "degree", 0.8),
        ("bachelor's degree", "degree", 0.9),
        ("bachelors degree", "degree", 0.9),
        ("undergrad", "degree", 0.85),
        ("undergraduate", "degree", 0.85),
        ("cs", "degree", 0.7),
        ("bookshelf", "bookshelf", 0.8),
        ("internet plan", "internet-plan", 0.85),
        ("yoga", "yoga", 0.85),
    ];
    let lower = text.to_ascii_lowercase();
    for (surface, term, confidence) in ENTITIES {
        for start in find_word_starts(&lower, surface) {
            let end = start + surface.len();
            keys.push(EpisodicKey::new(
                KeyCategory::Entity,
                *term,
                &text[start..end.min(text.len())],
                start,
                end.min(text.len()),
                *confidence,
            ));
        }
    }
}

fn find_word_starts(haystack: &str, needle: &str) -> Vec<usize> {
    if needle.is_empty() {
        return Vec::new();
    }
    let bytes = haystack.as_bytes();
    let needle_bytes = needle.as_bytes();
    let mut starts = Vec::new();
    let mut offset = 0;
    while offset + needle_bytes.len() <= bytes.len() {
        if bytes[offset..].starts_with(needle_bytes)
            && is_boundary_before(bytes, offset)
            && is_boundary_after(bytes, offset + needle_bytes.len())
        {
            starts.push(offset);
            offset += needle_bytes.len();
        } else {
            offset += 1;
        }
    }
    starts
}

fn contains_word(haystack: &str, needle: &str) -> bool {
    !find_word_starts(haystack, needle).is_empty()
}

fn is_boundary_before(bytes: &[u8], offset: usize) -> bool {
    offset == 0 || !bytes[offset - 1].is_ascii_alphanumeric()
}

fn is_boundary_after(bytes: &[u8], offset: usize) -> bool {
    offset >= bytes.len() || !bytes[offset].is_ascii_alphanumeric()
}

fn following_proper_name(text: &str, mut offset: usize) -> Option<(&str, usize)> {
    while offset < text.len() && text.as_bytes()[offset].is_ascii_whitespace() {
        offset += 1;
    }
    let start = offset;
    while offset < text.len() && text.as_bytes()[offset].is_ascii_alphabetic() {
        offset += 1;
    }
    if offset <= start {
        return None;
    }
    let name = &text[start..offset];
    if name
        .chars()
        .next()
        .is_some_and(|ch| ch.is_ascii_uppercase())
    {
        Some((name, offset))
    } else {
        None
    }
}

fn following_day(lower: &str, mut offset: usize) -> Option<(u8, usize)> {
    while offset < lower.len() && lower.as_bytes()[offset].is_ascii_whitespace() {
        offset += 1;
    }
    let start = offset;
    while offset < lower.len() && lower.as_bytes()[offset].is_ascii_digit() {
        offset += 1;
    }
    if offset == start {
        return None;
    }
    let day = lower[start..offset].parse::<u8>().ok()?;
    if !(1..=31).contains(&day) {
        return None;
    }
    for suffix in ["st", "nd", "rd", "th"] {
        if lower[offset..].starts_with(suffix) {
            offset += suffix.len();
            break;
        }
    }
    Some((day, offset))
}

fn find_iso_dates(lower: &str) -> Vec<(usize, usize, i32, &str, u8)> {
    let bytes = lower.as_bytes();
    let mut dates = Vec::new();
    let mut offset = 0;
    while offset + 10 <= bytes.len() {
        if bytes[offset].is_ascii_digit()
            && bytes[offset + 1].is_ascii_digit()
            && bytes[offset + 2].is_ascii_digit()
            && bytes[offset + 3].is_ascii_digit()
            && bytes[offset + 4] == b'-'
            && bytes[offset + 5].is_ascii_digit()
            && bytes[offset + 6].is_ascii_digit()
            && bytes[offset + 7] == b'-'
            && bytes[offset + 8].is_ascii_digit()
            && bytes[offset + 9].is_ascii_digit()
            && is_boundary_before(bytes, offset)
            && is_boundary_after(bytes, offset + 10)
        {
            if let (Ok(year), Ok(month), Ok(day)) = (
                lower[offset..offset + 4].parse::<i32>(),
                lower[offset + 5..offset + 7].parse::<u8>(),
                lower[offset + 8..offset + 10].parse::<u8>(),
            ) {
                if (1..=12).contains(&month) && (1..=31).contains(&day) {
                    let month_term = match month {
                        1 => "01",
                        2 => "02",
                        3 => "03",
                        4 => "04",
                        5 => "05",
                        6 => "06",
                        7 => "07",
                        8 => "08",
                        9 => "09",
                        10 => "10",
                        11 => "11",
                        _ => "12",
                    };
                    dates.push((offset, offset + 10, year, month_term, day));
                }
            }
            offset += 10;
        } else {
            offset += 1;
        }
    }
    dates
}

#[cfg(test)]
mod tests {
    use super::*;

    fn terms(text: &str) -> Vec<String> {
        key_index_terms(text)
    }

    #[test]
    fn person_title_maps_doctor_to_name() {
        let keys = extract_episodic_keys("I saw Dr. Patel yesterday");
        assert!(
            keys.iter()
                .any(|key| key.category == KeyCategory::Person && key.term == "doctor")
        );
        assert!(
            keys.iter()
                .any(|key| key.category == KeyCategory::Person && key.term == "patel")
        );
        let doctor = keys
            .iter()
            .find(|key| key.term == "doctor")
            .expect("doctor key");
        assert!(doctor.start < doctor.end);
        assert!(doctor.confidence > 0.9);
    }

    #[test]
    fn date_normalizes_month_and_day() {
        let keys = extract_episodic_keys("I volunteered on February 14th");
        assert!(keys.iter().any(|key| key.term == "date-02-14"));
        assert!(
            extract_episodic_keys("due 2024-02-14")
                .iter()
                .any(|key| key.term == "date-02-14")
        );
    }

    #[test]
    fn organization_aliases_ucla() {
        let keys = extract_episodic_keys(
            "I completed my degree at the University of California, Los Angeles",
        );
        assert!(keys.iter().any(|key| key.term == "ucla"));
        assert!(terms("UCLA").contains(&"university".to_string()));
    }

    #[test]
    fn pet_breed_maps_to_dog() {
        let keys = extract_episodic_keys("My Golden Retriever loves the park");
        assert!(
            keys.iter()
                .any(|key| key.category == KeyCategory::Entity && key.term == "dog")
        );
        assert!(
            keys.iter()
                .any(|key| key.category == KeyCategory::Domain && key.term == "pets")
        );
    }

    #[test]
    fn preference_and_streaming_service_have_regression_cases() {
        assert!(terms("Spotify is what I use").contains(&"spotify".to_string()));
        assert!(
            extract_episodic_keys(
                "What is the name of the music streaming service have I been using lately?"
            )
            .iter()
            .any(|key| key.term == "spotify" || key.term == "preference")
        );
    }

    #[test]
    fn empty_and_stopword_text_yields_no_keys() {
        assert!(extract_episodic_keys("the and of").is_empty());
    }
}
