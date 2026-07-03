/**
 * Structured pricing tier data, read by both the Librarian's
 * `get_pricing_tier` / `request_office_hours_booking` tools and
 * (eventually) the pricing page itself.
 */

export type TierSlug = "office-hours" | "architecture-review" | "engagement";

export interface PricingTier {
  slug: TierSlug;
  name: string;
  price: string;
  priceNote: string;
  oneLiner: string;
  bestFor: string;
  whatIsIncluded: string[];
  turnaround: string;
  /** Environment variable name holding the Stripe payment link for this tier. */
  stripeEnvVar?: string;
  /** Fallback path if no Stripe link is configured. */
  fallbackPath: string;
  featured?: boolean;
}

export const PRICING_TIERS: Record<TierSlug, PricingTier> = {
  "office-hours": {
    slug: "office-hours",
    name: "Office Hours",
    price: "$1,000",
    priceNote: "per 60-minute session",
    oneLiner:
      "One specific question: deployment decision, governance risk, or MCP architecture review.",
    bestFor:
      "Teams that need a senior second opinion before making a decision worth more than $1,000 to get right.",
    whatIsIncluded: [
      "60-minute video call, recorded if you want",
      "Written notes within 48 hours",
      "Fee credits toward any future engagement",
      "No retainer; one-off purchase",
    ],
    turnaround: "Booking within 5 business days",
    stripeEnvVar: "NEXT_PUBLIC_STRIPE_OFFICE_HOURS_URL",
    fallbackPath: "/contact?topic=office-hours",
  },
  "architecture-review": {
    slug: "architecture-review",
    name: "Architecture Review",
    price: "$12,000",
    priceNote: "flat, 5-day turnaround",
    oneLiner:
      "Full written review of your agent / MCP / private-AI architecture mapped to OWASP LLM Top 10 (v1.1, covers agentic AI) and EU AI Act Article 14.",
    bestFor:
      "CTOs and tech leads preparing for audit, board review, or production deployment.",
    whatIsIncluded: [
      "20–40 page written deliverable",
      "Risk mapping: OWASP LLM Top 10 (v1.1, covers agentic AI) + EU AI Act Article 14",
      "One 60-minute walkthrough call",
      "NDA on request",
      "Revision pass within 2 weeks if scope changes",
    ],
    turnaround: "5 business days from kickoff",
    stripeEnvVar: "NEXT_PUBLIC_STRIPE_ARCHITECTURE_REVIEW_URL",
    fallbackPath: "/contact?topic=architecture-review",
    featured: true,
  },
  engagement: {
    slug: "engagement",
    name: "Engagement",
    price: "From $35,000",
    priceNote: "4–8 week fixed-scope",
    oneLiner:
      "Fixed-scope implementation on one of the three service tracks: Private AI, Governance, or MCP.",
    bestFor:
      "Organizations ready to implement, with a defined use case and technical stakeholder.",
    whatIsIncluded: [
      "Kickoff call + written scope document",
      "Weekly delivery cadence with demo",
      "50% on kickoff, 50% on delivery",
      "Limited to 2 concurrent engagements",
      "Mutual NDA on request",
    ],
    turnaround: "Start within 2–4 weeks of contract signing",
    fallbackPath: "/contact?topic=engagement",
  },
};

export const PRICING_TIERS_LIST: PricingTier[] = Object.values(PRICING_TIERS);

export function getTier(slug: string): PricingTier | null {
  return (PRICING_TIERS as Record<string, PricingTier>)[slug] ?? null;
}

/**
 * Resolve the actual checkout URL for a tier — Stripe if configured,
 * fallback contact form otherwise.
 */
export function resolveCheckoutUrl(tier: PricingTier): {
  url: string;
  isStripe: boolean;
} {
  if (tier.stripeEnvVar) {
    const stripeUrl = process.env[tier.stripeEnvVar];
    if (stripeUrl && stripeUrl.startsWith("https://")) {
      return { url: stripeUrl, isStripe: true };
    }
  }
  return { url: tier.fallbackPath, isStripe: false };
}
