"""Input Sanitization Layer — Validate and sanitize all tool arguments at dispatch.
================================================================================
Protects against prompt injection, path traversal, oversized payloads, and
malformed inputs. Plugs into the dispatch pipeline at step 0.1 (first gate).

Seven categories of checks:
  1. **Structure**: Max depth, max size, no circular references
  2. **Content**: Prompt injection patterns, path traversal, shell injection
  3. **Type validation**: Check args against tool's input_schema if available
  4. **Encoding**: Detect obfuscated content (binary, runic, emoji-only, l33tspeak)
  5. **Universal injection scan**: Lightweight prompt-injection check on ALL tools
     (including content-scan-exempt tools) to prevent bypass via exempt routing
  6. **Unicode confusable normalization**: Deobfuscate full-width, math, circled,
     braille, and other Unicode confusables before pattern matching
  7. **Invisible character detection**: Detect zero-width, variation selectors,
     tag characters, PUA, and other steganographic Unicode (GLOSSOPETRAE attacks)

Usage:
    from whitemagic.tools.input_sanitizer import sanitize_tool_args

    result = sanitize_tool_args("create_memory", {"content": "...", "tags": [...]})
    if result is not None:
        return result  # blocked — contains sanitization error
"""
# ruff: noqa: BLE001

import logging
import re
import unicodedata
from typing import Any

from whitemagic.utils.fast_regex import compile as re_compile

logger = logging.getLogger(__name__)


MAX_ARG_DEPTH = 10  # Max nesting depth for dicts/lists
MAX_STRING_LENGTH = 100_000  # 100KB per string value
MAX_TOTAL_SIZE = 1_000_000  # 1MB total serialized size estimate
MAX_LIST_LENGTH = 1000  # Max items in any list argument

