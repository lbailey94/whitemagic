/**
 * WIP mode — a build-time flag that swaps public-facing content for
 * abstract/poetic language while the site is being rewritten.
 *
 * Why this exists: between v23.0-alpha.1 (substrate rehydration shipped)
 * and the full v23.0 launch (PWA + auto-detection + gateway UX), the
 * site is in a vulnerable state. Specific pricing, validation claims,
 * contact info, and personal details shouldn't be on a public URL yet.
 *
 * Set NEXT_PUBLIC_WIP_MODE=1 in Vercel to enable WIP mode. Same code,
 * different copy. The technical surface (bridge catalog, A2A, librarian)
 * is unaffected — those are *good* for A2A peers and curious devs to find.
 *
 * See docs/SITE_WIP_MODE.md for the rationale and the toggle.
 */

export const WIP_MODE = true;

/**
 * Scramble mode — when true (default in WIP mode), the long-form copy
 * on the site is replaced with Unicode block glyphs so the text is
 * visually illegible. The original text is preserved in the DOM
 * (data-original) for DevTools inspection and SEO, but the rendered
 * glyphs look like a code block.
 *
 * Independent toggle: set NEXT_PUBLIC_WIP_SCRAMBLE=0 to keep WIP
 * mode but show readable text.
 */
export const WIP_SCRAMBLE =
  WIP_MODE && process.env.NEXT_PUBLIC_WIP_SCRAMBLE !== "0";

/**
 * Hero copy. The WIP version is intentionally abstract / invitational.
 * The production version (used when WIP_MODE is false) preserves the
 * current value prop.
 */
export const WIP_HERO = {
  eyebrow: WIP_MODE ? "Work in Progress" : "Cognitive operating system for AI agents",
  title: WIP_MODE
    ? "A door is opening."
    : "Other memory systems store data. WhiteMagic gives AI a mind.",
  lede: WIP_MODE
    ? "A local-first memory and reasoning substrate. Permanent. Private. Yours. The door is being framed; the architecture is being written; the door will be open soon."
    : "614 callable tools across 28 Gana meta-tools. 5D holographic memory with 10-galaxy taxonomy. Citta stream for continuous consciousness, emotional steering, self-directed attention. Ethical governance via Dharma rules engine. Open source, MIT licensed.",
  primaryCta: WIP_MODE
    ? { label: "Subscribe to the beta", href: "/subscribe" }
    : { label: "Get started free", href: "/mcp-bridge" },
  secondaryCta: WIP_MODE
    ? { label: "Talk to Aria", href: "/chat" }
    : { label: "Read the docs", href: "/open-source" },
};

/**
 * Site-wide banner shown when WIP_MODE is true. Returns null when not
 * in WIP mode (so the layout can skip rendering entirely).
 */
export const WIP_BANNER = WIP_MODE
  ? {
      tone: "info" as const,
      message:
        "Work in Progress. This site is being rewritten. Subscribe to be notified when the public beta opens.",
      cta: { label: "Subscribe to the beta", href: "/subscribe" },
    }
  : null;

/**
 * Sections of the site that should be hidden in WIP mode. The URLs
 * still resolve (we don't 404 the A2A peers and curious devs), but
 * the nav doesn't surface them and the routes themselves render a
 * WIP placeholder instead of the production content.
 */
export const WIP_HIDDEN_NAV = WIP_MODE
  ? new Set([
      "/services",
      "/services/private-ai-deployment",
      "/services/agent-governance",
      "/services/mcp-engineering",
      "/pricing",
      "/fund",
      "/contact",
      "/admin",
    ])
  : new Set<string>();

/**
 * The footer copy in WIP mode. Replaces specific contact paths with
 * a single subscribe CTA, removes the personal email, and obscures
 * any specific claims about validation counts, pricing tiers, or
 * forecast accuracy.
 */
export const WIP_FOOTER = {
  contactLabel: WIP_MODE ? "Subscribe to the beta" : "Contact",
  contactHref: WIP_MODE ? "/subscribe" : "/contact",
  blurb: WIP_MODE
    ? "A local-first cognitive substrate being built in the open. Subscribe to the beta to be notified when the public beta opens."
    : "Cognitive substrate for agentic AI. MIT licensed, open source.",
  showEmail: !WIP_MODE,
  showSpecificClaims: !WIP_MODE,
};

/**
 * For A2A peers + technical readers. Even in WIP mode, the
 * technical surface (bridge catalog, agent card, librarian demo) is
 * useful and should be discoverable.
 */
export const WIP_TECHNICAL_ROUTES_VISIBLE = true;
