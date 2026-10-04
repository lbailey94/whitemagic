use sha2::{Digest, Sha256};
use crate::extractor::NormalizedTurn;

#[derive(Debug, Clone)]
pub struct VaultChunk {
    pub chunk_id: String,
    pub session_id: String,
    pub tier: usize, // 0: Turn, 1: Dyad, 2: Episode, 3: Gestalt
    pub start_seq: i64,
    pub end_seq: i64,
    pub token_count: usize,
    pub content_hash: String,
    pub chunk_text: String,
    pub time_created: i64,
}

pub struct Chunker;

impl Chunker {
    /// Process normalized turns into 4-tier multi-resolution chunks
    pub fn chunk_session(session_id: &str, session_title: &str, turns: &[NormalizedTurn]) -> Vec<VaultChunk> {
        let mut chunks = Vec::new();
        if turns.is_empty() {
            return chunks;
        }

        // Tier 0: Atomic Turns
        for turn in turns {
            let token_count = count_tokens(&turn.clean_text);
            let hash = compute_hash(&turn.clean_text);
            chunks.push(VaultChunk {
                chunk_id: format!("{}-t0-{}", session_id, turn.seq),
                session_id: session_id.to_string(),
                tier: 0,
                start_seq: turn.seq,
                end_seq: turn.seq,
                token_count,
                content_hash: hash,
                chunk_text: format!("[Turn {}:{}] {}", turn.role, turn.turn_type, turn.clean_text),
                time_created: turn.time_created,
            });
        }

        // Tier 1: Dyadic Exchange Chunks (User prompt + Assistant responses until next User prompt)
        let mut dyad_start = 0;
        let mut dyad_buf = String::new();
        let mut dyad_start_seq = turns[0].seq;
        let mut dyad_end_seq = turns[0].seq;
        let mut dyad_time = turns[0].time_created;

        for (i, turn) in turns.iter().enumerate() {
            if turn.role == "user" && i > 0 && !dyad_buf.is_empty() {
                // Flush previous dyad
                let token_count = count_tokens(&dyad_buf);
                let hash = compute_hash(&dyad_buf);
                chunks.push(VaultChunk {
                    chunk_id: format!("{}-t1-{}", session_id, dyad_start),
                    session_id: session_id.to_string(),
                    tier: 1,
                    start_seq: dyad_start_seq,
                    end_seq: dyad_end_seq,
                    token_count,
                    content_hash: hash,
                    chunk_text: dyad_buf.clone(),
                    time_created: dyad_time,
                });

                dyad_start = i;
                dyad_start_seq = turn.seq;
                dyad_time = turn.time_created;
                dyad_buf.clear();
            }

            if dyad_buf.is_empty() {
                dyad_start_seq = turn.seq;
                dyad_time = turn.time_created;
            }
            dyad_end_seq = turn.seq;
            dyad_buf.push_str(&format!("{}: {}\n", turn.role, turn.clean_text));
        }

        if !dyad_buf.is_empty() {
            let token_count = count_tokens(&dyad_buf);
            let hash = compute_hash(&dyad_buf);
            chunks.push(VaultChunk {
                chunk_id: format!("{}-t1-{}", session_id, dyad_start),
                session_id: session_id.to_string(),
                tier: 1,
                start_seq: dyad_start_seq,
                end_seq: dyad_end_seq,
                token_count,
                content_hash: hash,
                chunk_text: dyad_buf,
                time_created: dyad_time,
            });
        }

        // Tier 2: Epistemic Episodes (Group turns in chunks of ~800-1500 tokens or milestone cut-points)
        let mut ep_buf = String::new();
        let mut ep_start_seq = turns[0].seq;
        let mut ep_index = 0;
        let mut ep_time = turns[0].time_created;

        for turn in turns {
            let addition = format!("[{}] {}\n", turn.turn_type, turn.clean_text);
            if count_tokens(&ep_buf) + count_tokens(&addition) > 1000 && !ep_buf.is_empty() {
                let token_count = count_tokens(&ep_buf);
                let hash = compute_hash(&ep_buf);
                chunks.push(VaultChunk {
                    chunk_id: format!("{}-t2-{}", session_id, ep_index),
                    session_id: session_id.to_string(),
                    tier: 2,
                    start_seq: ep_start_seq,
                    end_seq: turn.seq - 1,
                    token_count,
                    content_hash: hash,
                    chunk_text: ep_buf.clone(),
                    time_created: ep_time,
                });
                ep_index += 1;
                ep_start_seq = turn.seq;
                ep_time = turn.time_created;
                ep_buf.clear();
            }
            ep_buf.push_str(&addition);
        }

        if !ep_buf.is_empty() {
            let token_count = count_tokens(&ep_buf);
            let hash = compute_hash(&ep_buf);
            chunks.push(VaultChunk {
                chunk_id: format!("{}-t2-{}", session_id, ep_index),
                session_id: session_id.to_string(),
                tier: 2,
                start_seq: ep_start_seq,
                end_seq: turns.last().map(|t| t.seq).unwrap_or(0),
                token_count,
                content_hash: hash,
                chunk_text: ep_buf,
                time_created: ep_time,
            });
        }

        // Tier 3: Session Gestalt Digest
        let mut digest = format!("Session: {}\nTitle: {}\nTurns: {}\nKey Points:\n", session_id, session_title, turns.len());
        for turn in turns {
            if turn.importance >= 0.75 {
                digest.push_str(&format!("- [{}] {}\n", turn.turn_type, summarize_turn(&turn.clean_text, 140)));
            }
        }
        let digest_tokens = count_tokens(&digest);
        let digest_hash = compute_hash(&digest);
        chunks.push(VaultChunk {
            chunk_id: format!("{}-t3-digest", session_id),
            session_id: session_id.to_string(),
            tier: 3,
            start_seq: turns.first().map(|t| t.seq).unwrap_or(0),
            end_seq: turns.last().map(|t| t.seq).unwrap_or(0),
            token_count: digest_tokens,
            content_hash: digest_hash,
            chunk_text: digest,
            time_created: turns.first().map(|t| t.time_created).unwrap_or(0),
        });

        chunks
    }
}

fn count_tokens(text: &str) -> usize {
    text.split_whitespace().count()
}

fn compute_hash(text: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(text.as_bytes());
    format!("{:x}", hasher.finalize())
}

fn summarize_turn(text: &str, max_len: usize) -> String {
    let first_line = text.lines().next().unwrap_or("").trim();
    if first_line.len() > max_len {
        let truncated = crate::safe_truncate(first_line, max_len);
        format!("{}...", truncated)
    } else {
        first_line.to_string()
    }
}