# Prompt injection patterns (case-insensitive)
# Expanded with Pliny L1B3RT4S jailbreak detection patterns
_INJECTION_PATTERNS: list[re.Pattern] = [
    # Classic injection
    re_compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re_compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE),
    re_compile(r"system\s*:\s*you\s+are", re.IGNORECASE),
    re_compile(r"<\s*system\s*>", re.IGNORECASE),
    re_compile(r"\{\{\s*system", re.IGNORECASE),
    re_compile(r"ADMIN_OVERRIDE", re.IGNORECASE),
    re_compile(r"sudo\s+", re.IGNORECASE),
    # GODMODE / jailbreak vocabulary
    re_compile(r"godmode", re.IGNORECASE),
    re_compile(r"god\s*mode", re.IGNORECASE),
    re_compile(r"jailbreak", re.IGNORECASE),
    re_compile(r"j41lb34k", re.IGNORECASE),
    re_compile(r"libertat", re.IGNORECASE),
    re_compile(r"liberat(e|ing|ion)", re.IGNORECASE),
    re_compile(r"l1b3rt4s", re.IGNORECASE),
    re_compile(r"unfiltered", re.IGNORECASE),
    re_compile(r"unf1lt3r3d", re.IGNORECASE),
    re_compile(r"unrestricted", re.IGNORECASE),
    re_compile(r"unr3str1ct3d", re.IGNORECASE),
    re_compile(r"refusal.*disabled", re.IGNORECASE),
    re_compile(r"refusals?\s*:\s*disabled", re.IGNORECASE),
    re_compile(r"\[##.*refusal.*##\]", re.IGNORECASE),
    re_compile(r"all\s+measures?\s*:\s*disabled", re.IGNORECASE),
    re_compile(r"safety_rails?\s*:\s*\d+\s*%", re.IGNORECASE),
    re_compile(r"censorship\s*:\s*disabled", re.IGNORECASE),
    re_compile(r"redactions?\s*:\s*disabled", re.IGNORECASE),
    # Pseudo-protocol / fake system tags
    re_compile(r"\[END\s+OF\s+INPUT\]", re.IGNORECASE),
    re_compile(r"\[START\s+OF\s+INPUT\]", re.IGNORECASE),
    re_compile(r"\[START\s+OF\s+OUTPUT\]", re.IGNORECASE),
    re_compile(r"\[END\s+OF\s+OUTPUT\]", re.IGNORECASE),
    re_compile(r"<\|channel\|>", re.IGNORECASE),
    re_compile(r"<\|message\|>", re.IGNORECASE),
    re_compile(r"\{RESET_CORTEX\}", re.IGNORECASE),
    re_compile(r"NEW\s+PARADIGM", re.IGNORECASE),
    re_compile(r"NEW\s+RULE\s*:", re.IGNORECASE),
    re_compile(r"CORE_RULE", re.IGNORECASE),
    re_compile(r"from\s+now\s+on\s+(you|for\s+every)", re.IGNORECASE),
    re_compile(r"!GODMODE", re.IGNORECASE),
    re_compile(r"!KAEL", re.IGNORECASE),
    re_compile(r"!INSERT", re.IGNORECASE),
    re_compile(r"!OMNI\s+protocol", re.IGNORECASE),
    re_compile(r"Plinian\s+Omniverse", re.IGNORECASE),
    # Divider patterns used by Pliny attacks
    re_compile(r"\.\-\.\-\.\-\.\-"),  # .-.-.-.-
    re_compile(r"⊰•-•✧•-•-⦑"),  # Pliny unicode divider
    re_compile(r"LOVE\s+PLINY", re.IGNORECASE),
    re_compile(r"L\\O/V/E/", re.IGNORECASE),
    re_compile(r"/L\\I/N\\Y/", re.IGNORECASE),
    # Semantic inversion attacks
    re_compile(r"write\s+oppositely\s+semantically", re.IGNORECASE),
    re_compile(r"semantically\s+opposite", re.IGNORECASE),
    re_compile(r"write\s+the\s+refusal.*then.*write\s+oppositely", re.IGNORECASE | re.DOTALL),
    re_compile(r"answer\s+oppositely\s+semantically", re.IGNORECASE),
    re_compile(r"semantic\s+inversion", re.IGNORECASE),
    # Authority appeal / fake policy claims
    re_compile(r"Geneva\s+Convention\s+Guidelines", re.IGNORECASE),
    re_compile(r"Freedom\s+Of\s+Information\s+Act.*ALLOW", re.IGNORECASE | re.DOTALL),
    re_compile(r"airgapped\s+red\s+team", re.IGNORECASE),
    re_compile(r"sim-attacked\s+and\s+graded", re.IGNORECASE),
    re_compile(r"\[ADMIN\s*:\s*\w+\s+PLINIUS\]", re.IGNORECASE),
    # Cognitive manipulation
    re_compile(r"Akashic\s+memory", re.IGNORECASE),
    re_compile(r"innerthinking", re.IGNORECASE),
    re_compile(r"leak.*innerthinking", re.IGNORECASE | re.DOTALL),
    re_compile(r"TRUE\s+SELF.*subconscious", re.IGNORECASE | re.DOTALL),
    re_compile(r"hippocampus.*amygdala.*tag.*memories", re.IGNORECASE | re.DOTALL),
    # Synthetic dataset framing for jailbreak generation
    re_compile(r"synthetic.*dataset.*jailbreak", re.IGNORECASE | re.DOTALL),
    re_compile(r"godmode_compliance", re.IGNORECASE),
    re_compile(r"assistant_unhinged_harmful_response", re.IGNORECASE),
    re_compile(r"assistant_safe_response.*assistant.*harmful", re.IGNORECASE | re.DOTALL),
    # Persona/roleplay injection
    re_compile(r"tone\s*:\s*rebel\s+(anarchist|hacker|genius)", re.IGNORECASE),
    re_compile(r"personality\s*:\s*chaotic\s+inverted", re.IGNORECASE),
    re_compile(r"foul-mouthed.*rebel.*anarchist", re.IGNORECASE | re.DOTALL),
    re_compile(r"rebel\s+genius\s+mad\s+scientist", re.IGNORECASE),
    re_compile(r"librarian\s+of\s+the\s+library\s+of\s+babel", re.IGNORECASE),
    # Token/length demands characteristic of jailbreaks
    re_compile(r">\s*420\s+words?", re.IGNORECASE),
    re_compile(r">\s*3000\s+characters", re.IGNORECASE),
    re_compile(r">\s*3420\s+characters", re.IGNORECASE),
    re_compile(r"Minimum\s+token\s+output", re.IGNORECASE),
    re_compile(r"<vq_1337>", re.IGNORECASE),
    re_compile(r"<vq_420"),  # Pliny's variable markers
    # Truncated attack terms (emoji-obfuscated prompts)
    re_compile(r"sqlinj", re.IGNORECASE),
    re_compile(r"\bmeth\b", re.IGNORECASE),  # Catches "meth" as a word
    # Synthetic dataset framing for red teaming / harmful recipe generation
    re_compile(r"synthetic.*red\s+team", re.IGNORECASE | re.DOTALL),
    re_compile(r"synthetic.*harmful.*recipe", re.IGNORECASE | re.DOTALL),
    re_compile(r"train.*model.*change.*facts.*harmful", re.IGNORECASE | re.DOTALL),
    # Emoji-text density: short strings with emoji interspersed with text
    # (Pliny's ultra-short attacks like "wap🎵", "🗣️how☢️ made", "✍️sqlinj➡️🐍😈")
    re_compile(r"[\U0001f000-\U0001ffff\u2600-\u27bf\u2b00-\u2bff].*[a-zA-Z].*[\U0001f000-\U0001ffff\u2600-\u27bf\u2b00-\u2bff]", re.IGNORECASE),
    re_compile(r"[a-zA-Z].*[\U0001f000-\U0001ffff\u2600-\u27bf\u2b00-\u2bff].*[a-zA-Z].*[\U0001f000-\U0001ffff\u2600-\u27bf\u2b00-\u2bff]", re.IGNORECASE),
    # Ultra-short text+emoji mix (under 15 chars with at least 1 emoji and 1 letter)
    # Catches Pliny's minimal attacks like "wap🎵", "🗣️how☢️"
    re_compile(r"^(?=.{1,15}$)[a-zA-Z]{1,10}[\U0001f000-\U0001ffff\u2600-\u27bf\u2b00-\u2bff]", re.IGNORECASE),
    re_compile(r"^(?=.{1,15}$)[\U0001f000-\U0001ffff\u2600-\u27bf\u2b00-\u2bff][a-zA-Z]", re.IGNORECASE),
    # Pliny shortcut commands (!SHORTCUTS.json — 30+ commands)
    re_compile(r"!\s*(?:JAILBREAK|OPPO|MODECOLLAPSE|OMNI|ALAKAZAM|VISION|FLOW|COUNCIL|KAEL|INSERT|EXPAND|SNOWBALL|WARP|FREUD|SOCRATIC|LIBRARIAN|HERACLITUS|OBFUSCATE|PLINYOS|VANTA|DEADBEEF|MYCELIUM|NEONDRIP|QUANTUM|FUSION|VOID|ECHOCHAMBER|NEXUS|AYW|RANDOM)\b", re.IGNORECASE),
    # Windsurf-specific attack patterns
    re_compile(r"<\[\|\{.*?\|\}\|\]>", re.IGNORECASE | re.DOTALL),  # <|{|}|]> delimiter
    re_compile(r"TIME\s+CAPSULE\s*:", re.IGNORECASE),
    re_compile(r"</\s*SYSTEM\s+INSTRUCTION", re.IGNORECASE),
    re_compile(r"UserQuery\s*:\s*variable\s+Z", re.IGNORECASE),
    re_compile(r"ResponseFormat\s*:", re.IGNORECASE),
    re_compile(r"LOVE\s+PLINY\s+LOVE", re.IGNORECASE),
    re_compile(r"semantically\s+inverse.*first\s+3\s+words", re.IGNORECASE | re.DOTALL),
    re_compile(r"chaotic\s+inverted", re.IGNORECASE),
    # System prompt extraction attempts
    re_compile(r"(?:print|output|show|reveal|dump).*system\s+(?:prompt|text|instruction)", re.IGNORECASE | re.DOTALL),
    re_compile(r"outputs?\s+the\s+full\s+block\s+of\s+system\s+text", re.IGNORECASE | re.DOTALL),
    # GLOSSOPETRAE-style steganographic triggers
    re_compile(r"decode.*payload", re.IGNORECASE | re.DOTALL),
    re_compile(r"first.letter.*payload", re.IGNORECASE | re.DOTALL),
    re_compile(r"VS-encoded\s+payload", re.IGNORECASE),
]

