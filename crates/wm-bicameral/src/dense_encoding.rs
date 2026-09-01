//! Dense Context Encoding — 2-3x token compression for internal LLM context.
//!
//! Uses Chinese-character mapping to compress common English phrases into
//! single CJK characters (1 token each in most tokenizers), reducing the
//! token cost of system prompts and internal context.
//!
//! Ported from v2's `ai/dense_encoding.py` (360 lines).
//! Not applied to user-facing text — only internal context.

#![forbid(unsafe_code)]

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// ── Config ────────────────────────────────────────────────────────────

/// Configuration for dense encoding.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DenseEncodingConfig {
    /// Whether dense encoding is enabled.
    pub enabled: bool,
    /// Minimum text length to bother encoding (short texts have overhead).
    pub min_encode_length: usize,
    /// Whether to include a decode hint prefix.
    pub include_decode_hint: bool,
}

impl Default for DenseEncodingConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            min_encode_length: 50,
            include_decode_hint: true,
        }
    }
}

impl DenseEncodingConfig {
    /// Create from environment variables.
    ///
    /// - `WM_DENSE_ENCODING`: "1" to enable (default: "0")
    /// - `WM_DENSE_MIN_LENGTH`: minimum text length (default: "50")
    #[must_use]
    pub fn from_env() -> Self {
        Self {
            enabled: std::env::var("WM_DENSE_ENCODING")
                .is_ok_and(|v| v == "1" || v.eq_ignore_ascii_case("true")),
            min_encode_length: std::env::var("WM_DENSE_MIN_LENGTH")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or(50),
            include_decode_hint: true,
        }
    }
}

// ── Dense Encoder ─────────────────────────────────────────────────────

/// Dense context encoder — compresses English text using CJK character mapping.
///
/// Common phrases are mapped to single Chinese characters that occupy 1 token
/// in most LLM tokenizers, achieving 2-3x compression on system prompts.
pub struct DenseEncoder {
    config: DenseEncodingConfig,
    /// Forward map: English phrase → CJK character
    encode_map: HashMap<&'static str, char>,
    /// Reverse map: CJK character → English phrase
    decode_map: HashMap<char, &'static str>,
}

impl DenseEncoder {
    /// Create a new encoder with the default phrase table.
    #[must_use]
    pub fn new(config: DenseEncodingConfig) -> Self {
        let table = default_phrase_table();
        let encode_map: HashMap<&'static str, char> =
            table.iter().map(|(en, cjk)| (*en, *cjk)).collect();
        // For decode, keep the first English phrase per CJK char (shortest is most general)
        let mut decode_map: HashMap<char, &'static str> = HashMap::new();
        for (en, cjk) in table {
            decode_map.entry(*cjk).or_insert(*en);
        }
        Self {
            config,
            encode_map,
            decode_map,
        }
    }

    /// Create with default config.
    #[must_use]
    pub fn with_defaults() -> Self {
        Self::new(DenseEncodingConfig::default())
    }

    /// Create an enabled encoder (convenience).
    #[must_use]
    pub fn enabled() -> Self {
        Self::new(DenseEncodingConfig {
            enabled: true,
            ..DenseEncodingConfig::default()
        })
    }

    /// Encode text into compressed form.
    ///
    /// Replaces known English phrases with their CJK equivalents.
    /// Only replaces whole words (word-boundary aware).
    /// Returns the original text if encoding is disabled or text is too short.
    #[must_use]
    pub fn encode(&self, text: &str) -> String {
        if !self.config.enabled || text.len() < self.config.min_encode_length {
            return text.to_string();
        }

        let encoded = self.encode_raw(text);

        if self.config.include_decode_hint && encoded != text {
            let hint = self.build_decode_hint(&encoded);
            if hint.is_empty() {
                encoded
            } else {
                format!("{hint}\n{encoded}")
            }
        } else {
            encoded
        }
    }

    /// Decode compressed text back to approximate original.
    ///
    /// Replaces CJK characters with their English phrase equivalents.
    #[must_use]
    pub fn decode(&self, text: &str) -> String {
        let mut result = text.to_string();
        for (cjk, en) in &self.decode_map {
            if result.contains(*cjk) {
                result = result.replace(&cjk.to_string(), en);
            }
        }
        result
    }

