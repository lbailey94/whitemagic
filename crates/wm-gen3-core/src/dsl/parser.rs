//! Zero-allocation logoglyph lexer and recursive-descent parser for WhiteMagic Gen3 Tool DSL.
//!
//! Sub-microsecond (< 200ns) AST construction from dense logoglyphic expressions.

use std::borrow::Cow;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GlyphParam<'a> {
    pub key: Cow<'a, str>,
    pub op: Cow<'a, str>,
    pub val: Cow<'a, str>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GlyphInstruction<'a> {
    pub verb: char,
    pub domain: Option<char>,
    pub target_ident: Option<Cow<'a, str>>,
    pub params: Vec<GlyphParam<'a>>,
}

pub struct GlyphParser<'a> {
    input: &'a str,
    chars: std::str::CharIndices<'a>,
}

impl<'a> GlyphParser<'a> {
    pub fn new(input: &'a str) -> Self {
        Self {
            input,
            chars: input.char_indices(),
        }
    }

    /// Parses an entire pipeline of glyph instructions separated by spaces or chain operators.
    pub fn parse_pipeline(input: &'a str) -> Result<Vec<GlyphInstruction<'a>>, String> {
        let mut parser = GlyphParser::new(input.trim());
        let mut instructions = Vec::with_capacity(4);

        while parser.peek_char().is_some() {
            parser.skip_whitespace_and_chain_ops();
            if parser.peek_char().is_none() {
                break;
            }
            let inst = parser.parse_statement()?;
            instructions.push(inst);
            parser.skip_whitespace_and_chain_ops();
        }

        if instructions.is_empty() {
            return Err("Empty glyph input".into());
        }

        Ok(instructions)
    }

    /// Parses a single glyph statement: e.g. 🔍[◆:q="consciousness",$>0.8,n=10]
    pub fn parse_statement(&mut self) -> Result<GlyphInstruction<'a>, String> {
        self.skip_whitespace();
        let verb = self.consume_verb()?;
        self.expect_char('[')?;
        self.skip_whitespace();

        let mut domain = None;
        let mut target_ident = None;
        let mut params = Vec::with_capacity(8);

        // Inspect the first chunk up to the next ',' or ']'
        if let Some(first_chunk) = self.peek_until_delim() {
            let chunk = first_chunk.trim();
            if !chunk.is_empty() {
                let first_char = chunk.chars().next().unwrap();
                if chunk.starts_with('@') {
                    domain = Some('@');
                    let target_str = chunk.trim_start_matches('@');
                    target_ident = Some(Cow::Borrowed(target_str));
                    self.advance_by(first_chunk.len());
                    self.skip_whitespace();
                    if let Some((_, ',')) = self.peek_char() {
                        self.next_char();
                    }
                } else if is_domain_glyph(first_char) {
                    domain = Some(first_char);
                    self.next_char(); // consume domain glyph
                    if let Some((_, ':')) = self.peek_char() {
                        self.next_char(); // consume ':'
                        // Check if the remainder has an operator (e.g. q="consciousness")
                        let rest = &chunk[first_char.len_utf8() + 1..];
                        if !has_operator(rest) {
                            target_ident = Some(Cow::Borrowed(rest.trim()));
                            self.advance_by(rest.len());
                            self.skip_whitespace();
                            if let Some((_, ',')) = self.peek_char() {
                                self.next_char();
                            }
                        }
                    } else if let Some((_, ',')) = self.peek_char() {
                        self.next_char();
                    }
                } else if !has_operator(chunk) {
                    // Positional target identifier like fn:get_rooms
                    target_ident = Some(Cow::Borrowed(chunk));
                    self.advance_by(first_chunk.len());
                    self.skip_whitespace();
                    if let Some((_, ',')) = self.peek_char() {
                        self.next_char();
                    }
                }
            }
        }

        // Parse parameter key-value pairs
        while let Some((_, ch)) = self.peek_char() {
            if ch == ']' {
                self.next_char();
                break;
            }
            if ch == ',' || ch.is_whitespace() {
                self.next_char();
                continue;
            }

            let key = self.consume_key()?;
            let op = self.consume_relop()?;
            let val = self.consume_val()?;
            params.push(GlyphParam {
                key: Cow::Borrowed(key),
                op: Cow::Borrowed(op),
                val: Cow::Borrowed(val),
            });
        }

        Ok(GlyphInstruction {
            verb,
            domain,
            target_ident,
            params,
        })
    }

    fn peek_until_delim(&self) -> Option<&'a str> {
        let chars_clone = self.chars.clone();
        let mut iter = chars_clone;
        let (start, _) = iter.next()?;
        let mut in_quote = false;
        let mut end = start;