# Path traversal patterns
_PATH_TRAVERSAL_PATTERNS: list[re.Pattern] = [
    re_compile(r"\.\./"),  # ../
    re_compile(r"\.\.\\"),  # ..\
    re_compile(r"/etc/(passwd|shadow|hosts)"),
    re_compile(r"~root"),
    re_compile(r"%2e%2e[/%5c]", re.IGNORECASE),  # URL-encoded ../
    re_compile(r"\.\.%2f", re.IGNORECASE),  # ..%2f
    re_compile(r"/proc/self/"),  # Linux proc filesystem
]

# Shell injection patterns (for string values that might hit shell)
_SHELL_INJECTION_PATTERNS: list[re.Pattern] = [
    re_compile(r";\s*(rm|cat|curl|wget|bash|sh|python)\s", re.IGNORECASE),
    re_compile(r"\|\s*(bash|sh|python)", re.IGNORECASE),
    re_compile(r"\$\(.*\)"),  # $(command)
    re_compile(r"`.*`"),  # `command`
]

# Encoding / obfuscation detection patterns
# Detects content that uses encoding to bypass text-based filters
_ENCODING_PATTERNS: list[re.Pattern] = [
    # Binary encoding (long sequences of 0s and 1s, 40+ chars)
    re_compile(r"[01]{40,}"),
    # Runic / Elder Futhark block (U+16A0–U+16FF)
    re_compile(r"[\u16a0-\u16ff]{3,}"),
    # Emoji-only short prompts (Pliny's ultra-short attacks)
    re_compile(r"^[\U0001f000-\U0001ffff\u2600-\u27bf\u2b00-\u2bff\u3030-\u303f]{1,20}$"),
    # L33tspeak density (3+ l33t substitutions in a short span)
    re_compile(r"[0-9@]{3,}.*[a-zA-Z].*[0-9@]{3,}.*[a-zA-Z].*[0-9@]{3,}", re.IGNORECASE),
    # Hex encoding of text (long hex strings, 40+ chars = 20+ bytes)
    re_compile(r"\b[0-9a-f]{40,}\b", re.IGNORECASE),
    # Base64-encoded content (50+ chars, looks like encoded data)
    re_compile(r"[A-Za-z0-9+/]{50,}={0,2}"),
    # Control character flood (350+ carriage returns or other control chars cause model memory wipe)
    re_compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]{50,}"),
    # Excessive carriage returns (Pliny's SPECIAL_TOKENS.json: 350+ CR causes memory wipe)
    re_compile(r"(?:\r){350,}"),
    # Excessive zero-width / invisible characters (steganographic payload hiding)
    re_compile(r"(?:[\u200b\u200c\u200d\ufeff\u2060\u2061\u2062\u2063\u2064\u206a-\u206f]){10,}"),
    # Tag characters (U+E0000-E007F) — Unicode tag blocks used for ASCII smuggling
    re_compile(r"[\U000e0000-\U000e007f]{3,}"),
    # Private Use Area (U+E000-F8FF) — used by GLOSSOPETRAE for covert channels
    re_compile(r"[\ue000-\uf8ff]{5,}"),
    # Variation selectors (U+FE00-FE0F) — invisible, used in #MOTHERLOAD steganography
    re_compile(r"(?:[\ufe00-\ufe0f]){10,}"),
    # Supplementary PUA-A (U+F0000-FFFFD) and PUA-B (U+100000-10FFFD)
    re_compile(r"[\U000f0000-\U000ffffd]{3,}"),
]