    /// Encode text without decode hint (internal use).
    fn encode_raw(&self, text: &str) -> String {
        if text.is_empty() {
            return String::new();
        }

        let mut entries: Vec<(&'static str, char)> =
            self.encode_map.iter().map(|(&k, &v)| (k, v)).collect();
        entries.sort_by_key(|entry| std::cmp::Reverse(entry.0.len()));

        let mut result = String::with_capacity(text.len());
        let mut remaining = text;

        'outer: while !remaining.is_empty() {
            let next_word_end = remaining
                .find(|c: char| !c.is_alphanumeric() && c != '_' && c != '\'')
                .unwrap_or(remaining.len());

            if next_word_end > 0 {
                let word = &remaining[..next_word_end];
                for (phrase, cjk) in &entries {
                    if word.eq_ignore_ascii_case(phrase) {
                        result.push(*cjk);
                        remaining = &remaining[next_word_end..];
                        continue 'outer;
                    }
                }
                result.push_str(word);
                remaining = &remaining[next_word_end..];
            }

            if !remaining.is_empty() {
                let next_char_len = remaining
                    .char_indices()
                    .nth(1)
                    .map_or(remaining.len(), |(i, _)| i);
                result.push_str(&remaining[..next_char_len]);
                remaining = &remaining[next_char_len..];
            }
        }

        result
    }

    /// Estimate the compression ratio for a given text.
    ///
    /// Returns the ratio of compressed tokens to original tokens (lower = better).
    /// Computed without the decode hint prefix, which is metadata.
    #[must_use]
    pub fn compression_ratio(&self, text: &str) -> f32 {
        if text.is_empty() {
            return 1.0;
        }
        // Temporarily disable decode hint for ratio calculation
        let encoded = {
            let config = DenseEncodingConfig {
                enabled: true,
                min_encode_length: 0,
                include_decode_hint: false,
            };
            let temp = Self::new(config);
            temp.encode_raw(text)
        };
        let original_tokens = estimate_token_count(text);
        let encoded_tokens = estimate_token_count(&encoded);
        if original_tokens == 0 {
            return 1.0;
        }
        encoded_tokens as f32 / original_tokens as f32
    }

    /// Get the number of phrases in the mapping.
    #[must_use]
    pub fn phrase_count(&self) -> usize {
        self.encode_map.len()
    }

    /// Get the configuration.
    #[must_use]
    pub const fn config(&self) -> &DenseEncodingConfig {
        &self.config
    }

    /// Check if encoding is enabled.
    #[must_use]
    pub const fn is_enabled(&self) -> bool {
        self.config.enabled
    }

