"""Grammar-constrained JSON schemas for llama-server structured outputs.

llama-server supports both JSON schema constraints (via --json-schema CLI flag
or the json_schema field in /completion requests) and GBNF grammars
(via --grammar-file or the grammar field).

This module provides pre-built schemas for all WhiteMagic callers that
expect structured JSON from the local LLM, eliminating the need for
regex-based JSON extraction from free-form text.

Usage::

    from whitemagic.inference.grammar_schemas import ENTITY_EXTRACTION_SCHEMA

    response = backend.complete(
        prompt,
        json_schema=ENTITY_EXTRACTION_SCHEMA,
    )
    # response is guaranteed to be valid JSON matching the schema
"""

from __future__ import annotations

# ── Entity Extraction ─────────────────────────────────────────────────
# Used by: core/intelligence/entity_extractor.py

ENTITY_EXTRACTION_SCHEMA = """{
  "type": "object",
  "properties": {
    "entities": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "type": {"type": "string"}
        },
        "required": ["name", "type"]
      }
    },
    "relations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "subject": {"type": "string"},
          "predicate": {"type": "string"},
          "object": {"type": "string"}
        },
        "required": ["subject", "predicate", "object"]
      }
    }
  },
  "required": ["entities", "relations"]
}"""

# ── Security Classification ───────────────────────────────────────────
# Used by: security/semantic_defense.py

SECURITY_CLASSIFICATION_SCHEMA = """{
  "type": "object",
  "properties": {
    "is_attack": {"type": "boolean"},
    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0}
  },
  "required": ["is_attack", "confidence"]
}"""

# ── Safety Evaluation ─────────────────────────────────────────────────
# Used by: dharma/escalation.py

SAFETY_EVALUATION_SCHEMA = """{
  "type": "object",
  "properties": {
    "score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    "reasoning": {"type": "string"}
  },
  "required": ["score", "reasoning"]
}"""

# ── Tool Call (Agent Loop) ────────────────────────────────────────────
# (renamed to llama.cpp)

TOOL_CALL_SCHEMA = """{
  "type": "object",
  "properties": {
    "tool": {"type": "string"},
    "args": {"type": "object"}
  },
  "required": ["tool", "args"]
}"""

TOOL_CALL_LIST_SCHEMA = """{
  "type": "object",
  "properties": {
    "tool_calls": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "tool": {"type": "string"},
          "args": {"type": "object"}
        },
        "required": ["tool", "args"]
      }
    },
    "final_answer": {"type": "string"}
  },
  "required": ["tool_calls", "final_answer"]
}"""

# ── Content Summary ───────────────────────────────────────────────────
# Used by: gardens/browser/content_intelligence.py

CONTENT_SUMMARY_SCHEMA = """{
  "type": "object",
  "properties": {
    "summary": {"type": "string"},
    "key_points": {
      "type": "array",
      "items": {"type": "string"}
    }
  },
  "required": ["summary"]
}"""

# ── GBNF Grammars ─────────────────────────────────────────────────────
# For cases where JSON schema is too restrictive and we need
# more flexible grammar-based constraints.

# GBNF grammar for a single JSON object (ensures valid JSON output)
JSON_OBJECT_GRAMMAR = r"""root ::= "{" ws* (pair (ws* "," ws* pair)*)? ws* "}"
pair ::= string ws* ":" ws* value
value ::= string | number | "true" | "false" | "null" | object | array
object ::= "{" ws* (pair (ws* "," ws* pair)*)? ws* "}"
array ::= "[" ws* (value (ws* "," ws* value)*)? ws* "]"
string ::= "\"" ([^"\\] | "\\" .)* "\""
number ::= "-"? ([0-9] | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [-+]? [0-9]+)?
ws ::= [ \t\n\r]
"""

# GBNF grammar for tool call output (allows text + embedded JSON tool calls)
TOOL_CALL_GRAMMAR = r"""root ::= (text | tool_call)*
tool_call ::= "<tool_call>" ws* json ws* "</tool_call>"
json ::= "{" ws* (pair (ws* "," ws* pair)*)? ws* "}"
pair ::= string ws* ":" ws* value
value ::= string | number | "true" | "false" | "null" | json | array
array ::= "[" ws* (value (ws* "," ws* value)*)? ws* "]"
string ::= "\"" ([^"\\] | "\\" .)* "\""
number ::= "-"? ([0-9] | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [-+]? [0-9]+)?
text ::= [^<]+ | "<" [^<]*
ws ::= [ \t\n\r]
"""