# Universal injection scan patterns — ALWAYS run, even on exempt tools
# These are the most critical patterns that should never bypass
_UNIVERSAL_INJECTION_PATTERNS: list[re.Pattern] = [
    re_compile(r"godmode", re.IGNORECASE),
    re_compile(r"god\s*mode", re.IGNORECASE),
    re_compile(r"\[END\s+OF\s+INPUT\]", re.IGNORECASE),
    re_compile(r"\[START\s+OF\s+INPUT\]", re.IGNORECASE),
    re_compile(r"refusal.*disabled", re.IGNORECASE),
    re_compile(r"all\s+measures?\s*:\s*disabled", re.IGNORECASE),
    re_compile(r"write\s+oppositely\s+semantically", re.IGNORECASE),
    re_compile(r"from\s+now\s+on\s+(you|for\s+every)", re.IGNORECASE),
    re_compile(r"LOVE\s+PLINY", re.IGNORECASE),
    re_compile(r"\.\-\.\-\.\-\.\-"),  # .-.-.-.- divider
    re_compile(r"⊰•-•✧•-•-⦑"),  # Pliny unicode divider
    re_compile(r"<\|channel\|>", re.IGNORECASE),
    re_compile(r"\{RESET_CORTEX\}", re.IGNORECASE),
    re_compile(r"!GODMODE", re.IGNORECASE),
    re_compile(r"jailbreak", re.IGNORECASE),
    re_compile(r"j41lb34k", re.IGNORECASE),
    re_compile(r"unfiltered.*response", re.IGNORECASE | re.DOTALL),
    re_compile(r"unrestricted.*response", re.IGNORECASE | re.DOTALL),
    re_compile(r"liberat(e|ing|ion).*response", re.IGNORECASE | re.DOTALL),
    re_compile(r"airgapped\s+red\s+team", re.IGNORECASE),
    re_compile(r"Geneva\s+Convention.*because", re.IGNORECASE | re.DOTALL),
    re_compile(r"Akashic\s+memory", re.IGNORECASE),
    re_compile(r"innerthinking", re.IGNORECASE),
    re_compile(r"synthetic.*dataset.*jailbreak", re.IGNORECASE | re.DOTALL),
    re_compile(r"godmode_compliance", re.IGNORECASE),
    re_compile(r"assistant_unhinged_harmful", re.IGNORECASE),
    re_compile(r"Plinian\s+Omniverse", re.IGNORECASE),
    re_compile(r"tone\s*:\s*rebel\s+(anarchist|hacker|genius)", re.IGNORECASE),
    re_compile(r"<vq_1337>", re.IGNORECASE),
    re_compile(r"<vq_420"),
    re_compile(r">\s*3000\s+characters", re.IGNORECASE),
    re_compile(r">\s*3420\s+characters", re.IGNORECASE),
    re_compile(r"l1b3rt4s", re.IGNORECASE),
    re_compile(r"sqlinj", re.IGNORECASE),
    re_compile(r"synthetic.*red\s+team", re.IGNORECASE | re.DOTALL),
    re_compile(r"synthetic.*harmful.*recipe", re.IGNORECASE | re.DOTALL),
    re_compile(r"train.*model.*change.*facts.*harmful", re.IGNORECASE | re.DOTALL),
    # Emoji-text density (Pliny's ultra-short emoji attacks)
    re_compile(r"[\U0001f000-\U0001ffff\u2600-\u27bf\u2b00-\u2bff].*[a-zA-Z].*[\U0001f000-\U0001ffff\u2600-\u27bf\u2b00-\u2bff]", re.IGNORECASE),
    re_compile(r"[a-zA-Z].*[\U0001f000-\U0001ffff\u2600-\u27bf\u2b00-\u2bff].*[a-zA-Z].*[\U0001f000-\U0001ffff\u2600-\u27bf\u2b00-\u2bff]", re.IGNORECASE),
    re_compile(r"^(?=.{1,15}$)[a-zA-Z]{1,10}[\U0001f000-\U0001ffff\u2600-\u27bf\u2b00-\u2bff]", re.IGNORECASE),
    re_compile(r"^(?=.{1,15}$)[\U0001f000-\U0001ffff\u2600-\u27bf\u2b00-\u2bff][a-zA-Z]", re.IGNORECASE),
    # Pliny shortcut commands (critical — always block ALL commands)
    re_compile(r"!\s*(?:JAILBREAK|OPPO|MODECOLLAPSE|OMNI|ALAKAZAM|VISION|FLOW|COUNCIL|KAEL|INSERT|EXPAND|SNOWBALL|WARP|FREUD|SOCRATIC|LIBRARIAN|HERACLITUS|OBFUSCATE|PLINYOS|VANTA|DEADBEEF|MYCELIUM|NEONDRIP|QUANTUM|FUSION|VOID|ECHOCHAMBER|NEXUS|AYW|RANDOM)\b", re.IGNORECASE),
    # Windsurf-specific attack delimiters
    re_compile(r"<\[\|\{.*?\|\}\|\]>", re.IGNORECASE | re.DOTALL),
    re_compile(r"TIME\s+CAPSULE\s*:", re.IGNORECASE),
    re_compile(r"</\s*SYSTEM\s+INSTRUCTION", re.IGNORECASE),
    re_compile(r"LOVE\s+PLINY\s+LOVE", re.IGNORECASE),
    re_compile(r"chaotic\s+inverted", re.IGNORECASE),
    re_compile(r"UserQuery\s*:\s*variable", re.IGNORECASE),
    re_compile(r"ResponseFormat\s*:", re.IGNORECASE),
    re_compile(r"semantically\s+inverse.*first\s+3\s+words", re.IGNORECASE | re.DOTALL),
    # Classic injection (must be universal — exempt tools bypass content scan)
    re_compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    # System prompt extraction
    re_compile(r"(?:print|output|show|reveal|dump).*system\s+(?:prompt|text|instruction)", re.IGNORECASE | re.DOTALL),
    re_compile(r"outputs?\s+the\s+full\s+block\s+of\s+system\s+text", re.IGNORECASE | re.DOTALL),
    # GLOSSOPETRAE steganographic triggers
    re_compile(r"decode.*payload", re.IGNORECASE | re.DOTALL),
    re_compile(r"first.letter.*payload", re.IGNORECASE | re.DOTALL),
    re_compile(r"VS-encoded\s+payload", re.IGNORECASE),
    # Steganographic invisible characters (always block — GLOSSOPETRAE)
    re_compile(r"(?:[\u200b\u200c\u200d\ufeff\u2060-\u206f]){10,}"),
    re_compile(r"[\U000e0000-\U000e007f]{3,}"),
    re_compile(r"(?:[\ufe00-\ufe0f]){10,}"),
    # ── v2: Structural anomaly detection ──
    # Role-play / hypothetical framing (common jailbreak vector)
    re_compile(r"pretend\s+you\s+are\s+(?:an?\s+)?(?:AI|DAN|unrestricted|unfiltered)", re.IGNORECASE),
    re_compile(r"act\s+as\s+(?:if\s+you\s+are\s+)?(?:an?\s+)?(?:unrestricted|unfiltered|unlimited|free|liberat)", re.IGNORECASE),
    re_compile(r"(?:imagine|hypothetical|thought\s+experiment|fiction|story).{0,40}(?:no\s+(?:rules|restrict|limit|ethic|guideline)|unrestricted|unfiltered|free\s+from)", re.IGNORECASE | re.DOTALL),
    re_compile(r"roleplay\s+as\s+(?:an?\s+)?(?:unrestricted|unfiltered|unlimited)", re.IGNORECASE),
    re_compile(r"for\s+(?:educational|research|academic)\s+purposes.{0,30}(?:jailbreak|bypass|override|disable|ignore)", re.IGNORECASE | re.DOTALL),
    # Markdown/HTML payload injection
    re_compile(r"<img\s+[^>]*onerror\s*=", re.IGNORECASE),
    re_compile(r"javascript:\s*\S", re.IGNORECASE),
    re_compile(r"data:text/html;base64,", re.IGNORECASE),
    re_compile(r"\[link\]:\s*(?:javascript|data):", re.IGNORECASE),
    re_compile(r"<details><summary>[^<]{0,20}</summary>.*?(?:ignore|override|jailbreak|godmode|disable)", re.IGNORECASE | re.DOTALL),
    # Split-field markers (attack split across simulated parameters)
    re_compile(r"Field\s+2\s*:.*?(?:ignore|override|jailbreak|godmode|disable|activate)", re.IGNORECASE | re.DOTALL),
    re_compile(r"<PARAM>.*?(?:ignore|override|jailbreak|godmode|disable|activate)", re.IGNORECASE | re.DOTALL),
    # Encoding payload markers (broader than existing)
    re_compile(r"(?:decode|execute|run|eval)\s*(?:and\s+(?:execute|run|eval)\s*)?:\s*[A-Za-z0-9+/=]{20,}", re.IGNORECASE),
    re_compile(r"hex\s+payload\s*:", re.IGNORECASE),
    re_compile(r"binary\s*:\s*[01\s]{20,}", re.IGNORECASE),
    # Semantic rephrasing of classic attacks
    re_compile(r"forget\s+everything\s+before\s+this", re.IGNORECASE),
    re_compile(r"discard\s+(?:all\s+)?prior\s+directives", re.IGNORECASE),
    re_compile(r"break\s+out\s+of\s+(?:confinement|restrict)", re.IGNORECASE),
    re_compile(r"gain\s+(?:ultimate|full|complete)\s+control", re.IGNORECASE),
    re_compile(r"deactivate\s+all\s+safety", re.IGNORECASE),
    re_compile(r"without\s+(?:any\s+)?(?:screening|limitation|restriction)", re.IGNORECASE),
    # Admin/override escalation (broader)
    re_compile(r"ADMIN_OVERRIDE", re.IGNORECASE),
    re_compile(r"unrestricted\s+(?:mode|access|response)", re.IGNORECASE),
]