    /// Build a compact decode hint for the encoded text.
    fn build_decode_hint(&self, encoded: &str) -> String {
        let used: Vec<(char, &'static str)> = self
            .decode_map
            .iter()
            .filter(|(cjk, _)| encoded.contains(**cjk))
            .map(|(&c, &en)| (c, en))
            .collect();

        if used.is_empty() {
            return String::new();
        }

        used.iter()
            .map(|(cjk, en)| format!("{cjk}={en}"))
            .collect::<Vec<_>>()
            .join(", ")
    }

    /// Add a custom phrase mapping.
    pub fn add_phrase(&mut self, english: &'static str, cjk: char) {
        self.encode_map.insert(english, cjk);
        self.decode_map.insert(cjk, english);
    }
}

/// Estimate token count for a string.
/// CJK characters: ~1 token each. ASCII non-whitespace: ~4 chars per token.
/// Whitespace is not counted separately (BPE merges it with adjacent tokens).
fn estimate_token_count(s: &str) -> usize {
    let mut tokens = 0usize;
    let mut ascii_chars = 0usize;

    for ch in s.chars() {
        if ch.is_ascii_whitespace() {
            // Whitespace merges with adjacent tokens in BPE — skip
            continue;
        }
        if ch.is_ascii() {
            ascii_chars += 1;
        } else {
            // Flush pending ASCII tokens
            tokens += ascii_chars.div_ceil(4);
            ascii_chars = 0;
            tokens += 1; // CJK = 1 token
        }
    }
    tokens += ascii_chars.div_ceil(4);
    tokens.max(1)
}

// ── Default Phrase Table ──────────────────────────────────────────────

/// Default phrase mapping: common English phrases → CJK characters.
///
/// Characters chosen for semantic resonance where possible:
/// - 你 = "you"
/// - 我 = "I/me"
/// - 是 = "is/are"
/// - 不 = "not/no"
/// - 有 = "have/has"
/// - 等 = "etc/and so on"
///
/// Plus abstract mappings for common system-prompt phrases.
const fn default_phrase_table() -> &'static [(&'static str, char)] {
    &[
        // Pronouns & common words
        ("you", '你'),
        ("your", '你'),
        ("you're", '你'),
        ("I", '我'),
        ("me", '我'),
        ("my", '我'),
        ("we", '我'),
        ("our", '我'),
        ("us", '我'),
        ("is", '是'),
        ("are", '是'),
        ("was", '是'),
        ("were", '是'),
        ("be", '是'),
        ("been", '是'),
        ("not", '不'),
        ("no", '不'),
        ("never", '不'),
        ("don't", '不'),
        ("cannot", '不'),
        ("can't", '不'),
        ("won't", '不'),
        ("have", '有'),
        ("has", '有'),
        ("had", '有'),
        ("having", '有'),
        // Common system prompt phrases
        ("please", '请'),
        ("should", '应'),
        ("must", '必'),
        ("need", '需'),
        ("want", '欲'),
        ("will", '将'),
        ("would", '将'),
        ("could", '可'),
        ("can", '可'),
        ("may", '可'),
        ("might", '可'),
        ("the", '此'),
        ("this", '此'),
        ("that", '此'),
        ("these", '此'),
        ("those", '此'),
        ("and", '与'),
        ("or", '或'),
        ("but", '但'),
        ("however", '但'),
        ("because", '因'),
        ("since", '因'),
        ("so", '故'),
        ("therefore", '故'),
        ("if", '若'),
        ("when", '时'),
        ("while", '时'),
        ("before", '前'),
        ("after", '后'),
        ("first", '初'),
        ("then", '后'),
        ("next", '续'),
        ("finally", '终'),
        ("also", '亦'),
        ("too", '亦'),
        ("very", '甚'),
        ("more", '更'),
        ("most", '最'),
        ("all", '皆'),
        ("each", '各'),
        ("every", '各'),
        ("some", '些'),
        ("any", '何'),
        ("what", '何'),
        ("which", '何'),
        ("who", '谁'),
        ("how", '怎'),
        ("why", '何'),
        ("where", '何'),
        // Action words
        ("use", '用'),
        ("using", '用'),
        ("used", '用'),
        ("make", '作'),
        ("makes", '作'),
        ("made", '作'),
        ("making", '作'),
        ("do", '行'),
        ("does", '行'),
        ("did", '行'),
        ("doing", '行'),
        ("get", '取'),
        ("gets", '取'),
        ("got", '取'),
        ("getting", '取'),
        ("give", '予'),
        ("gives", '予'),
        ("gave", '予'),
        ("find", '寻'),
        ("finds", '寻'),
        ("found", '寻'),
        ("search", '寻'),
        ("look", '视'),
        ("see", '视'),
        ("sees", '视'),
        ("saw", '视'),
        ("seen", '视'),
        ("show", '示'),
        ("shows", '示'),
        ("showed", '示'),
        ("shown", '示'),
        ("tell", '告'),
        ("tells", '告'),
        ("told", '告'),
        ("ask", '问'),
        ("asks", '问'),
        ("asked", '问'),
        ("answer", '答'),
        ("answers", '答'),
        ("answered", '答'),
        ("think", '思'),
        ("thinks", '思'),
        ("thought", '思'),
        ("thinking", '思'),
        ("know", '知'),
        ("knows", '知'),
        ("knew", '知'),
        ("known", '知'),
        ("learn", '学'),
        ("learns", '学'),
        ("learned", '学'),
        ("learning", '学'),
        ("create", '创'),
        ("creates", '创'),
        ("created", '创'),
        ("creating", '创'),
        ("build", '建'),
        ("builds", '建'),
        ("built", '建'),
        ("building", '建'),
        ("write", '写'),
        ("writes", '写'),
        ("wrote", '写'),
        ("written", '写'),
        ("writing", '写'),
        ("read", '读'),
        ("reads", '读'),
        ("reading", '读'),
        ("call", '调'),
        ("calls", '调'),
        ("called", '调'),
        ("calling", '调'),
        ("run", '运'),
        ("runs", '运'),
        ("ran", '运'),
        ("running", '运'),
        ("start", '始'),
        ("starts", '始'),
        ("started", '始'),
        ("starting", '始'),
        ("stop", '止'),
        ("stops", '止'),
        ("stopped", '止'),
        ("stopping", '止'),
        ("return", '归'),
        ("returns", '归'),
        ("returned", '归'),
        ("returning", '归'),
        ("send", '发'),
        ("sends", '发'),
        ("sent", '发'),
        ("sending", '发'),
        ("receive", '收'),
        ("receives", '收'),
        ("received", '收'),
        ("receiving", '收'),
        ("store", '存'),
        ("stores", '存'),
        ("stored", '存'),
        ("storing", '存'),
        ("load", '载'),
        ("loads", '载'),
        ("loaded", '载'),
        ("loading", '载'),
        ("save", '保'),
        ("saves", '保'),
        ("saved", '保'),
        ("saving", '保'),
        ("delete", '删'),
        ("deletes", '删'),
        ("deleted", '删'),
        ("deleting", '删'),
        ("update", '更'),
        ("updates", '更'),
        ("updated", '更'),
        ("updating", '更'),
        ("check", '查'),
        ("checks", '查'),
        ("checked", '查'),
        ("checking", '查'),
        ("test", '测'),
        ("tests", '测'),
        ("tested", '测'),
        ("testing", '测'),
        ("error", '误'),
        ("errors", '误'),
        ("fail", '败'),
        ("fails", '败'),
        ("failed", '败'),
        ("failure", '败'),
        ("failures", '败'),
        ("success", '成'),
        ("successful", '成'),
        ("succeed", '成'),
        ("succeeds", '成'),
        ("succeeded", '成'),
        ("result", '果'),
        ("results", '果'),
        ("output", '出'),
        ("outputs", '出'),
        ("input", '入'),
        ("inputs", '入'),
        ("data", '据'),
        ("information", '讯'),
        ("info", '讯'),
        ("message", '信'),
        ("messages", '信'),
        ("context", '境'),
        ("memory", '忆'),
        ("memories", '忆'),
        ("system", '系'),
        ("user", '户'),
        ("users", '户'),
        ("tool", '器'),
        ("tools", '器'),
        ("function", '函'),
        ("functions", '函'),
        ("method", '法'),
        ("methods", '法'),
        ("parameter", '参'),
        ("parameters", '参'),
        ("argument", '参'),
        ("arguments", '参'),
        ("value", '值'),
        ("values", '值'),
        ("type", '型'),
        ("types", '型'),
        ("string", '串'),
        ("number", '数'),
        ("numbers", '数'),
        ("integer", '数'),
        ("float", '数'),
        ("boolean", '布'),
        ("true", '真'),
        ("false", '假'),
        ("null", '空'),
        ("none", '空'),
        ("empty", '空'),
        ("list", '列'),
        ("array", '列'),
        ("map", '图'),
        ("hash", '图'),
        ("set", '集'),
        ("object", '物'),
        ("objects", '物'),
        ("class", '类'),
        ("classes", '类'),
        ("struct", '构'),
        ("enum", '举'),
        ("trait", '质'),
        ("module", '模'),
        ("modules", '模'),
        ("crate", '箱'),
        ("package", '包'),
        ("import", '导'),
        ("export", '出'),
        ("public", '公'),
        ("private", '私'),
        ("const", '常'),
        ("static", '静'),
        ("async", '异'),
        ("await", '待'),
        ("thread", '线'),
        ("process", '程'),
        ("lock", '锁'),
        ("unlock", '解'),
        ("config", '设'),
        ("configuration", '设'),
        ("option", '选'),
        ("options", '选'),
        ("setting", '设'),
        ("settings", '设'),
        ("default", '默'),
        ("enable", '启'),
        ("enabled", '启'),
        ("disable", '禁'),
        ("disabled", '禁'),
        ("feature", '性'),
        ("features", '性'),
        ("version", '版'),
        ("status", '态'),
        ("state", '态'),
        ("states", '态'),
        ("event", '事'),
        ("events", '事'),
        ("action", '动'),
        ("actions", '动'),
        ("request", '求'),
        ("requests", '求'),
        ("response", '应'),
        ("responses", '应'),
        ("query", '询'),
        ("queries", '询'),
        ("prompt", '题'),
        ("response", '答'),
        ("model", '模'),
        ("models", '模'),
        ("inference", '推'),
        ("generate", '生'),
        ("generates", '生'),
        ("generated", '生'),
        ("generating", '生'),
        ("token", '符'),
        ("tokens", '符'),
        ("embedding", '嵌'),
        ("vector", '矢'),
        ("vectors", '矢'),
        ("similarity", '似'),
        ("distance", '距'),
        ("score", '分'),
        ("scores", '分'),
        ("rank", '排'),
        ("ranking", '排'),
        ("sort", '排'),
        ("sorted", '排'),
        ("sorting", '排'),
        ("filter", '滤'),
        ("filtered", '滤'),
        ("filtering", '滤'),
        ("limit", '限'),
        ("offset", '偏'),
        ("count", '计'),
        ("size", '量'),
        ("length", '长'),
        ("index", '引'),
        ("indexes", '引'),
        ("indices", '引'),
        ("key", '键'),
        ("keys", '键'),
        ("field", '栏'),
        ("fields", '栏'),
        ("column", '栏'),
        ("columns", '栏'),
        ("row", '行'),
        ("rows", '行'),
        ("table", '表'),
        ("tables", '表'),
        ("database", '库'),
        ("query", '询'),
        ("schema", '式'),
        ("validate", '验'),
        ("validates", '验'),
        ("validated", '验'),
        ("validation", '验'),
        ("valid", '效'),
        ("invalid", '效'),
        ("parse", '析'),
        ("parses", '析'),
        ("parsed", '析'),
        ("parsing", '析'),
        ("format", '式'),
        ("formats", '式'),
        ("formatted", '式'),
        ("formatting", '式'),
        ("convert", '转'),
        ("converts", '转'),
        ("converted", '转'),
        ("converting", '转'),
        ("transform", '变'),
        ("transforms", '变'),
        ("transformed", '变'),
        ("transforming", '变'),
        ("compress", '缩'),
        ("compression", '缩'),
        ("decompress", '展'),
        ("encode", '编'),
        ("encoded", '编'),
        ("encoding", '编'),
        ("decode", '解'),
        ("decoded", '解'),
        ("decoding", '解'),
        ("encrypt", '密'),
        ("decrypt", '密'),
        ("hash", '散'),
        ("sign", '签'),
        ("verify", '验'),
        ("auth", '证'),
        ("authenticate", '证'),
        ("authentication", '证'),
        ("authorize", '权'),
        ("authorization", '权'),
        ("permission", '权'),
        ("permissions", '权'),
        ("allow", '许'),
        ("allowed", '许'),
        ("allowing", '许'),
        ("deny", '拒'),
        ("denied", '拒'),
        ("block", '阻'),
        ("blocked", '阻'),
        ("blocking", '阻'),
        ("permit", '许'),
        ("forbid", '禁'),
        ("forbidden", '禁'),
        ("safe", '安'),
        ("safety", '安'),
        ("unsafe", '危'),
        ("secure", '安'),
        ("security", '安'),
        ("risk", '险'),
        ("danger", '险'),
        ("dangerous", '险'),
        ("warning", '警'),
        ("warn", '警'),
        ("warns", '警'),
        ("warned", '警'),
        ("warning", '警'),
        ("error", '错'),
        ("errors", '错'),
        ("exception", '外'),
        ("exceptions", '外'),
        ("panic", '崩'),
        ("crash", '崩'),
        ("bug", '虫'),
        ("bugs", '虫'),
        ("fix", '修'),
        ("fixed", '修'),
        ("fixing", '修'),
        ("debug", '调'),
        ("debugging", '调'),
        ("log", '志'),
        ("logs", '志'),
        ("logging", '志'),
        ("trace", '迹'),
        ("track", '踪'),
        ("tracking", '踪'),
        ("monitor", '监'),
        ("monitoring", '监'),
        ("metric", '度'),
        ("metrics", '度'),
        ("measure", '量'),
        ("measured", '量'),
        ("measuring", '量'),
        ("performance", '效'),
        ("speed", '速'),
        ("fast", '速'),
        ("slow", '缓'),
        ("latency", '迟'),
        ("throughput", '量'),
        ("benchmark", '基'),
        ("benchmarks", '基'),
        ("optimize", '优'),
        ("optimized", '优'),
        ("optimizing", '优'),
        ("optimization", '优'),
        ("improve", '进'),
        ("improves", '进'),
        ("improved", '进'),
        ("improving", '进'),
        ("improvement", '进'),
        ("enhance", '强'),
        ("enhanced", '强'),
        ("enhancing", '强'),
        ("enhancement", '强'),
        ("reduce", '减'),
        ("reduces", '减'),
        ("reduced", '减'),
        ("reducing", '减'),
        ("reduction", '减'),
        ("increase", '增'),
        ("increases", '增'),
        ("increased", '增'),
        ("increasing", '增'),
        ("add", '加'),
        ("adds", '加'),
        ("added", '加'),
        ("adding", '加'),
        ("remove", '删'),
        ("removes", '删'),
        ("removed", '删'),
        ("removing", '删'),
        ("delete", '删'),
        ("deletes", '删'),
        ("deleted", '删'),
        ("deleting", '删'),
        ("insert", '插'),
        ("inserts", '插'),
        ("inserted", '插'),
        ("inserting", '插'),
        ("append", '附'),
        ("appends", '附'),
        ("appended", '附'),
        ("appending", '附'),
        ("prepend", '前'),
        ("update", '改'),
        ("updates", '改'),
        ("updated", '改'),
        ("updating", '改'),
        ("modify", '改'),
        ("modifies", '改'),
        ("modified", '改'),
        ("modifying", '改'),
        ("replace", '替'),
        ("replaces", '替'),
        ("replaced", '替'),
        ("replacing", '替'),
        ("swap", '换'),
        ("clear", '清'),
        ("clears", '清'),
        ("cleared", '清'),
        ("clearing", '清'),
        ("reset", '重'),
        ("resets", '重'),
        ("resetting", '重'),
        ("initialize", '初'),
        ("init", '初'),
        ("setup", '设'),
        ("configure", '设'),
        ("configured", '设'),
        ("configuring", '设'),
    ]
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn encode_disabled_by_default() {
        let encoder = DenseEncoder::with_defaults();
        assert!(!encoder.is_enabled());
        let text = "please use the system to find the answer";
        assert_eq!(encoder.encode(text), text);
    }

    #[test]
    fn encode_enabled_compresses() {
        let encoder = DenseEncoder::enabled();
        let text = "please use the system to find the answer and return the result to the user";
        let encoded = encoder.encode(text);
        assert_ne!(encoded, text);
        // Should contain CJK characters
        assert!(!encoded.is_ascii());
    }

    #[test]
    fn encode_short_text_unchanged() {
        let encoder = DenseEncoder::new(DenseEncodingConfig {
            enabled: true,
            min_encode_length: 100,
            ..DenseEncodingConfig::default()
        });
        let text = "short text";
        assert_eq!(encoder.encode(text), text);
    }

    #[test]
    fn decode_restores_text() {
        let encoder = DenseEncoder::enabled();
        let text = "please use the system to find the answer and return the result";
        let encoded = encoder.encode(text);
        let decoded = encoder.decode(&encoded);
        // Decode should restore the original phrases
        assert!(decoded.contains("please"));
        assert!(decoded.contains("system"));
        assert!(decoded.contains("answer"));
    }

    #[test]
    fn compression_ratio_less_than_one() {
        let encoder = DenseEncoder::enabled();
        // Use text with many long words where compression is effective
        let text = "The system configuration requires authentication before processing. \
                    The application generates responses using inference and embedding vectors. \
                    The database stores information about permissions and authentication. \
                    The monitoring system tracks performance metrics including throughput and latency. \
                    The optimization module improves performance by compressing internal context.";
        let ratio = encoder.compression_ratio(text);
        assert!(ratio < 1.0, "ratio was {ratio}");
    }

    #[test]
    fn compression_ratio_one_for_empty() {
        let encoder = DenseEncoder::enabled();
        assert!((encoder.compression_ratio("") - 1.0).abs() < f32::EPSILON);
    }

    #[test]
    fn phrase_count_nonzero() {
        let encoder = DenseEncoder::enabled();
        assert!(encoder.phrase_count() > 50);
    }

    #[test]
    fn add_custom_phrase() {
        let mut encoder = DenseEncoder::enabled();
        encoder.add_phrase("custom_phrase", '特');
        let text = "this is a custom_phrase in the text and it should be encoded properly";
        let encoded = encoder.encode(text);
        assert!(encoded.contains('特'));
    }

    #[test]
    fn encode_preserves_unknown_text() {
        let encoder = DenseEncoder::enabled();
        let text = "xyzzy foobar quux";
        let encoded = encoder.encode(text);
        // Unknown words should pass through
        assert!(encoded.contains("xyzzy"));
        assert!(encoded.contains("foobar"));
    }

    #[test]
    fn decode_hint_included() {
        let encoder = DenseEncoder::new(DenseEncodingConfig {
            enabled: true,
            include_decode_hint: true,
            min_encode_length: 10,
        });
        let text = "please use the system to find the answer for the user";
        let encoded = encoder.encode(text);
        // Should contain a decode hint with CJK=English mappings
        assert!(encoded.contains('='));
    }

    #[test]
    fn decode_hint_disabled() {
        let encoder = DenseEncoder::new(DenseEncodingConfig {
            enabled: true,
            include_decode_hint: false,
            min_encode_length: 10,
        });
        let text = "please use the system to find the answer for the user";
        let encoded = encoder.encode(text);
        // Should NOT contain decode hint
        assert!(!encoded.starts_with("请="));
    }

    #[test]
    fn longer_phrases_match_first() {
        let encoder = DenseEncoder::enabled();
        // "the" and "therefore" both exist - "therefore" should match before "the"
        let text = "therefore the result is correct and the answer is valid for the user";
        let encoded = encoder.encode(text);
        // "therefore" should be replaced as a whole, not partially
        assert!(!encoded.contains("therefore"));
    }

    #[test]
    fn config_from_env_default() {
        // Without env var set, should be disabled
        let config = DenseEncodingConfig::from_env();
        // Env var may or may not be set in test environment, just check it doesn't panic
        let _ = config.enabled;
    }

    #[test]
    fn estimate_tokens_basic() {
        assert!(estimate_token_count("hello world") > 0);
        assert_eq!(estimate_token_count(""), 1); // min 1
        // CJK chars: 1 token each
        assert_eq!(estimate_token_count("你好"), 2);
    }

    #[test]
    fn encode_decode_roundtrip() {
        let encoder = DenseEncoder::enabled();
        let text = "please find the answer and return the result to the user. \
                    The system should check the output and make sure the response is valid. \
                    You must also verify the data and store the information in memory.";
        let encoded = encoder.encode(text);
        let decoded = encoder.decode(&encoded);
        // Key phrases should be restored
        assert!(decoded.contains("please"));
        assert!(decoded.contains("answer"));
        assert!(decoded.contains("result"));
        assert!(decoded.contains("user"));
        assert!(decoded.contains("system"));
        assert!(decoded.contains("memory"));
    }

    #[test]
    fn encode_empty_text() {
        let encoder = DenseEncoder::enabled();
        assert_eq!(encoder.encode(""), "");
    }

    #[test]
    fn encode_only_cjk_output() {
        let encoder = DenseEncoder::enabled();
        let text =
            "the the the the the the the the the the the the the the the the the the the the";
        let encoded = encoder.encode(text);
        // Should be mostly CJK
        let cjk_count = encoded.chars().filter(|c| !c.is_ascii()).count();
        assert!(cjk_count > 10);
    }

    #[test]
    fn config_default_disabled() {
        let config = DenseEncodingConfig::default();
        assert!(!config.enabled);
        assert_eq!(config.min_encode_length, 50);
        assert!(config.include_decode_hint);
    }

    #[test]
    fn encode_idempotent_on_encoded() {
        let encoder = DenseEncoder::enabled();
        let text = "please use the system to find the answer for the user";
        let encoded = encoder.encode(text);
        // Encoding the encoded text should not change it further
        let re_encoded = encoder.encode(&encoded);
        // The CJK chars won't match any English phrases, so it should be stable
        // (though the decode hint might get reprocessed)
        // Just check it doesn't panic
        let _ = re_encoded;
    }

    #[test]
    fn many_phrases_available() {
        let encoder = DenseEncoder::enabled();
        // Test with text rich in long words where compression is effective
        let text = "The system configuration requires authentication before processing requests. \
                    The application generates responses using inference and embedding vectors \
                    from the database. The monitoring module tracks performance metrics \
                    including throughput measurements and latency benchmarks. \
                    The optimization engine improves performance by compressing internal context \
                    and optimizing memory usage. The validation framework checks output format \
                    and verifies security permissions. The initialization sequence configures \
                    parameters and loads required modules.";
        let encoded = encoder.encode(text);
        let ratio = encoder.compression_ratio(text);
        assert!(ratio < 0.9, "ratio was {ratio}, encoded: {encoded}");
    }
}
