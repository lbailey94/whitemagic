//! Bounded, deterministic resolver and verifier for caller supplied temporal assertions.
//!
//! This module decides only what follows from the supplied records and query scope. It
//! does not establish that records are true, complete, independently sourced, or authorized.

use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::io::Read;

use chrono::{DateTime, NaiveDate, Utc};
use serde::{Deserialize, Serialize};

use crate::temporal::parse_instant;

const MAX_INPUT_BYTES: usize = 1024 * 1024;
const MAX_ASSERTIONS: usize = 512;
const MAX_STRING_BYTES: usize = 4096;

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Assertion {
    pub record_id: String,
    pub subject: String,
    pub predicate: String,
    pub value: String,
    pub source_id: String,
    pub valid_from: String,
    #[serde(deserialize_with = "Option::deserialize")]
    pub valid_until: Option<String>,
    pub recorded_at: String,
    #[serde(deserialize_with = "Option::deserialize")]
    pub supersedes: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Question {
    pub question_id: String,
    pub query: String,
    pub subject: String,
    pub predicate: String,
    pub valid_at: Vec<String>,
    pub known_at: String,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Proposal {
    pub status: String,
    pub claims: Vec<ProposedClaim>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ProposedClaim {
    pub valid_at: String,
    pub record_id: String,
    pub value: String,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    assertions: Vec<Assertion>,
    question: Question,
    #[serde(default)]
    proposal: Option<Proposal>,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum DecisionStatus {
    Answer,
    Conflict,
    Insufficient,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct Fact {
    pub valid_at: String,
    pub value: String,
    pub record_id: String,
    pub source_id: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct Decision {
    pub question_id: String,
    pub authority: &'static str,
    pub status: DecisionStatus,
    pub facts: Vec<Fact>,
    pub citations: Vec<String>,
    pub reason_codes: Vec<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(untagged)]
pub enum Output {
    Resolve(Decision),
    Verify(Verification),
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct Verification {
    pub accepted: bool,
    pub decision: Option<Decision>,
    pub reason_codes: Vec<String>,
}

#[derive(Debug, Clone)]
struct ParsedAssertion {
    raw: Assertion,
    from: DateTime<Utc>,
    until: Option<DateTime<Utc>>,
    recorded: DateTime<Utc>,
}

/// Read and process a request without consuming more than the input limit plus
/// one byte. This supports pipes without allocating for an unbounded stream.
pub fn process_reader(mode: &str, reader: impl Read) -> Result<Output, String> {
    if mode != "resolve" && mode != "verify" {
        return Err("mode must be resolve or verify".into());
    }
    let mut bytes = Vec::new();
    reader
        .take((MAX_INPUT_BYTES + 1) as u64)
        .read_to_end(&mut bytes)
        .map_err(|_| "cannot read request".to_string())?;
    if bytes.len() > MAX_INPUT_BYTES {
        return Err("request exceeds 1 MiB".into());
    }
    let json = std::str::from_utf8(&bytes).map_err(|_| "request must be UTF-8".to_string())?;
    process(mode, json)
}

/// Resolve or verify one strict JSON request. `mode` is exactly `resolve` or `verify`.
pub fn process(mode: &str, json: &str) -> Result<Output, String> {
    if json.len() > MAX_INPUT_BYTES {
        return Err("request exceeds 1 MiB".into());
    }
    if mode != "resolve" && mode != "verify" {
        return Err("mode must be resolve or verify".into());
    }
    let mut request: Request =
        serde_json::from_str(json).map_err(|e| format!("invalid request: {e}"))?;
    validate_request(&request)?;
    let proposal = request.proposal.take();
    let parsed = parse_assertions(request.assertions)?;
    let decision = resolve(&parsed, &request.question)?;
    match mode {
        "resolve" => {
            if proposal.is_some() {
                return Err("resolve mode does not accept proposal".into());
            }
            Ok(Output::Resolve(decision))
        }
        "verify" => {
            let proposal = proposal.ok_or_else(|| "verify mode requires proposal".to_string())?;
            Ok(Output::Verify(verify_proposal(
                &decision,
                &request.question,
                proposal,
            )))
        }
        _ => unreachable!(),
    }
}

fn validate_request(request: &Request) -> Result<(), String> {
    if request.assertions.len() > MAX_ASSERTIONS {
        return Err(format!("assertions exceeds limit of {MAX_ASSERTIONS}"));
    }
    for (name, value) in [
        ("question_id", &request.question.question_id),
        ("query", &request.question.query),
        ("subject", &request.question.subject),
        ("predicate", &request.question.predicate),
        ("known_at", &request.question.known_at),
    ] {
        check_string(name, value)?;
        if value.trim().is_empty() {
            return Err(format!("{name} must be nonempty"));
        }
    }
    if request.question.valid_at.is_empty() || request.question.valid_at.len() > 2 {
        return Err("valid_at must contain one or two ascending ISO dates".into());
    }
    let points = request
        .question
        .valid_at
        .iter()
        .map(|s| parse_date(s))
        .collect::<Result<Vec<_>, _>>()?;
    if points.windows(2).any(|w| w[0] >= w[1]) {
        return Err("valid_at dates must be ascending and unique".into());
    }
    for point in &request.question.valid_at {
        check_string("valid_at", point)?;
    }
    parse_time(&request.question.known_at)?;
    if let Some(proposal) = &request.proposal {
        check_string("proposal.status", &proposal.status)?;
        let claim_limit = MAX_ASSERTIONS * request.question.valid_at.len();
        if proposal.claims.len() > claim_limit {
            return Err(format!("proposal claims exceeds limit of {claim_limit}"));
        }
        for claim in &proposal.claims {
            for (name, value) in [
                ("proposal.valid_at", &claim.valid_at),
                ("proposal.record_id", &claim.record_id),
                ("proposal.value", &claim.value),
            ] {
                check_string(name, value)?;
                if value.trim().is_empty() {
                    return Err(format!("{name} must be nonempty"));
                }
            }
        }
    }
    Ok(())
}

fn check_string(field: &str, value: &str) -> Result<(), String> {
    if value.len() > MAX_STRING_BYTES {
        return Err(format!("{field} exceeds {MAX_STRING_BYTES} bytes"));
    }
    Ok(())
}

fn parse_date(s: &str) -> Result<DateTime<Utc>, String> {
    let date =
        NaiveDate::parse_from_str(s, "%Y-%m-%d").map_err(|_| format!("invalid ISO date: {s}"))?;
    if date.format("%Y-%m-%d").to_string() != s {
        return Err(format!("invalid ISO date: {s}"));
    }
    let midnight = date
        .and_hms_opt(0, 0, 0)
        .ok_or_else(|| format!("invalid ISO date: {s}"))?;
    Ok(DateTime::from_naive_utc_and_offset(midnight, Utc))
}

fn parse_time(s: &str) -> Result<DateTime<Utc>, String> {
    check_string("timestamp", s)?;
    if s.len() == 10 {
        return parse_date(s);
    }
    parse_instant(s).map_err(|e| format!("invalid timestamp: {e}"))
}

fn parse_assertions(assertions: Vec<Assertion>) -> Result<Vec<ParsedAssertion>, String> {
    let mut ids = HashSet::new();
    let mut parsed = Vec::with_capacity(assertions.len());
    for raw in assertions {
        for (name, value) in [
            ("record_id", &raw.record_id),
            ("subject", &raw.subject),
            ("predicate", &raw.predicate),
            ("value", &raw.value),
            ("source_id", &raw.source_id),
            ("valid_from", &raw.valid_from),
            ("recorded_at", &raw.recorded_at),
        ] {
            check_string(name, value)?;
            if value.trim().is_empty() {
                return Err(format!("{name} must be nonempty"));
            }
        }
        if let Some(until) = &raw.valid_until {
            check_string("valid_until", until)?;
        }
        if let Some(prior) = &raw.supersedes {
            check_string("supersedes", prior)?;
        }
        if !ids.insert(raw.record_id.clone()) {
            return Err(format!("duplicate record_id: {}", raw.record_id));
        }
        let from = parse_time(&raw.valid_from)?;
        let until = raw.valid_until.as_deref().map(parse_time).transpose()?;
        let recorded = parse_time(&raw.recorded_at)?;
        if until.is_some_and(|end| from >= end) {
            return Err(format!("invalid interval for {}", raw.record_id));
        }
        parsed.push(ParsedAssertion {
            raw,
            from,
            until,
            recorded,
        });
    }
    let by_id: HashMap<_, _> = parsed
        .iter()
        .map(|r| (r.raw.record_id.as_str(), r))
        .collect();
    for item in &parsed {
        if let Some(prior_id) = &item.raw.supersedes {
            let prior = by_id
                .get(prior_id.as_str())
                .ok_or_else(|| format!("supersedes target missing: {prior_id}"))?;
            if item.raw.record_id == *prior_id {
                return Err("supersedes cycle".into());
            }
            if item.raw.source_id != prior.raw.source_id
                || item.raw.subject != prior.raw.subject
                || item.raw.predicate != prior.raw.predicate
            {
                return Err(format!("supersedes target scope mismatch: {prior_id}"));
            }
            if item.recorded < prior.recorded {
                return Err(format!(
                    "replacement recorded before prior: {}",
                    item.raw.record_id
                ));
            }
        }
    }
    let mut marks: HashMap<&str, u8> = HashMap::new();
    for item in &parsed {
        visit(item.raw.record_id.as_str(), &by_id, &mut marks)?;
    }
    Ok(parsed)
}

fn visit<'a>(
    id: &'a str,
    by_id: &HashMap<&'a str, &'a ParsedAssertion>,
    marks: &mut HashMap<&'a str, u8>,
) -> Result<(), String> {
    match marks.get(id).copied().unwrap_or(0) {
        1 => return Err("supersedes cycle".into()),
        2 => return Ok(()),
        _ => {}
    }
    marks.insert(id, 1);
    if let Some(prior) = by_id[id].raw.supersedes.as_deref() {
        visit(prior, by_id, marks)?;
    }
    marks.insert(id, 2);
    Ok(())
}

fn resolve(records: &[ParsedAssertion], question: &Question) -> Result<Decision, String> {
    let known = parse_time(&question.known_at)?;
    let points = question
        .valid_at
        .iter()
        .map(|s| Ok((s.clone(), parse_date(s)?)))
        .collect::<Result<Vec<_>, String>>()?;
    let scoped: Vec<&ParsedAssertion> = records
        .iter()
        .filter(|r| {
            r.raw.subject == question.subject
                && r.raw.predicate == question.predicate
                && r.recorded <= known
        })
        .collect();
    let mut facts = Vec::new();
    let mut reasons = BTreeSet::new();
    let mut conflict_dates = BTreeSet::new();
    let mut saw_conflict = false;
    let mut saw_missing = false;
    for (label, at) in points {
        let active: Vec<_> = scoped
            .iter()
            .copied()
            .filter(|r| {
                r.from <= at
                    && r.until.is_none_or(|u| at < u)
                    && !scoped.iter().any(|replacement| {
                        replacement.raw.supersedes.as_deref() == Some(r.raw.record_id.as_str())
                            && replacement.from <= at
                    })
            })
            .collect();
        let mut values: BTreeMap<&str, Vec<&ParsedAssertion>> = BTreeMap::new();
        for record in active {
            values
                .entry(record.raw.value.as_str())
                .or_default()
                .push(record);
        }
        if values.is_empty() {
            saw_missing = true;
            reasons.insert(format!("insufficient_evidence:{label}"));
        } else if values.len() > 1 {
            saw_conflict = true;
            conflict_dates.insert(label.clone());
            reasons.insert(format!("conflict:{label}"));
            for rs in values.values() {
                for r in rs {
                    facts.push(to_fact(&label, r));
                }
            }
        } else if let Some((_, rs)) = values.into_iter().next() {
            for r in rs {
                facts.push(to_fact(&label, r));
            }
        }
    }
    facts.sort_by(|a, b| {
        (&a.valid_at, &a.value, &a.record_id).cmp(&(&b.valid_at, &b.value, &b.record_id))
    });
    let status = if saw_conflict {
        DecisionStatus::Conflict
    } else if saw_missing {
        DecisionStatus::Insufficient
    } else {
        DecisionStatus::Answer
    };
    // A held question never delivers the resolved portion as a partial answer.
    // Conflict facts are proof of the hold; insufficient decisions have no facts.
    if saw_conflict {
        facts.retain(|fact| conflict_dates.contains(&fact.valid_at));
    } else if saw_missing {
        facts.clear();
    }
    let citations: BTreeSet<_> = facts.iter().map(|f| f.record_id.clone()).collect();
    if !saw_conflict && !saw_missing {
        reasons.insert("assertions_resolve_requested_dates".into());
    }
    Ok(Decision {
        question_id: question.question_id.clone(),
        authority: "caller_asserted_metadata",
        status,
        facts,
        citations: citations.into_iter().collect(),
        reason_codes: reasons.into_iter().collect(),
    })
}

fn to_fact(label: &str, record: &ParsedAssertion) -> Fact {
    Fact {
        valid_at: label.to_string(),
        value: record.raw.value.clone(),
        record_id: record.raw.record_id.clone(),
        source_id: record.raw.source_id.clone(),
    }
}

fn verify_proposal(decision: &Decision, question: &Question, proposal: Proposal) -> Verification {
    let mut errors = BTreeSet::new();
    if proposal.status != status_name(&decision.status) {
        errors.insert("proposal_status_mismatch".to_string());
    }
    let allowed: HashSet<_> = decision
        .facts
        .iter()
        .map(|f| (f.valid_at.as_str(), f.record_id.as_str(), f.value.as_str()))
        .collect();
    let mut seen = HashSet::new();
    for claim in &proposal.claims {
        if !question.valid_at.iter().any(|d| d == &claim.valid_at) {
            errors.insert("proposal_date_out_of_scope".into());
        }
        if !seen.insert((&claim.valid_at, &claim.record_id, &claim.value)) {
            errors.insert("duplicate_proposal_claim".into());
        }
        if !allowed.contains(&(
            claim.valid_at.as_str(),
            claim.record_id.as_str(),
            claim.value.as_str(),
        )) {
            errors.insert("proposal_claim_unsupported".into());
        }
    }
    for date in &question.valid_at {
        let canonical: Vec<_> = decision
            .facts
            .iter()
            .filter(|f| &f.valid_at == date)
            .collect();
        let proposed: Vec<_> = proposal
            .claims
            .iter()
            .filter(|c| &c.valid_at == date)
            .collect();
        let missing = canonical.is_empty();
        if missing && !proposed.is_empty() {
            errors.insert("proposal_claim_for_unresolved_date".into());
        }
        if !missing {
            let distinct: HashSet<_> = canonical.iter().map(|f| f.value.as_str()).collect();
            let supplied: HashSet<_> = proposed.iter().map(|c| c.value.as_str()).collect();
            if supplied != distinct {
                errors.insert("proposal_incomplete_date".into());
            }
        }
    }
    if errors.is_empty() {
        Verification {
            accepted: true,
            decision: Some(decision.clone()),
            reason_codes: vec!["proposal_matches_assertion_resolution".into()],
        }
    } else {
        Verification {
            accepted: false,
            decision: None,
            reason_codes: errors.into_iter().collect(),
        }
    }
}

fn status_name(status: &DecisionStatus) -> &'static str {
    match status {
        DecisionStatus::Answer => "answer",
        DecisionStatus::Conflict => "conflict",
        DecisionStatus::Insufficient => "insufficient",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stream_accepts_the_exact_byte_limit_and_stops_after_one_extra_byte() {
        let request = base("[]", r#"["2020-01-01"]"#, "2020-01-01");
        let expected = process("resolve", &request).unwrap();
        let mut padded = request.into_bytes();
        padded.resize(MAX_INPUT_BYTES, b' ');
        assert_eq!(
            process_reader("resolve", padded.as_slice()).unwrap(),
            expected
        );
        padded.extend_from_slice(&[b' '; 64]);
        let mut cursor = std::io::Cursor::new(padded);
        assert_eq!(
            process_reader("resolve", &mut cursor).unwrap_err(),
            "request exceeds 1 MiB"
        );
        assert_eq!(cursor.position(), (MAX_INPUT_BYTES + 1) as u64);
    }

    #[test]
    fn stream_rejects_invalid_encoding_partial_reads_and_invalid_modes() {
        struct BrokenReader;
        impl Read for BrokenReader {
            fn read(&mut self, _: &mut [u8]) -> std::io::Result<usize> {
                Err(std::io::Error::other("private diagnostic"))
            }
        }
        assert_eq!(
            process_reader("resolve", &[0xff][..]).unwrap_err(),
            "request must be UTF-8"
        );
        let request = base("[]", r#"["2020-01-01"]"#, "2020-01-01");
        let reader = std::io::Cursor::new(request).chain(BrokenReader);
        assert_eq!(
            process_reader("resolve", reader).unwrap_err(),
            "cannot read request"
        );
        assert_eq!(
            process_reader("invalid", BrokenReader).unwrap_err(),
            "mode must be resolve or verify"
        );
    }

    #[test]
    fn stream_verification_matches_inline_and_rejects_trailing_or_duplicate_json() {
        let request = base("[]", r#"["2020-01-01"]"#, "2020-01-01");
        let proposal = request.replacen(
            "{",
            r#"{"proposal":{"status":"insufficient","claims":[]},"#,
            1,
        );
        assert_eq!(
            process_reader("verify", proposal.as_bytes()).unwrap(),
            process("verify", &proposal).unwrap()
        );
        assert!(process_reader("resolve", format!("{request} {{}}").as_bytes()).is_err());
        let duplicate = request.replacen("{", r#"{"assertions":[],"#, 1);
        assert!(process_reader("resolve", duplicate.as_bytes()).is_err());
    }

    fn base(assertions: &str, dates: &str, known: &str) -> String {
        format!(
            r#"{{"assertions":{assertions},"question":{{"question_id":"q1","query":"What?","subject":"A","predicate":"role","valid_at":{dates},"known_at":"{known}"}}}}"#
        )
    }
    fn a(
        id: &str,
        value: &str,
        from: &str,
        until: &str,
        recorded: &str,
        supersedes: &str,
    ) -> String {
        format!(
            r#"{{"record_id":"{id}","subject":"A","predicate":"role","value":"{value}","source_id":"s1","valid_from":"{from}","valid_until":{until},"recorded_at":"{recorded}","supersedes":{supersedes}}}"#
        )
    }
    fn resolve_json(json: &str) -> Decision {
        match process("resolve", json).unwrap() {
            Output::Resolve(d) => d,
            _ => unreachable!(),
        }
    }

    #[test]
    fn date_ranges_and_same_value_support_are_deterministic() {
        let rows = format!(
            "[{},{}]",
            a(
                "r2",
                "x",
                "2020-01-01",
                "null",
                "2020-01-01T00:00:00Z",
                "null"
            ),
            a(
                "r1",
                "x",
                "2020-01-01",
                "null",
                "2020-01-01T00:00:00Z",
                "null"
            )
        );
        let d = resolve_json(&base(&rows, r#"["2020-01-01","2021-01-01"]"#, "2020-01-01"));
        assert_eq!(d.status, DecisionStatus::Answer);
        assert_eq!(d.citations, ["r1", "r2"]);
        assert_eq!(d.facts.len(), 4);
        assert_eq!(
            d,
            resolve_json(&base(&rows, r#"["2020-01-01","2021-01-01"]"#, "2020-01-01"))
        );
    }

    #[test]
    fn retroactive_correction_and_expiry_do_not_resurrect_prior() {
        let old = a(
            "old",
            "x",
            "2020-01-01",
            "null",
            "2020-01-01T00:00:00Z",
            "null",
        );
        let new = a(
            "new",
            "y",
            "2021-01-01",
            r#""2022-01-01""#,
            "2021-06-01T00:00:00Z",
            r#""old""#,
        );
        let rows = format!("[{old},{new}]");
        let d = resolve_json(&base(&rows, r#"["2021-01-01","2022-01-01"]"#, "2021-06-01"));
        assert_eq!(d.status, DecisionStatus::Insufficient);
        assert!(d.facts.is_empty() && d.citations.is_empty());
        let before_recording = resolve_json(&base(&rows, r#"["2021-01-01"]"#, "2021-05-31"));
        assert_eq!(before_recording.facts[0].value, "x");
        let corrected = resolve_json(&base(&rows, r#"["2021-01-01"]"#, "2021-06-01"));
        assert_eq!(
            corrected
                .facts
                .iter()
                .map(|f| f.value.as_str())
                .collect::<Vec<_>>(),
            ["y"]
        );
        let expired = resolve_json(&base(&rows, r#"["2022-01-01"]"#, "2021-06-01"));
        assert_eq!(expired.status, DecisionStatus::Insufficient);
        assert!(expired.facts.is_empty());
    }

    #[test]
    fn known_cutoff_and_conflict_are_enforced() {
        let rows = format!(
            "[{},{}]",
            a(
                "x",
                "x",
                "2020-01-01",
                "null",
                "2020-01-01T00:00:00Z",
                "null"
            ),
            a(
                "y",
                "y",
                "2020-01-01",
                "null",
                "2020-01-01T00:00:00Z",
                "null"
            )
        );
        assert_eq!(
            resolve_json(&base(&rows, r#"["2020-01-01"]"#, "2020-01-01")).status,
            DecisionStatus::Conflict
        );
    }

    #[test]
    fn scope_and_known_time_filter_before_fact_resolution_including_equality() {
        let eligible = a(
            "eligible",
            "right",
            "2020-01-01",
            "null",
            "2020-01-01T00:00:00Z",
            "null",
        );
        let later = a(
            "later",
            "wrong",
            "2020-01-01",
            "null",
            "2020-01-02T00:00:00Z",
            "null",
        );
        let lure = later
            .replace("\"subject\":\"A\"", "\"subject\":\"B\"")
            .replace("\"record_id\":\"later\"", "\"record_id\":\"lure\"");
        let rows = format!("[{eligible},{later},{lure}]");
        let d = resolve_json(&base(&rows, r#"["2020-01-01"]"#, "2020-01-01"));
        assert_eq!(d.status, DecisionStatus::Answer);
        assert_eq!(
            d.facts.iter().map(|f| f.value.as_str()).collect::<Vec<_>>(),
            ["right"]
        );
    }

    #[test]
    fn valid_until_is_exclusive_and_missing_date_holds_whole_result() {
        let row = a(
            "r",
            "x",
            "2020-01-01",
            r#""2020-01-02""#,
            "2020-01-01T00:00:00Z",
            "null",
        );
        let d = resolve_json(&base(
            &format!("[{row}]"),
            r#"["2020-01-01","2020-01-02"]"#,
            "2020-01-01",
        ));
        assert_eq!(d.status, DecisionStatus::Insufficient);
        assert!(d.facts.is_empty() && d.citations.is_empty());
    }

    #[test]
    fn replacement_scope_and_recorded_chronology_are_required() {
        let old = a(
            "old",
            "x",
            "2020-01-01",
            "null",
            "2020-01-02T00:00:00Z",
            "null",
        );
        let replacement = a(
            "new",
            "y",
            "2020-01-01",
            "null",
            "2020-01-03T00:00:00Z",
            r#""old""#,
        );
        let cross_source = replacement.replace("\"source_id\":\"s1\"", "\"source_id\":\"s2\"");
        assert!(
            process(
                "resolve",
                &base(
                    &format!("[{old},{cross_source}]"),
                    r#"["2020-01-01"]"#,
                    "2020-01-03"
                )
            )
            .is_err()
        );
        let early = a(
            "new",
            "y",
            "2020-01-01",
            "null",
            "2020-01-01T00:00:00Z",
            r#""old""#,
        );
        assert!(
            process(
                "resolve",
                &base(
                    &format!("[{old},{early}]"),
                    r#"["2020-01-01"]"#,
                    "2020-01-03"
                )
            )
            .is_err()
        );
    }

    #[test]
    fn verify_is_fail_closed_and_returns_only_canonical_decision() {
        let rows = format!(
            "[{}]",
            a(
                "r",
                "x",
                "2020-01-01",
                "null",
                "2020-01-01T00:00:00Z",
                "null"
            )
        );
        let mut json = base(&rows, r#"["2020-01-01"]"#, "2020-01-01");
        json.pop();
        json.push_str(r#", "proposal":{"status":"answer","claims":[{"valid_at":"2020-01-01","record_id":"r","value":"x"}]}}"#);
        match process("verify", &json).unwrap() {
            Output::Verify(v) => assert!(v.accepted && v.decision.is_some()),
            _ => unreachable!(),
        }
        let bad = json.replace("\"value\":\"x\"}]", "\"value\":\"no\"}]");
        match process("verify", &bad).unwrap() {
            Output::Verify(v) => assert!(!v.accepted && v.decision.is_none()),
            _ => unreachable!(),
        }
    }

    #[test]
    fn malformed_supersedes_and_unknown_fields_reject() {
        let cycle = format!(
            "[{},{}]",
            a(
                "r1",
                "x",
                "2020-01-01",
                "null",
                "2020-01-01T00:00:00Z",
                r#""r2""#
            ),
            a(
                "r2",
                "y",
                "2020-01-01",
                "null",
                "2020-01-01T00:00:00Z",
                r#""r1""#
            )
        );
        assert!(process("resolve", &base(&cycle, r#"["2020-01-01"]"#, "2020-01-01")).is_err());
        assert!(process("resolve", r#"{"assertions":[],"question":{"question_id":"q","query":"q","subject":"A","predicate":"p","valid_at":["2020-01-01"],"known_at":"2020-01-01","extra":1}}"#).is_err());
    }

    fn with_proposal(request: &str, status: &str, claims: serde_json::Value) -> String {
        let mut request: serde_json::Value = serde_json::from_str(request).unwrap();
        request["proposal"] = serde_json::json!({"status": status, "claims": claims});
        request.to_string()
    }

    fn verification(request: &str) -> Verification {
        match process("verify", request).unwrap() {
            Output::Verify(value) => value,
            _ => unreachable!(),
        }
    }

    #[test]
    fn mixed_date_holds_never_deliver_partial_answers() {
        let row = a(
            "r",
            "x",
            "2020-01-01",
            r#""2020-01-02""#,
            "2020-01-01",
            "null",
        );
        let request = base(
            &format!("[{row}]"),
            r#"["2020-01-01","2020-01-02"]"#,
            "2020-01-01",
        );
        let held = verification(&with_proposal(
            &request,
            "insufficient",
            serde_json::json!([]),
        ));
        assert!(held.accepted);
        assert!(held.decision.unwrap().facts.is_empty());
        let partial = with_proposal(
            &request,
            "insufficient",
            serde_json::json!([
                {"valid_at":"2020-01-01","record_id":"r","value":"x"}
            ]),
        );
        let rejected = verification(&partial);
        assert!(!rejected.accepted && rejected.decision.is_none());

        let competing = a("c", "y", "2020-01-02", "null", "2020-01-01", "null");
        let persistent = a("r", "x", "2020-01-01", "null", "2020-01-01", "null");
        let request = base(
            &format!("[{persistent},{competing}]"),
            r#"["2020-01-01","2020-01-02"]"#,
            "2020-01-01",
        );
        let conflict = resolve_json(&request);
        assert_eq!(conflict.status, DecisionStatus::Conflict);
        assert!(conflict.facts.iter().all(|f| f.valid_at == "2020-01-02"));
        let held = verification(&with_proposal(
            &request,
            "conflict",
            serde_json::json!([
                {"valid_at":"2020-01-02","record_id":"r","value":"x"},
                {"valid_at":"2020-01-02","record_id":"c","value":"y"}
            ]),
        ));
        assert!(held.accepted);
    }

    #[test]
    fn conflict_verification_requires_every_distinct_value() {
        let rows = format!(
            "[{},{},{}]",
            a("r1", "x", "2020-01-01", "null", "2020-01-01", "null"),
            a("r2", "y", "2020-01-01", "null", "2020-01-01", "null"),
            a("r3", "z", "2020-01-01", "null", "2020-01-01", "null")
        );
        let request = base(&rows, r#"["2020-01-01"]"#, "2020-01-01");
        let mut claims = serde_json::json!([
            {"valid_at":"2020-01-01","record_id":"r1","value":"x"},
            {"valid_at":"2020-01-01","record_id":"r2","value":"y"}
        ]);
        let incomplete = verification(&with_proposal(&request, "conflict", claims.clone()));
        assert!(!incomplete.accepted && incomplete.decision.is_none());
        claims
            .as_array_mut()
            .unwrap()
            .push(serde_json::json!({"valid_at":"2020-01-01","record_id":"r3","value":"z"}));
        assert!(verification(&with_proposal(&request, "conflict", claims)).accepted);
    }

    #[test]
    fn proposal_wrong_binding_and_duplicate_claims_return_no_decision() {
        let row = a("r", "x", "2020-01-01", "null", "2020-01-01", "null");
        let request = base(&format!("[{row}]"), r#"["2020-01-01"]"#, "2020-01-01");
        let correct = serde_json::json!({"valid_at":"2020-01-01","record_id":"r","value":"x"});
        for field in ["valid_at", "record_id", "value"] {
            let mut bad = correct.clone();
            bad[field] = serde_json::json!("wrong");
            let rejected =
                verification(&with_proposal(&request, "answer", serde_json::json!([bad])));
            assert!(!rejected.accepted && rejected.decision.is_none(), "{field}");
        }
        for (status, claims) in [
            ("insufficient", serde_json::json!([])),
            ("answer", serde_json::json!([])),
            (
                "answer",
                serde_json::json!([correct.clone(), correct.clone()]),
            ),
        ] {
            let rejected = verification(&with_proposal(&request, status, claims));
            assert!(!rejected.accepted && rejected.decision.is_none());
        }
        let mut extra = correct.clone();
        extra["source_id"] = serde_json::json!("s1");
        assert!(
            process(
                "verify",
                &with_proposal(&request, "answer", serde_json::json!([extra]))
            )
            .is_err()
        );
        assert!(
            verification(&with_proposal(
                &request,
                "answer",
                serde_json::json!([correct])
            ))
            .accepted
        );
    }

    #[test]
    fn transitive_correction_and_wrong_field_controls() {
        let rows = format!(
            "[{},{},{}]",
            a("r1", "x", "2020-01-01", "null", "2020-01-01", "null"),
            a("r2", "y", "2020-01-01", "null", "2020-01-02", r#""r1""#),
            a("r3", "z", "2020-01-01", "null", "2020-01-03", r#""r2""#)
        );
        let d = resolve_json(&base(&rows, r#"["2020-01-01"]"#, "2020-01-03"));
        assert_eq!(d.citations, ["r3"]);
        let wrong_field = rows.replace("\"predicate\":\"role\"", "\"predicate\":\"temperature\"");
        let d = resolve_json(&base(&wrong_field, r#"["2020-01-01"]"#, "2020-01-03"));
        assert_eq!(d.status, DecisionStatus::Insufficient);
    }

    #[test]
    fn strict_fields_limits_and_graph_errors_are_rejected() {
        let row = a("r", "x", "2020-01-01", "null", "2020-01-01", "null");
        let request = base(&format!("[{row}]"), r#"["2020-01-01"]"#, "2020-01-01");
        for missing in ["valid_until", "supersedes"] {
            let mut value: serde_json::Value = serde_json::from_str(&request).unwrap();
            value["assertions"][0]
                .as_object_mut()
                .unwrap()
                .remove(missing);
            assert!(process("resolve", &value.to_string()).is_err(), "{missing}");
        }
        assert!(
            process(
                "resolve",
                &request.replace(
                    "\"question_id\":",
                    "\"question_id\":\"duplicate\",\"question_id\":"
                )
            )
            .is_err()
        );
        assert!(
            process(
                "resolve",
                &base(&format!("[{row},{row}]"), r#"["2020-01-01"]"#, "2020-01-01")
            )
            .is_err()
        );
        assert!(
            process(
                "resolve",
                &base(
                    &format!("[{row}]"),
                    r#"["2020-01-02","2020-01-01"]"#,
                    "2020-01-01"
                )
            )
            .is_err()
        );
        assert!(
            process(
                "resolve",
                &base(
                    &format!("[{row}]"),
                    r#"["2020-01-01","2020-01-01"]"#,
                    "2020-01-01"
                )
            )
            .is_err()
        );
        assert!(
            process(
                "resolve",
                &base(&format!("[{row}]"), r#"["2020-02-30"]"#, "2020-01-01")
            )
            .is_err()
        );
        assert!(
            process(
                "resolve",
                &request.replace("\"supersedes\":null", "\"supersedes\":\"missing\"")
            )
            .is_err()
        );
        assert!(process("resolve", &" ".repeat(MAX_INPUT_BYTES + 1)).is_err());
        let mut value: serde_json::Value = serde_json::from_str(&request).unwrap();
        value["question"]["query"] = serde_json::json!("x".repeat(MAX_STRING_BYTES + 1));
        assert!(process("resolve", &value.to_string()).is_err());
        value["question"]["query"] = serde_json::json!("q");
        value["assertions"] =
            serde_json::json!(vec![value["assertions"][0].clone(); MAX_ASSERTIONS + 1]);
        assert!(process("resolve", &value.to_string()).is_err());
    }

    #[test]
    fn two_dates_can_verify_more_than_512_complete_conflict_claims() {
        let records: Vec<_> = (0..257)
            .map(|i| {
                serde_json::json!({
                    "record_id":format!("r{i}"),"subject":"A","predicate":"role",
                    "value":format!("v{i}"),"source_id":format!("s{i}"),
                    "valid_from":"2020-01-01","valid_until":null,
                    "recorded_at":"2020-01-01","supersedes":null
                })
            })
            .collect();
        let claims: Vec<_> = ["2020-01-01", "2020-01-02"]
            .iter()
            .flat_map(|date| {
                (0..257).map(move |i| {
                    serde_json::json!({
                        "valid_at":date,"record_id":format!("r{i}"),"value":format!("v{i}")
                    })
                })
            })
            .collect();
        assert_eq!(claims.len(), 514);
        let request = base(
            &serde_json::to_string(&records).unwrap(),
            r#"["2020-01-01","2020-01-02"]"#,
            "2020-01-01",
        );
        let result = verification(&with_proposal(
            &request,
            "conflict",
            serde_json::json!(claims),
        ));
        assert!(result.accepted);
        assert_eq!(result.decision.unwrap().facts.len(), 514);
    }
}
