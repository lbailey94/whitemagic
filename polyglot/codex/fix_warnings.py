#!/usr/bin/env python3
import os

# Fix codex-core: remove unused Path import
with open('crates/codex-core/src/lib.rs', 'r') as f:
    content = f.read()
content = content.replace('use std::path::{Path, PathBuf};', 'use std::path::PathBuf;')
with open('crates/codex-core/src/lib.rs', 'w') as f:
    f.write(content)
print('Fixed codex-core')

# Fix codex-embed: prefix unused vars and allow dead_code on RateLimiter
with open('crates/codex-embed/src/lib.rs', 'r') as f:
    content = f.read()
content = content.replace('    api_key: Option<&str>,', '    _api_key: Option<&str>,')
content = content.replace('    model_name: &str,', '    _model_name: &str,')
content = content.replace('    dimensions: usize,', '    _dimensions: usize,')
content = content.replace('    rate_limit_rps: f32,', '    _rate_limit_rps: f32,')
content = content.replace('    max_retries: usize,', '    _max_retries: usize,')
content = content.replace('struct RateLimiter {', '#[allow(dead_code)]\nstruct RateLimiter {')
content = content.replace('impl RateLimiter {', '#[allow(dead_code)]\nimpl RateLimiter {')
with open('crates/codex-embed/src/lib.rs', 'w') as f:
    f.write(content)
print('Fixed codex-embed')

# Fix codex-export: remove mut
with open('crates/codex-export/src/lib.rs', 'r') as f:
    content = f.read()
content = content.replace('let mut chunks = load_chunks', 'let chunks = load_chunks')
with open('crates/codex-export/src/lib.rs', 'w') as f:
    f.write(content)
print('Fixed codex-export')

# Fix codex-chunk: remove EntityId
with open('crates/codex-chunk/src/lib.rs', 'r') as f:
    content = f.read()
content = content.replace('use codex_core::{Chunk, Document, Result, CodexError, EntityId};', 'use codex_core::{Chunk, Document, Result, CodexError};')
with open('crates/codex-chunk/src/lib.rs', 'w') as f:
    f.write(content)
print('Fixed codex-chunk')

print('All warning fixes applied!')