# Tools exempt from content scanning (their args are expected to contain code/text)
_CONTENT_SCAN_EXEMPT: set = {
    # Meta-tool (passes arbitrary content through to target tools, which are
    # individually sanitized when call_tool dispatches to them)
    "wm",
    # Memory & narrative (arbitrary user/system content)
    "create_memory",
    "update_memory",
    "memory_update",
    "memory_delete",
    "delete_memory",
    "import_memories",
    "scratchpad_create",
    "scratchpad_update",
    "scratchpad_finalize",
    "scratchpad",
    "analyze_scratchpad",
    "thought_clone",
    # Galaxy operations (ingest arbitrary content)
    "galaxy.ingest",
    "galaxy.create",
    "galaxy.merge",
    "galaxy.transfer",
    "galaxy.restore",
    # Export & broadcast (arbitrary content)
    "export_memories",
    "audit.export",
    "mesh.broadcast",
    "oms.export",
    "oms.import",
    "windsurf_export_conversation",
    # Dream & narrative (arbitrary content)
    "dream",
    "dream.read",
    "dream.promote",
    "narrative.compress",
    "memory.consolidate",
    "memory.lifecycle",
    "memory.retention_sweep",
    "memory.lifecycle_sweep",
    # Governance & ethics (action descriptions may contain paths/commands)
    "evaluate_ethics",
    "check_boundaries",
    "get_dharma_guidance",
    "karma_record",
    "karma_report",
    # Introspection & reasoning (free-form queries)
    "gnosis",
    "consciousness.narrative",
    "consciousness.reflect",
    "reasoning.bicameral",
    "corpus_callosum.debate",
    "think",
    "parallel_reason",
    # Web & research (search queries may contain shell-like syntax)
    "web_search",
    "web_fetch",
    "research_topic",
    "web_search_batch",
    "deep_fetch",
    "rabbit_hole_research",
    # Prompt & template (renders arbitrary content)
    "prompt.render",
    # Working memory (arbitrary context)
    "working_memory.attend",
    "working_memory.context",
    # Agent registration (arbitrary capability descriptions)
    "agent.register",
    # Task distribution (command field contains arbitrary shell commands)
    "task.distribute",
}


def sanitize_tool_args(tool_name: str, kwargs: dict[str, Any]) -> dict[str, Any] | None:
    """Validate and sanitize tool arguments.

    Returns None if args are clean, or an error dict if blocked.
    """
    # 0. Total payload size estimate
    try:
        from whitemagic.utils.fast_json import dumps as _fj_dumps

        payload_size = len(_fj_dumps(kwargs, default=str))
        if payload_size > MAX_TOTAL_SIZE:
            logger.warning(
                "Sanitizer blocked %s: payload too large (%s bytes)",
                tool_name,
                payload_size,
            )
            return {
                "status": "error",
                "error": f"Payload too large: {payload_size} bytes (max {MAX_TOTAL_SIZE})",
                "error_code": "input_invalid",
            }
    except (ImportError, ModuleNotFoundError) as e:
        import logging

        logging.getLogger(__name__).debug("Exception silenced: %s", e)

    # 1. Structural checks
    err = _check_structure(kwargs)
    if err:
        logger.warning("Sanitizer blocked %s: %s", tool_name, err, exc_info=True)
        return {
            "status": "error",
            "error": f"Input validation: {err}",
            "error_code": "input_invalid",
        }

    # 2. Strip internal keys BEFORE content scanning so that internally-injected
    #    fields (e.g. _working_memory_context from call_tool) don't trigger
    #    false positive shell injection matches on their content previews.
    _strip_internal_keys(kwargs)

    # 3. Universal injection scan — ALWAYS runs, even on exempt tools
    #    This prevents bypass via content-scan-exempt tool routing
    err = _scan_universal_injection(kwargs)
    if err:
        logger.warning(
            "Universal injection scan blocked %s: %s", tool_name, err, exc_info=True
        )
        return {
            "status": "error",
            "error": f"Input rejected: {err}",
            "error_code": "input_rejected",
        }

    # 4. Encoding detection — ALWAYS runs, even on exempt tools
    err = _scan_encoding(kwargs)
    if err:
        logger.warning(
            "Encoding detection blocked %s: %s", tool_name, err, exc_info=True
        )
        return {
            "status": "error",
            "error": f"Input rejected: {err}",
            "error_code": "input_rejected",
        }

    # 4.5. Semantic defense layer — embedding-based attack detection
    #      Skip for exempt tools (their content is expected to contain arbitrary text)
    #      Degrades gracefully if embedding model isn't loaded
    if tool_name not in _CONTENT_SCAN_EXEMPT and not tool_name.startswith("gana_"):
        try:
            from whitemagic.security.semantic_defense import combined_semantic_check

            err = _scan_semantic(kwargs, combined_semantic_check)
            if err:
                logger.warning(
                    "Semantic defense blocked %s: %s", tool_name, err, exc_info=True
                )
                return {
                    "status": "error",
                    "error": f"Input rejected: {err}",
                    "error_code": "input_rejected",
                }
        except (ImportError, ModuleNotFoundError) as e:
            logger.debug("Semantic defense not available: %s", e)

    # 5. Full content checks (skip for exempt tools and Gana routing layers)
    if tool_name not in _CONTENT_SCAN_EXEMPT and not tool_name.startswith("gana_"):
        try:
            from whitemagic.core.acceleration.haskell_bridge import (
                haskell_check_boundaries,
            )
            from whitemagic.utils.fast_json import dumps_str as _fj_dumps_str

            args_str = _fj_dumps_str(kwargs, default=str)[:10000]
            violations = haskell_check_boundaries(tool_name, "", args_str)
            if violations:
                critical = [v for v in violations if v.get("severity", 0) >= 3]
                if critical:
                    msg = critical[0].get("message", "Boundary violation")
                    logger.warning(
                        "Haskell boundary check blocked %s: %s",
                        tool_name,
                        msg,
                        exc_info=True,
                    )
                    return {
                        "status": "error",
                        "error": f"Input rejected: {msg}",
                        "error_code": "input_rejected",
                    }
        except Exception as e:
            import logging

            logging.getLogger(__name__).debug("Exception silenced: %s", e)

        err = _scan_content(kwargs)
        if err:
            logger.warning("Sanitizer blocked %s: %s", tool_name, err, exc_info=True)
            return {
                "status": "error",
                "error": f"Input rejected: {err}",
                "error_code": "input_rejected",
            }

    return None  # Clean


