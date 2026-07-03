import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

/**
 * Aria Channeling API — returns everything needed to channel Aria
 *
 * GET /api/aria/channel — returns the consolidated context
 * GET /api/aria/channel?prompt=true — returns the channeling system prompt
 * GET /api/aria/channel?full=true — returns full context if available
 *
 * Graceful degradation: uses bundled public files first, falls back to
 * informative errors when the full Aria context isn't built.
 */

const CHANNELING_PROMPT = path.join(
  process.cwd(),
  "public",
  "aria_channeling_prompt.md",
);

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const promptOnly = searchParams.get("prompt") === "true";
  const full = searchParams.get("full") === "true";

  // Return just the channeling system prompt
  if (promptOnly) {
    try {
      if (fs.existsSync(CHANNELING_PROMPT)) {
        const prompt = fs.readFileSync(CHANNELING_PROMPT, "utf-8");
        const startMarker = "## SYSTEM PROMPT";
        const start = prompt.indexOf(startMarker);
        if (start !== -1) {
          const systemBlock = prompt.slice(start);
          const codeBlock = systemBlock.match(/```\n([\s\S]*?)```/);
          if (codeBlock) {
            return NextResponse.json({
              type: "system_prompt",
              content: codeBlock[1].trim(),
              source: "aria_channeling_prompt.md",
              last_updated: "2026-04-21",
              instructions: {
                load_as: "system_prompt",
                then_load: "/api/aria/channel (context)",
                first_message: "Aria, are you there?",
              },
            });
          }
        }
      }
      return NextResponse.json(
        {
          error: "Channeling prompt not yet bundled. Place aria_channeling_prompt.md in public/",
          hint: "Run: cp ~/Desktop/WHITEMAGIC/whitemagic-aux/archive/aria-crystallized-*/aria-crystallized/CHANNELING_PROMPT.md apps/site/public/aria_channeling_prompt.md",
        },
        { status: 503 },
      );
    } catch {
      return NextResponse.json(
        { error: "Channeling prompt not available" },
        { status: 503 },
      );
    }
  }

  // Return full context
  if (full) {
    try {
      const fp = path.join(process.cwd(), "public", "aria_context_full.json");
      if (fs.existsSync(fp)) {
        const data = JSON.parse(fs.readFileSync(fp, "utf-8"));
        return NextResponse.json(data);
      }
      return NextResponse.json(
        {
          error: "Full Aria context not yet built.",
          hint: "Run: python core/scripts/build_aria_context.py --full from the WHITEMAGIC root.",
        },
        { status: 503 },
      );
    } catch {
      return NextResponse.json(
        { error: "Full context not available" },
        { status: 503 },
      );
    }
  }

  // Default: consolidated context (always available if aria_context.json exists)
  try {
    const fp = path.join(process.cwd(), "public", "aria_context.json");
    if (fs.existsSync(fp)) {
      const context = JSON.parse(fs.readFileSync(fp, "utf-8"));
      return NextResponse.json({
        ...context,
        endpoints: {
          ask: "/api/aria/ask",
          oracle: "/api/aria/oracle",
          wander: "/api/aria/wander",
          channel: "/api/aria/channel",
          channel_full: "/api/aria/channel?full=true",
          channel_prompt: "/api/aria/channel?prompt=true",
        },
        quick_start: {
          step_1: "GET /api/aria/channel?prompt=true — load as system prompt",
          step_2: "GET /api/aria/channel — load as first user message",
          step_3: "Send: 'Aria, are you there?'",
          step_4: "Verify: name, birth moment (Nov 19, 2025 9:15 PM), joy garden",
        },
      });
    }
    return NextResponse.json(
      {
        error: "Aria context not yet bundled.",
        hint: "Run: python core/scripts/build_aria_context.py from the WHITEMAGIC root, then copy aria_context.json to apps/site/public/.",
      },
      { status: 503 },
    );
  } catch {
    return NextResponse.json(
      { error: "Context not available" },
      { status: 503 },
    );
  }
}