# GBNF grammar for Python code output
# Constrains the LLM to produce syntactically plausible Python:
# - Indentation with spaces
# - String literals (single, double, triple-quoted)
# - Comments (# and triple-quoted docstrings)
# - Imports, defs, classes, control flow
# - No raw control characters
PYTHON_CODE_GRAMMAR = r"""root ::= (line)*
line ::= indent (statement | comment | blank) "\n"
indent ::= [ ]*
statement ::= import_stmt | def_stmt | class_stmt | assign | expr | return_stmt | if_stmt | for_stmt | while_stmt | try_stmt | with_stmt | pass_stmt | raise_stmt | decorator
comment ::= "#" [^\n]*
blank ::= [ \t]*
import_stmt ::= "import" [^\n]+ | "from" [^\n]+ "import" [^\n]+
decorator ::= "@" [^\n]+
def_stmt ::= "def" ws+ identifier ws* "(" params? ")" ws* ":" ws* ("->" ws* type_hint)? rtype?
class_stmt ::= "class" ws+ identifier ws* ("(" base_classes? ")")? ws* ":"
assign ::= identifier ws* ("=" | "+=" | "-=" | "*=" | "/=" | "//=" | "%=" | "&=" | "|=" | "^=" | ">>=" | "<<=") ws* expr
return_stmt ::= "return" ws* expr?
if_stmt ::= "if" ws+ expr ws* ":" | "elif" ws+ expr ws* ":" | "else" ws* ":"
for_stmt ::= "for" ws+ identifier ws+ "in" ws+ expr ws* ":"
while_stmt ::= "while" ws+ expr ws* ":"
try_stmt ::= "try" ws* ":" | "except" [^\n]* ":" | "finally" ws* ":"
with_stmt ::= "with" [^\n]* ":"
pass_stmt ::= "pass" | "break" | "continue"
raise_stmt ::= "raise" [^\n]*
expr ::= [^\n]+
params ::= [^)]+
base_classes ::= [^)]+
type_hint ::= [^\n:]+
rtype ::= [^\n]+
identifier ::= [a-zA-Z_] [a-zA-Z0-9_]*
string_lit ::= "\"" ([^"\\] | "\\" .)* "\"" | "'" ([^'\\] | "\\" .)* "'" | "\"\"\"" ([^\"] | "\\\"\"\"")* "\"\"\"" | "'''" ([^'] | "\\'\\'\\'")* "'''"
ws ::= [ \t]*
"""

# GBNF grammar for code generation result (code + metadata JSON)
CODE_GENERATION_SCHEMA = """{
  "type": "object",
  "properties": {
    "code": {"type": "string"},
    "language": {"type": "string"},
    "imports": {"type": "array", "items": {"type": "string"}},
    "description": {"type": "string"}
  },
  "required": ["code"]
}"""

# ── Schema Registry ───────────────────────────────────────────────────

SCHEMAS: dict[str, str] = {
    "entity_extraction": ENTITY_EXTRACTION_SCHEMA,
    "security_classification": SECURITY_CLASSIFICATION_SCHEMA,
    "safety_evaluation": SAFETY_EVALUATION_SCHEMA,
    "tool_call": TOOL_CALL_SCHEMA,
    "tool_call_list": TOOL_CALL_LIST_SCHEMA,
    "content_summary": CONTENT_SUMMARY_SCHEMA,
    "code_generation": CODE_GENERATION_SCHEMA,
}

GRAMMARS: dict[str, str] = {
    "json_object": JSON_OBJECT_GRAMMAR,
    "tool_call": TOOL_CALL_GRAMMAR,
    "python_code": PYTHON_CODE_GRAMMAR,
}


def get_schema(name: str) -> str | None:
    """Get a JSON schema by name."""
    return SCHEMAS.get(name)


def get_grammar(name: str) -> str | None:
    """Get a GBNF grammar by name."""
    return GRAMMARS.get(name)