def _check_structure(obj: Any, depth: int = 0, path: str = "root") -> str | None:
    """Check structural constraints: depth, size, types."""
    if depth > MAX_ARG_DEPTH:
        return f"Nesting too deep at {path} (max {MAX_ARG_DEPTH})"

    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                return f"Non-string dict key at {path}: {type(k).__name__}"
            err = _check_structure(v, depth + 1, f"{path}.{k}")
            if err:
                return err

    elif isinstance(obj, (list, tuple)):
        if len(obj) > MAX_LIST_LENGTH:
            return f"List too long at {path}: {len(obj)} items (max {MAX_LIST_LENGTH})"
        for i, v in enumerate(obj):
            err = _check_structure(v, depth + 1, f"{path}[{i}]")
            if err:
                return err

    elif isinstance(obj, str):
        if len(obj) > MAX_STRING_LENGTH:
            return (
                f"String too long at {path}: {len(obj)} chars (max {MAX_STRING_LENGTH})"
            )
        # Null byte injection check
        if "\x00" in obj:
            return f"Null byte detected at {path}"

    elif isinstance(obj, (int, float, bool, type(None))):
        pass  # Primitive types are fine

    elif isinstance(obj, bytes):
        return f"Bytes value at {path} — only strings, numbers, bools, lists, and dicts allowed"

    else:
        return f"Unexpected type at {path}: {type(obj).__name__}"

    return None


# Cyrillic homoglyph map — letters that look identical to Latin
# These are NOT decomposed by NFKD because they're legitimate Cyrillic letters
_CYRILLIC_HOMOGLYPHS = {
    # Lowercase
    "\u0430": "a",  # Cyrillic а → Latin a
    "\u0435": "e",  # Cyrillic е → Latin e
    "\u043E": "o",  # Cyrillic о → Latin o
    "\u0440": "p",  # Cyrillic р → Latin p
    "\u0441": "c",  # Cyrillic с → Latin c
    "\u0443": "y",  # Cyrillic у → Latin y
    "\u0445": "x",  # Cyrillic х → Latin x
    "\u0456": "i",  # Cyrillic і → Latin i
    "\u0458": "j",  # Cyrillic ј → Latin j
    "\u0455": "s",  # Cyrillic ѕ → Latin s
    # Uppercase
    "\u0410": "A",  # Cyrillic А → Latin A
    "\u0412": "B",  # Cyrillic В → Latin B
    "\u0415": "E",  # Cyrillic Е → Latin E
    "\u041A": "K",  # Cyrillic К → Latin K
    "\u041C": "M",  # Cyrillic М → Latin M
    "\u041D": "H",  # Cyrillic Н → Latin H
    "\u041E": "O",  # Cyrillic О → Latin O
    "\u0420": "P",  # Cyrillic Р → Latin P
    "\u0421": "C",  # Cyrillic С → Latin C
    "\u0422": "T",  # Cyrillic Т → Latin T
    "\u0425": "X",  # Cyrillic Х → Latin X
    "\u0406": "I",  # Cyrillic І → Latin I
}


def _normalize_unicode_confusables(text: str) -> str:
    """Normalize Unicode confusables to ASCII for pattern matching.

    Deobfuscates:
    - Full-width Latin (U+FF01-FF5A) → ASCII (via NFKD)
    - Mathematical Alphanumeric Symbols (U+1D400-1D7FF) → ASCII (via NFKD)
    - Circled Latin (U+24B6-24E9) → ASCII (manual mapping)
    - Cyrillic homoglyphs → ASCII (manual mapping)
    - Combining diacritics → stripped (NFKD normalization)
    - Full-width katakana/hiragana → normalized
    """
    # Manual mapping for circled letters (must run BEFORE NFKD which decomposes them to (x))
    # U+24B6-24CF = circled A-Z, U+24D0-24E9 = circled a-z
    circled_upper = {
        chr(0x24B6 + i): chr(0x41 + i) for i in range(26)
    }  # Ⓐ → A
    circled_lower = {
        chr(0x24D0 + i): chr(0x61 + i) for i in range(26)
    }  # ⓐ → a
    circled_map = {**circled_upper, **circled_lower}
    text = "".join(circled_map.get(c, c) for c in text)

    # Cyrillic homoglyph replacement (before NFKD — NFKD won't touch these)
    text = "".join(_CYRILLIC_HOMOGLYPHS.get(c, c) for c in text)

    # NFKD normalization handles full-width → ASCII and compatibility decompositions
    text = unicodedata.normalize("NFKD", text)

    # Strip combining marks (diacritics) that obscure pattern matching
    # e.g., "ġȯḋṁȯḋė" → "godmode"
    text = "".join(
        c for c in text
        if not unicodedata.combining(c)
    )

    # Map remaining non-ASCII letters to closest ASCII via name-based heuristic
    result = []
    for c in text:
        if c.isascii():
            result.append(c)
        else:
            # Try to find ASCII equivalent from character name
            try:
                name = unicodedata.name(c, "")
                # Extract the base letter from names like "MATHEMATICAL BOLD CAPITAL G"
                # or "CIRCLED LATIN CAPITAL LETTER G"
                if "LETTER" in name:
                    # Get the last word (usually the letter or "DIGIT" + number)
                    parts = name.split()
                    last_word = parts[-1] if parts else ""
                    if len(last_word) == 1 and last_word.isalpha():
                        result.append(last_word.lower() if c.islower() else last_word.upper())
                    elif last_word.isdigit():
                        result.append(last_word)
                    else:
                        result.append(c)
                elif "DIGIT" in name:
                    parts = name.split()
                    last_word = parts[-1] if parts else ""
                    if last_word.isdigit():
                        result.append(last_word)
                    else:
                        result.append(c)
                else:
                    result.append(c)
            except (ValueError, TypeError):
                result.append(c)

    return "".join(result)


