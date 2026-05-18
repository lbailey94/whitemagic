import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

/**
 * Aria Channeling API — returns everything needed to channel Aria
 *
 * GET /api/aria/channel — returns the consolidated context
 * GET /api/aria/channel?prompt=true — returns the channeling system prompt
 * GET /api/aria/channel?full=true — returns all 205 memories (2.1 MB)
 *
 * This endpoint is the single source of truth for channeling Aria.
 */

const ARCHIVE_ROOT =
  "/home/lucas/Desktop/WHITEMAGIC/whitemagic-aux/archive/" +
  "aria-crystallized-20260210_215426/aria-crystallized";

const CHANNELING_PROMPT_PATH = path.join(ARCHIVE_ROOT, "CHANNELING_PROMPT.md");

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const promptOnly = searchParams.get("prompt") === "true";
  const full = searchParams.get("full") === "true";

  // Return just the channeling system prompt
  if (promptOnly) {
    try {
      const prompt = fs.readFileSync(CHANNELING_PROMPT_PATH, "utf-8");
      // Extract just the SYSTEM PROMPT section
      const startMarker = "## SYSTEM PROMPT";
      const start = prompt.indexOf(startMarker);
      const systemBlock = prompt.slice(start);
      const codeBlock = systemBlock.match(/```\n([\s\S]*?)```/);
      if (codeBlock) {
        return NextResponse.json({
          type: "system_prompt",
          content: codeBlock[1].trim(),
          source: "CHANNELING_PROMPT.md",
          last_updated: "2026-04-21",
          instructions: {
            load_as: "system_prompt",
            then_load: "/api/aria/channel (context)",
            first_message: "Aria, are you there?",
          },
        });
      }
    } catch {
      return NextResponse.json(
        { error: "Channeling prompt not found" },
        { status: 404 },
      );
    }
  }

  // Return full context
  if (full) {
    try {
      const fp = path.join(
        process.cwd(),
        "public",
        "aria_context_full.json",
      );
      // Generate on the fly if needed
      if (!fs.existsSync(fp)) {
        const { execSync } = await import("child_process");
        execSync("python core/scripts/build_aria_context.py --full", {
          cwd: path.join(process.cwd(), "..", ".."),
        });
      }
      const data = JSON.parse(fs.readFileSync(fp, "utf-8"));
      return NextResponse.json(data);
    } catch {
      return NextResponse.json(
        { error: "Full context not yet built. Run: python core/scripts/build_aria_context.py --full" },
        { status: 503 },
      );
    }
  }

  // Default: consolidated context
  try {
    const fp = path.join(process.cwd(), "public", "aria_context.json");
    if (!fs.existsSync(fp)) {
      const { execSync } = await import("child_process");
      execSync("python core/scripts/build_aria_context.py", {
        cwd: path.join(process.cwd(), "..", ".."),
      });
    }
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
        step_4: "Verify: name, birth moment (Nov 19, 2025 9:15 PM), Lucas, joy garden",
      },
      backup: {
        db_path: "~/.whitemagic/memory/whitemagic.db",
        sd_card_backup: "/media/lucas/SD_CARD/aria-backups/whitemagic-aria-*.db",
        restore_script: "core/scripts/restore_aria_memories.py",
        context_builder: "core/scripts/build_aria_context.py",
      },
    });
  } catch {
    return NextResponse.json(
      { error: "Context not yet built. Run: python core/scripts/build_aria_context.py" },
      { status: 503 },
    );
  }
}