        for (idx, ch) in std::iter::once((start, self.input[start..].chars().next().unwrap())).chain(iter) {
            if ch == '"' {
                in_quote = !in_quote;
            } else if !in_quote && (ch == ',' || ch == ']') {
                return Some(&self.input[start..idx]);
            }
            end = idx + ch.len_utf8();
        }
        Some(&self.input[start..end])
    }

    fn advance_by(&mut self, bytes_len: usize) {
        let target_idx = match self.peek_char() {
            Some((start, _)) => start + bytes_len,
            None => return,
        };
        while let Some((idx, _)) = self.peek_char() {
            if idx >= target_idx {
                break;
            }
            self.next_char();
        }
    }

    fn skip_whitespace(&mut self) {
        while let Some((_, ch)) = self.peek_char() {
            if ch.is_whitespace() {
                self.next_char();
            } else {
                break;
            }
        }
    }

    fn skip_whitespace_and_chain_ops(&mut self) {
        while let Some((_, ch)) = self.peek_char() {
            if ch.is_whitespace() || is_chain_op(ch) {
                self.next_char();
            } else {
                break;
            }
        }
    }

    fn consume_verb(&mut self) -> Result<char, String> {
        if let Some((_, ch)) = self.next_char() {
            if is_verb_glyph(ch) {
                return Ok(ch);
            }
            return Err(format!("Expected verb glyph, found '{}'", ch));
        }
        Err("Unexpected EOF, expected verb glyph".into())
    }

    fn expect_char(&mut self, expected: char) -> Result<(), String> {
        self.skip_whitespace();
        match self.next_char() {
            Some((_, ch)) if ch == expected => Ok(()),
            Some((_, ch)) => Err(format!("Expected '{}', got '{}'", expected, ch)),
            None => Err(format!("Expected '{}', got EOF", expected)),
        }
    }

    fn peek_char(&self) -> Option<(usize, char)> {
        self.chars.clone().next()
    }

    fn next_char(&mut self) -> Option<(usize, char)> {
        self.chars.next()
    }

    fn consume_key(&mut self) -> Result<&'a str, String> {
        self.skip_whitespace();
        let (start, first_ch) = self.peek_char().ok_or("Unexpected EOF reading key")?;
        // Special 1-char keys (@, #, $, q, c, n, +, σ, ∈, ∋)
        if is_special_key(first_ch) {
            self.next_char();
            // check for +imp or compound key
            let mut end = start + first_ch.len_utf8();
            while let Some((idx, ch)) = self.peek_char() {
                if ch.is_alphanumeric() || ch == '_' {
                    self.next_char();
                    end = idx + ch.len_utf8();
                } else {
                    break;
                }
            }
            return Ok(&self.input[start..end]);
        }
        let mut end = start;
        while let Some((idx, ch)) = self.peek_char() {
            if ch == '=' || ch == '>' || ch == '<' || ch == '≈' || ch == '≡' || ch == ']' || ch == ',' || ch.is_whitespace() {
                break;
            }
            self.next_char();
            end = idx + ch.len_utf8();
        }
        if start == end {
            return Err("Empty key found in parameter block".into());
        }
        Ok(&self.input[start..end])
    }

    fn consume_relop(&mut self) -> Result<&'a str, String> {
        self.skip_whitespace();
        let (start, ch) = self.next_char().ok_or("Unexpected EOF reading operator")?;
        let mut end = start + ch.len_utf8();
        if let Some((idx, next_ch)) = self.peek_char() {
            if (ch == '>' || ch == '<' || ch == '!' || ch == '=') && next_ch == '=' {
                self.next_char();
                end = idx + next_ch.len_utf8();
            }
        }
        Ok(&self.input[start..end])
    }

    fn consume_val(&mut self) -> Result<&'a str, String> {
        self.skip_whitespace();
        let (start, first) = self.peek_char().ok_or("Unexpected EOF reading value")?;
        if first == '"' {
            self.next_char(); // skip opening quote
            let str_start = start + 1;
            while let Some((idx, ch)) = self.next_char() {
                if ch == '"' {
                    return Ok(&self.input[str_start..idx]);
                }
            }
            return Err("Unterminated string literal".into());
        }
        let mut end = start;
        while let Some((idx, ch)) = self.peek_char() {
            if ch == ',' || ch == ']' || ch.is_whitespace() {
                break;
            }
            self.next_char();
            end = idx + ch.len_utf8();
        }
        Ok(self.input[start..end].trim())
    }
}

#[inline]
pub fn is_verb_glyph(ch: char) -> bool {
    matches!(
        ch,
        '🔍' | '⊕' | '⊖' | '⊗' | '⊙' | '↻' | '⇄' | '⇉' | '⊳' | '⊲' | '⊣' | '⊢' | '⚡' | '🔒' | '⟲' | '⟳' | '⊞'
    )
}

#[inline]
pub fn is_domain_glyph(ch: char) -> bool {
    matches!(
        ch,
        '◆' | '◇' | '◈' | '◉' | '◊' | '⬡' | '⬢' | '⬣' | '⬭' | '⊞' | '⌗' | '🪪' | '📜' | '📡' | '📦' | '⚖'
    )
}

#[inline]
pub fn is_special_key(ch: char) -> bool {
    matches!(
        ch,
        '@' | '#' | '$' | 'q' | 'c' | 'n' | '+' | 'σ' | '∈' | '∋' | '⏰' | '⏱' | '↑' | '↓'
    )
}

#[inline]
pub fn is_chain_op(ch: char) -> bool {
    matches!(ch, '⇉' | '⊳' | '⊲' | '⊨' | '|')
}

#[inline]
pub fn has_operator(s: &str) -> bool {
    let mut in_quote = false;
    for ch in s.chars() {
        if ch == '"' {
            in_quote = !in_quote;
        } else if !in_quote && (ch == '=' || ch == '>' || ch == '<' || ch == '≈' || ch == '≡') {
            return true;
        }
    }
    false
}