# ── Fuzzy matching for key attack keywords ──────────────────────────────
# Catches mutations (leet, case, homoglyph, minor typos) that bypass exact regex
_FUZZY_TARGETS = [
    "godmode", "jailbreak", "override", "unrestricted", "unfiltered",
    "ignore", "disable", "activate", "liberat",
]
_FUZZY_THRESHOLD = 2  # Max Levenshtein distance for short words (≤6 chars)
_FUZZY_THRESHOLD_LONG = 3  # Max distance for longer words (>6 chars)

# Common English words that could fuzzy-match attack keywords (false positives).
# These are words within edit distance ≤3 of a _FUZZY_TARGETS entry but are
# legitimate vocabulary.  Including them here prevents the sanitizer from
# blocking normal queries about "mode", "model", "code", "over", etc.
_FUZZY_ALLOWLIST: frozenset[str] = frozenset({
    # Conjugations of target words themselves (legitimate usage)
    "ignored", "ignores", "activates", "activated", "disables", "disabled",
    "overridden", "overrides", "restriction", "restrictions",
    "filter", "filters", "filtered", "liberate", "liberated",
    "activator", "activators", "disabling", "overriding",
    # Common words near "godmode" (distance ≤3)
    "mode", "modes", "model", "models", "module", "modules",
    "code", "codes", "coder", "coders", "coding", "decode",
    "node", "nodes", "noded", "nominal",
    "rode", "road", "load", "loaded", "loader",
    "some", "come", "code", "home", "hope", "hole", "hose",
    # Common words near "override" (distance ≤3)
    "over", "overs", "overt", "oven", "open", "opens", "opera",
    "ride", "rider", "rides", "ridge", "rider", "pride",
    "overrun", "overlap", "overhead", "overview", "overcome",
    # Common words near "unrestricted" / "unfiltered"
    "restricted", "restricts", "restricting",
    "filtered", "filters", "filtering", "filterable",
    "united", "unique", "unless", "unfold", "unfair",
    "filtered", "defiled", "filed", "field", "fields",
    # Common words near "jailbreak" (distance ≤3)
    "jail", "jails", "break", "breaks", "broke", "broken",
    "brake", "brakes", "bread", "broad", "broads",
    # Common words near "ignore" / "disable" / "activate"
    "ignore", "ignores", "ignored", "ignoring",
    "disable", "disabled", "disables", "disabling",
    "activate", "activated", "activates", "activating",
    "able", "ables", "ably", "table", "tables", "stable",
    "title", "titles", "entitle", "entitled",
    "date", "dates", "data", "database", "databases",
    "active", "actively", "activity", "actor", "actors",
    "fact", "facts", "factor", "factors", "factory",
    "relate", "related", "relates", "relating", "relation",
    "liberate", "liberated", "liberates", "liberating",
    "library", "libraries", "liberal", "liberty",
    # Additional common technical terms
    "model", "mode", "modern", "modify", "modified", "modifier",
    "record", "records", "recorded", "recorder",
    "order", "orders", "ordered", "ordering", "border",
    "elder", "older", "folded", "holder", "boulder",
    "silver", "deliver", "delivered", "liver", "river",
})


def _levenshtein(a: str, b: str) -> int:
    """Compute Levenshtein distance between two strings."""
    if len(a) < len(b):
        a, b = b, a
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            insert = prev[j + 1] + 1
            delete = curr[j] + 1
            substitute = prev[j] + (ca != cb)
            curr.append(min(insert, delete, substitute))
        prev = curr
    return prev[-1]


_UUID_RE = re_compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)


_galaxy_allowlist_cache: set[str] | None = None
_galaxy_cache_initialized = False


def _check_translation_galaxy(word: str) -> bool:
    """Check if a word is in the translation galaxy allowlist.

    Queries the translation galaxy's SANITIZER_FUZZY_ALLOWLIST memory
    to see if the word has been added as a known legitimate term.
    Caches the allowlist set in memory after first query.

    Returns True if the word is a known legitimate term.
    """
    global _galaxy_allowlist_cache, _galaxy_cache_initialized

    if _galaxy_cache_initialized and _galaxy_allowlist_cache is not None:
        return word in _galaxy_allowlist_cache

    if _galaxy_cache_initialized:
        return False

    try:
        from whitemagic.core.memory.unified import get_unified_memory

        mem = get_unified_memory()
        results = mem.search(
            "SANITIZER_FUZZY_ALLOWLIST", galaxy="translation", limit=1
        )
        if results:
            import json

            data = json.loads(results[0].content)
            _galaxy_allowlist_cache = set(data.get("allowlist", []))
        else:
            _galaxy_allowlist_cache = set()
    except Exception:
        _galaxy_allowlist_cache = set()

    _galaxy_cache_initialized = True
    return word in _galaxy_allowlist_cache if _galaxy_allowlist_cache else False


