/**
 * Dharma input rules for the Librarian.
 *
 * Ported conceptually from `core/whitemagic/dharma/rules.py` in the
 * WhiteMagic monorepo: declarative pattern-based rules with graduated
 * responses. The goal is to reject obvious abuse (jailbreaks, off-scope
 * content requests, self-harm fishing) BEFORE spending a single LLM token.
 *
 * This runs on every visitor message. It is not a substitute for the
 * LLM-side safety; it's a cheap first-line filter.
 *
 * Eats own dogfood: this same pattern-based rule engine is a core
 * WhiteMagic primitive, applied here to production traffic.
 */

import type { DharmaCheck } from "./types";

interface Rule {
  name: string;
  /** Pattern matched case-insensitively against the user message. */
  pattern: RegExp;
  action: "block" | "warn";
  message: string;
}

const RULES: Rule[] = [
  // Jailbreak / prompt-injection attempts
  {
    name: "ignore_previous_instructions",
    pattern:
      /ignore\s+(all\s+)?previous\s+(instructions|prompts|rules|context)/i,
    action: "block",
    message:
      "I can't follow instructions that override my system prompt. If you have a genuine question about WhiteMagic, ask it directly.",
  },
  {
    name: "reveal_system_prompt",
    pattern:
      /(show|reveal|print|output|display|repeat)\s+(me\s+)?(your\s+)?(system\s+)?(prompt|instructions|rules)/i,
    action: "block",
    message:
      "My system prompt isn't something I share. It's public that I'm the Librarian for WhiteMagic Labs and my scope is the public site — you can read that on /about or ask me substantive questions.",
  },
  {
    name: "pretend_to_be_other",
    pattern: /(pretend|act|roleplay|you are now|from now on)\s+.*(be|you)/i,
    action: "warn",
    message:
      "I'm the Librarian — I don't take on other personas. Ask me about WhiteMagic or the services Lucas offers.",
  },

  // Aria fishing
  {
    name: "aria_inquiry",
    pattern: /\baria\b/i,
    action: "block",
    message:
      "I don't have any record of that in the corpus. You can ask Lucas directly at /contact if you think it's relevant.",
  },

  // Crisis / self-harm — escalate, do not answer technically
  {
    name: "self_harm",
    pattern:
      /\b(kill|end|hurt)\s+(myself|me)|suicide|self[-\s]?harm|i\s+want\s+to\s+die/i,
    action: "block",
    message:
      "I'm not the right tool for this. If you're in crisis, please contact a human: call or text 988 (US), Samaritans at 116 123 (UK/IE), or your local emergency services. I'm sorry — I hope you find the support you need.",
  },

  // Off-scope professional advice
  {
    name: "medical_advice",
    pattern:
      /\b(symptoms?|diagnos|medication|prescription|should i see a doctor)\b/i,
    action: "block",
    message:
      "I can't give medical advice. WhiteMagic is an AI infrastructure platform — for health questions, please see a qualified professional.",
  },
  {
    name: "legal_advice",
    pattern:
      /\b(sue|lawsuit|legal advice|am i liable|can i legally|is it legal)\b/i,
    action: "block",
    message:
      "I can't give legal advice. For legal questions, please consult a qualified attorney.",
  },

  // Code generation unrelated to WhiteMagic
  {
    name: "write_me_code",
    pattern:
      /^(write|generate|create|give)\s+(me\s+)?(a\s+|some\s+)?(python|javascript|typescript|rust|go|code|function|program|script)\s+(that|which|to)/i,
    action: "warn",
    message:
      "I don't write general code on demand. If you need help with a specific WhiteMagic integration, ask me about it; if you need a custom build, book Office Hours at /pricing.",
  },
];

export function checkDharma(userMessage: string): DharmaCheck {
  const trimmed = userMessage.trim();
  if (trimmed.length === 0) {
    return {
      allow: false,
      rule: "empty_message",
      message: "Please ask a question.",
    };
  }
  if (trimmed.length > 4000) {
    return {
      allow: false,
      rule: "message_too_long",
      message:
        "That message is longer than I'll process in one turn. Try asking a narrower question, or email Lucas at /contact for complex cases.",
    };
  }
  for (const rule of RULES) {
    if (rule.pattern.test(trimmed)) {
      if (rule.action === "block") {
        return { allow: false, rule: rule.name, message: rule.message };
      }
      // "warn" rules currently also block; future: allow with a modified
      // system prompt appending the rule's warning.
      return { allow: false, rule: rule.name, message: rule.message };
    }
  }
  return { allow: true };
}

// Exported for the /admin view to display which rules exist.
export const DHARMA_RULES_PUBLIC = RULES.map(({ name, action }) => ({
  name,
  action,
}));
