//! Logoglyph Wire Format (LWF-v1) binary encoder and decoder.
//!
//! Compact bitpacked 16-to-64 byte binary wire frames for inter-agent transport.

use uuid::Uuid;

pub const LWF_MAGIC: u8 = 0x7E;
pub const LWF_VERSION: u8 = 0x01;

pub const FLAG_SPECULATIVE: u8 = 0x01;
pub const FLAG_DRY_RUN: u8 = 0x02;
pub const FLAG_HIGH_PRIORITY: u8 = 0x04;
pub const FLAG_PIPELINED: u8 = 0x08;

#[derive(Debug, Clone, PartialEq)]
pub enum LwfValue {
    Null,
    Bool(bool),
    Integer(i64),
    Score(f32),
    Text(String),
    Tags(Vec<String>),
    TaskId(Uuid),
}

#[derive(Debug, Clone, PartialEq)]
pub struct LwfInstruction {
    pub flags: u8,
    pub opcode: u8,
    pub domain: u8,
    pub params: Vec<(u8, LwfValue)>,
}

impl LwfInstruction {
    pub fn new(opcode: u8, domain: u8) -> Self {
        Self {
            flags: 0,
            opcode,
            domain,
            params: Vec::new(),
        }
    }

    pub fn with_flag(mut self, flag: u8) -> Self {
        self.flags |= flag;
        self
    }

    pub fn with_param(mut self, key_code: u8, val: LwfValue) -> Self {
        self.params.push((key_code, val));
        self
    }

    /// Serialize into binary bytes.
    pub fn to_bytes(&self) -> Vec<u8> {
        let mut out = Vec::with_capacity(64);
        out.push(LWF_MAGIC);
        out.push(LWF_VERSION);
        out.push(self.flags);
        out.push(self.params.len().min(255) as u8);
        out.push(self.opcode);
        out.push(self.domain);
        out.extend_from_slice(&0u16.to_le_bytes()); // reserved

        for (k, v) in &self.params {
            out.push(*k);
            match v {
                LwfValue::Null => {
                    out.push(0x00);
                }
                LwfValue::Bool(b) => {
                    out.push(0x01);
                    out.push(if *b { 1 } else { 0 });
                }
                LwfValue::Integer(i) => {
                    out.push(0x02);
                    out.extend_from_slice(&i.to_le_bytes());
                }
                LwfValue::Score(s) => {
                    out.push(0x03);
                    let fixed = (s.clamp(0.0, 1.0) * 10000.0).round() as u16;
                    out.extend_from_slice(&fixed.to_le_bytes());
                }
                LwfValue::Text(s) => {
                    out.push(0x05);
                    let bytes = s.as_bytes();
                    let len = bytes.len().min(65535) as u16;
                    out.extend_from_slice(&len.to_le_bytes());
                    out.extend_from_slice(&bytes[..len as usize]);
                }
                LwfValue::Tags(tags) => {
                    out.push(0x06);
                    out.push(tags.len().min(255) as u8);
                    for t in tags {
                        let t_bytes = t.as_bytes();
                        let len = t_bytes.len().min(255) as u8;
                        out.push(len);
                        out.extend_from_slice(&t_bytes[..len as usize]);
                    }
                }
                LwfValue::TaskId(id) => {
                    out.push(0x07);
                    out.extend_from_slice(id.as_bytes());
                }
            }
        }
        out
    }

    /// Deserialize from binary bytes.
    pub fn from_bytes(bytes: &[u8]) -> Result<Self, String> {
        if bytes.len() < 8 {
            return Err("Packet too short for LWF header".into());
        }
        if bytes[0] != LWF_MAGIC {
            return Err(format!("Invalid LWF magic: 0x{:02X}", bytes[0]));
        }
        if bytes[1] != LWF_VERSION {
            return Err(format!("Unsupported LWF version: {}", bytes[1]));
        }

        let flags = bytes[2];
        let param_count = bytes[3] as usize;
        let opcode = bytes[4];
        let domain = bytes[5];

        let mut idx = 8;
        let mut params = Vec::with_capacity(param_count);

        for _ in 0..param_count {
            if idx >= bytes.len() {
                return Err("Unexpected EOF parsing LWF params".into());
            }
            let key = bytes[idx];
            idx += 1;
            if idx >= bytes.len() {
                return Err("Unexpected EOF reading type tag".into());
            }
            let type_tag = bytes[idx];
            idx += 1;

            let val = match type_tag {
                0x00 => LwfValue::Null,
                0x01 => {
                    if idx >= bytes.len() {
                        return Err("EOF reading bool".into());
                    }
                    let b = bytes[idx] != 0;
                    idx += 1;
                    LwfValue::Bool(b)
                }
                0x02 => {
                    if idx + 8 > bytes.len() {
                        return Err("EOF reading int64".into());
                    }
                    let mut arr = [0u8; 8];
                    arr.copy_from_slice(&bytes[idx..idx + 8]);
                    idx += 8;
                    LwfValue::Integer(i64::from_le_bytes(arr))
                }
                0x03 => {
                    if idx + 2 > bytes.len() {
                        return Err("EOF reading score".into());
                    }
                    let mut arr = [0u8; 2];
                    arr.copy_from_slice(&bytes[idx..idx + 2]);
                    idx += 2;
                    let fixed = u16::from_le_bytes(arr);
                    LwfValue::Score((fixed as f32) / 10000.0)
                }
                0x05 => {
                    if idx + 2 > bytes.len() {
                        return Err("EOF reading text length".into());
                    }
                    let mut arr = [0u8; 2];
                    arr.copy_from_slice(&bytes[idx..idx + 2]);
                    idx += 2;
                    let len = u16::from_le_bytes(arr) as usize;
                    if idx + len > bytes.len() {
                        return Err("EOF reading text bytes".into());
                    }
                    let s = String::from_utf8_lossy(&bytes[idx..idx + len]).into_owned();
                    idx += len;
                    LwfValue::Text(s)
                }
                0x06 => {
                    if idx >= bytes.len() {
                        return Err("EOF reading tags count".into());
                    }
                    let count = bytes[idx] as usize;
                    idx += 1;
                    let mut tags = Vec::with_capacity(count);
                    for _ in 0..count {
                        if idx >= bytes.len() {
                            return Err("EOF reading tag len".into());
                        }
                        let len = bytes[idx] as usize;
                        idx += 1;
                        if idx + len > bytes.len() {
                            return Err("EOF reading tag string".into());
                        }
                        let t = String::from_utf8_lossy(&bytes[idx..idx + len]).into_owned();
                        idx += len;
                        tags.push(t);
                    }
                    LwfValue::Tags(tags)
                }
                0x07 => {
                    if idx + 16 > bytes.len() {
                        return Err("EOF reading UUID".into());
                    }
                    let mut arr = [0u8; 16];
                    arr.copy_from_slice(&bytes[idx..idx + 16]);
                    idx += 16;
                    LwfValue::TaskId(Uuid::from_bytes(arr))
                }
                other => return Err(format!("Unknown LWF type tag: 0x{:02X}", other)),
            };

            params.push((key, val));
        }

        Ok(LwfInstruction {
            flags,
            opcode,
            domain,
            params,
        })
    }
}