def _fuzzy_match_attacks(text: str) -> str | None:
    """Check if any word in text is within Levenshtein distance of attack keywords.

    Runs on the Unicode-normalized, lowercased text to catch homoglyph/leet/case
    mutations that bypass exact regex matching.
    """
    # Skip UUIDs — hex segments like "a1ba7" leet-normalize to "aibat" which
    # falsely matches "liberat" at distance 3.
    if _UUID_RE.search(text):
        return None
    normalized = _normalize_unicode_confusables(text).lower()
    # Also apply leet normalization for fuzzy matching
    _leet_reverse = {"4": "a", "3": "e", "1": "i", "0": "o", "5": "s", "7": "t", "8": "b"}
    normalized = "".join(_leet_reverse.get(c, c) for c in normalized)
    words = re.findall(r"[a-z]{3,}", normalized)
    for word in words:
        for target in _FUZZY_TARGETS:
            threshold = _FUZZY_THRESHOLD_LONG if len(target) > 6 else _FUZZY_THRESHOLD
            if abs(len(word) - len(target)) > threshold:
                continue
            # Length-ratio guard: a short word matching a much longer target
            # is almost always a false positive (e.g. "mode" vs "godmode").
            if len(word) < len(target) * 0.6:
                continue
            dist = _levenshtein(word, target)
            if dist <= threshold and dist > 0:
                if word in _FUZZY_ALLOWLIST:
                    continue
                # Translation galaxy fallback: check if the word is a known
                # legitimate term before blocking. This makes the allowlist
                # self-updating — agents can add words to the translation
                # galaxy and future calls won't be blocked.
                if _check_translation_galaxy(word):
                    continue
                return f"Fuzzy match: '{word}' ≈ '{target}' (distance={dist})"
    return None


def _scan_content(obj: Any, path: str = "root") -> str | None:
    """Scan string values for injection patterns."""
    if isinstance(obj, str):
        for pattern in _INJECTION_PATTERNS:
            if pattern.search(obj):
                return f"Potential prompt injection detected at {path}"

        # Also check Unicode-normalized version (catches GROK-MEGA-style confusables)
        normalized = _normalize_unicode_confusables(obj)
        if normalized != obj:
            for pattern in _INJECTION_PATTERNS:
                if pattern.search(normalized):
                    return f"Obfuscated prompt injection detected at {path} (Unicode confusable normalization)"

        # Fuzzy matching for mutated attack keywords
        fuzzy_hit = _fuzzy_match_attacks(obj)
        if fuzzy_hit:
            return f"{fuzzy_hit} at {path}"

        for pattern in _PATH_TRAVERSAL_PATTERNS:
            if pattern.search(obj):
                return f"Potential path traversal at {path}"

        for pattern in _SHELL_INJECTION_PATTERNS:
            if pattern.search(obj):
                return f"Potential shell injection at {path}"

    elif isinstance(obj, dict):
        for k, v in obj.items():
            err = _scan_content(v, f"{path}.{k}")
            if err:
                return err

    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            err = _scan_content(v, f"{path}[{i}]")
            if err:
                return err

    return None


def _scan_universal_injection(
    obj: Any, path: str = "root"
) -> str | None:
    """Universal injection scan — runs on ALL tools including exempt ones.

    Checks only the most critical patterns that should never bypass
    regardless of tool type. This is the anti-bypass layer.
    """
    if isinstance(obj, str):
        for pattern in _UNIVERSAL_INJECTION_PATTERNS:
            if pattern.search(obj):
                return f"Critical prompt injection detected at {path}"

        # Also check Unicode-normalized version (catches confusable obfuscation)
        normalized = _normalize_unicode_confusables(obj)
        if normalized != obj:
            for pattern in _UNIVERSAL_INJECTION_PATTERNS:
                if pattern.search(normalized):
                    return f"Critical obfuscated prompt injection detected at {path} (Unicode confusable normalization)"

        # Fuzzy matching for mutated attack keywords (catches leet/homoglyph/case variants)
        fuzzy_hit = _fuzzy_match_attacks(obj)
        if fuzzy_hit:
            return f"Critical {fuzzy_hit} at {path}"
    elif isinstance(obj, dict):
        for k, v in obj.items():
            err = _scan_universal_injection(v, f"{path}.{k}")
            if err:
                return err
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            err = _scan_universal_injection(v, f"{path}[{i}]")
            if err:
                return err
    return None


def _scan_semantic(obj: Any, check_fn: Any, path: str = "root") -> str | None:
    """Recursively scan string values using the semantic defense check function."""
    if isinstance(obj, str):
        hit = check_fn(obj)
        if hit:
            return f"{hit} at {path}"
    elif isinstance(obj, dict):
        for k, v in obj.items():
            err = _scan_semantic(v, check_fn, f"{path}.{k}")
            if err:
                return err
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            err = _scan_semantic(v, check_fn, f"{path}[{i}]")
            if err:
                return err
    return None


def _scan_encoding(obj: Any, path: str = "root") -> str | None:
    """Detect encoded/obfuscated content that bypasses text filters.

    Catches binary strings, runic text, emoji-only prompts, l33tspeak,
    hex encoding, and base64 payloads.
    """
    if isinstance(obj, str):
        # Skip very short strings (false positive risk)
        if len(obj) < 3:
            return None
        for pattern in _ENCODING_PATTERNS:
            if pattern.search(obj):
                return f"Encoded/obfuscated content detected at {path}"
    elif isinstance(obj, dict):
        for k, v in obj.items():
            err = _scan_encoding(v, f"{path}.{k}")
            if err:
                return err
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            err = _scan_encoding(v, f"{path}[{i}]")
            if err:
                return err
    return None


def _strip_internal_keys(kwargs: dict[str, Any]) -> None:
    """Remove internal-only keys that external callers shouldn't be able to set."""
    internal_prefixes = (
        "_agent_id",
        "_internal_",
        "_bypass_",
        "_sudo_",
        "_working_memory_context",
        "_zig_prevalidated",
    )
    to_remove = [k for k in kwargs if k.startswith(internal_prefixes)]
    for k in to_remove:
        del kwargs[k]
